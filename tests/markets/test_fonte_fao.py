# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector FAO — Food Price Index (FFPI) mensal.

Os riscos específicos desta fonte, e por que cada teste existe:

1. **Mês ausente tem de ser UNKNOWN, nunca zero.** A FAO publica o mês M no
   início de M+1 (em 01/09/2026, julho era o último mês no CSV). Um conector
   que devolvesse 0.0 para mês não publicado liquidaria "o índice caiu abaixo
   de X?" como SIM todo início de mês, contra um número que não existe.

2. **O cabeçalho NÃO é a primeira linha.** O CSV real tem título, base
   (``2014-2016=100``) e uma linha vazia decorativa antes dos dados. Um parser
   ingênuo de ``DictReader`` leria o título como cabeçalho e não acharia nada —
   silenciosamente.

3. **Ponto decimal, conferido ao vivo.** O arquivo real traz ``64.4`` e
   ``44.59``. Vírgula num valor é layout novo e levanta — trocar vírgula por
   ponto às cegas poderia mascarar um separador de milhar.

4. **A página oferece xlsx ao lado do CSV.** Um link trocado no CMS entrega
   planilha binária (``PK..``) que até decodifica parcialmente como UTF-8 — o
   diagnóstico tem de ser próprio e claro, não um erro de parse qualquer.
"""

from __future__ import annotations

import pytest

from asus_theye.markets.fonte_base import FonteError
from asus_theye.markets.fonte_fao import FonteFAOError, indice_no_mes, serie_ffpi
from asus_theye.net.http import HttpResponse

CABECALHO = "Date,Food Price Index,Meat,Dairy,Cereals,Oils,Sugar"


def csv_fao(*linhas_de_dado: str) -> bytes:
    """CSV sintético com a MESMA moldura do arquivo real conferido em 01/09/2026:
    título, base, cabeçalho, linha vazia decorativa e então os dados."""
    return "\n".join(
        [
            "FAO Food Price Index,,,,,,",
            "2014-2016=100,,,,,,",
            CABECALHO,
            ",,,,,,",
            *linhas_de_dado,
        ]
    ).encode("utf-8")


#: Recorte fiel do arquivo real, incluindo a precisão que ele publica
#: (``44.59`` com duas casas em 1990-01; uma casa nos meses recentes).
PADRAO = csv_fao(
    "1990-01,64.4,74.3,53.5,64.1,44.59,87.9",
    "2026-05,131.0,131.3,119.1,114.2,185.0,95.1",
    "2026-06,130.3,131.3,117.0,110.0,192.0,90.0",
    "2026-07,131.1,127.7,116.2,113.8,195.7,95.0",
)


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes | None = None) -> None:
        self.status, self.body = status, PADRAO if body is None else body

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


def test_le_o_indice_do_mes_com_a_precisao_publicada() -> None:
    valor = indice_no_mes("2026-07", transport=TransporteFalso())
    assert valor == pytest.approx(131.1)


def test_o_ponto_e_decimal_e_nao_separador_de_milhar() -> None:
    # 44.59 e 64.4 vêm do arquivo real. Se alguém tratar '.' como milhar,
    # 64.4 pontos viram 644 — e o índice nunca passou de ~160 na história.
    valor = indice_no_mes("1990-01", transport=TransporteFalso())
    assert valor == pytest.approx(64.4)
    assert valor is not None and 10 < valor < 1000


def test_mes_ainda_nao_publicado_e_None_e_nunca_zero() -> None:
    # Agosto não está no recorte — como não estava no CSV real em 01/09/2026.
    assert indice_no_mes("2026-08", transport=TransporteFalso()) is None


def test_mes_anterior_ao_inicio_da_serie_tambem_e_None() -> None:
    # A série começa em 1990-01. Antes disso é o mesmo UNKNOWN, não erro.
    assert indice_no_mes("1989-12", transport=TransporteFalso()) is None


def test_serie_ffpi_devolve_o_mapa_completo_validado() -> None:
    serie = serie_ffpi(transport=TransporteFalso())
    assert serie == {
        "1990-01": pytest.approx(64.4),
        "2026-05": pytest.approx(131.0),
        "2026-06": pytest.approx(130.3),
        "2026-07": pytest.approx(131.1),
    }


def test_csv_sem_a_coluna_do_indice_levanta() -> None:
    corpo = "\n".join(
        [
            "FAO Food Price Index,,,,,",
            "2014-2016=100,,,,,",
            "Date,Meat,Dairy,Cereals,Oils,Sugar",
            "2026-07,127.7,116.2,113.8,195.7,95.0",
        ]
    ).encode("utf-8")
    with pytest.raises(FonteFAOError, match="Food Price Index"):
        indice_no_mes("2026-07", transport=TransporteFalso(body=corpo))


def test_csv_sem_linha_de_cabecalho_levanta() -> None:
    # Sem a linha que começa com 'Date', nada garante qual coluna é o índice.
    corpo = b"FAO Food Price Index,,\n2014-2016=100,,\n1990-01,64.4,74.3\n"
    with pytest.raises(FonteFAOError, match="cabeçalho"):
        indice_no_mes("1990-01", transport=TransporteFalso(body=corpo))


def test_http_nao_200_levanta_dizendo_o_codigo() -> None:
    with pytest.raises(FonteFAOError, match="HTTP 503"):
        indice_no_mes("2026-07", transport=TransporteFalso(status=503))


@pytest.mark.parametrize(
    "assinatura",
    [b"PK\x03\x04conteudo-de-zip", b"\xd0\xcf\x11\xe0planilha-ole"],
    ids=["xlsx", "xls-antigo"],
)
def test_planilha_binaria_no_lugar_do_csv_levanta_com_mensagem_clara(assinatura: bytes) -> None:
    # A página da FAO oferece xlsx AO LADO do CSV; link trocado no CMS entrega
    # binário aqui — e 'PK..' até decodifica como UTF-8, então o diagnóstico
    # genérico de decodificação não pegaria.
    with pytest.raises(FonteFAOError, match="planilha binária"):
        indice_no_mes("2026-07", transport=TransporteFalso(body=assinatura))


def test_corpo_nao_utf8_levanta_com_mensagem_clara() -> None:
    with pytest.raises(FonteFAOError, match="não decodifica em UTF-8"):
        indice_no_mes("2026-07", transport=TransporteFalso(body=b"\xff\xfe corpo qualquer"))


@pytest.mark.parametrize("mes", ["2026-7", "07/2026", "2026-13", "", "202607"])
def test_mes_referencia_malformado_levanta(mes: str) -> None:
    with pytest.raises(FonteFAOError, match="formato inesperado"):
        indice_no_mes(mes, transport=TransporteFalso())


def test_mes_repetido_levanta_em_vez_de_sobrescrever() -> None:
    corpo = csv_fao(
        "2026-07,131.1,127.7,116.2,113.8,195.7,95.0",
        "2026-07,999.0,127.7,116.2,113.8,195.7,95.0",
    )
    with pytest.raises(FonteFAOError, match="repetido"):
        indice_no_mes("2026-07", transport=TransporteFalso(body=corpo))


def test_valor_nao_numerico_levanta() -> None:
    corpo = csv_fao("2026-07,n.d.,127.7,116.2,113.8,195.7,95.0")
    with pytest.raises(FonteFAOError, match="não numérico"):
        indice_no_mes("2026-07", transport=TransporteFalso(body=corpo))


def test_mes_listado_sem_valor_levanta_em_vez_de_pular() -> None:
    # Mês presente com índice vazio não é "não publicado" — é anomalia de
    # layout, e pular a linha em silêncio a transformaria em UNKNOWN falso.
    corpo = csv_fao("2026-07,,127.7,116.2,113.8,195.7,95.0")
    with pytest.raises(FonteFAOError, match="vazio"):
        indice_no_mes("2026-07", transport=TransporteFalso(body=corpo))


def test_virgula_decimal_levanta_em_vez_de_adivinhar() -> None:
    # A FAO usa ponto (conferido ao vivo). '131,1' entre aspas é layout novo.
    corpo = csv_fao('2026-07,"131,1",127.7,116.2,113.8,195.7')
    with pytest.raises(FonteFAOError, match="vírgula no valor"):
        indice_no_mes("2026-07", transport=TransporteFalso(body=corpo))


def test_indice_nao_positivo_levanta() -> None:
    corpo = csv_fao("2026-07,0,127.7,116.2,113.8,195.7,95.0")
    with pytest.raises(FonteFAOError, match="não-positivo"):
        indice_no_mes("2026-07", transport=TransporteFalso(body=corpo))


def test_indice_acima_do_teto_de_sanidade_levanta() -> None:
    # Máxima histórica ~160 pontos. 1311 é troca de base/unidade, não comida cara.
    corpo = csv_fao("2026-07,1311.0,127.7,116.2,113.8,195.7,95.0")
    with pytest.raises(FonteFAOError, match="acima de 1000"):
        indice_no_mes("2026-07", transport=TransporteFalso(body=corpo))


def test_linha_curta_sem_a_coluna_do_indice_levanta() -> None:
    corpo = csv_fao("2026-03")
    with pytest.raises(FonteFAOError, match="colunas"):
        indice_no_mes("2026-03", transport=TransporteFalso(body=corpo))


def test_rodape_inesperado_levanta_em_vez_de_ignorar() -> None:
    # Se a FAO acrescentar 'Source: ...' no fim, alguém tem de olhar antes de
    # liquidar — linha não-mês não se ignora em silêncio.
    corpo = csv_fao(
        "2026-07,131.1,127.7,116.2,113.8,195.7,95.0",
        "Source: FAO,,,,,,",
    )
    with pytest.raises(FonteFAOError, match="não começa com mês"):
        indice_no_mes("2026-07", transport=TransporteFalso(body=corpo))


def test_csv_sem_nenhuma_linha_de_dado_levanta() -> None:
    with pytest.raises(FonteFAOError, match="nenhuma linha de dado"):
        serie_ffpi(transport=TransporteFalso(body=csv_fao()))


def test_o_erro_da_casa_herda_de_FonteError() -> None:
    # Quem trata fonte genericamente na rodada tem de pegar este também.
    assert issubclass(FonteFAOError, FonteError)
