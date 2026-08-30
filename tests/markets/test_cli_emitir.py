# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do subcomando ``asus-theye markets-emitir``.

Este arquivo nasceu de um defeito concreto: o ramo do `markets-emitir` fazia
`except (LiveMarketError, MarketClaimError)` sem que `MarketClaimError`
estivesse importado NAQUELE caminho — o import existia só no ramo do
`markets-resolve`, e imports condicionais não ligam o nome nos outros ramos.

O efeito era pior que a falha original: qualquer erro de claim virava
`UnboundLocalError` e MASCARAVA a mensagem real. O operador via um erro de
Python sobre variável não associada, quando a causa era "deadline não pode ser
anterior à criação". Erro que esconde erro é pior que erro.

Não havia teste de CLI para `markets-emitir` — por isso passou.
"""

from __future__ import annotations

import json
from pathlib import Path

from asus_theye.cli import main


def test_deadline_no_passado_da_mensagem_legivel(tmp_path: Path, capsys) -> None:
    """O caso que revelou o bug: contrato para evento que já aconteceu.

    Recusar é correto — não se emite contrato sobre desfecho já conhecido. O
    que se exige aqui é que a recusa seja EXPLICADA, não que vire traceback.
    """
    store = tmp_path / "registro.json"
    codigo = main(
        [
            "markets-emitir",
            "--area", "loteria-soma",
            "--mes", "2020-01-01",
            "--limiar", "184",
            "--store", str(store),
            "--sem-gerador",
        ]
    )
    saida = capsys.readouterr().out
    assert codigo == 1, "emitir para o passado tem de falhar"
    assert "markets-emitir:" in saida, "a falha tem de sair pelo caminho tratado"
    assert "deadline" in saida, f"a mensagem tem de dizer a CAUSA, veio: {saida!r}"
    assert "UnboundLocalError" not in saida
    assert not store.exists(), "registro não pode ser criado quando a emissão falha"


def test_area_desconhecida_da_mensagem_legivel(tmp_path: Path, capsys) -> None:
    """O outro caminho que passa por MarketClaimError: 'Enum fechado'."""
    store = tmp_path / "registro.json"
    codigo = main(
        [
            "markets-emitir",
            "--area", "area-que-nao-existe",
            "--mes", "2030-01",
            "--limiar", "1",
            "--store", str(store),
            "--sem-gerador",
        ]
    )
    saida = capsys.readouterr().out
    assert codigo == 1
    assert "markets-emitir:" in saida
    assert "UnboundLocalError" not in saida


def test_emissao_valida_grava_o_registro(tmp_path: Path, capsys) -> None:
    """Caminho feliz — para provar que as guardas acima não quebraram nada."""
    store = tmp_path / "registro.json"
    codigo = main(
        [
            "markets-emitir",
            "--area", "loteria-soma",
            "--mes", "2030-06-01",
            "--limiar", "184",
            "--store", str(store),
            "--sem-gerador",
        ]
    )
    assert codigo == 0
    assert "MERCADO EMITIDO" in capsys.readouterr().out
    dados = json.loads(store.read_text(encoding="utf-8"))
    mercados = dados.get("markets") or dados.get("mercados") or []
    assert len(mercados) == 1
    assert mercados[0]["claim_id"] == "SOMA-MEGA::2030-06-01"
    # o prior honesto: sem gerador, nasce em 0,50 declarado — nunca num palpite
    assert mercados[0]["probability"] == 0.5
