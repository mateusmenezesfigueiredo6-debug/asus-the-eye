# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector ClinicalTrials.gov — contagem de estudos por mês de início e país.

Os riscos específicos desta fonte, e por que cada teste existe:

1. **A contagem é DECLARADA pela API, não apurada por nós.** ``totalCount``
   ausente, string, booleano ou negativo não pode virar número em silêncio —
   um total que não dá para ler honestamente é quebra, não zero.

2. **Zero é resposta legítima da CONSULTA — não do mês.** A API declara 0
   quando nada casa com o filtro na hora da leitura; mas StartDate pode ser
   antecipado e registros chegam com atraso, então a contagem só assenta
   semanas depois do mês fechar. O conector devolve o 0 honesto; a folga de
   deadline é do desenho do mercado (doutrina no módulo do conector).

3. **O intervalo do mês tem de acabar no dia certo.** RANGE com fim fixo em
   dia 31 quebraria em fevereiro; fim em dia 28 subcontaria três dias de um
   mês de 31. O último dia (28/29/30/31, bissexto incluído) vem de
   ``calendar.monthrange`` e os testes o conferem por mês.

4. **A URL percent-encoded foi conferida ao vivo em 02/09/2026** — colchetes
   e vírgula como %5B/%5D/%2C devolveram o MESMO totalCount (46 para
   2026-08 + Brazil) que a forma crua. Os testes decodificam a query gravada
   pelo transporte falso e conferem cada parâmetro.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from asus_theye.markets.fonte_base import FonteError
from asus_theye.markets.fonte_clinicaltrials import (
    MAX_BYTES,
    PAGE_SIZE,
    TIMEOUT,
    FonteClinicalTrialsError,
    contagem_estudos_no_mes,
)
from asus_theye.net.http import HttpResponse


def resposta_com(total: object = 7) -> bytes:
    """Documento no formato conferido ao vivo em 02/09/2026: totalCount,
    studies (1 entrada, por pageSize=1) e nextPageToken no topo."""
    return json.dumps(
        {
            "totalCount": total,
            "studies": [
                {
                    "protocolSection": {"identificationModule": {"nctId": "NCT07797335"}},
                    "derivedSection": {},
                    "hasResults": False,
                }
            ],
            "nextPageToken": "abcdef",
        }
    ).encode("utf-8")


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes | None = None) -> None:
        self.status, self.body = status, resposta_com() if body is None else body

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


class TransporteQueGravaKwargs(TransporteFalso):
    """Além de responder, guarda os kwargs — prova o contrato de transporte."""

    def __init__(self, body: bytes | None = None) -> None:
        super().__init__(body=body)
        self.chamadas: list[dict] = []

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        self.chamadas.append(
            {"url": url, "headers": dict(headers), "timeout": timeout, "max_bytes": max_bytes}
        )
        return super().request(url, headers=headers, timeout=timeout, max_bytes=max_bytes)


class TransporteProibido:
    """Explode se for usado — prova que a validação vem antes de qualquer rede."""

    def request(self, url: str, *, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
        raise AssertionError("a validação deveria ter levantado antes de tocar a rede")


def query_da_unica_chamada(transporte: TransporteQueGravaKwargs) -> dict[str, str]:
    assert len(transporte.chamadas) == 1
    bruto = parse_qs(urlsplit(transporte.chamadas[0]["url"]).query, strict_parsing=True)
    assert all(len(valores) == 1 for valores in bruto.values())
    return {chave: valores[0] for chave, valores in bruto.items()}


def test_devolve_o_total_declarado_pela_api() -> None:
    """Caminho feliz: countTotal=true declara totalCount=7 — o conector devolve 7."""
    assert contagem_estudos_no_mes("2026-08", transport=TransporteFalso()) == 7


def test_zero_e_resposta_legitima_da_consulta() -> None:
    """totalCount=0 é 0 de verdade — a estabilização tardia é problema do deadline, não do conector."""
    transporte = TransporteFalso(body=resposta_com(total=0))
    assert contagem_estudos_no_mes("2026-08", transport=transporte) == 0


def test_http_fora_do_esperado_levanta_dizendo_o_codigo() -> None:
    """Status != 200 nunca vira contagem — levanta nomeando o código para o triage."""
    with pytest.raises(FonteClinicalTrialsError, match="HTTP 503"):
        contagem_estudos_no_mes("2026-08", transport=TransporteFalso(status=503))


def test_json_malformado_levanta() -> None:
    """Corpo que não é JSON (página de erro, HTML de proxy) não pode virar palpite."""
    with pytest.raises(FonteClinicalTrialsError, match="JSON válido"):
        contagem_estudos_no_mes("2026-08", transport=TransporteFalso(body=b"nao-e-json"))


def test_topo_que_nao_e_objeto_levanta() -> None:
    """JSON válido mas com topo lista/escalar é layout trocado — levanta, não indexa às cegas."""
    with pytest.raises(FonteClinicalTrialsError, match="objeto JSON"):
        contagem_estudos_no_mes("2026-08", transport=TransporteFalso(body=b"[1, 2, 3]"))


def test_totalCount_ausente_levanta() -> None:
    """Sem totalCount não há o que devolver — ausência de campo é quebra, não zero."""
    corpo = b'{"studies": [], "nextPageToken": null}'
    with pytest.raises(FonteClinicalTrialsError, match="totalCount"):
        contagem_estudos_no_mes("2026-08", transport=TransporteFalso(body=corpo))


@pytest.mark.parametrize("total", ["46", True, -1, 4.5])
def test_totalCount_que_nao_e_inteiro_nao_negativo_levanta(total: object) -> None:
    """String, booleano, negativo ou float no total é layout trocado — nunca vira contagem."""
    transporte = TransporteFalso(body=resposta_com(total=total))
    with pytest.raises(FonteClinicalTrialsError, match="inteiro não-negativo"):
        contagem_estudos_no_mes("2026-08", transport=transporte)


@pytest.mark.parametrize("mes", ["2026-8", "08/2026", "2026-13", "2026-00", "", "2026-08-31"])
def test_mes_de_referencia_malformado_levanta_antes_de_qualquer_rede(mes: str) -> None:
    """Formato errado (inclusive dia em vez de mês) levanta mostrando o valor, sem tocar a rede."""
    with pytest.raises(FonteClinicalTrialsError, match="formato inesperado"):
        contagem_estudos_no_mes(mes, transport=TransporteProibido())


@pytest.mark.parametrize("pais", ["", "   "])
def test_pais_vazio_levanta_antes_de_qualquer_rede(pais: str) -> None:
    """País vazio consultaria o mundo inteiro por acidente — levanta antes da rede."""
    with pytest.raises(FonteClinicalTrialsError, match="país"):
        contagem_estudos_no_mes("2026-08", pais=pais, transport=TransporteProibido())


def test_max_bytes_timeout_e_accept_viajam_na_chamada() -> None:
    """max_bytes é obrigatório na casa (corpo truncado = mentira): prova que ele viaja."""
    transporte = TransporteQueGravaKwargs()
    contagem_estudos_no_mes("2026-08", transport=transporte)
    chamada = transporte.chamadas[0]
    assert chamada["max_bytes"] == MAX_BYTES == 2_000_000
    assert chamada["timeout"] == TIMEOUT == 60
    assert chamada["headers"]["Accept"] == "application/json"
    assert chamada["url"].startswith("https://clinicaltrials.gov/api/v2/studies?")


def test_a_url_carrega_o_filtro_conferido_ao_vivo() -> None:
    """A consulta exata validada em 02/09/2026 (totalCount=46 para 2026-08 + Brazil)."""
    transporte = TransporteQueGravaKwargs()
    contagem_estudos_no_mes("2026-08", transport=transporte)
    query = query_da_unica_chamada(transporte)
    assert query == {
        "query.locn": "Brazil",
        "filter.advanced": "AREA[StartDate]RANGE[2026-08-01,2026-08-31]",
        "countTotal": "true",
        "pageSize": str(PAGE_SIZE),
    }


@pytest.mark.parametrize(
    ("mes", "fim_esperado"),
    [
        ("2026-02", "2026-02-28"),  # fevereiro comum
        ("2028-02", "2028-02-29"),  # bissexto
        ("2026-04", "2026-04-30"),  # mês de 30
        ("2026-12", "2026-12-31"),  # mês de 31
    ],
)
def test_o_intervalo_acaba_no_ultimo_dia_certo_do_mes(mes: str, fim_esperado: str) -> None:
    """Fim fixo em 31 quebraria fevereiro; fim em 28 subcontaria 3 dias — o fim é por mês."""
    transporte = TransporteQueGravaKwargs()
    contagem_estudos_no_mes(mes, transport=transporte)
    filtro = query_da_unica_chamada(transporte)["filter.advanced"]
    assert filtro == f"AREA[StartDate]RANGE[{mes}-01,{fim_esperado}]"


def test_pais_customizado_viaja_na_url() -> None:
    """O kwarg pais troca a localização consultada — inclusive nomes com espaço."""
    transporte = TransporteQueGravaKwargs()
    contagem_estudos_no_mes("2026-08", pais="United States", transport=transporte)
    assert query_da_unica_chamada(transporte)["query.locn"] == "United States"


def test_o_erro_da_casa_herda_de_FonteError() -> None:
    """Quem resolve mercados captura FonteError por mercado — este também tem de cair lá."""
    assert issubclass(FonteClinicalTrialsError, FonteError)
