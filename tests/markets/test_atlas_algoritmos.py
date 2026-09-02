# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Atlas v0 — a camada da casa sobre as centrais de algoritmos públicas.

O que se trava aqui: a disciplina do catálogo (nada entra sem hub, licença e
versão), as recusas do adaptador (série curta, dado podre, algoritmo fora do
catálogo) e que o adaptador devolve número finito — a MEDIÇÃO fica com os
benchmarks selados, não com a suíte."""

from __future__ import annotations

import numpy as np
import pytest

from asus_theye.markets.atlas_algoritmos import (
    CATALOGO,
    MINIMO_DE_PONTOS,
    AtlasError,
    prever_um_passo,
)

pytest.importorskip("statsforecast", reason="extra do Atlas não instalado")


def _serie(n: int = 60) -> np.ndarray:
    rng = np.random.default_rng(42)
    return 0.4 + 0.15 * np.sin(np.arange(n) / 6) + rng.normal(0, 0.05, n)


def test_catalogo_nada_entra_sem_hub_licenca_e_versao() -> None:
    """A regra de proveniência do Atlas: absorver sem declarar é clonar."""
    assert CATALOGO, "catálogo vazio não é Atlas"
    for slug, meta in CATALOGO.items():
        for campo in ("nome", "hub", "licenca", "versao_absorvida"):
            assert meta.get(campo, "").strip(), f"{slug}: sem {campo!r}"


@pytest.mark.parametrize("algoritmo", sorted(CATALOGO))
def test_adaptador_devolve_numero_finito(algoritmo: str) -> None:
    previsto = prever_um_passo(_serie(), algoritmo)
    assert np.isfinite(previsto)
    assert 0.0 < previsto < 1.0  # série sintética oscila em torno de 0,4


def test_serie_curta_levanta_em_vez_de_chutar() -> None:
    with pytest.raises(AtlasError, match="mínimo honesto"):
        prever_um_passo([0.4] * (MINIMO_DE_PONTOS - 1), "auto_ets")


def test_dado_podre_levanta() -> None:
    serie = _serie().tolist()
    serie[10] = float("nan")
    with pytest.raises(AtlasError, match="NaN"):
        prever_um_passo(serie, "auto_ets")


def test_fora_do_catalogo_levanta_nomeando_o_catalogo() -> None:
    with pytest.raises(AtlasError, match="fora do catálogo"):
        prever_um_passo(_serie(), "lstm-magico")
