#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reconcilia o settlement legado cujo conteúdo selado se perdeu para o esquema.

O caso, nomeado: ``MACRO-01::2026-07`` foi selado em 17/08/2026 com um conteúdo
cujo hash é ``5b94e646…``. Depois disso o esquema da linha de resolução ganhou
campos (``determination_date``, ``determination_basis``, ``mes_referencia``,
``limiar``, ``max_uncertainty``) — e o conteúdo exato que gerou aquele hash não
existe mais em lugar nenhum. A re-selagem idempotente passou a acusar divergência
em toda rodada, derrubando a liquidação automática inteira.

O que este script faz, em ordem, e por quê:

1. **Completa** a linha legada com os campos que o esquema atual exige,
   declarando ``determination_basis = "desconhecida"`` — que é FATO: ninguém
   registrou quando a fonte publicou. A calibração já exclui essa base
   (``BASES_CONFIAVEIS``), então nada fica elegível que não era; o que muda é
   que o campo para de fingir que não existe.
2. **Sela** um evento ``audit.reconciliation`` que nomeia o hash órfão, o hash
   atual e o motivo. É APÊNDICE — a corrente não é reescrita, o evento antigo
   fica onde está, e quem auditar vê a história inteira.
3. É **idempotente**: rodar de novo não duplica nada (dedupe por correlação).

Depois disto a varredura de selagem reconhece o par (claim, hash atual) como
divergência documentada e a rodada volta a fechar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from asus_theye.markets.auditoria import (  # noqa: E402
    abrir_auditoria,
    hash_de_conteudo,
    reconciliar_divergencia,
    settlement_selado,
)
from asus_theye.markets.live import _linha_de_resolucao, carregar_registro, salvar_registro  # noqa: E402
from asus_theye.markets.resolution import BASE_DESCONHECIDA  # noqa: E402

CLAIM = "MACRO-01::2026-07"
STORE = Path("reports/markets/registro.json")
RESOLUCOES = Path("reports/markets/resolucoes.jsonl")
MOTIVO = (
    "settlement selado em 2026-08-17 sob esquema antigo; o esquema da linha de resolução "
    "ganhou campos depois (determination_date/basis, mes_referencia, limiar, max_uncertainty) "
    "e o conteúdo exato do hash original não é mais reproduzível. Campos completados com "
    "base 'desconhecida' declarada — a calibração continua a excluí-lo, como deve."
)


def main() -> int:
    registro = carregar_registro(STORE)
    mercado = next((m for m in registro["mercados"] if m["claim_id"] == CLAIM), None)
    if mercado is None:
        print(f"reconciliar: {CLAIM} não está no registro — nada a fazer")
        return 1

    # 1. completa o registro (idempotente: só escreve se faltava)
    mudou = False
    if not mercado.get("determination_basis"):
        mercado["determination_basis"] = BASE_DESCONHECIDA
        mercado.setdefault("determination_date", "")
        mudou = True
    if mudou:
        salvar_registro(STORE, registro)
        print(f"  registro: {CLAIM} completado com determination_basis={BASE_DESCONHECIDA!r}")

    # 1b. completa a MESMA linha no store publicado, para os dois artefatos
    # contarem a mesma história (o recibo desta mudança é o evento do passo 2)
    linha_canonica = _linha_de_resolucao(mercado)
    linhas = [json.loads(li) for li in RESOLUCOES.read_text(encoding="utf-8").splitlines() if li.strip()]
    for i, li in enumerate(linhas):
        if li.get("claim_id") == CLAIM and "determination_basis" not in li:
            linhas[i] = linha_canonica
            RESOLUCOES.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in linhas), encoding="utf-8")
            print("  resolucoes.jsonl: linha legada completada para a forma canônica")
            break

    # 2. sela a reconciliação
    selado = settlement_selado(CLAIM)
    if selado is None:
        print(f"reconciliar: não há settlement selado para {CLAIM} — nada a reconciliar")
        return 1
    hash_atual = hash_de_conteudo(linha_canonica)
    if selado["content_hash_sha256"] == hash_atual:
        print("reconciliar: hash atual bate com o selado — não há divergência")
        return 0

    sdk = abrir_auditoria()
    recibo = reconciliar_divergencia(
        sdk,
        correlation_id=CLAIM,
        hash_selado_original=selado["content_hash_sha256"],
        hash_atual=hash_atual,
        motivo=MOTIVO,
    )
    estado = "dedupe (já registrada)" if recibo.get("duplicate") else "SELADA"
    print(f"  reconciliação {estado}: {selado['content_hash_sha256'][:16]}… -> {hash_atual[:16]}…")
    print(f"  event_hash: {recibo.get('event_hash_sha256', '')[:24]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
