# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector CISA KEV — catálogo de vulnerabilidades exploradas conhecidas.

Os riscos específicos desta fonte, e por que cada teste existe:

1. **Zero é legítimo AQUI — e só aqui.** O KEV é um catálogo completo e
   enumerável, não uma série temporal com defasagem: mês sem entrada conta 0
   de verdade. O risco é o inverso do ONS — alguém "corrigir" o 0 para None
   por analogia e transformar resposta honesta em UNKNOWN falso.

2. **Documento parcial não pode contar.** O feed declara ``count``; se a
   lista vier com tamanho diferente, o documento está truncado ou
   inconsistente, e contar sobre ele seria liquidar contra um catálogo que a
   própria CISA diz estar errado.

3. **Entrada sem data não pode ser pulada em silêncio.** Um ``dateAdded``
   ausente ou fora de aaaa-mm-dd não dá para incluir nem excluir honestamente
   — pular calado subcontaria o mês sem ninguém perceber.
"""

from __future__ import annotations

import json

import pytest

from asus_theye.markets.fonte_base import FonteError
from asus_theye.markets.fonte_cisa import (
    MAX_BYTES,
    TIMEOUT,
    FonteCISAError,
    catalogo_kev,
    contagem_kev_no_mes,
)
from asus_theye.net.http import HttpResponse


def catalogo_com(*entradas: dict, count: int | None = None) -> bytes:
    """Documento no formato conferido ao vivo em 01/09/2026."""
    return json.dumps(
        {
            "title": "CISA Catalog of Known Exploited Vulnerabilities",
            "catalogVersion": "2026.09.01",
            "dateReleased": "2026-09-01T19:22:46.2162Z",
            "count": len(entradas) if count is None else count,
            "vulnerabilities": list(entradas),
        }
    ).encode("utf-8")


#: Recorte fiel: duas entradas de agosto/2026 e o Log4Shell, adicionado ao
#: catálogo real em 10/12/2021 — datas sempre aaaa-mm-dd, sem hora.
PADRAO = catalogo_com(
    {"cveID": "CVE-2026-82078", "vendorProject": "PaperCut", "dateAdded": "2026-08-31"},
    {"cveID": "CVE-2026-50001", "vendorProject": "Exemplo", "dateAdded": "2026-08-01"},
    {"cveID": "CVE-2021-44228", "vendorProject": "Apache", "dateAdded": "2021-12-10"},
)


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes | None = None) -> None:
        self.status, self.body = status, PADRAO if body is None else body

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


class TransporteQueGravaKwargs(TransporteFalso):
    """Além de responder, guarda os kwargs — prova o contrato de transporte."""

    def __init__(self) -> None:
        super().__init__()
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


def test_conta_os_cves_do_mes_pedido() -> None:
    """Caminho feliz: só o mês pedido conta — 2 de agosto, 1 de dezembro/21."""
    assert contagem_kev_no_mes("2026-08", transport=TransporteFalso()) == 2
    assert contagem_kev_no_mes("2021-12", transport=TransporteFalso()) == 1


def test_mes_sem_entrada_conta_zero_legitimo() -> None:
    """Catálogo completo é enumerável: mês sem entrada é 0 de verdade, não UNKNOWN."""
    assert contagem_kev_no_mes("2026-07", transport=TransporteFalso()) == 0


def test_mes_futuro_conta_o_que_existe_no_catalogo() -> None:
    """Mês futuro devolve a contagem do que EXISTE hoje — 0 — como o critério declara."""
    assert contagem_kev_no_mes("2027-01", transport=TransporteFalso()) == 0


def test_http_fora_do_esperado_levanta_dizendo_o_codigo() -> None:
    """Status != 200 nunca vira contagem — levanta nomeando o código para o triage."""
    with pytest.raises(FonteCISAError, match="HTTP 503"):
        contagem_kev_no_mes("2026-08", transport=TransporteFalso(status=503))


def test_json_malformado_levanta() -> None:
    """Corpo que não é JSON (página de erro, HTML de proxy) não pode virar palpite."""
    with pytest.raises(FonteCISAError, match="JSON válido"):
        contagem_kev_no_mes("2026-08", transport=TransporteFalso(body=b"nao-e-json"))


def test_topo_que_nao_e_objeto_levanta() -> None:
    """JSON válido mas com topo lista/escalar é layout trocado — levanta, não indexa às cegas."""
    with pytest.raises(FonteCISAError, match="objeto JSON"):
        catalogo_kev(transport=TransporteFalso(body=b"[1, 2, 3]"))


def test_vulnerabilities_ausente_levanta() -> None:
    """Sem a lista o catálogo não conta nada — ausência de campo é quebra, não zero."""
    with pytest.raises(FonteCISAError, match="layout mudou"):
        contagem_kev_no_mes("2026-08", transport=TransporteFalso(body=b'{"count": 0}'))


def test_vulnerabilities_nao_lista_levanta() -> None:
    """'vulnerabilities' como objeto/escalar é o mesmo defeito de layout — levanta."""
    corpo = b'{"count": 1, "vulnerabilities": {"cveID": "CVE-2026-1"}}'
    with pytest.raises(FonteCISAError, match="layout mudou"):
        contagem_kev_no_mes("2026-08", transport=TransporteFalso(body=corpo))


def test_count_divergente_do_tamanho_da_lista_levanta() -> None:
    """count != len(lista) é documento truncado — contar sobre ele seria mentir com número."""
    corpo = catalogo_com({"cveID": "CVE-2026-1", "dateAdded": "2026-08-01"}, count=5)
    with pytest.raises(FonteCISAError, match="inconsistente"):
        contagem_kev_no_mes("2026-08", transport=TransporteFalso(body=corpo))


@pytest.mark.parametrize("mes", ["2026-8", "08/2026", "2026-13", "2026-00", "", "2026-08-31"])
def test_mes_de_referencia_malformado_levanta_antes_de_qualquer_rede(mes: str) -> None:
    """Formato errado (inclusive dia em vez de mês) levanta mostrando o valor, sem tocar a rede."""
    with pytest.raises(FonteCISAError, match="formato inesperado"):
        contagem_kev_no_mes(mes, transport=TransporteProibido())


def test_entrada_sem_dateAdded_levanta_em_vez_de_pular() -> None:
    """Entrada sem data não dá para incluir nem excluir — pular calado subcontaria o mês."""
    corpo = catalogo_com({"cveID": "CVE-2026-1"})
    with pytest.raises(FonteCISAError, match="aaaa-mm-dd"):
        contagem_kev_no_mes("2026-08", transport=TransporteFalso(body=corpo))


def test_dateAdded_fora_do_formato_levanta_nomeando_o_cve() -> None:
    """Se a CISA mudar o formato da data, o conector grita nomeando o CVE — nunca subconta."""
    corpo = catalogo_com({"cveID": "CVE-2026-1", "dateAdded": "08/31/2026"})
    with pytest.raises(FonteCISAError, match="CVE-2026-1"):
        contagem_kev_no_mes("2026-08", transport=TransporteFalso(body=corpo))


def test_entrada_que_nao_e_objeto_levanta() -> None:
    """Item escalar na lista é corrupção de layout — não é pulável em silêncio."""
    corpo = b'{"count": 1, "vulnerabilities": ["CVE-2026-1"]}'
    with pytest.raises(FonteCISAError, match="não-objeto"):
        contagem_kev_no_mes("2026-08", transport=TransporteFalso(body=corpo))


def test_max_bytes_e_timeout_viajam_na_chamada() -> None:
    """max_bytes é obrigatório na casa (corpo truncado = mentira): prova que ele viaja."""
    transporte = TransporteQueGravaKwargs()
    contagem_kev_no_mes("2026-08", transport=transporte)
    assert len(transporte.chamadas) == 1
    chamada = transporte.chamadas[0]
    assert chamada["max_bytes"] == MAX_BYTES == 8_000_000
    assert chamada["timeout"] == TIMEOUT == 60
    assert chamada["headers"]["Accept"] == "application/json"
    assert chamada["url"].endswith("known_exploited_vulnerabilities.json")


def test_catalogo_kev_devolve_o_documento_validado() -> None:
    """catalogo_kev entrega o documento inteiro já validado, com count coerente."""
    documento = catalogo_kev(transport=TransporteFalso())
    assert documento["catalogVersion"] == "2026.09.01"
    assert documento["count"] == len(documento["vulnerabilities"]) == 3


def test_o_erro_da_casa_herda_de_FonteError() -> None:
    """Quem resolve mercados captura FonteError por mercado — este também tem de cair lá."""
    assert issubclass(FonteCISAError, FonteError)
