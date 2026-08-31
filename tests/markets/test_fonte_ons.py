# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector ONS — carga de energia diária por subsistema.

Os riscos específicos desta fonte, e por que cada teste existe:

1. **Ponto decimal, não separador de milhar.** O arquivo real traz
   ``46535.75866666667``. Se alguém copiar o tratamento numérico do conector do
   TSE (onde ponto É milhar), 46 mil MWmed viram 4,6 quatrilhões — calado, sem
   exceção, e o contrato liquida contra um número inventado.

2. **Dia futuro tem de ser UNKNOWN, nunca zero.** A carga verificada entra no
   CSV com ~3 dias de atraso. Um conector que devolvesse 0.0 para dia não
   publicado liquidaria todo contrato "a carga passa de X?" como NÃO, todo dia,
   até o atraso acabar.

3. **Subsistema desconhecido levanta.** Se o ONS criar ou renomear um
   subsistema, a linha não pode ser ignorada em silêncio.
"""

from __future__ import annotations

import pytest

from asus_theye.markets.fonte_base import FonteError
from asus_theye.markets.fonte_ons import (
    SUBSISTEMAS,
    FonteOnsError,
    carga_do_dia,
    ear_percentual_do_dia,
    mediana_do_subsistema,
    mediana_ear,
    ultimo_dia_publicado,
)
from asus_theye.net.http import HttpResponse

CABECALHO = "id_subsistema;nom_subsistema;din_instante;val_cargaenergiamwmed"


def csv_com(*linhas: str) -> bytes:
    return ("\n".join([CABECALHO, *linhas])).encode("utf-8")


#: Recorte fiel do arquivo real de 2026, incluindo a precisão que ele publica.
PADRAO = csv_com(
    "N;Norte;2026-08-27;9812.100000000000",
    "NE;Nordeste;2026-08-27;14001.500000000000",
    "SE;Sudeste/Centro-Oeste;2026-08-27;44100.250000000000",
    "N;Norte;2026-08-28;9934.260083333333",
    "NE;Nordeste;2026-08-28;14578.10354166667",
    "S;Sul;2026-08-28;16501.086166666664",
    "SE;Sudeste/Centro-Oeste;2026-08-28;46535.75866666667",
)


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes | None = None) -> None:
        self.status, self.body = status, PADRAO if body is None else body

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


def test_le_a_carga_do_dia_com_a_precisao_publicada() -> None:
    valor = carga_do_dia("2026-08-28", "SE", transport=TransporteFalso())
    assert valor == pytest.approx(46535.75866666667)


def test_o_ponto_e_decimal_e_nao_separador_de_milhar() -> None:
    # O defeito que este teste existe para impedir: tratar '.' como milhar
    # transformaria 46.535 MWmed em 4653575866666667. A ordem de grandeza da
    # carga do SE é dezenas de milhares — nunca quatrilhões.
    valor = carga_do_dia("2026-08-28", "SE", transport=TransporteFalso())
    assert 10_000 < valor < 100_000


def test_dia_nao_publicado_e_None_e_nunca_zero() -> None:
    # 29/08 não está no recorte: o ONS ainda não publicou.
    assert carga_do_dia("2026-08-29", "SE", transport=TransporteFalso()) is None


def test_dia_publicado_mas_subsistema_ausente_naquele_dia_e_None() -> None:
    # O Sul só aparece em 28/08 no recorte. Em 27/08 o dia existe, o subsistema
    # não — e isso continua sendo UNKNOWN, não zero.
    assert carga_do_dia("2026-08-27", "S", transport=TransporteFalso()) is None


@pytest.mark.parametrize("sigla", sorted(SUBSISTEMAS))
def test_aceita_os_quatro_subsistemas_do_sin(sigla: str) -> None:
    # Não deve levantar por causa da sigla; devolver None (não publicado) é ok.
    carga_do_dia("2026-08-28", sigla, transport=TransporteFalso())


def test_subsistema_desconhecido_levanta_em_vez_de_ignorar() -> None:
    with pytest.raises(FonteOnsError, match="não é do SIN"):
        carga_do_dia("2026-08-28", "CO", transport=TransporteFalso())


@pytest.mark.parametrize("dia", ["2026-8-28", "28/08/2026", "2026-13-01", "2026-08-32", ""])
def test_dia_malformado_levanta(dia: str) -> None:
    with pytest.raises(FonteOnsError, match="formato inesperado"):
        carga_do_dia(dia, "SE", transport=TransporteFalso())


def test_layout_mudado_levanta_nomeando_a_coluna_que_sumiu() -> None:
    corpo = b"id_subsistema;din_instante;carga\nSE;2026-08-28;46535.75\n"
    with pytest.raises(FonteOnsError, match="layout mudou"):
        carga_do_dia("2026-08-28", "SE", transport=TransporteFalso(body=corpo))


def test_csv_vazio_levanta() -> None:
    with pytest.raises(FonteOnsError, match="vazio"):
        carga_do_dia("2026-08-28", "SE", transport=TransporteFalso(body=CABECALHO.encode()))


def test_http_nao_200_levanta_dizendo_o_codigo() -> None:
    with pytest.raises(FonteOnsError, match="HTTP 503"):
        carga_do_dia("2026-08-28", "SE", transport=TransporteFalso(status=503))


def test_dia_duplicado_levanta_em_vez_de_escolher_um() -> None:
    corpo = csv_com(
        "SE;Sudeste/Centro-Oeste;2026-08-28;46535.75",
        "SE;Sudeste/Centro-Oeste;2026-08-28;99999.99",
    )
    with pytest.raises(FonteOnsError, match="2 vezes"):
        carga_do_dia("2026-08-28", "SE", transport=TransporteFalso(body=corpo))


def test_carga_nao_positiva_levanta_porque_o_sin_nao_desliga() -> None:
    corpo = csv_com("SE;Sudeste/Centro-Oeste;2026-08-28;0")
    with pytest.raises(FonteOnsError, match="não-positiva"):
        carga_do_dia("2026-08-28", "SE", transport=TransporteFalso(body=corpo))


def test_valor_nao_numerico_levanta() -> None:
    corpo = csv_com("SE;Sudeste/Centro-Oeste;2026-08-28;indisponível")
    with pytest.raises(FonteOnsError, match="não numérico"):
        carga_do_dia("2026-08-28", "SE", transport=TransporteFalso(body=corpo))


def test_ultimo_dia_publicado_mede_a_defasagem_em_vez_de_assumi_la() -> None:
    assert ultimo_dia_publicado(2026, transport=TransporteFalso()) == "2026-08-28"


def test_mediana_sai_da_propria_serie() -> None:
    # Regra da casa: limiar é a mediana lida da fonte, nunca escolhida a dedo.
    corpo = csv_com(
        "SE;Sudeste/Centro-Oeste;2026-08-26;10.0",
        "SE;Sudeste/Centro-Oeste;2026-08-27;20.0",
        "SE;Sudeste/Centro-Oeste;2026-08-28;60.0",
    )
    assert mediana_do_subsistema(2026, "SE", transport=TransporteFalso(body=corpo)) == 20.0


def test_mediana_de_subsistema_sem_dado_levanta() -> None:
    corpo = csv_com("SE;Sudeste/Centro-Oeste;2026-08-28;46535.75")
    with pytest.raises(FonteOnsError, match="nenhuma carga de N"):
        mediana_do_subsistema(2026, "N", transport=TransporteFalso(body=corpo))


def test_o_erro_da_casa_herda_de_FonteError() -> None:
    # Quem trata fonte genericamente na rodada tem de pegar este também.
    assert issubclass(FonteOnsError, FonteError)


# ---------------------------------------------------------------------------
# EAR — energia armazenada (nível dos reservatórios), série DIÁRIA em %.
#
# Riscos próprios desta série, distintos dos da carga:
#
# 1. **Espaço à direita na sigla.** O ONS publica ``'S '`` e ``'S  '`` neste
#    arquivo, enquanto o de carga vem limpo. Comparar sem strip faria o Sul
#    não existir — e a ausência seria lida como "ainda não publicado", que é
#    exatamente a falha silenciosa que este conector existe para não ter.
#
# 2. **Zero é o cenário de racionamento.** Devolver 0.0 para dia não publicado
#    seria o pior erro possível: liquidaria "sim, o reservatório está zerado".
# ---------------------------------------------------------------------------

CABECALHO_EAR = (
    "id_subsistema;nom_subsistema;ear_data;ear_max_subsistema;"
    "ear_verif_subsistema_mwmes;ear_verif_subsistema_percentual"
)

EAR_PADRAO = (
    "\n".join(
        [
            CABECALHO_EAR,
            "SE;SUDESTE;2026-08-29;204615.328;119493.645;58.3992",
            # o Sul vem com espaço à direita no arquivo real — de propósito aqui
            "S ;SUL;2026-08-29;20459.242;16437.349;80.3419",
            "NE;NORDESTE;2026-08-29;51000.000;30000.000;58.8235",
            "SE;SUDESTE;2026-08-28;204615.328;119000.000;58.1583",
            "S  ;SUL;2026-08-28;20459.242;16000.000;78.2050",
        ]
    )
).encode("utf-8")


class TransporteEar:
    def __init__(self, status: int = 200, body: bytes | None = None) -> None:
        self.status, self.body = status, EAR_PADRAO if body is None else body

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


def test_ear_le_o_percentual_do_dia() -> None:
    assert ear_percentual_do_dia(
        "2026-08-29", "SE", transport=TransporteEar()
    ) == pytest.approx(58.3992)


def test_ear_acha_o_sul_apesar_do_espaco_a_direita_na_sigla() -> None:
    # Sem strip() o Sul sumiria e viraria "não publicado" — falha silenciosa.
    assert ear_percentual_do_dia(
        "2026-08-29", "S", transport=TransporteEar()
    ) == pytest.approx(80.3419)
    assert ear_percentual_do_dia(
        "2026-08-28", "S", transport=TransporteEar()
    ) == pytest.approx(78.2050)


def test_ear_dia_nao_publicado_e_None_nunca_zero() -> None:
    # Zero aqui significaria reservatório vazio — o cenário de racionamento.
    assert ear_percentual_do_dia("2026-08-30", "SE", transport=TransporteEar()) is None


def test_ear_acima_de_100_por_cento_levanta() -> None:
    corpo = "\n".join(
        [CABECALHO_EAR, "SE;SUDESTE;2026-08-29;204615.328;119493.645;158.0"]
    ).encode()
    with pytest.raises(FonteOnsError, match="acima de 100"):
        ear_percentual_do_dia("2026-08-29", "SE", transport=TransporteEar(body=corpo))


def test_ear_layout_mudado_levanta() -> None:
    corpo = b"id_subsistema;data;percentual\nSE;2026-08-29;58.4\n"
    with pytest.raises(FonteOnsError, match="layout mudou"):
        ear_percentual_do_dia("2026-08-29", "SE", transport=TransporteEar(body=corpo))


def test_ear_subsistema_desconhecido_levanta() -> None:
    with pytest.raises(FonteOnsError, match="não é do SIN"):
        ear_percentual_do_dia("2026-08-29", "CO", transport=TransporteEar())


def test_mediana_ear_usa_janela_recente() -> None:
    # Duas leituras do SE: 58,3992 e 58,1583 -> mediana é a média das duas.
    assert mediana_ear(2026, "SE", transport=TransporteEar()) == pytest.approx(
        (58.3992 + 58.1583) / 2
    )


def test_mediana_ear_de_subsistema_sem_dado_levanta() -> None:
    with pytest.raises(FonteOnsError, match="nenhum EAR de N"):
        mediana_ear(2026, "N", transport=TransporteEar())
