# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do agregado diário da cobertura GDELT — o conserto de 2026-09-02.

O defeito diagnosticado não era coluna nem arquivo: era medir UMA janela de
15 minutos contra ``MINIMO_DE_EVENTOS``, calibrado para o DIA. Estes testes
provam o regime novo: as 96 janelas do dia UTC somadas ANTES do piso, tom
ponderado por eventos, e janela ausente virando número — não zero silencioso.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field

import pytest

from asus_theye.markets.fonte_gdelt import (
    COL_PAIS,
    COL_TOM,
    JANELAS_POR_DIA,
    MINIMO_DE_EVENTOS,
    FonteGDELTError,
    cobertura_do_dia,
)

DIA = "2026-08-21"


def _linha(pais: str, tom: float) -> str:
    """Uma linha de evento com as 61 colunas do formato — só as duas que lemos preenchidas."""
    colunas = [""] * 61
    colunas[COL_PAIS] = pais
    colunas[COL_TOM] = str(tom)
    return "\t".join(colunas)


def _pacote(linhas: list[str]) -> bytes:
    corpo = io.BytesIO()
    with zipfile.ZipFile(corpo, "w") as pacote:
        pacote.writestr("eventos.CSV", "\n".join(linhas))
    return corpo.getvalue()


@dataclass
class RespostaFalsa:
    status: int
    body: bytes


@dataclass
class TransporteDoDia:
    """Serve as 96 janelas por carimbo: mapa de exceções + um padrão para o resto.

    Entrada ``bytes`` vira 200 com aquele corpo; entrada ``int`` vira aquele
    status HTTP. O padrão de um dia normal é um pacote sem eventos do país.
    """

    especiais: dict[str, bytes | int]
    padrao: bytes | int = field(default_factory=lambda: _pacote([]))
    urls: list[str] = field(default_factory=list)

    def request(self, url: str, **_: object) -> RespostaFalsa:
        self.urls.append(url)
        carimbo = url.rsplit("/", 1)[-1].split(".")[0]
        entrada = self.especiais.get(carimbo, self.padrao)
        if isinstance(entrada, int):
            return RespostaFalsa(entrada, b"nao achei")
        return RespostaFalsa(200, entrada)


class TransporteProibido:
    """Para provar que dia malformado levanta ANTES de qualquer rede."""

    def request(self, url: str, **_: object) -> RespostaFalsa:
        raise AssertionError(f"a rede foi tocada com dia malformado: {url}")


# ------------------------------------------------------------ a agregação


def test_soma_as_janelas_e_pondera_o_tom_por_eventos() -> None:
    """2 eventos (tons 1 e 3) + 1 evento (tom 7) + uma janela 404.

    Ponderado por eventos: (1+3+7)/3 = 3.6667 — e NÃO a média das médias das
    janelas ((2+7)/2 = 4.5), que é o que uma implementação errada devolveria.
    """
    transporte = TransporteDoDia(
        especiais={
            "20260821060000": _pacote([_linha("BR", 1.0), _linha("BR", 3.0), _linha("AR", -9.0)]),
            "20260821123000": _pacote([_linha("BR", 7.0)]),
            "20260821184500": 404,
        }
    )
    agregado = cobertura_do_dia(DIA, pais_fips="BR", transport=transporte)

    assert agregado.eventos == 3
    assert agregado.tom_medio == 3.6667
    assert agregado.janelas_ok == JANELAS_POR_DIA - 1
    assert agregado.janelas_falhas == 1


def test_deriva_as_96_urls_do_dia_utc_em_https() -> None:
    transporte = TransporteDoDia(especiais={})
    cobertura_do_dia(DIA, transport=transporte)

    assert len(transporte.urls) == JANELAS_POR_DIA
    assert transporte.urls[0] == "https://data.gdeltproject.org/gdeltv2/20260821000000.export.CSV.zip"
    assert transporte.urls[-1] == "https://data.gdeltproject.org/gdeltv2/20260821234500.export.CSV.zip"


def test_metodo_declara_o_regime_e_as_janelas_usadas() -> None:
    """É pelo metodo que o índice separa o agregado diário das linhas antigas
    de janela única — a string tem de declarar o regime, não sugerir."""
    transporte = TransporteDoDia(especiais={"20260821184500": 404})
    agregado = cobertura_do_dia(DIA, transport=transporte)

    assert agregado.metodo.startswith(f"agregado de {JANELAS_POR_DIA - 1} janelas de 15min do dia UTC")
    assert agregado.as_dict()["dia"] == DIA
    assert agregado.as_dict()["minimo_de_eventos"] == MINIMO_DE_EVENTOS


# ------------------------------------------------------------------ o piso


def test_piso_continua_o_mesmo_agora_contra_o_agregado_do_dia() -> None:
    """A MESMA constante de sempre — o que mudou é o lado esquerdo da conta."""
    assert MINIMO_DE_EVENTOS == 5  # o piso declarado; recalibrar é decisão, não acidente

    abaixo = cobertura_do_dia(
        DIA,
        transport=TransporteDoDia(especiais={"20260821060000": _pacote([_linha("BR", 1.0), _linha("BR", 3.0)])}),
    )
    assert abaixo.eventos == 2
    assert abaixo.suficiente is False

    acima = cobertura_do_dia(
        DIA,
        transport=TransporteDoDia(
            especiais={"20260821060000": _pacote([_linha("BR", -2.0) for _ in range(MINIMO_DE_EVENTOS)])}
        ),
    )
    assert acima.eventos == MINIMO_DE_EVENTOS
    assert acima.suficiente is True
    assert acima.tom_medio == -2.0


# ------------------------------------------------------------------ os erros


def test_todas_as_janelas_falhando_levanta() -> None:
    """Dia inteiro sem fonte é erro de fonte, não cobertura zero."""
    with pytest.raises(FonteGDELTError, match="todas as 96 janelas"):
        cobertura_do_dia(DIA, transport=TransporteDoDia(especiais={}, padrao=404))


@pytest.mark.parametrize("torto", ["21/08/2026", "2026-8-2", "20260821", "2026-02-30", "ontem"])
def test_dia_malformado_levanta_antes_da_rede(torto: str) -> None:
    """Data torta não vira 96 URLs tortas — levanta antes de tocar o transporte."""
    with pytest.raises(FonteGDELTError, match="dia malformado"):
        cobertura_do_dia(torto, transport=TransporteProibido())
