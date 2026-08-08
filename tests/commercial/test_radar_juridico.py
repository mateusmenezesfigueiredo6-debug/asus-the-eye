"""Testes do Radar Juridico — a qualidade do lead e o produto.

Cobrem os quatro criterios que separam lead de lixo: descarte de texto padrao
de edital, extracao da entidade nomeada, deduplicacao e guarda de dado pessoal.
Tambem verificam escape de HTML, ja que a edicao vai para a web.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.comercial.radar_juridico import (
    ONT,
    _chave,
    extrair,
    render,
    sem_dado_pessoal,
)

RECUPERACAO = next(n for n in ONT["nichos"] if n["niche_id"] == "recuperacao")
SEM_PADRAO = next(n for n in ONT["nichos"] if "regex_entidade" not in n)


def gazette(
    trecho: str,
    municipio: str = "Planalto",
    uf: str = "SP",
    data: str = "2026-07-31",
    url: str = "https://exemplo/a.pdf",
) -> dict:
    return {"excerpts": [trecho], "territory_name": municipio, "state_code": uf, "date": data, "url": url}


# ------------------------------------------------------- descarte de ruido
def test_exigencia_de_certidao_nao_e_lead():
    """O defeito original do produto: edital pedindo certidao virava 'lead'."""
    ruido = (
        "b) Certidao negativa de Recuperacao Judicial ou Extrajudicial "
        "expedida pelo distribuidor da sede da pessoa juridica."
    )
    assert extrair(RECUPERACAO, [gazette(ruido)]) == []


def test_qualificacao_economico_financeira_e_descartada():
    ruido = (
        "Documentos relativos a Qualificacao Economico-Financeira "
        "(Certidao Negativa de Falencia, Concordata, Recuperacao Judicial)."
    )
    assert extrair(RECUPERACAO, [gazette(ruido)]) == []


def test_empresa_nomeada_e_lead():
    real = (
        "AMAZONIA PESCADOS LTDA EM RECUPERACAO JUDICIAL, inscrita com CNPJ "
        "n 27.591.142/0001-27, torna publico que requereu licenca ambiental."
    )
    leads = extrair(RECUPERACAO, [gazette(real)])
    assert len(leads) == 1
    assert "AMAZONIA PESCADOS" in leads[0]["entidade"]
    assert leads[0]["municipio"] == "Planalto"
    assert leads[0]["url"] == "https://exemplo/a.pdf"


# --------------------------------------------------------- deduplicacao
def test_mesma_empresa_em_municipios_diferentes_entra_uma_vez():
    texto = "OI S.A. EM RECUPERACAO JUDICIAL prestou servicos de conectividade."
    leads = extrair(
        RECUPERACAO,
        [
            gazette(texto, "Mascote", "BA"),
            gazette(texto, "Vicosa", "AL", url="https://exemplo/b.pdf"),
        ],
    )
    assert len(leads) == 1, "o mesmo ato replicado em varios diarios nao e lead novo"


def test_dedup_ignora_sufixo_societario_e_acento():
    assert _chave("CONSTRUTORA LYTORANEA S/A") == _chave("Construtora Lytoranea LTDA")


def test_nicho_sem_padrao_tambem_deduplica():
    """Defeito real: dedup so valia para nichos com regex de entidade."""
    texto = "Ato administrativo identico publicado em varios municipios do estado."
    leads = extrair(
        SEM_PADRAO,
        [
            gazette(texto, "Cidade A"),
            gazette(texto, "Cidade B", url="https://exemplo/b.pdf"),
        ],
    )
    assert len(leads) == 1


def test_nicho_sem_padrao_aceita_excerto_sem_entidade():
    leads = extrair(SEM_PADRAO, [gazette("Texto qualquer de ato oficial publicado.")])
    assert len(leads) == 1
    assert leads[0]["entidade"] is None


# ------------------------------------------------------ dado pessoal
def test_excerto_com_cpf_nao_entra_na_edicao():
    com_cpf = (
        "FULANO COMERCIO LTDA EM RECUPERACAO JUDICIAL, socio inscrito no CPF 123.456.789-00, comunica aos credores."
    )
    assert sem_dado_pessoal(com_cpf) is False
    assert extrair(RECUPERACAO, [gazette(com_cpf)]) == []


def test_cnpj_nao_e_bloqueado():
    """CNPJ e dado de pessoa juridica, publico por definicao."""
    assert sem_dado_pessoal("CNPJ 27.591.142/0001-27 em recuperacao") is True


# ------------------------------------------------------------ limites
def test_um_lead_por_publicacao():
    dois = (
        "ALFA COMERCIO LTDA EM RECUPERACAO JUDICIAL e tambem BETA "
        "INDUSTRIA LTDA EM RECUPERACAO JUDICIAL constam do mesmo ato."
    )
    assert len(extrair(RECUPERACAO, [gazette(dois)])) == 1


def test_edicao_respeita_o_teto_de_leads():
    from apps.comercial.radar_juridico import MAX_LEADS

    nomes = [f"EMPRESA {chr(65 + i)}{chr(65 + i)}{chr(65 + i)}{chr(65 + i)} COMERCIO" for i in range(MAX_LEADS + 8)]
    gazettes = [
        gazette(f"{nome} LTDA EM RECUPERACAO JUDICIAL informa.", url=f"https://exemplo/{i}.pdf")
        for i, nome in enumerate(nomes)
    ]
    assert len(extrair(RECUPERACAO, gazettes)) == MAX_LEADS


def test_nome_curto_demais_e_descartado():
    assert extrair(RECUPERACAO, [gazette("XY EM RECUPERACAO JUDICIAL informa.")]) == []


# ------------------------------------------------------------ render
def test_edicao_vazia_admite_que_nao_ha_lead():
    saida = render(RECUPERACAO, [], 500, 14)
    assert "Nenhum caso novo" in saida
    assert "500" in saida, "o total apurado continua sendo declarado"


def test_render_escapa_html_do_diario():
    veneno = "SELLIX AMBIENTAL LTDA EM RECUPERACAO JUDICIAL <script>alert(1)</script> comunica aos credores."
    leads = extrair(RECUPERACAO, [gazette(veneno)])
    saida = render(RECUPERACAO, leads, 1, 14)
    assert "<script>" not in saida
    assert "&lt;script&gt;" in saida


def test_render_traz_link_do_ato_de_origem():
    real = "SELLIX AMBIENTAL LTDA EM RECUPERACAO JUDICIAL comunica aos credores."
    leads = extrair(RECUPERACAO, [gazette(real)])
    saida = render(RECUPERACAO, leads, 1, 14)
    assert "https://exemplo/a.pdf" in saida
    assert "Conferir no diario oficial" in saida


def test_render_declara_a_janela_e_a_expressao():
    saida = render(RECUPERACAO, [], 10, 21)
    assert "JANELA DE 21 DIAS" in saida
    assert "RECUPERA" in saida.upper(), "a expressao vigiada e declarada na capa"
