# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do subcomando export-static e do módulo export_static."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.dashboard.export_static import exportar


def test_exportar_gera_html_basico(tmp_path: Path) -> None:
    """Painéis base devem ser gerados sem ASUS_MARKETS_DB; markets é pulado."""
    resultado = exportar(tmp_path)
    assert set(resultado["gerados"]) == {
        "projeto.html",
        "evidencia.html",
        "calibracao.html",
        "corrente.html",
        "benchmark.html",
        "mercados.html",
        "mlops.html",
        "api.html",
        "index.html",
    }
    assert len(resultado["pulados"]) == 1
    assert "markets" in resultado["pulados"][0]


def test_exportar_conteudo_projeto(tmp_path: Path) -> None:
    exportar(tmp_path)
    html = (tmp_path / "projeto.html").read_text(encoding="utf-8")
    assert "MEDIÇÃO DO PROJETO" in html
    assert "<!doctype html>" in html.lower()


def test_exportar_conteudo_evidencia(tmp_path: Path) -> None:
    exportar(tmp_path)
    html = (tmp_path / "evidencia.html").read_text(encoding="utf-8")
    assert "EVIDÊNCIA" in html
    assert "<!doctype html>" in html.lower()


def test_exportar_conteudo_benchmark(tmp_path: Path) -> None:
    exportar(tmp_path)
    html = (tmp_path / "benchmark.html").read_text(encoding="utf-8")
    assert "BENCHMARK" in html
    assert "<svg" in html
    assert "<script>" not in html
    assert "<!doctype html>" in html.lower()


def test_exportar_index_tem_links(tmp_path: Path) -> None:
    exportar(tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "projeto.html" in html
    assert "evidencia.html" in html
    assert "corrente.html" in html
    assert "mercados.html" in html  # a vitrine linka produto, não telemetria
    assert "api.html" in html
    assert "<!doctype html>" in html.lower()


def test_exportar_markets_com_db_ausente_listado_em_pulados(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)
    resultado = exportar(tmp_path)
    assert any("markets" in p for p in resultado["pulados"])
    assert not (tmp_path / "markets.html").exists()


def test_exportar_markets_com_db_existente(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    duckdb = pytest.importorskip("duckdb")

    db = tmp_path / "mini.duckdb"
    con = duckdb.connect(str(db))
    con.execute(
        "create table mercados (id varchar, produto varchar, etiqueta varchar, "
        "pergunta_leiga varchar, data_abertura varchar, data_limite varchar, "
        "fonte_resolucao varchar, criterio_resolucao varchar, limiar double, status varchar)"
    )
    con.execute(
        "create table resolucoes (mercado_id varchar, timestamp varchar, resultado_real integer, "
        "valor_observado double, brier_do_contrato double, acerto integer, fonte_confirmacao varchar)"
    )
    con.close()

    monkeypatch.setenv("ASUS_MARKETS_DB", str(db))
    resultado = exportar(tmp_path)
    assert "markets.html" in resultado["gerados"]
    assert all("markets" not in p for p in resultado["pulados"])
    html = (tmp_path / "markets.html").read_text(encoding="utf-8")
    assert "MERCADOS PREDITIVOS" in html


def test_cli_export_static_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)
    from asus_theye.cli import main

    code = main(["export-static", "--out", str(tmp_path), "--json"])
    assert code == 0


def test_cli_export_static_json_valido(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)
    from asus_theye.cli import main

    main(["export-static", "--out", str(tmp_path), "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "gerados" in data and "pulados" in data


def test_export_inclui_mercados_html(tmp_path, monkeypatch):
    """O painel dos mercados vivos entra no site estático."""
    from asus_theye.dashboard.export_static import exportar

    monkeypatch.delenv("ASUS_MARKETS_DB", raising=False)
    resultado = exportar(tmp_path)
    assert "mercados.html" in resultado["gerados"]
    conteudo = (tmp_path / "mercados.html").read_text(encoding="utf-8")
    assert "probabilidade com proveniência" in conteudo or "MERCADOS" in conteudo


# ------------------------------------------------------------ o site publicado


def test_index_e_a_landing_e_nao_uma_lista_de_arquivos(tmp_path: Path) -> None:
    """A porta da frente do produto não pode ser um <ul> de nomes de arquivo.

    Havia um _INDEX_TEMPLATE próprio em export_static.py, escrito antes de
    landing.py existir: o index publicado tinha 963 bytes e listava
    "projeto.html", "evidencia.html"… A landing real, com os dois produtos e os
    números vivos, nunca chegava ao dist/. Este teste falha se alguém
    reintroduzir um índice cru.
    """
    from asus_theye.dashboard.export_static import exportar

    exportar(tmp_path)
    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "THE EYE Markets" in index and "THE EYE Ledger" in index
    assert "ASUS THE EYE" in index
    assert len(index) > 3000, "index pequeno demais para ser a landing"


def test_todo_link_do_site_aponta_para_arquivo_existente(tmp_path: Path) -> None:
    """Link morto em site publicado é pior do que site não publicado.

    A navegação emite rotas absolutas (/mercados) no servidor; no dist/ os
    arquivos são mercados.html. Depender do host resolver URL sem extensão é
    apostar numa configuração que pode não existir — este teste prova que não
    dependemos.
    """
    import re

    from asus_theye.dashboard.export_static import exportar

    resultado = exportar(tmp_path)
    quebrados = []
    for pagina in resultado["gerados"]:
        html = (tmp_path / pagina).read_text(encoding="utf-8")
        for alvo in re.findall(r'href="([^"]+)"', html):
            if alvo.startswith(("http://", "https://", "#", "mailto:")):
                continue
            if not (tmp_path / alvo).exists():
                quebrados.append(f"{pagina} -> {alvo}")
    assert not quebrados, f"links mortos no site publicado: {quebrados}"


def test_todo_painel_publicado_carrega_o_aviso_de_escopo(tmp_path: Path) -> None:
    """Sem isto, 'mercados preditivos' em PT-BR pode ser lido como casa de apostas."""
    from asus_theye.dashboard.export_static import exportar

    resultado = exportar(tmp_path)
    sem_aviso = [
        p for p in resultado["gerados"] if "não é casa de apostas" not in (tmp_path / p).read_text(encoding="utf-8")
    ]
    assert not sem_aviso, f"páginas publicadas sem o aviso de escopo: {sem_aviso}"
