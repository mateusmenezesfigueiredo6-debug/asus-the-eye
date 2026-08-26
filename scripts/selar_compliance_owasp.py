#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sela um evento project.compliance com o mapeamento OWASP GenAI LLM Top 10 2026.

Por que este script existe: docs/security/OWASP_LLM_TOP10_2026.md documenta a
exposição residual da superfície LLM contra a lista OWASP 2026, mas um
Markdown solto é revogável — qualquer um pode editar o arquivo depois. Selar
o *sha256 do documento tal como está agora* num evento project.compliance
torna a asserção "no dia X, a plataforma se auto-mapeou desta forma contra
esta versão do framework" imutável na corrente auditável, e — quando a
próxima raiz Merkle for ancorada — publicamente verificável on-chain sem
revelar o texto do documento.

Segue a mesma mecânica que projeto/fronteira.py usa para project.boundary.

USO:
  python scripts/selar_compliance_owasp.py --conferir   # imprime o payload, não sela
  python scripts/selar_compliance_owasp.py              # sela na corrente REAL

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
DOC = RAIZ / "docs" / "security" / "OWASP_LLM_TOP10_2026.md"
FRAMEWORK = "OWASP GenAI LLM Top 10 2026"
REFERENCIA = "https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/"

# Superfície LLM real coberta pelo doc. Se algum destes sumir do repo, o doc
# está mentindo e a selagem deve refletir isso — a lista é conferida, não
# ornamento.
SUPERFICIE = (
    "src/asus_theye/llm/audited.py",
    "src/asus_theye/llm/dual.py",
    "src/asus_theye/llm/ollama_client.py",
    "src/asus_theye/llm/remote_client.py",
)

# Os dez riscos, no rótulo canônico de 2026. Fonte: o próprio doc, na tabela.
# Mantido literal em vez de importado do Markdown porque este é o *contrato*
# que se está selando — se o rótulo mudar no doc sem mudar aqui, a diferença
# aparece no diff.
RISCOS = (
    "LLM01:2026 Prompt Injection",
    "LLM02:2026 Sensitive Information Disclosure",
    "LLM03:2026 Excessive Agency",
    "LLM04:2026 Supply Chain",
    "LLM05:2026 Data and Model Poisoning",
    "LLM06:2026 Unbounded Consumption",
    "LLM07:2026 Misinformation",
    "LLM08:2026 Hidden Context Exposure",
    "LLM09:2026 Vector and Embedding Weaknesses",
    "LLM10:2026 Improper Output Handling",
)


def sha256_arquivo(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def montar_payload() -> dict[str, Any]:
    if not DOC.exists():
        raise SystemExit(f"selar_compliance_owasp: doc ausente em {DOC}")
    faltando = [rel for rel in SUPERFICIE if not (RAIZ / rel).exists()]
    if faltando:
        raise SystemExit(
            "selar_compliance_owasp: o doc declara arquivos que não existem no repo, "
            f"não vai selar: {faltando}"
        )
    return {
        "framework": FRAMEWORK,
        "referencia": REFERENCIA,
        "doc": "docs/security/OWASP_LLM_TOP10_2026.md",
        "doc_sha256": sha256_arquivo(DOC),
        "riscos": list(RISCOS),
        "superficie_llm": list(SUPERFICIE),
        "metodo": (
            "mapeamento risco → superfície → controle → arquivo:linha; cada linha da "
            "tabela cita um arquivo real e a lista superficie_llm é conferida antes "
            "de selar (arquivo ausente aborta)"
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

    # imports tardios: --conferir precisa rodar sem dependências de auditoria
    from asus_theye.audit.schema import hash_json
    from asus_theye.markets.auditoria import AuditoriaError, abrir_auditoria, selar_registro

    try:
        sdk = abrir_auditoria()
        recibo = selar_registro(
            sdk,
            payload,
            tipo_evento="project.compliance",
            recurso="compliance",
            correlation_id=f"compliance:owasp-llm-2026:{payload['doc_sha256'][:32]}",
        )
    except AuditoriaError as error:
        print(f"selar_compliance_owasp: {error}", file=sys.stderr)
        return 1

    print(json.dumps({"selagem": recibo, "conteudo_hash": hash_json(payload)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
