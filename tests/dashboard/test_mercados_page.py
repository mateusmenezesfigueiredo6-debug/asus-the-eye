# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do painel dos mercados vivos."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_pagina_real_mostra_os_tres_mercados() -> None:
    """O painel real, sem observação de comparador.

    A divergência que este teste afirmava saía do preço da Kalshi e
    foi expurgada (``data.redaction``, termos de terceiro). O painel degrada
    honestamente: mostra os mercados e continua declarando a doutrina, sem
    inventar um número de comparador que não existe mais.
    """
    from asus_theye.dashboard.mercados import mercados_page

    page = mercados_page()  # estado REAL do repo
    for marca in ("MACRO-01::2026-08", "JUROS-01::2026-09", "CAMBIO-01::2026-09", "comparador, nunca fonte"):
        assert marca in page, f"marca ausente: {marca}"
    assert "retrospectivas" in page.lower()  # a exclusão honesta é dita


def test_probabilidade_carrega_proveniencia(tmp_path: Path) -> None:
    from asus_theye.dashboard.mercados import mercados_page

    base = tmp_path
    registro = {
        "versao": 1,
        "mercados": [
            {
                "claim_id": "X::2026-09",
                "market_area_id": "macroeconomia",
                "question": "P?",
                "deadline": "2026-09-30",
                "probability": 0.8333,
                "resolution_source": "f",
                "created_at": "t",
                "mes_referencia": "2026-09",
                "limiar": 0.5,
                "criterio": "c",
                "serie_sgs": 433,
                "estado": "ABERTO",
                "tentativas": [],
                "gerador": {"fontes": ["BCB Focus"], "valor": 0.8333},
            },
            {
                "claim_id": "Y::2026-09",
                "market_area_id": "juros",
                "question": "Q?",
                "deadline": "2026-09-30",
                "probability": 0.5,
                "resolution_source": "f",
                "created_at": "t",
                "mes_referencia": "2026-09",
                "limiar": 14.0,
                "criterio": "c",
                "serie_sgs": 432,
                "estado": "ABERTO",
                "tentativas": [],
            },
        ],
    }
    (base / "registro.json").write_text(json.dumps(registro), encoding="utf-8")
    page = mercados_page(base)
    assert "WPAM" in page and "BCB Focus" in page  # proveniência visível
    assert "prior declarado" in page  # sem sinal = dito como tal


def test_registro_vazio_e_honesto(tmp_path: Path) -> None:
    from asus_theye.dashboard.mercados import mercados_page

    page = mercados_page(tmp_path)
    assert "nenhum" in page and "markets-emitir" in page


def test_rota_montada_no_app() -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from asus_theye.dashboard.app import create_dashboard_app

    resposta = TestClient(create_dashboard_app()).get("/mercados")
    assert resposta.status_code == 200 and "MERCADOS" in resposta.text


# ------------------------------------------------- a segunda probabilidade


def _mercado(**extra: object) -> dict:
    base = {
        "claim_id": "X::2026-09",
        "market_area_id": "macroeconomia",
        "question": "P?",
        "deadline": "2026-09-30",
        "probability": 0.20,
        "resolution_source": "api.bcb.gov.br",
        "created_at": "t",
        "mes_referencia": "2026-09",
        "limiar": 0.5,
        "estado": "ABERTO",
        "gerador": {"valor": 0.20, "fontes": ["Focus"]},
    }
    base.update(extra)
    return base


def _pagina(tmp_path: Path, mercados: list[dict]) -> str:
    from asus_theye.dashboard.mercados import mercados_page

    (tmp_path / "registro.json").write_text(json.dumps({"versao": 1, "mercados": mercados}), encoding="utf-8")
    return mercados_page(base=tmp_path)


def test_as_duas_trilhas_aparecem_lado_a_lado(tmp_path: Path) -> None:
    """A tela mais visível do produto tem de mostrar a comparação que ele faz."""
    page = _pagina(
        tmp_path,
        [_mercado(gerador_proprio={"valor": 0.6875, "max_uncertainty": False, "fontes": ["GDELT — tom -6.31"]})],
    )
    assert "p consenso" in page and "p notícia" in page
    assert "0.6875" in page
    assert "GDELT" in page  # a proveniência viaja no title, como na outra trilha


def test_ausencia_de_sinal_nao_vira_meio_a_meio(tmp_path: Path) -> None:
    """0,50 seco faria o leitor achar que a plataforma está em cima do muro.

    A verdade é que ela não mediu nada naquela janela, e as duas coisas levam
    a leituras opostas.
    """
    page = _pagina(tmp_path, [_mercado(gerador_proprio={"valor": 0.5, "max_uncertainty": True, "fontes": []})])
    assert "sem sinal na janela" in page


def test_trilha_ausente_e_declarada_ausente(tmp_path: Path) -> None:
    page = _pagina(tmp_path, [_mercado()])
    assert "ainda não publicada" in page


def test_discordancia_so_existe_quando_as_duas_mediram(tmp_path: Path) -> None:
    """Distância até uma ausência de medição não é discordância.

    Sem esta trava, um mercado sem sinal exibiria "50,0 pp de discordância"
    contra um 0,50 que ninguém mediu — número fabricado na coluna que existe
    justamente para chamar atenção.
    """
    com_sinal = _pagina(tmp_path, [_mercado(gerador_proprio={"valor": 0.6875, "max_uncertainty": False, "fontes": []})])
    assert "48.8 pp" in com_sinal  # |0.20 - 0.6875|

    sem_sinal = _pagina(tmp_path, [_mercado(gerador_proprio={"valor": 0.5, "max_uncertainty": True, "fontes": []})])
    assert "pp" not in sem_sinal.split("<tbody>")[1].split("</tbody>")[0]


def test_a_trilha_propria_nao_e_apresentada_como_preco(tmp_path: Path) -> None:
    """A distinção que impede a tela de mentir sobre o que ela mostra.

    O preço do contrato é o do consenso. A trilha de notícia é registro
    paralelo — se a página deixar de dizer isso, um leitor razoável conclui
    que a plataforma publica dois preços e não sabe qual é o dela.
    """
    page = _pagina(tmp_path, [_mercado(gerador_proprio={"valor": 0.6875, "max_uncertainty": False, "fontes": []})])
    assert "não</b> move o preço" in page or "não move o preço" in page
    assert "mesma régua" in page
