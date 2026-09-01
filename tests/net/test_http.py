# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Contrato de ``net.http`` — a rede de proteção que a ADR-011 pede.

O cabeçalho do módulo declara a dívida: as outras cópias de urllib do projeto
só poderão ser consolidadas aqui quando ESTE caminho tiver testes. Estes
testes fixam o contrato do qual os conectores dependem: transporte injetável,
``max_bytes`` obrigatório (corpo truncado em silêncio seria "o hash de um
documento parcial — uma mentira criptografada"), e o mapeamento de erros.
Tudo offline: ou transporte fake injetado, ou ``urlopen`` falso.
"""

from __future__ import annotations

import io
import urllib.error
import urllib.request
from collections.abc import Mapping

import pytest

from asus_theye.net.http import HttpError, HttpResponse, ResponseTooLarge, get_bytes

URL = "https://fonte.example.test/serie.json"
HEADERS = {"accept": "application/json"}


# ------------------------------------------------------------ transporte injetável


class TransporteFake:
    """Grava a chamada e devolve uma resposta pronta — nenhum socket é aberto."""

    def __init__(self, resposta: HttpResponse) -> None:
        self.resposta = resposta
        self.chamadas: list[dict[str, object]] = []

    def request(self, url: str, *, headers: Mapping[str, str], timeout: int, max_bytes: int) -> HttpResponse:
        self.chamadas.append({"url": url, "headers": dict(headers), "timeout": timeout, "max_bytes": max_bytes})
        return self.resposta


def test_get_bytes_delega_ao_transporte_injetado_com_os_parametros_intactos():
    """O contrato central: quem injeta o transporte controla a rede inteira."""
    resposta = HttpResponse(url=URL, status=200, headers={"content-type": "application/json"}, body=b'{"ok": true}')
    transporte = TransporteFake(resposta)

    devolvida = get_bytes(URL, headers=HEADERS, timeout=7, max_bytes=1024, transport=transporte)

    assert devolvida is resposta  # volta intacta, sem cópia nem mutação
    assert transporte.chamadas == [{"url": URL, "headers": HEADERS, "timeout": 7, "max_bytes": 1024}]


def test_max_bytes_nao_positivo_e_recusado_antes_de_tocar_o_transporte():
    """max_bytes é obrigatório e positivo; a recusa acontece ANTES de qualquer I/O."""
    transporte = TransporteFake(HttpResponse(url=URL, status=200, headers={}, body=b""))
    for invalido in (0, -1):
        with pytest.raises(ValueError, match="max_bytes deve ser positivo"):
            get_bytes(URL, headers=HEADERS, timeout=7, max_bytes=invalido, transport=transporte)
    assert transporte.chamadas == [], "transporte nunca é consultado com limite inválido"


def test_erro_do_transporte_propaga_como_http_error_sem_disfarce():
    """Conectores tratam falha de rede capturando HttpError — o tipo não pode mudar."""

    class TransporteQueFalha:
        def request(self, url: str, *, headers: Mapping[str, str], timeout: int, max_bytes: int) -> HttpResponse:
            raise HttpError(f"inalcançável: {url}")

    with pytest.raises(HttpError, match="inalcançável"):
        get_bytes(URL, headers=HEADERS, timeout=7, max_bytes=1024, transport=TransporteQueFalha())


def test_response_too_large_e_um_http_error():
    """Invariante de captura: quem trata HttpError também apanha o estouro de tamanho."""
    assert issubclass(ResponseTooLarge, HttpError)


# --------------------------------- UrllibTransport com urlopen falso (zero rede)


class RespostaUrllibFalsa:
    """O mínimo que UrllibTransport consome de urlopen: status, headers, read(n)."""

    def __init__(self, body: bytes, *, status: int = 200, headers: dict[str, str] | None = None) -> None:
        self._body = body
        self.status = status
        self.headers = headers if headers is not None else {"Content-Type": "application/json"}

    def read(self, n: int) -> bytes:
        return self._body[:n]

    def __enter__(self) -> RespostaUrllibFalsa:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _urlopen_devolvendo(resposta: RespostaUrllibFalsa):
    def urlopen_falso(request: urllib.request.Request, timeout: int) -> RespostaUrllibFalsa:
        return resposta

    return urlopen_falso


def test_corpo_no_limite_exato_de_max_bytes_passa(monkeypatch: pytest.MonkeyPatch):
    """Fronteira: exatamente max_bytes não é estouro — o byte extra lido é só sonda."""
    corpo = b"x" * 10
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_devolvendo(RespostaUrllibFalsa(corpo)))

    resposta = get_bytes(URL, headers=HEADERS, timeout=7, max_bytes=10)

    assert resposta.status == 200
    assert resposta.body == corpo  # completo, nunca truncado


def test_corpo_maior_que_max_bytes_levanta_response_too_large(monkeypatch: pytest.MonkeyPatch):
    """O porquê do módulo: corpo além do limite LEVANTA — nunca vira hash parcial."""
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_devolvendo(RespostaUrllibFalsa(b"x" * 11)))

    with pytest.raises(ResponseTooLarge, match="excedeu 10 bytes") as excecao:
        get_bytes(URL, headers=HEADERS, timeout=7, max_bytes=10)
    assert excecao.value.status == 200  # o status da resposta viaja junto


def test_status_de_erro_http_nao_levanta_devolve_a_resposta_com_detalhe(monkeypatch: pytest.MonkeyPatch):
    """HTTP != 200 é resposta, não exceção: o chamador decide o que fazer com o status."""
    erro = urllib.error.HTTPError(
        URL, 404, "Not Found", {"Content-Type": "text/html", "X-Detail": "v"}, io.BytesIO(b"pagina nao encontrada")
    )

    def urlopen_falso(request: urllib.request.Request, timeout: int) -> RespostaUrllibFalsa:
        raise erro

    monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)

    resposta = get_bytes(URL, headers=HEADERS, timeout=7, max_bytes=1024)

    assert resposta.status == 404
    assert resposta.body == b"pagina nao encontrada"
    assert resposta.headers == {"content-type": "text/html", "x-detail": "v"}  # minúsculas


def test_timeout_e_url_error_viram_http_error_sem_status(monkeypatch: pytest.MonkeyPatch):
    """Falha de transporte (timeout, DNS, conexão) mapeia para HttpError com status None."""
    for causa in (TimeoutError("timed out"), urllib.error.URLError(ConnectionRefusedError(111, "recusada"))):

        def urlopen_falso(request: urllib.request.Request, timeout: int, _causa: Exception = causa) -> object:
            raise _causa

        monkeypatch.setattr(urllib.request, "urlopen", urlopen_falso)
        with pytest.raises(HttpError, match="inalcançável") as excecao:
            get_bytes(URL, headers=HEADERS, timeout=7, max_bytes=1024)
        assert excecao.value.status is None
        assert not isinstance(excecao.value, ResponseTooLarge)


def test_headers_da_resposta_chegam_normalizados_em_minusculas(monkeypatch: pytest.MonkeyPatch):
    """Conectores consultam headers por chave minúscula; a normalização é contrato."""
    resposta_falsa = RespostaUrllibFalsa(b"{}", headers={"Content-Type": "application/json", "ETag": "abc"})
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_devolvendo(resposta_falsa))

    resposta = get_bytes(URL, headers=HEADERS, timeout=7, max_bytes=1024)

    assert resposta.headers == {"content-type": "application/json", "etag": "abc"}
