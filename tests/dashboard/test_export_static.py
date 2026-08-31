# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do subcomando export-static e do módulo export_static."""

from __future__ import annotations

from asus_theye.audit.dados_pessoais import achar_cpf

import re

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
        "verificar.html",
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
    # A página do benchmark passou a herdar o invólucro de tema.py (pagina()),
    # que emite o h1 sem forçar CAPS. Verificamos a palavra sem casar caixa —
    # e as demais peças-âncora que provam que é ela.
    assert "benchmark" in html.lower()
    assert "Best score" in html
    assert "<svg" in html
    assert "<script>" not in html
    assert "<!doctype html>" in html.lower()


def test_exportar_index_linka_a_vitrine_e_nao_a_telemetria(tmp_path: Path) -> None:
    """A porta da frente mostra os dois produtos, não a instrumentação da obra.

    /projeto, /mlops e /benchmark continuam sendo GERADOS e acessíveis por URL —
    só não entram no menu. Um cliente não abre o site para ver o percentual de
    fases do projeto nem as corridas de ML.
    """
    resultado = exportar(tmp_path)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")
    for publica in ("mercados.html", "calibracao.html", "corrente.html", "evidencia.html", "api.html"):
        assert publica in html, f"a vitrine deixou de linkar {publica}"
    for interna in ("projeto.html", "mlops.html"):
        assert interna not in html, f"{interna} é telemetria interna e não pertence à vitrine"
        assert interna in resultado["gerados"], f"{interna} deve continuar sendo gerada e acessível por URL"
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
    assert "Markets" in index and "Ledger" in index
    assert "THE EYE" in index
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
            # data: URIs (ex.: favicon embutido) e absolutos externos não são links
            # a arquivos do dist/ — nunca devem entrar na verificação de link morto.
            if alvo.startswith(("http://", "https://", "#", "mailto:", "data:")):
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


def test_bundle_publico_exclui_fabrica_e_nao_vaza_terceiro(tmp_path: Path) -> None:
    """O bundle de lançamento mostra os produtos, não a instrumentação.

    E — trava de titularidade — o HTML público não pode carregar marca de
    terceiro (Palantir/Chaox) nem dado pessoal. As menções factuais à Chaox
    vivem só nos painéis internos, que este bundle exclui.
    """
    resultado = exportar(tmp_path, publico=True)
    for interno in ("projeto.html", "mlops.html", "benchmark.html"):
        assert interno not in resultado["gerados"], f"{interno} não devia estar no bundle público"
        assert not (tmp_path / interno).exists()
    # os produtos e a porta continuam
    for publico in ("index.html", "mercados.html", "corrente.html", "verificar.html"):
        assert publico in resultado["gerados"]

    # nenhuma marca de terceiro nem dado pessoal no que vai ao ar
    for arquivo in tmp_path.glob("*.html"):
        texto = arquivo.read_text(encoding="utf-8").lower()
        assert "palantir" not in texto, f"marca de terceiro em {arquivo.name}"
        assert "chaox" not in texto, f"marca de terceiro em {arquivo.name}"
        assert not achar_cpf(texto), f"dado pessoal em {arquivo.name}: {achar_cpf(texto)}"
        assert "@gmail.com" not in texto
