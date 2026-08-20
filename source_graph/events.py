# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Corpos de evento para o ledger — só hashes e contagens, nunca conteúdo.

Nenhum corpo de resposta, título, resumo ou nome de pessoa vai ao ledger. O que
vai é a prova de que algo foi buscado, quando, sob qual base de acesso, e com
qual hash — o suficiente para verificar depois, insuficiente para reconstruir.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.parse import urlsplit

from asus_theye.audit.remote_ledger import DEFAULT_TENANT


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def snapshot_hash(payload: Any) -> str:
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def source_snapshot_event(result: Any, source_id: str, tenant_id: str = DEFAULT_TENANT) -> dict:
    """Uma captura de fonte externa. ``result`` é um FetchResult."""
    return {
        "tenant_id": tenant_id,
        "idempotency_key": f"srcgraph-{result.content_hash_sha256[:32]}",
        "event_type": "source.snapshot.recorded",
        "resource_type": "knowledge_source",
        "resource_id_pseudonymous": f"src-{result.content_hash_sha256[:16]}",
        "payload": {
            "source_id": source_id,
            "connector_id": result.connector_id,
            "host": urlsplit(result.url).netloc,
            "content_hash_sha256": result.content_hash_sha256,
            "retrieved_at": result.retrieved_at,
            "byte_length": result.byte_length,
            "http_status": result.status,
            "robots_decision": result.robots_decision,
            "license_id": result.license_id,
            "retries": result.retries,
        },
    }


def graph_built_event(snapshot: dict[str, Any], commit: str, tenant_id: str = DEFAULT_TENANT) -> dict:
    """O grafo inteiro num momento: contagens e hash, nunca as entidades."""
    digest = snapshot_hash(snapshot)
    return {
        "tenant_id": tenant_id,
        "idempotency_key": f"srcgraph-built-{digest[:26]}",
        "event_type": "source.graph.built",
        "resource_type": "source_graph_snapshot",
        "resource_id_pseudonymous": f"graph-{digest[:16]}",
        "payload": {
            "snapshot_hash_sha256": digest,
            "sources_total": snapshot.get("sources_total", 0),
            "by_category": snapshot.get("by_category", {}),
            "methodology_version": snapshot.get("methodology_version", ""),
            "commit": commit,
        },
    }


def ranking_published_event(ranking_list: dict[str, Any], tenant_id: str = DEFAULT_TENANT) -> dict:
    """Uma lista ranqueada: metadados de cobertura, nenhuma entidade nomeada."""
    digest = snapshot_hash(ranking_list)
    return {
        "tenant_id": tenant_id,
        "idempotency_key": f"srcgraph-rank-{digest[:26]}",
        "event_type": "ranking.published",
        "resource_type": "ranking_list",
        "resource_id_pseudonymous": f"rank-{digest[:16]}",
        "payload": {
            "list_id": ranking_list["list_id"],
            "entity_type": ranking_list["entity_type"],
            "list_scope": ranking_list["list_scope"],
            "category_id": ranking_list["category_id"],
            "methodology_version": ranking_list["methodology_version"],
            "qualified_count": ranking_list["qualified_count"],
            "target_size": ranking_list["target_size"],
            "padded": ranking_list["padded"],
            "cut_off_date": ranking_list["cut_off_date"],
            "snapshot_hash_sha256": digest,
        },
    }
