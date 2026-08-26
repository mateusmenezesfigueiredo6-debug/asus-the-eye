#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sela um evento project.reference com o estudo de arquitetura do Ahmia index.

Por que este script existe: reports/provenance/Ahmia-index-study.md registra
que, em 2026-08-23, o titular estudou o schema Elasticsearch e os scripts de
manutenção do Ahmia (BSD-3-Clause © 2024 Juha Nurmi, commit upstream
9b99b6da0c35cbf81d5820a2fd05697ce3aca5c5), e que NENHUM código foi copiado
nessa data. Um Markdown solto é revogável — qualquer um pode editar depois.
Selar o *sha256 do documento tal como está agora* num evento project.reference
torna a asserção "no dia X, este projeto foi estudado desta forma sem código
absorvido" imutável na corrente auditável — carimbo de anterioridade útil se a
incorporação real acontecer no futuro e alguém questionar a cronologia.

Segue a mesma mecânica de scripts/selar_compliance_owasp.py.

USO:
  python scripts/selar_referencia_ahmia.py --conferir   # imprime o payload, não sela
  python scripts/selar_referencia_ahmia.py              # sela na corrente REAL

Idempotente: rodar duas vezes com o mesmo doc não duplica (correlation_id
deriva do hash do doc). Editar o doc muda o hash → vira evento novo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parent.parent
DOC = RAIZ / "reports" / "provenance" / "Ahmia-index-study.md"

PROJETO = "Ahmia index"
REPOSITORIO = "https://github.com/ahmia/ahmia-index"
COMMIT_UPSTREAM = "9b99b6da0c35cbf81d5820a2fd05697ce3aca5c5"
COMMIT_DATA = "2026-03-17"
LICENCA = "BSD-3-Clause"
AUTOR_UPSTREAM = "Juha Nurmi"


def sha256_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def montar_payload() -> dict[str, Any]:
    if not DOC.exists():
        raise SystemExit(f"selar_referencia_ahmia: doc ausente em {DOC}")
    return {
        "projeto": PROJETO,
        "repositorio": REPOSITORIO,
        "commit_upstream": COMMIT_UPSTREAM,
        "commit_data": COMMIT_DATA,
        "licenca": LICENCA,
        "autor_upstream": AUTOR_UPSTREAM,
        "doc": "reports/provenance/Ahmia-index-study.md",
        "doc_sha256": sha256_arquivo(DOC),
        "natureza": "estudo_de_arquitetura_sem_uso_implementado",
        "codigo_absorvido": False,
        "declaracao": (
            "em 2026-08-23, o titular estudou a arquitetura do Ahmia index (schema "
            "Elasticsearch e scripts de manutenção de índice para serviços .onion). "
            "NENHUM código foi copiado, adaptado, vendorado ou tornado dependência do "
            "THE EYE nessa data. Cláusula 3 da BSD-3-Clause do Ahmia respeitada: o "
            "nome 'Ahmia' não é usado para promover produtos derivados."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--conferir",
        action="store_true",
        help="imprime o payload e sai; não toca a corrente",
    )
    args = parser.parse_args()

    payload = montar_payload()

    if args.conferir:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    from asus_theye.audit.schema import hash_json
    from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria, selar_registro

    try:
        sdk = abrir_auditoria()
        recibo = selar_registro(
            sdk,
            payload,
            tipo_evento="project.reference",
            recurso="reference",
            correlation_id=f"reference:ahmia-index:{payload['doc_sha256'][:32]}",
        )
    except AuditoriaError as error:
        print(f"selar_referencia_ahmia: {error}", file=sys.stderr)
        return 1

    print(json.dumps({"selagem": recibo, "conteudo_hash": hash_json(payload)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
