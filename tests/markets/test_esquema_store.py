# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""O contrato do store de mercados vale para o store REAL — não só para exemplos.

Estes testes existem porque o store vivo (reports/markets/) nunca teve contrato
além do registro.json: um writer renomeando campo quebraria um reader depois,
em silêncio. O teste contra o store real transforma qualquer deriva de esquema
em falha de suíte no mesmo dia.
"""

from __future__ import annotations

import json
from pathlib import Path

from asus_theye.markets.esquema_store import (
    CAMPOS_POR_ARQUIVO,
    VERSAO_DO_STORE,
    validar_store,
)

STORE_REAL = Path(__file__).resolve().parents[2] / "reports" / "markets"


def test_o_store_real_valida_sem_nenhuma_violacao() -> None:
    """A medida de pronto da F1: 100% do store real passa no contrato."""
    violacoes = validar_store(STORE_REAL)
    assert violacoes == [], "\n".join(violacoes)


def test_store_inexistente_e_violacao_nao_silencio(tmp_path: Path) -> None:
    assert validar_store(tmp_path / "nao-existe") != []


def test_campo_ausente_e_apontado_com_arquivo_e_linha(tmp_path: Path) -> None:
    (tmp_path / "resolucoes.jsonl").write_text(
        json.dumps({"claim_id": "X::2026-01"}) + "\n", encoding="utf-8"
    )
    violacoes = validar_store(tmp_path)
    assert any("resolucoes.jsonl:1" in v and "campos ausentes" in v for v in violacoes)


def test_probabilidade_fora_de_zero_um_e_violacao(tmp_path: Path) -> None:
    linha = {campo: "x" for campo in CAMPOS_POR_ARQUIVO["serie_p.jsonl"]}
    linha["probability"] = 1.7
    (tmp_path / "serie_p.jsonl").write_text(json.dumps(linha) + "\n", encoding="utf-8")
    assert any("fora de [0, 1]" in v for v in validar_store(tmp_path))


def test_tabela_desconhecida_na_raiz_e_violacao(tmp_path: Path) -> None:
    """Ninguém cria tabela nova no store sem declarar no contrato."""
    (tmp_path / "surpresa.jsonl").write_text("{}\n", encoding="utf-8")
    assert any("fora do contrato" in v for v in validar_store(tmp_path))


def test_versao_do_registro_diferente_do_contrato_e_violacao(tmp_path: Path) -> None:
    (tmp_path / "registro.json").write_text(
        json.dumps({"versao": VERSAO_DO_STORE + 1, "mercados": []}), encoding="utf-8"
    )
    assert any("versao" in v for v in validar_store(tmp_path))


def test_json_invalido_no_meio_da_tabela_nao_derruba_o_resto(tmp_path: Path) -> None:
    """Linha podre é apontada; as demais continuam sendo validadas."""
    boa = {campo: "x" for campo in CAMPOS_POR_ARQUIVO["ancoras.jsonl"]}
    (tmp_path / "ancoras.jsonl").write_text(
        "{nao-e-json\n" + json.dumps(boa) + "\n", encoding="utf-8"
    )
    violacoes = validar_store(tmp_path)
    assert any("ancoras.jsonl:1" in v and "JSON inválido" in v for v in violacoes)
    assert not any("ancoras.jsonl:2" in v for v in violacoes)
