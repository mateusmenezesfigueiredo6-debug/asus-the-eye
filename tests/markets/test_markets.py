# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes dos mercados preditivos: as regras que impedem o número de mentir.

Onde dá, os testes usam os números reais do classificador — em especial o
``voto_legislativo``, cujo Brier de vitrine (0,003293) é *pior* que um palpite
constante (0,001671). Se o módulo esconder isso, um teste quebra.
"""

from __future__ import annotations

import pytest

from asus_theye.markets import (
    MarketClaim,
    MarketClaimError,
    ResolutionError,
    ScoringError,
    base_rate,
    brier_score,
    load_areas,
    load_classifier,
    make_claim,
    record_comparator,
    resolve,
    skill_score,
)

# Fontes nomeadas de verdade, lidas do classificador.
JUROS = "juros"  # fonte: api.bcb.gov.br (Selic)
ENERGIA = "energia"  # fonte: "a declarar" — não liquida
VOTO = "voto-legislativo"  # fonte: dadosabertos.camara.leg.br


def a_claim(area: str = JUROS, probability: float = 0.5) -> object:
    return make_claim(
        claim_id="mkt-0001",
        market_area_id=area,
        question="A Selic sobe na próxima reunião do Copom?",
        deadline="2026-12-31",
        probability=probability,
        created_at="2026-08-17T00:00:00Z",
    )


# --------------------------------------------------------------- claim


def test_area_desconhecida_levanta() -> None:
    with pytest.raises(MarketClaimError, match="desconhecido"):
        make_claim(
            claim_id="x",
            market_area_id="nao-existe",
            question="?",
            deadline="2026-12-31",
            probability=0.5,
        )


def test_fonte_de_resolucao_vem_da_area() -> None:
    claim = a_claim(JUROS)
    assert claim.resolution_source == "api.bcb.gov.br (Selic)"
    assert claim.resolvable is True


def test_area_a_declarar_gera_mas_nao_resolve() -> None:
    """energia existe (estado aberto) mas a fonte é 'a declarar': nasce não-liquidável."""
    claim = a_claim(ENERGIA)
    assert claim.resolution_source == "a declarar"
    assert claim.resolvable is False


@pytest.mark.parametrize("bad", [-0.1, 1.1, "0.5", True])
def test_probabilidade_fora_de_intervalo_levanta(bad: object) -> None:
    with pytest.raises(MarketClaimError):
        make_claim(claim_id="x", market_area_id=JUROS, question="?", deadline="2026-12-31", probability=bad)  # type: ignore[arg-type]


def test_limiar_de_maxima_incerteza_e_marcado() -> None:
    assert a_claim(JUROS, probability=0.5).max_uncertainty is True
    assert a_claim(JUROS, probability=0.72).max_uncertainty is False


def test_deadline_anterior_a_criacao_levanta() -> None:
    with pytest.raises(MarketClaimError, match="anterior"):
        make_claim(
            claim_id="x",
            market_area_id=JUROS,
            question="?",
            deadline="2026-08-16",
            probability=0.5,
            created_at="2026-08-17T00:00:00Z",
        )


def test_classificador_bate_com_o_arquivo_de_dominio() -> None:
    """O invariante é a COERÊNCIA, não a contagem.

    Antes isto cravava ``== 10`` e ficava vermelho a cada área nova — número
    mágico não é invariante, é dívida. O que de fato não pode acontecer é o
    classificador divergir do arquivo que o alimenta: ``area_count`` mentindo
    sobre quantas áreas existem, ou duas áreas com o mesmo id se engolindo no
    dicionário. É isso que se testa aqui.
    """
    areas = load_areas()
    bruto = load_classifier()
    assert len(areas) == len(bruto["areas"]), "id de área duplicado engoliu uma entrada"
    assert len(areas) == bruto["area_count"], (
        f"area_count={bruto['area_count']} mente: o arquivo tem {len(areas)} áreas"
    )
    assert {"juros", "cambio", "cripto", "voto-legislativo"} <= set(areas)


# --------------------------------------------------------------- resolution


def test_resolve_contra_a_fonte_declarada() -> None:
    claim = a_claim(JUROS)
    res = resolve(claim, outcome=1, source="api.bcb.gov.br (Selic)", resolved_at="2026-12-31T12:00:00Z")
    assert res.outcome == 1
    assert res.resolution_source == "api.bcb.gov.br (Selic)"


@pytest.mark.parametrize("bad", [2, -1, True, 0.5])
def test_outcome_nao_binario_levanta(bad: object) -> None:
    with pytest.raises(ResolutionError, match="0 ou 1"):
        resolve(a_claim(JUROS), outcome=bad, source="api.bcb.gov.br (Selic)")  # type: ignore[arg-type]


def test_kalshi_nunca_resolve() -> None:
    with pytest.raises(ResolutionError, match="comparador"):
        resolve(a_claim(JUROS), outcome=1, source="Kalshi")


def test_kalshi_bloqueada_como_fonte_de_claim() -> None:
    """Defesa em profundidade: mesmo que o classificador registre Kalshi, criar recusa."""
    hostil = {"kx": {"market_area_id": "kx", "fonte_resolucao": "Kalshi"}}
    with pytest.raises(MarketClaimError, match="proibida|comparador"):
        make_claim(
            claim_id="x",
            market_area_id="kx",
            question="?",
            deadline="2026-12-31",
            probability=0.5,
            areas=hostil,
        )


def test_claim_com_fonte_kalshi_nasce_nao_resolvivel() -> None:
    """Uma afirmação que de algum modo carregue Kalshi como fonte não é liquidável."""
    claim = MarketClaim(
        claim_id="x",
        market_area_id="kx",
        question="?",
        deadline="2026-12-31",
        probability=0.5,
        resolution_source="Kalshi",
        created_at="2026-08-17T00:00:00Z",
        max_uncertainty=True,
    )
    assert claim.resolvable is False


def test_fonte_errada_levanta() -> None:
    with pytest.raises(ResolutionError, match="fonte declarada"):
        resolve(a_claim(JUROS), outcome=1, source="algum-blog.com")


def test_area_sem_fonte_nao_liquida() -> None:
    with pytest.raises(ResolutionError, match="não liquida|nomeada"):
        resolve(a_claim(ENERGIA), outcome=1, source="a declarar")


def test_comparador_registra_divergencia_mas_nao_resolve() -> None:
    claim = a_claim(JUROS, probability=0.30)
    div = record_comparator(claim, comparator_price=0.75, recorded_at="2026-09-01T00:00:00Z")
    assert div.comparator == "Kalshi"
    assert div.divergence == pytest.approx(0.45)
    assert "comparador" in div.note


@pytest.mark.parametrize("bad", [-0.1, 1.5, True])
def test_preco_comparador_fora_de_intervalo_levanta(bad: object) -> None:
    with pytest.raises(ResolutionError):
        record_comparator(a_claim(JUROS), comparator_price=bad)  # type: ignore[arg-type]


# --------------------------------------------------------------- scoring


def test_brier_vazio_e_none_nunca_zero() -> None:
    assert brier_score([]) is None
    assert base_rate([]) is None


@pytest.mark.parametrize("pares", [[(1.7, 1)], [(-0.1, 0)], [("x", 1)], [(True, 1)]])
def test_brier_rejeita_probabilidade_invalida(pares: list) -> None:
    with pytest.raises(ScoringError):
        brier_score(pares)


@pytest.mark.parametrize("pares", [[(0.5, 2)], [(0.5, -1)], [(0.5, True)]])
def test_brier_rejeita_desfecho_nao_binario(pares: list) -> None:
    with pytest.raises(ScoringError, match="0 ou 1"):
        brier_score(pares)


@pytest.mark.parametrize("outcomes", [[2], [True], [0, 3]])
def test_base_rate_rejeita_desfecho_nao_binario(outcomes: list) -> None:
    with pytest.raises(ScoringError, match="0 ou 1"):
        base_rate(outcomes)


def test_baseline_quase_perfeito_nao_e_tratado_como_perfeito() -> None:
    """Brier verdadeiro em (0, 5e-7] arredonda a 0, mas NÃO é perfeito: skill é real."""
    resultado = skill_score([(0.0, 0), (0.0, 0)], window="2 contratos", baseline_probability=0.0005)
    # baseline Brier verdadeiro = 0.0005^2 = 2.5e-7 (não zero): modelo vence de verdade
    assert resultado["skill_score"] == pytest.approx(1.0)
    assert resultado["baseline_beats_model"] is False
    assert resultado["limitations"] == [], "não há ressalva falsa de 'já perfeito'"


@pytest.mark.parametrize(
    "pairs,esperado",
    [
        ([(1.0, 1)], 0.0),
        ([(0.0, 1)], 1.0),
        ([(0.5, 1), (0.5, 0)], 0.25),
    ],
)
def test_brier_valores_conhecidos(pairs: list, esperado: float) -> None:
    assert brier_score(pairs) == pytest.approx(esperado)


def test_skill_exige_janela() -> None:
    with pytest.raises(ScoringError, match="window|janela"):
        skill_score([(0.9, 1)], window="")


def test_skill_sem_pares_levanta() -> None:
    with pytest.raises(ScoringError, match="liquidados"):
        skill_score([], window="qualquer")


def test_voto_legislativo_baseline_vence_o_modelo() -> None:
    """O caso real: 40 contratos, todos 1; modelo pior que o palpite constante."""
    pairs = [(0.942615, 1)] * 40  # Brier do modelo ~ 0.003293
    resultado = skill_score(
        pairs,
        window="40 contratos, votação 2637721-10 (14/07/2026), 7 partidos",
        baseline_probability=0.959126,  # taxa histórica de seguimento partidário
    )
    assert resultado["model_brier"] == pytest.approx(0.003293, abs=1e-6)
    assert resultado["baseline_brier"] == pytest.approx(0.001671, abs=1e-6)
    assert resultado["baseline_beats_model"] is True
    assert resultado["skill_score"] <= 0
    assert resultado["window"].startswith("40 contratos")
    assert resultado["limitations"], "quando o baseline vence, a ressalva é publicada"


def test_modelo_com_skill_genuina() -> None:
    pairs = [(0.9, 1), (0.8, 1), (0.2, 0)]
    resultado = skill_score(pairs, window="3 contratos, exemplo")
    assert resultado["baseline_beats_model"] is False
    assert resultado["skill_score"] > 0
    assert resultado["baseline_probability"] == pytest.approx(0.666667, abs=1e-5)


def test_baseline_perfeito_deixa_skill_indefinida() -> None:
    """Todos os desfechos 1 e baseline em 1,0: Brier do baseline é 0 — não se divide."""
    pairs = [(0.7, 1), (0.9, 1)]
    resultado = skill_score(pairs, window="2 contratos", baseline_probability=1.0)
    assert resultado["baseline_brier"] == 0.0
    assert resultado["skill_score"] is None
    assert resultado["baseline_beats_model"] is True
    assert resultado["limitations"], "skill indefinida é declarada, não escondida"


@pytest.mark.parametrize("bad", [-0.1, 1.5, True])
def test_baseline_fora_de_intervalo_levanta(bad: object) -> None:
    with pytest.raises(ScoringError, match="baseline"):
        skill_score([(0.5, 1)], window="1 contrato", baseline_probability=bad)  # type: ignore[arg-type]


def test_claim_id_e_pergunta_obrigatorios() -> None:
    with pytest.raises(MarketClaimError, match="claim_id"):
        make_claim(claim_id="  ", market_area_id=JUROS, question="?", deadline="2026-12-31", probability=0.5)
    with pytest.raises(MarketClaimError, match="question|pergunta"):
        make_claim(claim_id="x", market_area_id=JUROS, question="", deadline="2026-12-31", probability=0.5)


def test_deadline_com_formato_invalido_levanta() -> None:
    with pytest.raises(MarketClaimError, match="ISO"):
        make_claim(claim_id="x", market_area_id=JUROS, question="?", deadline="31/12/2026", probability=0.5)


def test_as_dict_serializa_o_ciclo_completo() -> None:
    claim = a_claim(JUROS, probability=0.4)
    d = claim.as_dict()
    assert d["resolvable"] is True and d["market_area_id"] == JUROS
    res = resolve(claim, outcome=0, source="api.bcb.gov.br (Selic)", resolved_at="2026-12-31T00:00:00Z")
    assert res.as_dict()["outcome"] == 0
    div = record_comparator(claim, comparator_price=0.5)
    assert div.as_dict()["comparator"] == "Kalshi"


# ------------------------------------------------------------ determination_date


def test_determinacao_e_distinta_do_resolved_at() -> None:
    """Dois relógios: o do mundo (determination_date) e o do nosso processo."""
    from asus_theye.markets.claim import make_claim
    from asus_theye.markets.resolution import BASE_PRIMEIRA_OBSERVACAO, resolve

    claim = make_claim(
        claim_id="MACRO-01::2026-07",
        market_area_id="macroeconomia",
        question="IPCA de julho >= 0,50%?",
        deadline="2026-07-31",
        probability=0.5,
        created_at="2026-07-01T00:00:00Z",
    )
    r = resolve(
        claim,
        outcome=0,
        source=claim.resolution_source,
        resolved_at="2026-08-17T15:17:37Z",
        determination_date="2026-08-08",
    )
    assert r.determination_date == "2026-08-08"
    assert r.resolved_at.startswith("2026-08-17")
    assert r.determination_date[:10] != r.resolved_at[:10]  # o atraso do processo aparece
    assert r.determination_basis == BASE_PRIMEIRA_OBSERVACAO
    assert r.as_dict()["determination_date"] == "2026-08-08"


def test_base_de_determinacao_invalida_levanta() -> None:
    """Data sem método declarado não entra — a base muda o que a data significa."""
    from asus_theye.markets.claim import make_claim
    from asus_theye.markets.resolution import ResolutionError, resolve

    claim = make_claim(
        claim_id="MACRO-01::2026-07",
        market_area_id="macroeconomia",
        question="IPCA?",
        deadline="2026-07-31",
        probability=0.5,
        created_at="2026-07-01T00:00:00Z",
    )
    with pytest.raises(ResolutionError, match="determination_basis"):
        resolve(claim, outcome=0, source=claim.resolution_source, determination_basis="achismo")


def test_determination_date_malformada_levanta() -> None:
    from asus_theye.markets.claim import make_claim
    from asus_theye.markets.resolution import ResolutionError, resolve

    claim = make_claim(
        claim_id="MACRO-01::2026-07",
        market_area_id="macroeconomia",
        question="IPCA?",
        deadline="2026-07-31",
        probability=0.5,
        created_at="2026-07-01T00:00:00Z",
    )
    with pytest.raises(ResolutionError, match="data ISO"):
        resolve(claim, outcome=0, source=claim.resolution_source, determination_date="17/08/2026")
