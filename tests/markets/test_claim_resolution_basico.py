# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Caminho feliz de claim/resolution — a doutrina que os conectores novos herdam.

Antes dos conectores de F2, fixa-se o contrato básico: uma afirmação válida
herda a fonte da ÁREA (o chamador não escolhe), liquida contra essa fonte e
só ela, e as recusas óbvias levantam em vez de degradar. Datas explícitas em
tudo: nada aqui pode depender do relógio real (é exatamente essa dependência
que derruba test_live/test_sinais_ipca na virada do mês).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from asus_theye.markets.claim import MarketClaimError, make_claim
from asus_theye.markets.resolution import BASE_PRIMEIRA_OBSERVACAO, ResolutionError, resolve

CRIADO = "2026-08-01T00:00:00Z"
PRAZO = "2026-08-31"
FONTE_JUROS = "api.bcb.gov.br (Selic)"  # declarada no classificador para a área "juros"


def _claim_de_juros(probability: float = 0.62):
    return make_claim(
        claim_id="JUROS-TESTE::2026-08",
        market_area_id="juros",
        question="A meta Selic estará em 15,00% a.a. ou mais ao fim de 2026-08?",
        deadline=PRAZO,
        probability=probability,
        created_at=CRIADO,
    )


# ---------------------------------------------------------------- caminho feliz


def test_claim_valido_herda_a_fonte_da_area_e_nasce_resolvivel():
    """A fonte vem do classificador, não do chamador — regra estrutural nº 2."""
    claim = _claim_de_juros()
    assert claim.resolution_source == FONTE_JUROS
    assert claim.resolvable is True
    assert claim.probability == pytest.approx(0.62)
    assert claim.max_uncertainty is False


def test_probabilidade_no_limiar_de_maxima_incerteza_e_marcada():
    """p=0,50 é desenho do gerador, não acaso — a afirmação carrega o aviso."""
    assert _claim_de_juros(probability=0.5).max_uncertainty is True
    assert _claim_de_juros(probability=0.62).max_uncertainty is False


def test_resolver_contra_a_fonte_da_area_produz_o_desfecho_completo():
    """Liquidar contra a fonte declarada devolve a resolução com tudo auditável."""
    claim = _claim_de_juros()
    resolucao = resolve(
        claim,
        outcome=1,
        source=FONTE_JUROS,
        resolved_at="2026-09-01T12:00:00Z",
        determination_date="2026-09-01",
    )
    assert resolucao.claim_id == claim.claim_id
    assert resolucao.market_area_id == "juros"
    assert resolucao.outcome == 1
    assert resolucao.resolution_source == FONTE_JUROS
    assert resolucao.determination_date == "2026-09-01"
    assert resolucao.determination_basis == BASE_PRIMEIRA_OBSERVACAO  # padrão declarado


# ------------------------------------------------------------- recusas óbvias


def test_area_desconhecida_levanta_em_vez_de_virar_mercado_fantasma():
    """Enum fechado: área inventada (ou com typo) levanta na criação."""
    with pytest.raises(MarketClaimError, match="desconhecido"):
        make_claim(
            claim_id="X::2026-08",
            market_area_id="area-inventada",
            question="?",
            deadline=PRAZO,
            probability=0.5,
            created_at=CRIADO,
        )


def test_probabilidade_fora_de_zero_um_e_recusada():
    """Probabilidade é medida, não enfeite: fora de [0,1] não existe afirmação."""
    with pytest.raises(MarketClaimError, match=r"\[0,1\]"):
        _claim_de_juros(probability=1.5)


def test_deadline_anterior_a_criacao_e_recusado():
    """Pergunta sobre prazo já vencido na criação seria previsão do passado."""
    with pytest.raises(MarketClaimError, match="anterior"):
        make_claim(
            claim_id="JUROS-TESTE::2026-07",
            market_area_id="juros",
            question="?",
            deadline="2026-07-31",
            probability=0.5,
            created_at=CRIADO,  # 2026-08-01, depois do prazo
        )


def test_fonte_a_declarar_gera_claim_mas_nunca_liquida():
    """UNKNOWN over guess: sem fonte oficial nomeada não há desfecho a medir."""
    claim = make_claim(
        claim_id="ENERGIA-TESTE::2026-08",
        market_area_id="energia",  # fonte_resolucao = "a declarar" no classificador
        question="O subsistema SE/CO terminará 2026-08 acima do limiar?",
        deadline=PRAZO,
        probability=0.5,
        created_at=CRIADO,
    )
    assert claim.resolvable is False
    with pytest.raises(ResolutionError, match="não liquida"):
        resolve(claim, outcome=1, source="a declarar")


def test_fonte_trocada_na_hora_de_liquidar_e_recusada():
    """Não se troca a fonte na liquidação: seria medir acerto contra o mundo errado."""
    with pytest.raises(ResolutionError, match="fonte declarada"):
        resolve(_claim_de_juros(), outcome=1, source="api.bcb.gov.br (SGS)")


def test_resolucao_dupla_no_ledger_e_recusada(tmp_path: Path) -> None:
    """O apêndice do ledger é idempotente por claim_id: liquidar duas vezes não grava duas linhas."""
    from asus_theye.markets.live import _apendar_resolucao

    store = tmp_path / "registro.json"
    linha = {"claim_id": "JUROS-TESTE::2026-08", "outcome": 1, "resolution_source": FONTE_JUROS}

    assert _apendar_resolucao(store, linha) is True  # primeira liquidação grava
    assert _apendar_resolucao(store, {**linha, "outcome": 0}) is False  # segunda é recusada

    conteudo = store.with_name("resolucoes.jsonl").read_text(encoding="utf-8")
    assert len(conteudo.strip().splitlines()) == 1  # e o desfecho gravado não mudou
    assert '"outcome": 1' in conteudo
