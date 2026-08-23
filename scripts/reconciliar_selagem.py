#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Registra na corrente que um conteúdo selado divergiu de forma — decisão assinada.

Uso:
    python scripts/reconciliar_selagem.py CORRELATION_ID HASH_ATUAL --motivo "..."

O HASH_ATUAL vem da própria mensagem de erro da selagem, que imprime os dois
hashes completos. O hash original é buscado na corrente pela correlação.

A reconciliação NÃO é passe livre: cobre exatamente o par (correlação, hash
atual). Se a forma mudar de novo, a selagem volta a falhar e uma decisão nova é
exigida. Fail-closed continua sendo o padrão — isto aqui é a assinatura da
exceção, com motivo, no mesmo lugar auditável que tudo o mais.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from asus_theye.markets.auditoria import (  # noqa: E402
    abrir_auditoria,
    evento_por_correlacao,
    reconciliar_divergencia,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("correlation_id")
    parser.add_argument("hash_atual", help="content_hash atual (64 hex), da mensagem de erro")
    parser.add_argument("--motivo", required=True, help="por que a forma mudou — vai selado, escreva de verdade")
    args = parser.parse_args()

    if len(args.hash_atual) != 64:
        print(f"reconciliar: hash_atual deve ter 64 hex, veio {len(args.hash_atual)}")
        return 1
    if len(args.motivo.strip()) < 20:
        print("reconciliar: motivo curto demais — a assinatura exige o porquê, não um ok")
        return 1

    selado = evento_por_correlacao(args.correlation_id)
    if selado is None:
        print(f"reconciliar: nenhum evento selado com correlação {args.correlation_id!r}")
        return 1

    sdk = abrir_auditoria()
    recibo = reconciliar_divergencia(
        sdk,
        correlation_id=args.correlation_id,
        hash_selado_original=selado["content_hash_sha256"],
        hash_atual=args.hash_atual,
        motivo=args.motivo.strip(),
    )
    estado = "dedupe (já registrada)" if recibo.get("duplicate") else "SELADA"
    print(f"  reconciliação {estado}: {selado['content_hash_sha256'][:16]}… -> {args.hash_atual[:16]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
