# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Smoke da corrente versionada REAL do repositório.

Antes de mexer em armazenamento (F1), fixa-se o fato de que a corrente de
eventos publicada em ``reports/markets/eventos.jsonl`` verifica de ponta a
ponta. Qualquer mudança que quebre a leitura, o encadeamento ou a selagem
desses eventos tem de acusar AQUI, não em produção. O último teste corrompe
uma corrente sintética para provar que o ``True`` do verificador não é vácuo.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import GENESIS_HASH, SCHEMA_VERSION, seal_event
from asus_theye.audit.verifier import verify_chain

REPO = Path(__file__).resolve().parents[2]
EVENTOS_JSONL = REPO / "reports" / "markets" / "eventos.jsonl"

# Os campos que fazem um evento ser um ELO: sem qualquer um deles não há
# corrente, só uma lista de dicionários.
CAMPOS_DE_ENCADEAMENTO = ("tenant_id", "sequence", "previous_event_hash_sha256", "event_hash_sha256")


def _carregar_eventos() -> list[dict[str, Any]]:
    linhas = EVENTOS_JSONL.read_text(encoding="utf-8").splitlines()
    return [json.loads(linha) for linha in linhas if linha.strip()]


# ------------------------------------------------------------------ corrente real


def test_corrente_real_do_repo_verifica_de_ponta_a_ponta():
    """O JSONL publicado é história selada: 184+ elos, todos íntegros."""
    eventos = _carregar_eventos()
    assert len(eventos) >= 184
    assert verify_chain(eventos) is True


def test_todo_evento_da_corrente_real_tem_os_campos_de_encadeamento():
    """Um elo sem hash ou sem sequência quebraria a verificação em silêncio."""
    for evento in _carregar_eventos():
        for campo in CAMPOS_DE_ENCADEAMENTO:
            assert campo in evento, f"evento {evento.get('event_id', '?')} sem campo {campo!r}"


def test_primeiro_elo_da_corrente_real_ancora_no_genesis():
    """A corrente começa no hash gênese — não num elo perdido de outra história."""
    primeiro = min(_carregar_eventos(), key=lambda evento: evento["sequence"])
    assert primeiro["previous_event_hash_sha256"] == GENESIS_HASH


# ------------------------------------- prova de não-vacuidade (corrente sintética)


def _evento_selado(sequence: int, previous: str) -> dict[str, Any]:
    """Evento mínimo válido do esquema 1.0.0, selado. Valores 100% de teste."""
    corpo = {
        "schema_version": SCHEMA_VERSION,
        "event_id": f"evento-sintetico-{sequence}",
        "idempotency_key": f"idem-{sequence:016d}",
        "tenant_id": "tenant-teste",
        "sequence": sequence,
        "event_type": "market.settlement",
        "action": "settle",
        "occurred_at": "2026-08-02T00:00:00Z",
        "recorded_at": "2026-08-02T00:00:01Z",
        "actor_type": "service",
        "actor_id_pseudonymous": "1" * 64,
        "actor_role": "resolver",
        "source_system": "teste",
        "resource_type": "market",
        "resource_id_pseudonymous": "2" * 64,
        "resource_version": str(sequence),
        "jurisdiction": "BR",
        "legal_area_ids": [],
        "classification": "internal",
        "retention_policy_id": "audit-default-v1",
        "lawful_basis_reference": "apenas-teste",
        "content_hash_sha256": "3" * 64,
        "metadata_hash_sha256": "4" * 64,
        "previous_event_hash_sha256": previous,
        "correlation_id": "correlacao-teste",
        "causation_id": None,
        "model_provider": None,
        "model_name": None,
        "model_version": None,
        "prompt_template_version": None,
        "source_citation_hashes": [],
        "human_review_status": "not_required",
        "reviewer_pseudonymous": None,
        "result_status": "success",
        "error_code": None,
        "created_by_service": "teste",
        "build_version": "teste",
    }
    return seal_event(corpo)


def _corrente_sintetica(tamanho: int = 3) -> list[dict[str, Any]]:
    eventos, previous = [], GENESIS_HASH
    for sequence in range(1, tamanho + 1):
        evento = _evento_selado(sequence, previous)
        eventos.append(evento)
        previous = evento["event_hash_sha256"]
    return eventos


def test_elo_do_meio_corrompido_e_acusado():
    """Prova que o True dos testes acima não é vácuo: adulterar um corpo acusa."""
    corrente = _corrente_sintetica(3)
    assert verify_chain(corrente) is True  # o construtor produz corrente válida

    corrompida = copy.deepcopy(corrente)
    corrompida[1]["action"] = "delete"  # muda o corpo do elo do meio sem re-selar
    assert verify_chain(corrompida) is False

    religada = copy.deepcopy(corrente)
    religada[1]["previous_event_hash_sha256"] = "f" * 64  # religa o meio a outra história
    assert verify_chain(religada) is False


def test_elo_removido_do_meio_quebra_a_corrente():
    """Apagar história também acusa: a lacuna de sequência derruba a verificação."""
    corrente = _corrente_sintetica(3)
    assert verify_chain([corrente[0], corrente[2]]) is False
