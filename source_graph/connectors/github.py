# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector GitHub — mineração de metadados de repositórios públicos.

Legitimidade, em quatro pontos:

1. **Dados públicos**: só repositórios públicos, via a API REST oficial.
2. **Credencial do próprio usuário**: usa o ``gh`` já autenticado; nenhum token é
   lido, guardado ou transmitido por este código.
3. **Nada de raspagem**: a API é o caminho documentado; robots.txt do site não se
   aplica a ela, e os termos autorizam uso programático (``access_basis``).
4. **Nada de popularidade**: estrelas, forks e seguidores são coletados como
   contexto factual mas **nunca** viram componente de score — a missão proíbe
   ranquear por métrica social, e ``component_id`` é enum fechado.

O que se extrai e vira evidência: **licença verificada** (o campo `spdx_id` da
API, com hash do conteúdo), atividade datada (para `recency_continuity`), e
existência de release (para `poc_status: production`).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from typing import Any

CONNECTOR_ID = "github"
LICENSE_URL = "https://docs.github.com/en/rest"
TERMS_URL = "https://docs.github.com/en/site-policy/github-terms/github-terms-of-service"
ACCESS_BASIS = f"api_terms:{TERMS_URL}"

# Coletados como contexto factual, NUNCA como componente de score.
SOCIAL_FIELDS = ("stargazers_count", "forks_count", "subscribers_count", "watchers_count")


class GitHubError(RuntimeError):
    """A API do GitHub falhou ou o repositório não existe."""


def _gh_api(path: str) -> dict[str, Any]:
    """Chama a API via o ``gh`` já autenticado do usuário.

    Delegar ao ``gh`` é deliberado: este código nunca vê, lê nem grava o token.
    """
    try:
        proc = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=60, check=True)
    except subprocess.CalledProcessError as error:
        raise GitHubError(f"{path}: {error.stderr.strip()[:200]}") from error
    except FileNotFoundError as error:
        raise GitHubError("gh CLI não encontrado — instale ou autentique com `gh auth login`") from error
    except subprocess.TimeoutExpired as error:
        raise GitHubError(f"{path}: tempo esgotado") from error
    return json.loads(proc.stdout)


def _repo_path(repo_url: str) -> str:
    """Extrai ``owner/name`` de uma URL do GitHub."""
    parts = repo_url.rstrip("/").split("github.com/", 1)
    if len(parts) != 2:
        raise GitHubError(f"não é uma URL do GitHub: {repo_url}")
    return "/".join(parts[1].split("/")[:2])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _years_since(timestamp: str | None) -> float | None:
    if not timestamp:
        return None
    moment = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return round((datetime.now(timezone.utc) - moment).days / 365.25, 2)


def fetch_repository(repo_url: str) -> dict[str, Any]:
    """Metadados verificados de um repositório público.

    Devolve o registro com ``content_hash_sha256`` da resposta exata, para que a
    afirmação seja auditável depois — a mesma regra do resto do projeto.
    """
    path = _repo_path(repo_url)
    payload = _gh_api(f"repos/{path}")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    license_info = payload.get("license") or {}
    latest_release: dict[str, Any] | None = None
    try:
        latest_release = _gh_api(f"repos/{path}/releases/latest")
    except GitHubError:
        latest_release = None  # repositório sem release é fato, não falha

    return {
        "repo": path,
        "official_url": payload.get("html_url"),
        "retrieved_at": _utc_now(),
        "content_hash_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        # --- evidência que vira componente de score ---
        "license_spdx": license_info.get("spdx_id"),
        "license_name": license_info.get("name"),
        "license_url": license_info.get("url"),
        "has_release": latest_release is not None,
        "latest_release_tag": (latest_release or {}).get("tag_name"),
        "latest_release_at": (latest_release or {}).get("published_at"),
        "pushed_at": payload.get("pushed_at"),
        "years_since_push": _years_since(payload.get("pushed_at")),
        "archived": payload.get("archived", False),
        "open_issues": payload.get("open_issues_count"),
        "language": payload.get("language"),
        "topics": payload.get("topics", []),
        "description": (payload.get("description") or "")[:280],
        # --- contexto factual, NUNCA componente de score ---
        "social_context_not_scored": {field: payload.get(field) for field in SOCIAL_FIELDS if field in payload},
        "connector_id": CONNECTOR_ID,
        "access_basis": ACCESS_BASIS,
        "claim_class": "FACT",
    }


def verify_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    """Confronta a licença DECLARADA no registry com a que o GitHub reporta.

    Este é o ponto: promover ``declared_unverified`` a ``verified`` só quando a
    fonte primária concorda. Divergência não é corrigida em silêncio — vira
    ``license_mismatch``, com os dois valores lado a lado para revisão humana.
    """
    declared = artifact.get("license_id", "")
    try:
        fetched = fetch_repository(artifact["repo_url"])
    except GitHubError as error:
        return {
            **artifact,
            "verification_status": "fetch_failed",
            "verification_note": str(error)[:200],
            "verified_at": _utc_now(),
        }

    observed = fetched.get("license_spdx") or "NOASSERTION"
    # SPDX-Modified etc. são variações locais do registry; comparação por prefixo.
    matches = observed != "NOASSERTION" and declared.split("-Modified")[0] == observed

    poc = artifact.get("poc_status")
    if poc == "production" and not fetched["has_release"]:
        poc_note = "declarado 'production' mas o repositório não tem release publicada"
    elif fetched["archived"]:
        poc_note = "repositório ARQUIVADO — não é mais mantido"
    else:
        poc_note = None

    return {
        **artifact,
        "verification_status": "verified" if matches else "license_mismatch",
        "license_declared": declared,
        "license_observed": observed,
        "license_name": fetched.get("license_name"),
        "content_hash_sha256": fetched["content_hash_sha256"],
        "official_url": fetched["official_url"],
        "has_release": fetched["has_release"],
        "latest_release_tag": fetched.get("latest_release_tag"),
        "pushed_at": fetched.get("pushed_at"),
        "years_since_push": fetched.get("years_since_push"),
        "archived": fetched["archived"],
        "language": fetched.get("language"),
        "topics": fetched.get("topics", []),
        "poc_note": poc_note,
        "social_context_not_scored": fetched["social_context_not_scored"],
        "verified_at": _utc_now(),
        "claim_class": "FACT",
    }
