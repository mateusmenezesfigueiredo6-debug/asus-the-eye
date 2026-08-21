# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da calibração — sobretudo da recusa em desenhar curva sobre ruído."""

from __future__ import annotations

import json
from pathlib import Path

from asus_theye.markets.calibracao import (
    AMOSTRA_MINIMA,
    CLAIMS_MINIMOS,
    curva_de_confiabilidade,
    decomposicao_de_murphy,
    medir,
    pares,
)
from asus_theye.markets.resolution import BASE_DESCONHECIDA, BASE_PRIMEIRA_OBSERVACAO


def _escrever(caminho: Path, linhas: list[dict]) -> Path:
    caminho.write_text("".join(json.dumps(li) + "\n" for li in linhas), encoding="utf-8")
    return caminho


def _ponto(claim: str, dia: str, p: float, area: str = "macroeconomia") -> dict:
    return {
        "claim_id": claim,
        "market_area_id": area,
        "observado_em": dia,
        "probability": p,
        "deadline": "2026-07-31",
        "horizonte_dias": 10,
    }


def _desfecho(claim: str, outcome: int, determinada: str | None, base: str = BASE_PRIMEIRA_OBSERVACAO) -> dict:
    linha = {"claim_id": claim, "outcome": outcome, "determination_basis": base}
    if determinada:
        linha["determination_date"] = determinada
    return linha


# ------------------------------------------------------------ pareamento


def test_horizonte_e_reancorado_contra_a_determinacao(tmp_path: Path) -> None:
    """O relógio que vale é o da publicação da fonte, não o do contrato."""
    s = _escrever(tmp_path / "s.jsonl", [_ponto("A::2026-07", "2026-07-01", 0.7)])
    r = _escrever(tmp_path / "r.jsonl", [_desfecho("A::2026-07", 1, "2026-08-10")])
    resultado = pares(serie=s, resolucoes=r)
    assert len(resultado["pares"]) == 1
    assert resultado["pares"][0]["horizonte_dias"] == 40  # 01/07 -> 10/08
    assert resultado["pares"][0]["horizonte_ate_deadline"] == 10  # o proxy antigo


def test_base_desconhecida_e_excluida(tmp_path: Path) -> None:
    """Legado: sem saber quando a fonte publicou, o horizonte é ficção."""
    s = _escrever(tmp_path / "s.jsonl", [_ponto("A::2026-07", "2026-07-01", 0.7)])
    r = _escrever(tmp_path / "r.jsonl", [_desfecho("A::2026-07", 1, "2026-08-10", BASE_DESCONHECIDA)])
    resultado = pares(serie=s, resolucoes=r)
    assert resultado["pares"] == []
    assert resultado["excluidos"]["base_nao_confiavel"] == 1


def test_claim_vivo_nao_entra_e_o_motivo_e_contado(tmp_path: Path) -> None:
    """É o estado real do repositório hoje — e o painel precisa poder explicá-lo."""
    s = _escrever(tmp_path / "s.jsonl", [_ponto("VIVO::2026-09", "2026-08-20", 0.5)])
    r = _escrever(tmp_path / "r.jsonl", [])
    resultado = pares(serie=s, resolucoes=r)
    assert resultado["pares"] == []
    assert resultado["excluidos"]["claim_sem_desfecho"] == 1


def test_liquidacao_sem_determination_date_e_excluida(tmp_path: Path) -> None:
    s = _escrever(tmp_path / "s.jsonl", [_ponto("A::2026-07", "2026-07-01", 0.7)])
    r = _escrever(tmp_path / "r.jsonl", [_desfecho("A::2026-07", 1, None)])
    assert pares(serie=s, resolucoes=r)["excluidos"]["sem_determination_date"] == 1


# ------------------------------------------------------------ a trava


def test_recusa_agregar_abaixo_da_amostra_minima(tmp_path: Path) -> None:
    """Curva com poucos pontos é ruído desenhado com régua."""
    s = _escrever(tmp_path / "s.jsonl", [_ponto("A::2026-07", "2026-07-01", 0.7)])
    r = _escrever(tmp_path / "r.jsonl", [_desfecho("A::2026-07", 1, "2026-08-10")])
    snap = medir(serie=s, resolucoes=r)
    assert snap["suficiente"] is False
    assert snap["brier"] is None and snap["curva"] is None and snap["murphy"] is None
    assert "insuficiente" in snap["metodo"]


def test_agrega_a_partir_da_amostra_minima(tmp_path: Path) -> None:
    pontos = [_ponto(f"A{i}::2026-07", "2026-07-01", 0.8) for i in range(AMOSTRA_MINIMA)]
    desfechos = [_desfecho(f"A{i}::2026-07", 1, "2026-08-10") for i in range(AMOSTRA_MINIMA)]
    snap = medir(serie=_escrever(tmp_path / "s.jsonl", pontos), resolucoes=_escrever(tmp_path / "r.jsonl", desfechos))
    assert snap["suficiente"] is True
    assert snap["n"] == AMOSTRA_MINIMA
    assert snap["brier"] == round((0.8 - 1) ** 2, 4)  # 0.04
    assert snap["por_horizonte"] is not None and snap["por_area"] is not None


# ------------------------------------------------------------ estatística


def test_curva_omite_faixa_com_amostra_fraca() -> None:
    """Frequência estimada com 2 casos não é frequência, é anedota."""
    itens = [{"probability": 0.9, "outcome": 1}, {"probability": 0.9, "outcome": 0}]
    faixa = [f for f in curva_de_confiabilidade(itens) if f["faixa"] == "0.8–1.0"][0]
    assert faixa["n"] == 2
    assert faixa["frequencia_observada"] is None
    assert faixa["suficiente"] is False


def test_previsor_perfeitamente_calibrado_tem_confiabilidade_zero() -> None:
    """Dizer 0,8 e acontecer 80% das vezes: erro de nível nulo."""
    itens = [{"probability": 0.8, "outcome": 1} for _ in range(8)]
    itens += [{"probability": 0.8, "outcome": 0} for _ in range(2)]
    murphy = decomposicao_de_murphy(itens)
    assert murphy is not None
    assert murphy["confiabilidade"] == 0.0
    assert murphy["taxa_base"] == 0.8


def test_previsor_que_so_diz_a_taxa_base_tem_resolucao_zero() -> None:
    """Perfeitamente confiável e completamente inútil — só a decomposição mostra.

    É por isso que o Brier sozinho não basta: este previsor não distingue
    caso nenhum, e ainda assim não erra o nível.
    """
    itens = [{"probability": 0.5, "outcome": i % 2} for i in range(10)]
    murphy = decomposicao_de_murphy(itens)
    assert murphy is not None
    assert murphy["resolucao"] == 0.0
    assert murphy["confiabilidade"] == 0.0


def test_brier_por_area_separa_os_dominios(tmp_path: Path) -> None:
    metade = AMOSTRA_MINIMA // 2
    pontos = [_ponto(f"M{i}::2026-07", "2026-07-01", 1.0, "macroeconomia") for i in range(metade)]
    pontos += [_ponto(f"J{i}::2026-07", "2026-07-01", 0.0, "juros") for i in range(AMOSTRA_MINIMA - metade)]
    desfechos = [_desfecho(f"M{i}::2026-07", 1, "2026-08-10") for i in range(metade)]
    desfechos += [_desfecho(f"J{i}::2026-07", 1, "2026-08-10") for i in range(AMOSTRA_MINIMA - metade)]
    snap = medir(serie=_escrever(tmp_path / "s.jsonl", pontos), resolucoes=_escrever(tmp_path / "r.jsonl", desfechos))
    por_area = {a["area"]: a["brier"] for a in snap["por_area"]}
    assert por_area["macroeconomia"] == 0.0  # acertou em cheio
    assert por_area["juros"] == 1.0  # errou em cheio


# ------------------------------------------------------------ painel


def test_painel_sem_amostra_explica_o_que_falta(tmp_path: Path) -> None:
    """Vazio útil: em vez de curva bonita sobre nada, diz o que precisa acontecer."""
    from asus_theye.dashboard.calibracao import calibracao_page

    s = _escrever(tmp_path / "s.jsonl", [_ponto("VIVO::2026-09", "2026-08-20", 0.5)])
    r = _escrever(tmp_path / "r.jsonl", [])
    page = calibracao_page(serie=s, resolucoes=r)
    assert "Amostra insuficiente" in page
    assert "O que precisa acontecer" in page
    assert "claim sem desfecho" in page
    assert "<svg" not in page  # nenhuma curva é desenhada


def test_painel_com_amostra_desenha_a_curva(tmp_path: Path) -> None:
    from asus_theye.dashboard.calibracao import calibracao_page

    pontos = [_ponto(f"A{i}::2026-07", "2026-07-01", 0.9) for i in range(AMOSTRA_MINIMA)]
    desfechos = [_desfecho(f"A{i}::2026-07", 1, "2026-08-10") for i in range(AMOSTRA_MINIMA)]
    page = calibracao_page(
        serie=_escrever(tmp_path / "s.jsonl", pontos), resolucoes=_escrever(tmp_path / "r.jsonl", desfechos)
    )
    assert "<svg" in page and "polyline" not in page  # um ponto só: sem linha
    assert "Curva de confiabilidade" in page
    assert "Brier por área" in page


def test_rota_calibracao_responde_200() -> None:
    import pytest

    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from asus_theye.dashboard.app import create_dashboard_app

    resposta = TestClient(create_dashboard_app()).get("/calibracao")
    assert resposta.status_code == 200
    assert "CALIBRAÇÃO" in resposta.text


# ------------------------------------------------------- as duas trilhas


def _ponto_de(claim: str, dia: str, p: float, origem: str, area: str = "macroeconomia") -> dict:
    ponto = _ponto(claim, dia, p, area)
    ponto["origem"] = origem
    return ponto


def test_ponto_sem_origem_e_do_focus(tmp_path: Path) -> None:
    """Fato histórico, não suposição: a série antiga precede a trilha própria."""
    s = _escrever(tmp_path / "s.jsonl", [_ponto("A::2026-07", "2026-07-01", 0.7)])
    r = _escrever(tmp_path / "r.jsonl", [_desfecho("A::2026-07", 1, "2026-08-10")])
    assert pares(serie=s, resolucoes=r)["pares"][0]["trilha"] == "focus"


def test_origem_desconhecida_e_excluida_e_contada(tmp_path: Path) -> None:
    """Classificar no lugar errado contamina a régua das DUAS trilhas de uma vez."""
    s = _escrever(tmp_path / "s.jsonl", [_ponto_de("A::2026-07", "2026-07-01", 0.7, "palpite-do-estagiario")])
    r = _escrever(tmp_path / "r.jsonl", [_desfecho("A::2026-07", 1, "2026-08-10")])
    resultado = pares(serie=s, resolucoes=r)
    assert resultado["pares"] == []
    assert resultado["excluidos"]["origem_nao_classificada"] == 1


def test_as_metricas_de_manchete_nao_misturam_as_trilhas(tmp_path: Path) -> None:
    """O defeito que esta separação existe para impedir.

    Somar as duas trilhas num Brier só produz um número que não mede nenhuma.
    """
    linhas = []
    desfechos = []
    for i in range(AMOSTRA_MINIMA):
        claim = f"A{i}::2026-07"
        # Focus perfeito, trilha própria pessima — se misturassem, o Brier de
        # manchete deixaria de ser 0 e ninguem saberia de quem era a culpa
        linhas.append(_ponto_de(claim, "2026-07-01", 1.0, "registro"))
        linhas.append(_ponto_de(claim, "2026-07-01", 0.0, "propria"))
        desfechos.append(_desfecho(claim, 1, "2026-08-10"))
    s = _escrever(tmp_path / "s.jsonl", linhas)
    r = _escrever(tmp_path / "r.jsonl", desfechos)

    snap = medir(serie=s, resolucoes=r)
    assert snap["trilha_das_metricas"] == "focus"
    assert snap["n"] == AMOSTRA_MINIMA  # só os pontos do Focus
    assert snap["brier"] == 0.0  # e o Brier é o DELE, intacto

    por_trilha = {t["trilha"]: t for t in snap["trilhas"]["por_trilha"]}
    assert por_trilha["propria"]["brier"] == 1.0  # a trilha própria aparece, medida à parte


def test_skill_score_so_conta_pontos_casados(tmp_path: Path) -> None:
    """O viés de sobrevivência que a comparação tem de recusar.

    A trilha própria some justamente nos dias em que erraria. Se os pontos sem
    par entrassem, ela exibiria vantagem por ter faltado — não por ter acertado.
    """
    linhas = []
    desfechos = []
    for i in range(AMOSTRA_MINIMA):
        claim = f"A{i}::2026-07"
        linhas.append(_ponto_de(claim, "2026-07-01", 0.6, "registro"))
        linhas.append(_ponto_de(claim, "2026-07-01", 0.6, "propria"))
        desfechos.append(_desfecho(claim, 1, "2026-08-10"))
    # os dias difíceis: só o Focus esteve lá, e apanhou
    for i in range(AMOSTRA_MINIMA):
        claim = f"B{i}::2026-07"
        linhas.append(_ponto_de(claim, "2026-07-02", 0.0, "registro"))
        desfechos.append(_desfecho(claim, 1, "2026-08-10"))
    s = _escrever(tmp_path / "s.jsonl", linhas)
    r = _escrever(tmp_path / "r.jsonl", desfechos)

    comparacao = medir(serie=s, resolucoes=r)["trilhas"]
    assert comparacao["n_casados"] == AMOSTRA_MINIMA
    # empate nos casados: a ausência nos dias difíceis NÃO virou vantagem
    assert comparacao["skill_score"] == 0.0
    assert "parid" in comparacao["leitura"].lower()

    # e a prova de que havia armadilha: sobre TODOS os pontos, o Brier da
    # trilha própria é muito melhor que o do Focus — vantagem que ela teria
    # exibido sem ter acertado nada a mais, só por ter faltado
    bruto = {t["trilha"]: t["brier"] for t in comparacao["por_trilha"]}
    assert bruto["propria"] < bruto["focus"]


def test_sem_pares_casados_suficientes_nao_ha_skill_score(tmp_path: Path) -> None:
    """Declarar vantagem sobre punhado de pontos é o erro que a casa não comete."""
    s = _escrever(
        tmp_path / "s.jsonl",
        [_ponto_de("A::2026-07", "2026-07-01", 0.9, "registro"), _ponto_de("A::2026-07", "2026-07-01", 0.9, "propria")],
    )
    r = _escrever(tmp_path / "r.jsonl", [_desfecho("A::2026-07", 1, "2026-08-10")])
    comparacao = medir(serie=s, resolucoes=r)["trilhas"]
    assert comparacao["suficiente"] is False
    assert comparacao["skill_score"] is None


def test_focus_perfeito_nao_vira_divisao_por_zero(tmp_path: Path) -> None:
    """A razão não existe — e inventar número aqui seria pior que não ter."""
    linhas, desfechos = [], []
    for i in range(AMOSTRA_MINIMA):
        claim = f"A{i}::2026-07"
        linhas.append(_ponto_de(claim, "2026-07-01", 1.0, "registro"))
        linhas.append(_ponto_de(claim, "2026-07-01", 0.4, "propria"))
        desfechos.append(_desfecho(claim, 1, "2026-08-10"))
    s = _escrever(tmp_path / "s.jsonl", linhas)
    r = _escrever(tmp_path / "r.jsonl", desfechos)

    comparacao = medir(serie=s, resolucoes=r)["trilhas"]
    assert comparacao["brier_casado"]["focus"] == 0.0
    assert comparacao["skill_score"] is None
    assert "não existe" in comparacao["leitura"]


def test_o_benchmark_e_declarado_e_e_o_focus(tmp_path: Path) -> None:
    """Benchmark escolhido depois do resultado é benchmark escolhido para vencer."""
    s = _escrever(tmp_path / "s.jsonl", [_ponto_de("A::2026-07", "2026-07-01", 0.9, "registro")])
    r = _escrever(tmp_path / "r.jsonl", [_desfecho("A::2026-07", 1, "2026-08-10")])
    assert medir(serie=s, resolucoes=r)["trilhas"]["benchmark"] == "focus"


# ------------------------------------------- desfechos, não observações


def _quarenta_dias() -> list[str]:
    """Quarenta dias corridos de série, como um mercado vivo de verdade gera."""
    from datetime import date, timedelta

    inicio = date(2026, 6, 20)
    return [(inicio + timedelta(days=d)).isoformat() for d in range(40)]


def test_muitos_pontos_de_poucos_contratos_nao_liberam_a_agregacao(tmp_path: Path) -> None:
    """O defeito que mais perto chegou de ser publicado como verdade.

    A série grava um ponto por dia para cada mercado aberto. Três mercados
    vivos por quarenta dias produzem cento e vinte pares — e TRÊS desfechos.
    Com o portão contando pontos, a plataforma publicaria Brier, curva de
    confiabilidade, decomposição de Murphy e skill score, todos selados na
    corrente, com aparência de amostra grande e apoiados em três
    caras-ou-coroas.

    O tamanho amostral efetivo de uma calibração é o número de desfechos
    distintos: pontos do mesmo claim compartilham o desfecho e não são
    evidência independente.
    """
    linhas, desfechos = [], []
    for i in range(3):
        claim = f"A{i}::2026-07"
        for dia in _quarenta_dias():  # quarenta dias de série, como no mundo real
            linhas.append(_ponto(claim, dia, 0.7))
        desfechos.append(_desfecho(claim, 1, "2026-08-10"))
    s = _escrever(tmp_path / "s.jsonl", linhas)
    r = _escrever(tmp_path / "r.jsonl", desfechos)

    snap = medir(serie=s, resolucoes=r)
    assert snap["n"] == 120  # os pares existem…
    assert snap["claims"] == 3  # …mas são três desfechos
    assert snap["suficiente"] is False
    assert snap["brier"] is None
    assert snap["curva"] is None
    assert "desfecho(s) distinto(s)" in snap["metodo"]


def test_o_portao_abre_com_desfechos_distintos_suficientes(tmp_path: Path) -> None:
    """E o portão não é intransponível — ele exige a coisa certa."""
    linhas, desfechos = [], []
    for i in range(CLAIMS_MINIMOS):
        claim = f"A{i}::2026-07"
        linhas.append(_ponto(claim, "2026-07-01", 0.7))
        desfechos.append(_desfecho(claim, 1, "2026-08-10"))
    snap = medir(
        serie=_escrever(tmp_path / "s.jsonl", linhas),
        resolucoes=_escrever(tmp_path / "r.jsonl", desfechos),
    )
    assert snap["claims"] == CLAIMS_MINIMOS
    assert snap["suficiente"] is True
    assert snap["brier"] is not None


def test_a_comparacao_entre_trilhas_usa_o_mesmo_portao(tmp_path: Path) -> None:
    """Cem pares casados vindos de três contratos são três desfechos."""
    linhas, desfechos = [], []
    for i in range(3):
        claim = f"A{i}::2026-07"
        for dia in _quarenta_dias():
            linhas.append(_ponto_de(claim, dia, 0.7, "registro"))
            linhas.append(_ponto_de(claim, dia, 0.4, "propria"))
        desfechos.append(_desfecho(claim, 1, "2026-08-10"))
    comparacao = medir(
        serie=_escrever(tmp_path / "s.jsonl", linhas),
        resolucoes=_escrever(tmp_path / "r.jsonl", desfechos),
    )["trilhas"]
    assert comparacao["n_casados"] == 120
    assert comparacao["claims_casados"] == 3
    assert comparacao["suficiente"] is False
    assert comparacao["skill_score"] is None


def test_faixa_da_curva_tambem_conta_desfechos(tmp_path: Path) -> None:
    """Cinco pontos do mesmo contrato dão frequência 0 ou 1 — isso é ruído.

    A faixa precisa de desfechos distintos pelo mesmo motivo que o agregado.
    """
    from asus_theye.markets.calibracao import curva_de_confiabilidade

    # um único claim, dez pontos, todos na mesma faixa
    itens = [{"claim_id": "A::2026-07", "probability": 0.72, "outcome": 1, "market_area_id": "m"} for _ in range(10)]
    faixa = next(f for f in curva_de_confiabilidade(itens) if f["n"] == 10)
    assert faixa["claims"] == 1
    assert faixa["suficiente"] is False
    assert faixa["frequencia_observada"] is None
