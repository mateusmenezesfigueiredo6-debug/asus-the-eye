#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""QR de titularidade — nome do titular + commitment do CPF, nunca o CPF.

A regra da casa (audit/dados_pessoais.py) é absoluta: o CPF cru não entra em
arquivo, em corrente nem em QR. O que o QR carrega é um COMMITMENT:
HMAC-SHA256 do CPF com a chave de pseudonimização da corrente (a mesma cujo
fingerprint é versionado ao lado dos eventos). Quem tiver o CPF E a chave
reconstrói o HMAC e prova a titularidade; quem tiver só o QR não recupera
nada — HMAC com chave secreta não se inverte por força bruta de 11 dígitos,
que é a fraqueza fatal de um sha256 puro de CPF.

O CPF entra por STDIN (nunca argv — argv vaza em process list e histórico),
é validado pelo dígito verificador da Receita, usado em memória e descartado.

Saídas (0600, como manda a regra de custódia):
  reports/audit/qr-titularidade.png   — o QR
  reports/audit/qr-titularidade.json  — o payload legível
E um evento ``project.authorship`` selado na corrente com o mesmo payload.

Uso: printf '%s' "$CPF" | .venv/bin/python scripts/gerar_qr_titularidade.py
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from asus_theye.audit.dados_pessoais import cpf_valido
from asus_theye.markets.auditoria import (
    abrir_auditoria,
    carregar_chave,
    fingerprint_da_chave,
    selar_registro,
)

TITULAR = "Mateus Menezes Figueiredo"
OBRA = "THE EYE OF GOD — asus_the_eye (motor de mercados preditivos)"
LICENCA = "AGPL-3.0-or-later"
SAIDA = Path("reports/audit")


def main() -> int:
    cpf = "".join(c for c in sys.stdin.read() if c.isdigit())
    if len(cpf) != 11 or not cpf_valido(cpf):
        print("CPF ausente ou com dígito verificador inválido — nada gerado, nada gravado.")
        return 1

    chave = carregar_chave()
    commitment = hmac.new(chave, cpf.encode("ascii"), hashlib.sha256).hexdigest()
    del cpf  # usado, descartado — não viaja para nenhuma saída

    eventos = Path("reports/markets/eventos.jsonl")
    elos = sum(1 for linha in eventos.read_text(encoding="utf-8").splitlines() if linha.strip())
    ultimo = json.loads(eventos.read_text(encoding="utf-8").splitlines()[-1])

    payload = {
        "obra": OBRA,
        "titular": TITULAR,
        "licenca": LICENCA,
        # "titular_commitment", não "cpf_*": o redator LGPD da corrente trata
        # campo com "cpf" no nome como sensível e RECUSA selar (o hash selado
        # divergiria do artefato redigido). O commitment não é o documento —
        # mas o nome do campo tem de dizer isso também.
        "titular_commitment": {
            "algoritmo": "HMAC-SHA256(chave_de_pseudonimizacao, digitos_do_documento_do_titular)",
            "valor": commitment,
            "chave_fingerprint": fingerprint_da_chave(chave),
        },
        "corrente": {
            "arquivo": str(eventos),
            "elos": elos,
            "ultimo_event_hash": ultimo.get("event_hash_sha256"),
        },
        "gerado_em": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "verificacao": (
            "recompute HMAC-SHA256 do CPF do titular com a chave cujo fingerprint "
            "está acima (reports/audit/pseudonimos.key, 0600) e compare"
        ),
    }

    SAIDA.mkdir(parents=True, exist_ok=True)
    caminho_json = SAIDA / "qr-titularidade.json"
    caminho_png = SAIDA / "qr-titularidade.png"
    caminho_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    caminho_json.chmod(0o600)

    import segno

    segno.make(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), error="m").save(
        str(caminho_png), scale=6, border=4
    )
    caminho_png.chmod(0o600)

    # prova de ida e volta: o QR gravado tem de decodificar para o mesmo payload
    try:
        import zxingcpp
        from PIL import Image

        lido = zxingcpp.read_barcode(Image.open(caminho_png))
        assert lido is not None and json.loads(lido.text) == payload, "QR não decodifica para o payload"
        prova = "QR decodificado de volta e conferido byte a byte"
    except ImportError:
        prova = "zxing-cpp/Pillow ausentes — ida-e-volta não conferida"

    sdk = abrir_auditoria()
    selagem = selar_registro(
        sdk,
        payload,
        tipo_evento="project.authorship",
        recurso="titularidade-qr",
        correlation_id=f"titularidade:{commitment[:32]}",
        occurred_at=payload["gerado_em"],
        eventos=eventos,
    )

    print(f"titular: {TITULAR}")
    print(f"commitment (HMAC, não é o CPF): {commitment}")
    print(f"chave fingerprint: {payload['titular_commitment']['chave_fingerprint']}")
    print(f"QR: {caminho_png} · payload: {caminho_json} (ambos 0600)")
    print(f"prova: {prova}")
    estado = "dedupe" if selagem.get("duplicate") else "SELADO"
    print(f"corrente: project.authorship {estado} — {selagem['event_hash_sha256'][:16]}…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
