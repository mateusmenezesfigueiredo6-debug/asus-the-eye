"""N1 — espelha a corrente selada local no ledger restrito da nuvem (D1).

A corrente canônica continua sendo o arquivo versionado
``reports/markets/eventos.jsonl`` — a nuvem guarda o **espelho**: um registro
por evento selado, carregando os hashes que permitem provar o arquivo local
contra o D1 (``event_hash_sha256``, ``content_hash_sha256``, encadeamento).

Regras herdadas do resto da plataforma:

1. **Nunca espelha corrente quebrada.** ``verify_chain`` roda antes de
   qualquer POST — espelhar lixo carimbado de evidência seria pior que não
   espelhar.
2. **Idempotente por conteúdo.** A ``idempotency_key`` deriva do
   ``event_hash_sha256`` do evento local: re-rodar o sync não duplica nada (o
   worker responde ``deduplicated`` em vez de apendar).
3. **Só resumo + hashes sobem.** O conteúdo integral fica no repo; o espelho
   carrega o suficiente para o tie-out (mesma régua do ``--publish`` do
   benchmark).
4. **Falha alto.** Ledger fora do ar ou recusa = exceção, nunca sucesso
   silencioso (regra da mutação crítica).

Token: ``THE_EYE_LEDGER_TOKEN`` ou ``~/.the-eye/staging-token`` (nunca no
repo). URL: ``THE_EYE_LEDGER_URL`` ou ``--ledger-url``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from asus_theye.audit.remote_ledger import publish_event
from asus_theye.audit.schema import verify_chain

EVENTOS_PADRAO = Path("reports/markets/eventos.jsonl")
RECURSO_ESPELHO = "sealed_event_mirror"


class SyncError(RuntimeError):
    """Corrente inválida ou ledger recusou. Sempre levanta — espelho não mente."""


def corpo_do_espelho(evento: dict[str, Any]) -> dict[str, Any]:
    """Traduz um evento selado local para o corpo de ingestão do worker.

    O contrato do worker é estreito (6 campos, strings ≤ 256); o espelho põe a
    prova no ``payload``: hashes e encadeamento do evento local.
    """
    return {
        "tenant_id": str(evento["tenant_id"]),
        "idempotency_key": f"espelho-{evento['event_hash_sha256'][:32]}",
        "event_type": str(evento["event_type"]),
        "resource_type": RECURSO_ESPELHO,
        "resource_id_pseudonymous": f"seq-{int(evento['sequence']):08d}",
        "payload": {
            "sequence": int(evento["sequence"]),
            "event_id": evento.get("event_id"),
            "event_hash_sha256": evento["event_hash_sha256"],
            "content_hash_sha256": evento.get("content_hash_sha256"),
            "previous_event_hash_sha256": evento.get("previous_event_hash_sha256"),
            "occurred_at": evento.get("occurred_at"),
            "schema_version": evento.get("schema_version"),
        },
    }


def sincronizar(
    ledger_url: str,
    *,
    eventos: Path = EVENTOS_PADRAO,
    tenant: str = "tenant-demo",
    publicar: Any = publish_event,
) -> dict[str, Any]:
    """Espelha a corrente local inteira no ledger. Devolve o placar do sync.

    ``publicar`` é injetável (testes não fazem rede). O placar diz quantos
    eventos subiram agora e quantos o worker já conhecia (dedupe) — re-rodar
    com corrente inalterada tem de dar ``novos == 0``.
    """
    if not eventos.exists():
        raise SyncError(f"corrente ausente: {eventos} — nada a espelhar")
    selados = [json.loads(li) for li in eventos.read_text(encoding="utf-8").splitlines() if li.strip()]
    selados = [evento for evento in selados if evento.get("tenant_id") == tenant]
    if not selados:
        raise SyncError(f"nenhum evento do tenant {tenant!r} em {eventos}")
    if not verify_chain(selados):
        raise SyncError(f"{eventos}: a corrente não verifica — corrente quebrada não se espelha")

    novos = 0
    dedupe = 0
    recibos: list[dict[str, Any]] = []
    for evento in sorted(selados, key=lambda e: int(e["sequence"])):
        recibo = publicar(corpo_do_espelho(evento), ledger_url)
        if recibo.get("deduplicated"):
            dedupe += 1
        else:
            novos += 1
        recibos.append(
            {
                "sequence_local": int(evento["sequence"]),
                "event_hash_local": evento["event_hash_sha256"],
                "sequence_remota": recibo.get("sequence"),
                "deduplicated": bool(recibo.get("deduplicated", False)),
            }
        )
    return {
        "eventos_locais": len(selados),
        "novos": novos,
        "dedupe": dedupe,
        "recibos": recibos,
        "metodo": (
            "um espelho por evento selado; idempotency_key = espelho-<event_hash[:32]>; "
            "re-rodar com corrente inalterada dá novos == 0"
        ),
    }
