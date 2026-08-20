# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da fonte global — offline, com transporte injetado."""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from asus_theye.markets.fonte_worldbank import (
    ATRIBUICAO,
    LICENCA,
    FonteWorldBankError,
    indicador_anual,
)
from asus_theye.net.http import HttpError

IPCA_GLOBAL = "FP.CPI.TOTL.ZG"


@dataclass
class RespostaFalsa:
    status: int
    body: bytes


class TransporteFalso:
    """Transporte injetado — a suíte roda offline, como o resto da casa."""

    def __init__(self, resposta: object) -> None:
        self.resposta = resposta
        self.url_chamada = ""

    def request(self, url: str, **_: object) -> object:
        self.url_chamada = url
        if isinstance(self.resposta, Exception):
            raise self.resposta
        return self.resposta


def _corpo(valor: object, pais: str = "Brazil", iso3: str = "BRA", ano: str = "2024") -> bytes:
    dados = [
        {
            "indicator": {"id": IPCA_GLOBAL, "value": "Inflation, consumer prices (annual %)"},
            "country": {"id": iso3[:2], "value": pais},
            "countryiso3code": iso3,
            "date": ano,
            "value": valor,
        }
    ]
    return json.dumps([{"page": 1, "total": 1}, dados]).encode("utf-8")


# ------------------------------------------------------------ caminho feliz


def test_devolve_valor_com_pais_ano_e_unidade() -> None:
    t = TransporteFalso(RespostaFalsa(200, _corpo(4.37)))
    obs = indicador_anual(IPCA_GLOBAL, "BRA", "2024", transport=t)
    assert obs is not None
    assert obs.valor == 4.37
    assert obs.pais_iso3 == "BRA"
    assert obs.nome_do_pais == "Brazil"
    assert obs.unidade == "percentual_anual"
    assert obs.periodicidade == "anual"


def test_a_atribuicao_viaja_no_dado() -> None:
    """A exigência da CC-BY é cumprida no próprio registro, não num rodapé esquecível."""
    t = TransporteFalso(RespostaFalsa(200, _corpo(2.95, "United States", "USA")))
    obs = indicador_anual(IPCA_GLOBAL, "USA", "2024", transport=t)
    assert obs is not None
    assert obs.licenca == LICENCA == "CC-BY-4.0"
    assert obs.atribuicao == ATRIBUICAO
    assert "World Bank" in obs.as_dict()["atribuicao"]  # sobrevive à serialização


def test_qualquer_pais_iso3_e_aceito() -> None:
    """O que destrava o escopo global: a fonte não é de um país só."""
    for iso3, nome in (("JPN", "Japan"), ("DEU", "Germany"), ("ZAF", "South Africa")):
        t = TransporteFalso(RespostaFalsa(200, _corpo(2.5, nome, iso3)))
        obs = indicador_anual(IPCA_GLOBAL, iso3, "2024", transport=t)
        assert obs is not None and obs.pais_iso3 == iso3


# ------------------------------------------------------------ UNKNOWN honesto


def test_ano_nao_publicado_devolve_none() -> None:
    """None significa UMA coisa: não publicado. Nunca zero."""
    t = TransporteFalso(RespostaFalsa(200, json.dumps([{"page": 1}, []]).encode("utf-8")))
    assert indicador_anual(IPCA_GLOBAL, "BRA", "2030", transport=t) is None


def test_valor_nulo_da_fonte_devolve_none() -> None:
    t = TransporteFalso(RespostaFalsa(200, _corpo(None)))
    assert indicador_anual(IPCA_GLOBAL, "BRA", "2024", transport=t) is None


# ------------------------------------------------------------ falha-fechada


def test_fonte_inalcancavel_levanta_em_vez_de_virar_unknown() -> None:
    """Rede caída não é 'ano não publicado' — confundir os dois corromperia o Brier."""
    t = TransporteFalso(HttpError("timeout"))
    with pytest.raises(FonteWorldBankError, match="inalcançável"):
        indicador_anual(IPCA_GLOBAL, "BRA", "2024", transport=t)


def test_http_nao_200_levanta() -> None:
    t = TransporteFalso(RespostaFalsa(503, b"[]"))
    with pytest.raises(FonteWorldBankError, match="HTTP 503"):
        indicador_anual(IPCA_GLOBAL, "BRA", "2024", transport=t)


def test_recusa_da_fonte_levanta_em_vez_de_virar_unknown() -> None:
    """A API sinaliza erro devolvendo só os metadados — caso que precisa gritar."""
    t = TransporteFalso(RespostaFalsa(200, json.dumps([{"message": [{"key": "invalid"}]}]).encode("utf-8")))
    with pytest.raises(FonteWorldBankError, match="recusou a consulta"):
        indicador_anual(IPCA_GLOBAL, "XXX", "2024", transport=t)


def test_json_invalido_levanta() -> None:
    t = TransporteFalso(RespostaFalsa(200, b"nao e json"))
    with pytest.raises(FonteWorldBankError, match="JSON"):
        indicador_anual(IPCA_GLOBAL, "BRA", "2024", transport=t)


def test_valor_nao_numerico_levanta() -> None:
    t = TransporteFalso(RespostaFalsa(200, _corpo("mais ou menos")))
    with pytest.raises(FonteWorldBankError, match="não numérico"):
        indicador_anual(IPCA_GLOBAL, "BRA", "2024", transport=t)


# ------------------------------------------------------------ erro de chamada ≠ UNKNOWN


def test_indicador_fora_do_registro_levanta() -> None:
    """Cada indicador precisa declarar unidade e periodicidade antes de entrar."""
    with pytest.raises(FonteWorldBankError, match="fora do registro"):
        indicador_anual("INVENTADO", "BRA", "2024")


def test_iso3_malformado_levanta_sem_tocar_a_rede() -> None:
    """Código errado devolveria lista vazia — indistinguível de 'não publicado'."""
    t = TransporteFalso(RespostaFalsa(200, _corpo(1.0)))
    with pytest.raises(FonteWorldBankError, match="ISO-3"):
        indicador_anual(IPCA_GLOBAL, "BRASIL", "2024", transport=t)
    assert t.url_chamada == ""  # nem chegou a chamar


def test_ano_malformado_levanta() -> None:
    with pytest.raises(FonteWorldBankError, match="ano"):
        indicador_anual(IPCA_GLOBAL, "BRA", "24")
