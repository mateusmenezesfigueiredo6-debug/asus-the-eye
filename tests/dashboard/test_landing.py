# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da landing e da navegação — a rota que antes devolvia 404."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.dashboard.landing import landing_page
from asus_theye.dashboard.navegacao import PAINEIS, barra

FASES = {
    "versao": 1,
    "fases": [{"id": "F0", "nome": "A", "estado": "concluida", "peso_concluido": 1.0, "metodo": "m"}],
}


def _base(tmp: Path) -> Path:
    (tmp / "projeto").mkdir(parents=True, exist_ok=True)
    (tmp / "projeto" / "fases.json").write_text(json.dumps(FASES), encoding="utf-8")
    (tmp / "markets").mkdir(exist_ok=True)
    return tmp


# ------------------------------------------------------------ navegação


def test_barra_marca_a_pagina_corrente() -> None:
    marcado = barra("/mercados")
    assert 'href="/mercados" aria-current="page"' in marcado
    assert 'href="/corrente" aria-current="page"' not in marcado


def test_barra_sem_rota_conhecida_nao_marca_ninguem() -> None:
    """Rota desconhecida degrada para 'nenhum marcado' — melhor que marcar errado."""
    assert 'aria-current="page"' not in barra("/rota-que-nao-existe")


def test_a_vitrine_nao_expoe_a_telemetria_interna() -> None:
    """O cliente vê dois produtos, não a instrumentação de quem os construiu.

    /projeto (percentual de fases), /mlops (corridas de ML) e /benchmark
    (quântico, legado de outro projeto) continuam servidos e versionados — mas
    fora do menu. Misturar as duas coisas fazia a porta da frente parecer um
    painel de engenharia.
    """
    from asus_theye.dashboard.navegacao import PAINEIS, PAINEIS_INTERNOS

    publicas = {rota for rota, _ in PAINEIS}
    for rota, _ in PAINEIS_INTERNOS:
        assert rota not in publicas, f"{rota} é telemetria interna e não pertence à vitrine"
    assert "/mercados" in publicas and "/corrente" in publicas  # um de cada produto


def test_barra_lista_todos_os_paineis() -> None:
    marcado = barra("/")
    for rota, rotulo in PAINEIS:
        assert f'href="{rota}"' in marcado
        assert rotulo in marcado


# ------------------------------------------------------------ landing


def test_landing_mostra_os_dois_produtos_e_navega(tmp_path: Path) -> None:
    page = landing_page(_base(tmp_path))
    assert "THE EYE Markets" in page and "THE EYE Ledger" in page
    assert 'href="/mercados"' in page and 'href="/corrente"' in page
    assert 'aria-current="page"' in page  # a própria landing marcada na barra


def test_landing_usa_numeros_da_medicao_selada(tmp_path: Path) -> None:
    """Os números da landing vêm da medição real, não de valor escrito à mão."""
    page = landing_page(_base(tmp_path))
    assert "Corrente auditável" in page
    assert "Atividade prospectiva" in page  # eixo capacidade_real
    assert "100.0%" in page  # caminho mínimo do fixture


def test_landing_degrada_sem_medicao_mas_mantem_a_navegacao(tmp_path: Path) -> None:
    """Sem fases declaradas a página diz que não sabe — e continua navegável."""
    page = landing_page(tmp_path)  # sem projeto/fases.json
    assert "Medição indisponível" in page
    assert 'href="/mercados"' in page  # navegação sobrevive à falha da medição
    assert "THE EYE Markets" in page


def test_rota_raiz_responde_200(tmp_path: Path) -> None:
    """O 404 na raiz era o buraco: quem abria o servidor não via nada."""
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from asus_theye.dashboard.app import create_dashboard_app

    resposta = TestClient(create_dashboard_app()).get("/")
    assert resposta.status_code == 200
    assert "ASUS THE EYE" in resposta.text
