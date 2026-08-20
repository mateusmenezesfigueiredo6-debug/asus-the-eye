# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do M1 — sinais reais (Focus/IPCA-15) alimentando o gerador WPAM.

Tudo offline: transporte roteado por URL (Olinda e SGS respondem corpos falsos).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from asus_theye.markets.gerador import Sinal, gerar_probabilidade
from asus_theye.markets.live import emitir_macro, resolver_pendentes, salvar_registro
from asus_theye.markets.sinais_ipca import (
    PESO_FOCUS,
    PESO_IPCA15,
    SinaisError,
    mediana_focus_ipca,
    probabilidade_para_ipca,
    sinais_para_ipca,
)
from asus_theye.net.http import HttpResponse

HOJE = date(2026, 8, 17)
OLINDA_COM_MEDIANA = b'{"value":[{"Data":"2026-08-14","Mediana":0.10}]}'
OLINDA_VAZIO = b'{"value":[]}'
SGS_COM_PREVIA = b'[{"data":"01/09/2026","valor":"0.62"}]'
# série com ponto de OUTRO mês: o mês consultado ainda não publicou → None
# (série totalmente vazia é MALFORMADA para o conector — levanta, não degrada)
SGS_SEM_O_MES = b'[{"data":"01/07/2026","valor":"0.30"}]'


class TransporteRoteado:
    """Responde por URL: Olinda (Focus) e api.bcb (SGS) com corpos distintos."""

    def __init__(self, olinda: tuple[int, bytes], sgs: tuple[int, bytes]) -> None:
        self.olinda, self.sgs = olinda, sgs

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        status, body = self.olinda if "olinda.bcb.gov.br" in url else self.sgs
        return HttpResponse(url=url, status=status, headers={}, body=body)


# --------------------------------------------------------------- Focus/Olinda


def test_mediana_focus_acha_a_linha() -> None:
    transporte = TransporteRoteado((200, OLINDA_COM_MEDIANA), (200, SGS_SEM_O_MES))
    assert mediana_focus_ipca("2026-09", transport=transporte) == (0.10, "2026-08-14")


def test_mediana_focus_mes_sem_linha_e_none() -> None:
    transporte = TransporteRoteado((200, OLINDA_VAZIO), (200, SGS_SEM_O_MES))
    assert mediana_focus_ipca("2026-09", transport=transporte) is None


@pytest.mark.parametrize("status,body", [(500, b"{}"), (200, b"nao-e-json"), (200, b'{"sem_value": 1}')])
def test_mediana_focus_malformado_levanta(status: int, body: bytes) -> None:
    transporte = TransporteRoteado((status, body), (200, SGS_SEM_O_MES))
    with pytest.raises(SinaisError):
        mediana_focus_ipca("2026-09", transport=transporte)


def test_mes_referencia_invalido_levanta() -> None:
    with pytest.raises(SinaisError, match="aaaa-mm"):
        mediana_focus_ipca("09/2026", transport=TransporteRoteado((200, OLINDA_VAZIO), (200, SGS_SEM_O_MES)))


# --------------------------------------------------------------- sinais


def test_sinais_direcao_e_peso_declarados() -> None:
    # Focus 0.10 < 0.50 → NÃO peso 20; IPCA-15 0.62 >= 0.50 → SIM peso 10
    transporte = TransporteRoteado((200, OLINDA_COM_MEDIANA), (200, SGS_COM_PREVIA))
    sinais = sinais_para_ipca("2026-09", 0.5, transport=transporte)
    assert [(s.direcao, s.peso) for s in sinais] == [("nao", PESO_FOCUS), ("sim", PESO_IPCA15)]
    assert all(s.fonte for s in sinais)  # proveniência obrigatória
    assert "Focus" in sinais[0].fonte and "7478" in sinais[1].fonte


def test_sem_nenhuma_fonte_probabilidade_e_o_prior_honesto() -> None:
    transporte = TransporteRoteado((200, OLINDA_VAZIO), (200, SGS_SEM_O_MES))
    prob = probabilidade_para_ipca("2026-09", 0.5, transport=transporte)
    assert prob.valor == 0.5 and prob.max_uncertainty is True and prob.fontes == []


def test_probabilidade_so_com_focus_nao() -> None:
    transporte = TransporteRoteado((200, OLINDA_COM_MEDIANA), (200, SGS_SEM_O_MES))
    prob = probabilidade_para_ipca("2026-09", 0.5, transport=transporte)
    # WPAM: (0.5*10 + 0) / (10 + 0 + 20) = 5/30
    assert prob.valor == pytest.approx(5 / 30, abs=1e-6)
    assert prob.max_uncertainty is False


# --------------------------------------------------------------- emissão com sinais


def test_emitir_macro_com_probabilidade_carrega_gerador() -> None:
    registro = {"versao": 1, "mercados": []}
    prob = gerar_probabilidade([Sinal(direcao="nao", peso=20.0, fonte="fonte-teste")])
    mercado = emitir_macro(registro, "2026-09", agora="2026-08-17T00:00:00Z", probabilidade=prob)
    assert mercado is not None
    assert mercado["probability"] == pytest.approx(5 / 30, abs=1e-6)
    assert mercado["gerador"]["fontes"] == ["fonte-teste"]
    assert mercado["max_uncertainty"] is False


def test_emitir_macro_sem_probabilidade_mantem_prior() -> None:
    registro = {"versao": 1, "mercados": []}
    mercado = emitir_macro(registro, "2026-09", agora="2026-08-17T00:00:00Z")
    assert mercado is not None
    assert mercado["probability"] == 0.5 and "gerador" not in mercado


def _store_com_julho(tmp: Path) -> Path:
    store = tmp / "registro.json"
    registro: dict = {"versao": 1, "mercados": []}
    emitir_macro(registro, "2026-07", agora="2026-07-25T05:54:18Z")
    salvar_registro(store, registro)
    return store


def test_resolvedor_emite_o_proximo_mes_com_sinais(tmp_path: Path) -> None:
    store = _store_com_julho(tmp_path)
    prob = gerar_probabilidade([Sinal(direcao="nao", peso=20.0, fonte="fonte-teste")])
    acoes = resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE, gerador_de_sinais=lambda mes, limiar: prob)
    emitido = next(a for a in acoes if a["acao"] == "emitido")
    assert "WPAM" in emitido["motivo"] and "fonte-teste" in emitido["motivo"]
    import json

    registro = json.loads(store.read_text(encoding="utf-8"))
    agosto = next(m for m in registro["mercados"] if m["mes_referencia"] == "2026-08")
    assert agosto["probability"] == pytest.approx(5 / 30, abs=1e-6)
    assert agosto["gerador"]["fontes"] == ["fonte-teste"]


def test_falha_de_sinal_nunca_bloqueia_a_emissao(tmp_path: Path) -> None:
    store = _store_com_julho(tmp_path)

    def gerador_quebrado(mes: str, limiar: float):
        raise SinaisError("Olinda fora do ar")

    acoes = resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE, gerador_de_sinais=gerador_quebrado)
    emitido = next(a for a in acoes if a["acao"] == "emitido")
    assert "sinais indisponíveis" in emitido["motivo"]
    import json

    registro = json.loads(store.read_text(encoding="utf-8"))
    agosto = next(m for m in registro["mercados"] if m["mes_referencia"] == "2026-08")
    assert agosto["probability"] == 0.5 and "gerador" not in agosto  # prior honesto, dito como tal
