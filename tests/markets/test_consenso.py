# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da comparação contra o consenso Focus — sobretudo, da recusa em agregar."""

from __future__ import annotations

import json
from pathlib import Path

from asus_theye.markets.consenso import AMOSTRA_MINIMA, medir, parear


def _escrever(caminho: Path, linhas: list[dict]) -> Path:
    caminho.write_text("".join(json.dumps(li) + "\n" for li in linhas), encoding="utf-8")
    return caminho


def _vintage(mes: str, mediana: float) -> dict:
    return {"mes_referencia": mes, "indicador": "IPCA", "mediana": mediana, "data_do_boletim": f"{mes}-14"}


def _resolucao(mes: str, observado: float, area: str = "macroeconomia") -> dict:
    return {
        "claim_id": f"MACRO-01::{mes}",
        "market_area_id": area,
        "mes_referencia": mes,
        "valor_observado": observado,
        "probability": 0.5,
        "outcome": int(observado >= 0.5),
    }


# ------------------------------------------------------------ pareamento


def test_pareia_por_mes_de_referencia(tmp_path: Path) -> None:
    v = _escrever(tmp_path / "v.jsonl", [_vintage("2026-07", 0.30)])
    r = _escrever(tmp_path / "r.jsonl", [_resolucao("2026-07", 0.07)])
    pares = parear(vintages=v, resolucoes=r)
    assert len(pares) == 1
    assert pares[0]["erro_absoluto_focus"] == 0.23
    assert pares[0]["regime"] == "choque_maior"


def test_mes_sem_contraparte_nao_vira_par(tmp_path: Path) -> None:
    """Vintage de mês ainda aberto e liquidação anterior ao arquivamento não pareiam.

    É exatamente o estado real do repositório hoje — e a ausência é reportada,
    nunca preenchida com um valor plausível.
    """
    v = _escrever(tmp_path / "v.jsonl", [_vintage("2026-09", 0.52)])
    r = _escrever(tmp_path / "r.jsonl", [_resolucao("2026-07", 0.07)])
    assert parear(vintages=v, resolucoes=r) == []


def test_pares_saem_em_ordem_cronologica(tmp_path: Path) -> None:
    meses = ["2026-03", "2026-01", "2026-02"]
    v = _escrever(tmp_path / "v.jsonl", [_vintage(m, 0.4) for m in meses])
    r = _escrever(tmp_path / "r.jsonl", [_resolucao(m, 0.4) for m in meses])
    assert [p["mes_referencia"] for p in parear(vintages=v, resolucoes=r)] == ["2026-01", "2026-02", "2026-03"]


def test_regimes_classificam_pela_surpresa(tmp_path: Path) -> None:
    casos = {"2026-01": (0.40, 0.45), "2026-02": (0.40, 0.55), "2026-03": (0.40, 0.70)}
    v = _escrever(tmp_path / "v.jsonl", [_vintage(m, c[0]) for m, c in casos.items()])
    r = _escrever(tmp_path / "r.jsonl", [_resolucao(m, c[1]) for m, c in casos.items()])
    regimes = {p["mes_referencia"]: p["regime"] for p in parear(vintages=v, resolucoes=r)}
    assert regimes == {"2026-01": "normal", "2026-02": "choque_moderado", "2026-03": "choque_maior"}


# ------------------------------------------------------------ a trava que importa


def test_recusa_agregar_abaixo_da_amostra_minima(tmp_path: Path) -> None:
    """Com poucos meses o MAE diz mais sobre o acaso do que sobre o previsor."""
    v = _escrever(tmp_path / "v.jsonl", [_vintage("2026-07", 0.30)])
    r = _escrever(tmp_path / "r.jsonl", [_resolucao("2026-07", 0.07)])
    snap = medir(vintages=v, resolucoes=r)
    assert snap["suficiente"] is False
    assert snap["mae_focus"] is None
    assert snap["por_regime"] is None
    assert "insuficiente" in snap["metodo"]
    assert len(snap["pares"]) == 1  # os pares brutos continuam visíveis


def test_agrega_a_partir_da_amostra_minima(tmp_path: Path) -> None:
    meses = [f"2026-{m:02d}" for m in range(1, AMOSTRA_MINIMA + 1)]
    v = _escrever(tmp_path / "v.jsonl", [_vintage(m, 0.40) for m in meses])
    r = _escrever(tmp_path / "r.jsonl", [_resolucao(m, 0.45) for m in meses])
    snap = medir(vintages=v, resolucoes=r)
    assert snap["suficiente"] is True
    assert snap["n"] == AMOSTRA_MINIMA
    assert snap["mae_focus"] == 0.05
    assert snap["por_regime"]["normal"]["n"] == AMOSTRA_MINIMA


def test_a_dependencia_do_focus_viaja_em_todo_resultado(tmp_path: Path) -> None:
    """O ponto mais importante: nosso p DERIVA do Focus, então não há superação.

    Se este texto sumir, alguém vai ler o MAE como vantagem independente — e
    seria mérito fabricado.
    """
    v = _escrever(tmp_path / "v.jsonl", [_vintage("2026-07", 0.30)])
    r = _escrever(tmp_path / "r.jsonl", [_resolucao("2026-07", 0.07)])
    for snap in (medir(vintages=v, resolucoes=r), medir(vintages=tmp_path / "vazio.jsonl", resolucoes=r)):
        assert "DERIVA do consenso" in snap["dependencia_declarada"]
        assert "sinal independente" in snap["dependencia_declarada"]


def test_cortes_de_regime_sao_declarados_provisorios(tmp_path: Path) -> None:
    """Importar o corte de outra economia traria a variância dela junto."""
    snap = medir(vintages=tmp_path / "vazio.jsonl", resolucoes=tmp_path / "vazio2.jsonl")
    assert snap["cortes_de_regime"]["provisorios"] is True
    assert "PROVISÓRIOS" in snap["cortes_de_regime"]["nota"]


def test_sem_nenhum_insumo_degrada_sem_quebrar(tmp_path: Path) -> None:
    snap = medir(vintages=tmp_path / "a.jsonl", resolucoes=tmp_path / "b.jsonl")
    assert snap["n"] == 0
    assert snap["suficiente"] is False
    assert snap["pares"] == []


# ------------------------------------------------------------ selagem


def test_selagem_e_idempotente_por_conjunto_de_pares(tmp_path: Path) -> None:
    from asus_theye.markets.auditoria import abrir_auditoria, cabeca_da_corrente
    from asus_theye.markets.consenso import selar

    v = _escrever(tmp_path / "v.jsonl", [_vintage("2026-07", 0.30)])
    r = _escrever(tmp_path / "r.jsonl", [_resolucao("2026-07", 0.07)])
    corrente = tmp_path / "corrente.jsonl"
    sdk = abrir_auditoria(
        tmp_path / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=corrente,
        fingerprint=tmp_path / "chave.fingerprint",
    )
    snap = medir(vintages=v, resolucoes=r)
    assert selar(sdk, snap, eventos=corrente)["duplicate"] is False
    assert selar(sdk, medir(vintages=v, resolucoes=r), eventos=corrente)["duplicate"] is True
    assert cabeca_da_corrente(sdk) == 1


def test_nao_pareia_indicador_com_area_diferente(tmp_path: Path) -> None:
    """Regressão: parear só por mês casava a mediana do IPCA com o dólar.

    O Focus do IPCA (0,52%) contra a PTAX observada (5,42) produzia um erro de
    4,9 p.p. rotulado "choque_maior" — número fabricado, que seria SELADO na
    corrente e ancorado on-chain. É a falha que esta plataforma existe para
    impedir, e por isso ela tem teste próprio.
    """
    v = _escrever(tmp_path / "v.jsonl", [_vintage("2026-09", 0.52)])
    r = _escrever(tmp_path / "r.jsonl", [_resolucao("2026-09", 5.42, area="cambio")])
    assert parear(vintages=v, resolucoes=r) == []


def test_pareia_a_area_certa_quando_ha_varias_no_mesmo_mes(tmp_path: Path) -> None:
    v = _escrever(tmp_path / "v.jsonl", [_vintage("2026-09", 0.52)])
    r = _escrever(
        tmp_path / "r.jsonl",
        [
            _resolucao("2026-09", 5.42, area="cambio"),
            _resolucao("2026-09", 0.48, area="macroeconomia"),
            _resolucao("2026-09", 14.25, area="juros"),
        ],
    )
    pares = parear(vintages=v, resolucoes=r)
    assert len(pares) == 1
    assert pares[0]["market_area_id"] == "macroeconomia"
    assert pares[0]["erro_absoluto_focus"] == 0.04


def test_indicador_sem_area_declarada_nao_pareia(tmp_path: Path) -> None:
    """Parear às cegas é como o erro fabricado nasce."""
    v = _escrever(tmp_path / "v.jsonl", [{"mes_referencia": "2026-09", "indicador": "DESCONHECIDO", "mediana": 1.0}])
    r = _escrever(tmp_path / "r.jsonl", [_resolucao("2026-09", 0.48)])
    assert parear(vintages=v, resolucoes=r) == []
