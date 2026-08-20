# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da reprecificação e do laço que move p entre emissão e liquidação."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from asus_theye.markets.reprecificar import MOVIMENTO_MINIMO, ReprecificacaoError, reprecificar


@dataclass
class ProbabilidadeFalsa:
    valor: float

    def as_dict(self) -> dict:
        return {"valor": self.valor, "metodo": "fonte de teste", "sinais": []}


def _store(tmp: Path, *, p: float = 0.5, estado: str = "ABERTO") -> Path:
    caminho = tmp / "registro.json"
    caminho.write_text(
        json.dumps(
            {
                "versao": 1,
                "mercados": [
                    {
                        "claim_id": "MACRO-01::2026-09",
                        "market_area_id": "macroeconomia",
                        "mes_referencia": "2026-09",
                        "limiar": 0.5,
                        "probability": p,
                        "estado": estado,
                        "deadline": "2026-09-30",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return caminho


def test_move_p_e_guarda_o_valor_anterior(tmp_path: Path) -> None:
    store = _store(tmp_path)
    r = reprecificar(
        claim_id="MACRO-01::2026-09", probabilidade=ProbabilidadeFalsa(0.8), motivo="sinal novo", store=store
    )
    assert r["reprecificado"] is True
    assert r["mudanca"]["probabilidade_anterior"] == 0.5
    assert r["mudanca"]["probabilidade_nova"] == 0.8
    mercado = json.loads(store.read_text(encoding="utf-8"))["mercados"][0]
    assert mercado["probability"] == 0.8
    assert mercado["reprecificacoes"][0]["probabilidade_anterior"] == 0.5


def test_recusa_reprecificar_claim_liquidado(tmp_path: Path) -> None:
    """A única fraude que este módulo poderia viabilizar, barrada na porta.

    Mudar a previsão depois que o mundo respondeu é fabricar acerto — e num
    ledger imutável isso seria fabricar acerto de forma permanente.
    """
    store = _store(tmp_path, estado="LIQUIDADO")
    with pytest.raises(ReprecificacaoError, match="fabricar acerto"):
        reprecificar(claim_id="MACRO-01::2026-09", probabilidade=ProbabilidadeFalsa(0.99), motivo="x" * 40, store=store)
    assert json.loads(store.read_text(encoding="utf-8"))["mercados"][0]["probability"] == 0.5


def test_movimento_minusculo_nao_vira_evento(tmp_path: Path) -> None:
    """Ruído do gerador encheria a corrente e tornaria a trajetória ilegível."""
    store = _store(tmp_path, p=0.5)
    r = reprecificar(
        claim_id="MACRO-01::2026-09",
        probabilidade=ProbabilidadeFalsa(0.5 + MOVIMENTO_MINIMO / 2),
        motivo="ruído",
        store=store,
    )
    assert r["reprecificado"] is False
    assert json.loads(store.read_text(encoding="utf-8"))["mercados"][0]["probability"] == 0.5


def test_motivo_vazio_levanta(tmp_path: Path) -> None:
    with pytest.raises(ReprecificacaoError, match="motivo"):
        reprecificar(
            claim_id="MACRO-01::2026-09", probabilidade=ProbabilidadeFalsa(0.8), motivo="  ", store=_store(tmp_path)
        )


def test_probabilidade_fora_da_faixa_levanta(tmp_path: Path) -> None:
    with pytest.raises(ReprecificacaoError, match="fora de"):
        reprecificar(
            claim_id="MACRO-01::2026-09", probabilidade=ProbabilidadeFalsa(1.4), motivo="x" * 40, store=_store(tmp_path)
        )


def test_claim_inexistente_levanta(tmp_path: Path) -> None:
    with pytest.raises(ReprecificacaoError, match="não existe"):
        reprecificar(
            claim_id="FANTASMA::2026-09", probabilidade=ProbabilidadeFalsa(0.8), motivo="x" * 40, store=_store(tmp_path)
        )


# ------------------------------------------------------------ o laço


def test_laco_ignora_liquidado_e_area_sem_gerador(tmp_path: Path) -> None:
    """Área sem gerador NÃO cai no gerador do IPCA por aproximação.

    Perguntas diferentes têm sinais diferentes; usar o sinal errado é pior do
    que ficar no prior honesto.
    """
    from asus_theye.markets.reprecificar import rodada

    store = tmp_path / "r.json"
    store.write_text(
        json.dumps(
            {
                "versao": 1,
                "mercados": [
                    {
                        "claim_id": "X::2026-07",
                        "market_area_id": "macroeconomia",
                        "mes_referencia": "2026-07",
                        "limiar": 0.5,
                        "probability": 0.5,
                        "estado": "LIQUIDADO",
                        "deadline": "2026-07-31",
                    },
                    {
                        "claim_id": "Y::2026-09",
                        "market_area_id": "area_inventada",
                        "mes_referencia": "2026-09",
                        "limiar": 1.0,
                        "probability": 0.5,
                        "estado": "ABERTO",
                        "deadline": "2026-09-30",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    r = rodada(store=store, serie=tmp_path / "s.jsonl", hoje="2026-08-20")
    acoes = {a["claim_id"]: a["acao"] for a in r["acoes"]}
    assert "X::2026-07" not in acoes  # liquidado nem é consultado
    assert acoes["Y::2026-09"] == "sem_gerador"
    assert r["reprecificados"] == 0
