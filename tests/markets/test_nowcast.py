# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Nowcast do IPCA: cálculos determinísticos e nenhuma chamada de rede."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path

import numpy as np
import pytest

from asus_theye.markets import nowcast
from asus_theye.markets.nowcast import (
    JANELA_TREINO,
    MIN_RESIDUOS,
    Painel,
    Snapshot,
    ajustar_ridge,
    corrida_do_nowcast,
    montar_painel,
    probabilidade_laplace,
    transformar_ptax_mensal,
    transformar_selic_mensal,
    walk_forward,
)
from asus_theye.net.http import HttpResponse


class TransporteSGSFalso:
    """Devolve payloads SGS por código; qualquer URL não preparada falha."""

    def __init__(self, series: Mapping[int, list[dict[str, str]]]) -> None:
        self.series = series
        self.urls: list[str] = []

    def request(self, url: str, *, headers: Mapping[str, str], timeout: int, max_bytes: int) -> HttpResponse:
        del headers, timeout
        self.urls.append(url)
        encontrado = re.search(r"bcdata\.sgs\.(\d+)", url)
        if encontrado is None:
            raise AssertionError(f"URL SGS inesperada: {url}")
        codigo = int(encontrado.group(1))
        corpo = json.dumps(self.series[codigo]).encode()
        assert len(corpo) <= max_bytes
        return HttpResponse(url=url, status=200, headers={}, body=corpo)


def _ponto(data: str, valor: float) -> dict[str, str]:
    return {"data": data, "valor": f"{valor:.12f}"}


def _painel_linear(n: int, *, choque_no_ultimo: bool = False) -> Painel:
    meses: list[str] = []
    valores_r2: list[float] = []
    valores_igpm: list[float] = []
    alvo: list[float] = []
    for indice in range(n):
        ano, mes_zero = divmod(indice, 12)
        meses.append(f"{2000 + ano:04d}-{mes_zero + 1:02d}")
        x1 = float(indice % 17) - 8.0
        x2 = float((indice * 7) % 19) - 9.0
        valores_r2.append(x1)
        valores_igpm.append(x2)
        alvo.append(1.25 + 1.8 * x1 - 0.6 * x2)
    if choque_no_ultimo:
        valores_r2[-1] = 1_000_000.0
        valores_igpm[-1] = -2_000_000.0
        alvo[-1] = 999_999.0
    vazia: tuple[Snapshot, ...] = ()
    return Painel(
        tuple(meses),
        np.asarray(alvo, dtype=np.float64),
        {
            "ipca_15": np.asarray(valores_r2, dtype=np.float64),
            "igp_m": np.asarray(valores_igpm, dtype=np.float64),
            "dolar_variacao": np.zeros(n, dtype=np.float64),
            "selic_media": np.ones(n, dtype=np.float64),
        },
        vazia,
    )


def test_transformacoes_ptax_e_selic_com_transporte_falso() -> None:
    mensais = [_ponto("01/01/2024", 0.1), _ponto("01/02/2024", 0.2), _ponto("01/03/2024", 0.3)]
    transporte = TransporteSGSFalso(
        {
            433: mensais,
            7478: mensais,
            189: mensais,
            1: [
                _ponto("02/01/2024", 4.0),
                _ponto("03/01/2024", 6.0),  # média jan = 5
                _ponto("01/02/2024", 5.0),
                _ponto("02/02/2024", 10.0),  # média fev = 7,5; variação = 50%
                _ponto("01/03/2024", 6.0),
                _ponto("02/03/2024", 6.0),  # média mar = 6; variação = -20%
            ],
            432: [
                _ponto("01/01/2024", 10.0),
                _ponto("02/01/2024", 14.0),
                _ponto("01/02/2024", 9.0),
                _ponto("02/02/2024", 15.0),
                _ponto("01/03/2024", 13.0),
                _ponto("02/03/2024", 17.0),
            ],
        }
    )

    painel = montar_painel(transport=transporte)

    assert painel.meses == ("2024-02", "2024-03")  # janeiro cai: PTAX precisa do mês anterior.
    assert painel.valores["dolar_variacao"] == pytest.approx([50.0, -20.0])
    assert painel.valores["selic_media"] == pytest.approx([12.0, 15.0])
    assert len(transporte.urls) > 5  # séries diárias são paginadas no limite oficial de dez anos.


def test_transformacoes_nao_unem_meses_nao_consecutivos() -> None:
    ptax = transformar_ptax_mensal([("01/01/2024", 5.0), ("01/03/2024", 10.0)])
    selic = transformar_selic_mensal([("01/01/2024", 10.0), ("02/01/2024", 14.0)])

    assert ptax == {}  # fevereiro ausente não pode ser imputado nem atravessado.
    assert selic == {"2024-01": 12.0}


def test_padronizacao_do_fold_usa_somente_treino() -> None:
    painel = _painel_linear(JANELA_TREINO + 1, choque_no_ultimo=True)

    fold = walk_forward(painel, "R2")[0]

    assert fold.mes not in fold.meses_treino
    assert fold.meses_treino == painel.meses[:JANELA_TREINO]
    assert fold.medias_treino == pytest.approx(
        [np.mean(painel.valores["ipca_15"][:JANELA_TREINO]), np.mean(painel.valores["igp_m"][:JANELA_TREINO])]
    )
    assert max(abs(valor) for valor in fold.medias_treino) < 1.0  # o choque do alvo não contaminou a média.


def test_walk_forward_exclui_mes_alvo_e_move_janela() -> None:
    painel = _painel_linear(JANELA_TREINO + 2)

    folds = walk_forward(painel, "R2")

    assert len(folds) == 2
    assert folds[0].meses_treino == painel.meses[:120]
    assert folds[1].meses_treino == painel.meses[1:121]
    assert all(fold.mes not in fold.meses_treino for fold in folds)
    assert all(max(fold.meses_treino) < fold.mes for fold in folds)


def test_walk_forward_nao_atravessa_mes_ausente() -> None:
    painel = _painel_linear(JANELA_TREINO + 2)
    meses_com_buraco = painel.meses[:60] + painel.meses[61:]
    indices = list(range(60)) + list(range(61, JANELA_TREINO + 2))
    painel_com_buraco = Painel(
        meses_com_buraco,
        painel.alvo[indices],
        {nome: valores[indices] for nome, valores in painel.valores.items()},
        (),
    )

    assert walk_forward(painel_com_buraco, "R2") == []


def test_probabilidade_e_unknown_antes_de_24_residuos() -> None:
    assert probabilidade_laplace([0.0] * (MIN_RESIDUOS - 1), previsao=0.5, limiar=0.5) is None


def test_probabilidade_laplace_com_contagem_conhecida() -> None:
    # corte = 0,1; 12 dos 24 resíduos o alcançam: (1 + 12) / (24 + 2) = 0,5.
    residuos = [-0.2] * 12 + [0.1] * 12

    assert probabilidade_laplace(residuos, previsao=0.4, limiar=0.5) == pytest.approx(0.5)


def test_ridge_recupera_coeficientes_de_relacao_linear() -> None:
    x1 = np.linspace(-5.0, 5.0, 101)
    x2 = np.sin(np.linspace(-3.0, 3.0, 101))
    x = np.column_stack((x1, x2))
    y = 2.5 + 3.0 * x1 - 1.75 * x2

    ajuste = ajustar_ridge(x, y, alpha=1e-12)

    assert ajuste.intercepto == pytest.approx(2.5, abs=1e-10)
    assert ajuste.coeficientes == pytest.approx([3.0, -1.75], abs=1e-10)


def test_corrida_grava_manifesto_com_hash_e_focus_bloqueado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    series: dict[int, list[dict[str, str]]] = {codigo: [] for codigo in (433, 7478, 189, 1, 432)}
    for indice in range(150):
        ano, mes_zero = divmod(indice, 12)
        data = f"01/{mes_zero + 1:02d}/{2000 + ano:04d}"
        ipca_15 = 0.4 + 0.01 * (indice % 11)
        igp_m = -0.2 + 0.02 * (indice % 7)
        series[433].append(_ponto(data, 0.1 + 0.8 * ipca_15 + 0.2 * igp_m))
        series[7478].append(_ponto(data, ipca_15))
        series[189].append(_ponto(data, igp_m))
        series[1].append(_ponto(data, 4.0 + 0.01 * indice))
        series[432].append(_ponto(data, 10.0 + 0.01 * indice))
    transporte = TransporteSGSFalso(series)
    artefatos = tmp_path / "artefatos"
    monkeypatch.setattr(nowcast, "ARTEFATOS_DIR", artefatos)

    corrida = corrida_do_nowcast("R2", transport=transporte)

    caminho = Path(corrida.artefatos[0]["caminho"])
    corpo = caminho.read_bytes()
    manifesto = json.loads(corpo)
    assert corrida.artefatos[0]["sha256"] == hashlib.sha256(corpo).hexdigest()
    assert manifesto["metricas"]["brier_focus"] == "BLOCKED"
    assert "vintage" in manifesto["metricas"]["motivo_brier_focus"]
    assert all(len(fold["fontes"]) == len(transporte.urls) for fold in manifesto["folds"])
    assert corrida.params["janela"] == 120
    assert corrida.params["especificacao"] == "R2"


# ------------------------------------------------- baseline Focus por vintage


def test_baseline_focus_bloqueado_ate_ter_serie(tmp_path) -> None:
    """Menos que o mínimo de vintages = BLOCKED honesto, com quanto falta."""
    import json as _json

    from asus_theye.markets.nowcast import VINTAGES_MINIMOS, baseline_focus_por_vintage

    r = baseline_focus_por_vintage(base=tmp_path)
    assert r["estado"] == "BLOCKED" and r["faltam"] == VINTAGES_MINIMOS

    (tmp_path / "vintage_focus.jsonl").write_text(
        "\n".join(
            _json.dumps(
                {"mes_referencia": f"2026-{m:02d}", "mediana": 0.4, "capturado_em": f"2026-{m:02d}-01T00:00:00Z"}
            )
            for m in range(1, 4)
        )
        + "\n",
        encoding="utf-8",
    )
    r = baseline_focus_por_vintage(base=tmp_path)
    assert r["estado"] == "BLOCKED" and r["meses_com_vintage"] == 3
    assert "não se fabrica retroativamente" in r["motivo"]


def test_baseline_usa_o_primeiro_vintage_de_cada_mes(tmp_path) -> None:
    """Com série suficiente, o baseline sai do bloqueio usando o consenso do corte."""
    import json as _json

    from asus_theye.markets.nowcast import Fold, baseline_focus_por_vintage

    linhas = []
    for m in range(1, 25):  # 24 meses = mínimo
        mes = f"2025-{m:02d}" if m <= 12 else f"2026-{m - 12:02d}"
        # duas capturas do mesmo mês: a PRIMEIRA é a que vale (sem revisão)
        linhas.append({"mes_referencia": mes, "mediana": 0.60, "capturado_em": f"{mes}-01T00:00:00Z"})
        linhas.append({"mes_referencia": mes, "mediana": 0.10, "capturado_em": f"{mes}-28T00:00:00Z"})
    (tmp_path / "vintage_focus.jsonl").write_text("\n".join(_json.dumps(li) for li in linhas) + "\n", encoding="utf-8")
    folds = [
        Fold(
            mes="2025-01",
            meses_treino=(),
            alpha=1.0,
            intercepto=0.0,
            coeficientes=(),
            medias_treino=(),
            desvios_treino=(),
            previsao=0.0,
            observado=0.7,
            residuo=0.7,
            limiar=0.5,
            probabilidade=None,
            desfecho=1,
        )
    ]
    r = baseline_focus_por_vintage(folds, base=tmp_path)
    assert r["estado"] == "OK"
    # primeiro vintage = 0.60 >= 0.50 → p=1; observado 0.7 >= 0.50 → o=1 → Brier 0
    assert r["brier_focus"] == 0.0 and r["n_meses"] == 1
