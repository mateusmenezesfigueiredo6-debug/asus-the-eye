# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""F2 — a liquidação sela um evento REAL na cadeia auditável.

Até aqui a cadeia tinha 0 eventos: o núcleo de auditoria (evento de 37 campos
obrigatórios; 38 no schema JSON, + hash de selagem no arquivo; RFC 8785 +
SHA-256, corrente por tenant) existia testado mas desligado de
qualquer mutação real. Este adaptador liga a medição da F1 ao ``AuditSDK``:
cada mercado LIQUIDADO vira um evento ``market.settlement`` selado.

Decisões de desenho (endurecidas pela revisão adversarial):

1. **O mesmo evento que o verificador valida.** Nada de esquema paralelo: o
   evento selado é o de 37 campos obrigatórios (38 no schema JSON, + hash de
   selagem no arquivo) que ``verify_event``/``verify_chain`` aceitam.
2. **O arquivo versionado é a corrente canônica; o SQLite é cache operacional.**
   ``reports/markets/eventos.jsonl`` viaja com o repo e qualquer um verifica sem
   o banco. Na abertura, o banco é RESSINCRONIZADO a partir do arquivo
   (verificado primeiro): clone fresco ou banco apagado não bifurca a corrente —
   as posições e as chaves de idempotência são restauradas antes de qualquer
   selagem nova.
3. **Export auto-reparador.** A presença no arquivo é conferida por
   ``event_id`` em TODA selagem (inclusive ``duplicate=True``): queda entre o
   commit SQLite e o append não perde evento — a próxima rodada repara.
4. **Idempotente por claim_id, com divergência DETECTADA.** Selar de novo a
   mesma liquidação devolve ``duplicate=True``; se o conteúdo divergir do que
   foi selado (``content_hash``), LEVANTA — dedupe nunca esconde divergência.
5. **A corrente pertence a UMA chave.** A impressão digital da chave de
   pseudonimização (HMAC de constante) fica VERSIONADA ao lado da corrente;
   chave diferente da original é recusada com instrução clara, em vez de trocar
   pseudônimos no meio da corrente em silêncio.

A chave vem de ``THE_EYE_AUDIT_KEY`` ou de um arquivo local gerado uma vez
(``reports/audit/pseudonimos.key``, coberto pelo .gitignore). Aqui ela não
protege pessoa (identificadores são de mercados e do serviço); protege a
ESTABILIDADE dos pseudônimos entre rodadas.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from importlib import metadata
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import hash_json, verify_chain
from asus_theye.audit.sdk import AuditSDK, SQLiteAuditStore, redact

TENANT_PADRAO = "tenant-demo"
DB_PADRAO = Path("reports/audit/markets-ledger.db")
CHAVE_PADRAO = Path("reports/audit/pseudonimos.key")
EVENTOS_PADRAO = Path("reports/markets/eventos.jsonl")
FINGERPRINT_PADRAO = Path("reports/markets/chave.fingerprint")
SERVICO = "markets-resolver"


class AuditoriaError(RuntimeError):
    """Falha ao selar, sincronizar ou exportar. O chamador decide se surface ou aborta."""


def _versao() -> str:
    try:
        return metadata.version("asus-the-eye")
    except metadata.PackageNotFoundError:  # pragma: no cover - editable quebrado
        return "0.0.0"


def _fingerprint(chave: bytes) -> str:
    """Identidade pública da chave: HMAC de constante. Não revela a chave
    (32 bytes aleatórios), mas deixa qualquer máquina detectar chave trocada."""
    return hmac.new(chave, b"the-eye-markets-key-fingerprint", hashlib.sha256).hexdigest()


def fingerprint_da_chave(chave: bytes) -> str:
    """API pública da impressão da chave, sem expor a chave em si."""
    return _fingerprint(chave)


def _eventos_do_arquivo(eventos: Path) -> list[dict[str, Any]]:
    if not eventos.exists():
        return []
    selados = []
    for linha in eventos.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            selados.append(json.loads(linha))
    return selados


def carregar_chave(caminho: Path = CHAVE_PADRAO) -> bytes:
    """Chave de pseudonimização: env ``THE_EYE_AUDIT_KEY`` ou arquivo local.

    O arquivo é gerado uma vez (32 bytes aleatórios, hex) e NUNCA versionado
    (``*.key`` está no .gitignore).
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


def _travar_chave(chave: bytes, fingerprint: Path) -> None:
    """A corrente pertence a UMA chave: compara (ou grava) a impressão digital.

    A impressão é VERSIONADA junto da corrente: num clone fresco, a chave local
    recém-gerada não bate com a da corrente e a selagem é recusada com
    instrução, em vez de bifurcar pseudônimos em silêncio.
    """
    atual = _fingerprint(chave)
    if fingerprint.exists():
        gravada = fingerprint.read_text(encoding="utf-8").strip()
        if gravada and gravada != atual:
            raise AuditoriaError(
                "a chave de pseudonimização ativa não é a da corrente "
                f"(impressão {atual[:16]}… ≠ {gravada[:16]}…). Defina THE_EYE_AUDIT_KEY "
                "com a chave original (ou copie reports/audit/pseudonimos.key da máquina "
                "de origem). Selar com chave trocada bifurcaria os pseudônimos."
            )
        if gravada:
            return
    fingerprint.parent.mkdir(parents=True, exist_ok=True)
    fingerprint.write_text(atual + "\n", encoding="utf-8")


def _sincronizar_do_export(sdk: AuditSDK, eventos: Path, tenant: str) -> int:
    """Ressincroniza o SQLite a partir da corrente versionada (a canônica).

    Verifica a corrente do arquivo e apende no banco, na ordem, todo evento à
    frente da cabeça local — restaurando posições E chaves de idempotência.
    Devolve quantos eventos foram restaurados.
    """
    selados = [e for e in _eventos_do_arquivo(eventos) if e.get("tenant_id") == tenant]
    if not selados:
        return 0
    if not verify_chain(selados):
        raise AuditoriaError(
            f"{eventos}: a corrente versionada não verifica (hash ou encadeamento) — "
            "investigue antes de qualquer selagem nova"
        )
    cabeca = cabeca_da_corrente(sdk, tenant=tenant)
    restaurados = 0
    for evento in sorted(selados, key=lambda e: int(e["sequence"])):
        if int(evento["sequence"]) > cabeca:
            sdk.store.append(evento)  # verbatim: verify_event + posição conferidos pelo store
            restaurados += 1
    return restaurados


def abrir_auditoria(
    db: Path = DB_PADRAO,
    *,
    chave: bytes | None = None,
    caminho_chave: Path = CHAVE_PADRAO,
    eventos: Path = EVENTOS_PADRAO,
    fingerprint: Path = FINGERPRINT_PADRAO,
    tenant: str = TENANT_PADRAO,
) -> AuditSDK:
    """Abre a corrente local pronta para selar: chave travada e banco em dia.

    Ordem: trava de chave (recusa chave trocada) → ressincronização do banco a
    partir da corrente versionada (clone fresco não bifurca).
    """
    chave_ativa = chave or carregar_chave(caminho_chave)
    _travar_chave(chave_ativa, fingerprint)
    db.parent.mkdir(parents=True, exist_ok=True)
    store = SQLiteAuditStore(db)
    sdk = AuditSDK(store, pseudonymization_key=chave_ativa, service=SERVICO, build_version=_versao())
    _sincronizar_do_export(sdk, eventos, tenant)
    return sdk


def selar_registro(
    sdk: AuditSDK,
    conteudo: dict[str, Any],
    *,
    tipo_evento: str,
    recurso: str,
    correlation_id: str,
    action: str | None = None,
    occurred_at: str = "",
    tenant: str = TENANT_PADRAO,
    eventos: Path = EVENTOS_PADRAO,
) -> dict[str, Any]:
    """Sela QUALQUER medição na corrente e garante o export — a via genérica.

    Toda medição da plataforma vira evento com hash por aqui: liquidações,
    medições do projeto, corridas de ML. Garantias herdadas do endurecimento F2:
    idempotente por ``(tipo_evento, correlation_id)``; divergência de conteúdo no
    dedupe LEVANTA; export auto-reparador (presença por ``event_id`` em toda
    selagem, com ``export_reparado=True`` quando a rodada só reparou).
    """
    conteudo_hash = hash_json(redact(conteudo))
    if conteudo_hash != hash_json(conteudo):
        raise AuditoriaError(
            f"{correlation_id}: o conteúdo tem campo tratado como sensível pelo redator — o hash "
            "selado divergiria do artefato publicado; renomeie o campo"
        )

    extras: dict[str, Any] = {}
    if occurred_at:  # vazio: sdk.record usa o agora — string vazia não é ISO 8601
        extras["occurred_at"] = occurred_at
    recibo = sdk.record(
        tenant_id=tenant,
        event_type=tipo_evento,
        action=action or tipo_evento.split(".")[-1],
        correlation_id=correlation_id,
        actor_id=SERVICO,
        actor_type="service",
        actor_role="resolver",
        resource_id=correlation_id,
        resource_type=recurso,
        classification="internal",
        idempotency_key=hash_json([tipo_evento, correlation_id]),
        content=conteudo,
        **extras,
    )

    selado = next(
        (evento for evento in sdk.store.events(tenant) if evento["event_id"] == recibo["event_id"]),
        None,
    )
    if selado is None:  # pragma: no cover - append bem-sucedido garante presença
        raise AuditoriaError(f"{correlation_id}: evento gravado mas não encontrado para export")

    # dedupe NUNCA esconde divergência: mesma correlação com conteúdo diferente levanta
    if recibo.get("duplicate") and selado["content_hash_sha256"] != conteudo_hash:
        raise AuditoriaError(
            f"{correlation_id}: o conteúdo atual diverge do já selado "
            f"(content_hash {conteudo_hash[:16]}… ≠ {selado['content_hash_sha256'][:16]}…) — "
            "investigue antes de qualquer selagem nova"
        )

    # export auto-reparador: presença por event_id, nunca condicionada a duplicate
    exportados = {evento.get("event_id") for evento in _eventos_do_arquivo(eventos)}
    if selado["event_id"] not in exportados:
        eventos.parent.mkdir(parents=True, exist_ok=True)
        with eventos.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(selado, ensure_ascii=False) + "\n")
        if recibo.get("duplicate"):
            recibo["export_reparado"] = True
    return recibo


def selar_liquidacao(
    sdk: AuditSDK,
    linha: dict[str, Any],
    *,
    tenant: str = TENANT_PADRAO,
    eventos: Path = EVENTOS_PADRAO,
) -> dict[str, Any]:
    """Sela a liquidação como ``market.settlement`` — atalho sobre a via genérica."""
    claim_id = str(linha["claim_id"])
    return selar_registro(
        sdk,
        linha,
        tipo_evento="market.settlement",
        recurso="market",
        correlation_id=claim_id,
        action="settle",
        occurred_at=str(linha.get("resolved_at") or ""),
        tenant=tenant,
        eventos=eventos,
    )


def cabeca_da_corrente(sdk: AuditSDK, *, tenant: str = TENANT_PADRAO) -> int:
    """Sequência do topo da corrente (0 = vazia)."""
    proxima, _hash = sdk.store.next_position(tenant)
    return proxima - 1


# ------------------------------------------------- reconciliação de selagem


def reconciliar_divergencia(
    sdk: AuditSDK,
    *,
    correlation_id: str,
    hash_selado_original: str,
    hash_atual: str,
    motivo: str,
    tenant: str = TENANT_PADRAO,
    eventos: Path = EVENTOS_PADRAO,
) -> dict[str, Any]:
    """Documenta, na própria corrente, que um conteúdo selado divergiu — e por quê.

    O caso que exige isto: o esquema do conteúdo evolui DEPOIS de um evento ter
    sido selado. O hash antigo fica órfão — o conteúdo que o gerou não existe
    mais em lugar nenhum — e a re-selagem idempotente passa a acusar divergência
    para sempre. Reescrever a corrente é proibido; silenciar a divergência seria
    pior. O que resta é o caminho desta função: **apendar** um evento de
    reconciliação que nomeia os dois hashes e o motivo, para que a divergência
    vire história documentada em vez de alarme eterno.

    A identidade do evento AMARRA o par: ``reconciliacao:{correlation}:{hash_atual[:16]}``.
    Se o conteúdo atual mudar de novo, o hash muda, a reconciliação antiga deixa
    de cobrir, e a varredura volta a falhar — que é o comportamento certo: cada
    forma nova exige decisão nova, nunca um passe livre permanente.
    """
    conteudo = {
        "correlation_id": correlation_id,
        "hash_selado_original": hash_selado_original,
        "hash_atual": hash_atual,
        "motivo": motivo,
    }
    return selar_registro(
        sdk,
        conteudo,
        tipo_evento="audit.reconciliation",
        recurso="audit",
        correlation_id=f"reconciliacao:{correlation_id}:{hash_atual[:16]}",
        action="reconcile",
        tenant=tenant,
        eventos=eventos,
    )


def divergencia_reconciliada(
    correlation_id: str,
    hash_atual: str,
    *,
    eventos: Path = EVENTOS_PADRAO,
) -> bool:
    """A divergência deste par (correlação, hash atual) já foi documentada?

    A resposta vem do export versionado, e a chave é o ``correlation_id``
    estruturado — que amarra o hash ATUAL. Reconciliação de um hash antigo não
    cobre um conteúdo que mudou de novo.
    """
    alvo = f"reconciliacao:{correlation_id}:{hash_atual[:16]}"
    return any(
        evento.get("event_type") == "audit.reconciliation" and evento.get("correlation_id") == alvo
        for evento in _eventos_do_arquivo(eventos)
    )


def hash_de_conteudo(conteudo: dict[str, Any]) -> str:
    """O hash que a selagem usaria — exposto para quem precisa comparar antes."""
    return hash_json(redact(conteudo))


def settlement_selado(
    correlation_id: str,
    *,
    eventos: Path = EVENTOS_PADRAO,
) -> dict[str, Any] | None:
    """O evento market.settlement já selado para este claim, se houver."""
    for evento in _eventos_do_arquivo(eventos):
        if evento.get("event_type") == "market.settlement" and evento.get("correlation_id") == correlation_id:
            return evento
    return None
