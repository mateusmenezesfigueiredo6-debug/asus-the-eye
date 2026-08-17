"""F2 — a liquidação sela um evento REAL na cadeia auditável.

Até aqui a cadeia tinha 0 eventos: o núcleo de auditoria (evento de 40 campos,
RFC 8785 + SHA-256, corrente por tenant) existia testado mas desligado de
qualquer mutação real. Este adaptador liga a medição da F1 ao ``AuditSDK``:
cada mercado LIQUIDADO vira um evento ``market.settlement`` selado.

Três decisões de desenho:

1. **O mesmo evento que o verificador valida.** Nada de esquema paralelo: o
   evento selado é o de 40 campos que ``verify_event``/``verify_chain`` aceitam
   — a divergência 6-campos-vs-40-campos do caminho remoto não é reproduzida
   aqui.
2. **Store local + export versionado.** O SQLite (``reports/audit/*.db``,
   fora do git) é a corrente operacional; cada evento selado também é apendado
   em ``reports/markets/eventos.jsonl`` (versionado), de modo que QUALQUER um
   com o repositório consegue verificar hash e encadeamento sem o banco.
3. **Idempotente por claim_id.** A chave de idempotência deriva do
   ``claim_id``: selar de novo a mesma liquidação devolve ``duplicate=True`` e
   não gera evento novo — o laço pode varrer tudo a cada rodada.

A chave de pseudonimização vem de ``THE_EYE_AUDIT_KEY`` ou de um arquivo local
gerado uma vez (``reports/audit/pseudonimos.key``, já coberto pelo .gitignore).
Aqui ela não protege pessoa (os identificadores são de mercados e do serviço);
protege a ESTABILIDADE dos pseudônimos entre rodadas.
"""

from __future__ import annotations

import json
import os
import secrets
from importlib import metadata
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import hash_json
from asus_theye.audit.sdk import AuditSDK, SQLiteAuditStore

TENANT_PADRAO = "tenant-demo"
DB_PADRAO = Path("reports/audit/markets-ledger.db")
CHAVE_PADRAO = Path("reports/audit/pseudonimos.key")
EVENTOS_PADRAO = Path("reports/markets/eventos.jsonl")
SERVICO = "markets-resolver"


class AuditoriaError(RuntimeError):
    """Falha ao selar ou exportar o evento. O chamador decide se surface ou aborta."""


def _versao() -> str:
    try:
        return metadata.version("asus-the-eye")
    except metadata.PackageNotFoundError:  # pragma: no cover - editable quebrado
        return "0.0.0"


def carregar_chave(caminho: Path = CHAVE_PADRAO) -> bytes:
    """Chave de pseudonimização: env ``THE_EYE_AUDIT_KEY`` ou arquivo local.

    O arquivo é gerado uma vez (32 bytes aleatórios, hex) e NUNCA versionado
    (``*.key`` está no .gitignore). Sem estabilidade de chave, os pseudônimos
    mudariam a cada rodada e a corrente perderia a ligação entre eventos.
    """
    env = os.environ.get("THE_EYE_AUDIT_KEY", "")
    if env:
        chave = env.encode("utf-8")
        if len(chave) < 16:
            raise AuditoriaError("THE_EYE_AUDIT_KEY precisa de pelo menos 16 bytes")
        return chave
    if caminho.exists():
        try:
            return bytes.fromhex(caminho.read_text(encoding="utf-8").strip())
        except ValueError as exc:
            raise AuditoriaError(f"chave corrompida em {caminho} (esperado hex)") from exc
    caminho.parent.mkdir(parents=True, exist_ok=True)
    chave = secrets.token_bytes(32)
    caminho.write_text(chave.hex() + "\n", encoding="utf-8")
    return chave


def abrir_auditoria(
    db: Path = DB_PADRAO,
    *,
    chave: bytes | None = None,
    caminho_chave: Path = CHAVE_PADRAO,
) -> AuditSDK:
    """Abre (ou cria) a corrente local e devolve o SDK pronto para selar."""
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteAuditStore(db)
    return AuditSDK(
        store,
        pseudonymization_key=chave or carregar_chave(caminho_chave),
        service=SERVICO,
        build_version=_versao(),
    )


def selar_liquidacao(
    sdk: AuditSDK,
    linha: dict[str, Any],
    *,
    tenant: str = TENANT_PADRAO,
    eventos: Path = EVENTOS_PADRAO,
) -> dict[str, Any]:
    """Sela a liquidação como evento ``market.settlement`` e exporta o selado.

    Idempotente: a chave de idempotência deriva do ``claim_id``; selar duas
    vezes devolve ``duplicate=True`` sem evento novo nem export repetido.
    """
    claim_id = str(linha["claim_id"])
    recibo = sdk.record(
        tenant_id=tenant,
        event_type="market.settlement",
        action="settle",
        correlation_id=claim_id,
        actor_id=SERVICO,
        actor_type="service",
        actor_role="resolver",
        resource_id=claim_id,
        resource_type="market",
        classification="internal",
        occurred_at=str(linha.get("resolved_at") or ""),
        idempotency_key=hash_json(["market.settlement", claim_id]),
        content=linha,
    )
    if recibo.get("duplicate"):
        return recibo

    # export versionado: o evento selado COMPLETO, verificável sem o SQLite
    selado = next(
        (evento for evento in sdk.store.events(tenant) if evento["event_id"] == recibo["event_id"]),
        None,
    )
    if selado is None:  # pragma: no cover - append bem-sucedido garante presença
        raise AuditoriaError(f"{claim_id}: evento gravado mas não encontrado para export")
    eventos.parent.mkdir(parents=True, exist_ok=True)
    with eventos.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(selado, ensure_ascii=False) + "\n")
    return recibo


def cabeca_da_corrente(sdk: AuditSDK, *, tenant: str = TENANT_PADRAO) -> int:
    """Sequência do topo da corrente (0 = vazia)."""
    proxima, _hash = sdk.store.next_position(tenant)
    return proxima - 1
