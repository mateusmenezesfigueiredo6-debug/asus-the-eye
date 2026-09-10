# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Um arquivo de eventos pode conter MAIS DE UMA corrente.

Aconteceu de verdade em 04/09/2026: o commit a113557 trocou o TENANT_PADRAO de
`tenant-demo` para o nome do titular. A partir daí `eventos.jsonl` passou a
guardar duas correntes — 220 elos da antiga, 42 da nova — cada uma íntegra.

`verify_chain` é mono-tenant POR CONSTRUÇÃO: fixa o tenant no primeiro evento e
reprova qualquer outro (schema.py:91,96). Essa rigidez é garantia, e os testes
em test_audit_core.py e test_eventos_corrente_smoke.py dependem dela — por isso
ela NÃO muda.

O que estava errado era o leitor: quem lê o arquivo inteiro precisa perguntar
"cada corrente aqui dentro está íntegra?", não "isto tudo é uma corrente só?".
Ler errado fez o grafo de evidência gravar `estado="tampered"` — o sistema
acusando a própria corrente do titular de adulteração, sem adulteração alguma.
"""
import json
from pathlib import Path

import pytest

from asus_theye.audit.schema import verify_chain, verify_chains


def _evento(tenant: str, sequence: int, previous: str) -> dict:
    """Evento mínimo válido do esquema 1.0.0, selado, com tenant parametrizado.

    Mesmo corpo de `tests/markets/test_eventos_corrente_smoke.py::_evento_selado`
    — copiado em vez de importado porque aquele crava um tenant só, e é
    justamente o tenant que este arquivo precisa variar.
    """
    from asus_theye.audit.schema import SCHEMA_VERSION, seal_event

    return seal_event(
        {
            "schema_version": SCHEMA_VERSION,
            "event_id": f"{tenant}-{sequence}",
            "idempotency_key": f"idem-{tenant}-{sequence:012d}",
            "tenant_id": tenant,
            "sequence": sequence,
            "event_type": "market.settlement",
            "action": "settle",
            "occurred_at": "2026-09-06T00:00:00Z",
            "recorded_at": "2026-09-06T00:00:01Z",
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
    )


def _corrente(tenant: str, n: int = 3) -> list[dict]:
    """Corrente válida de n elos para um tenant."""
    from asus_theye.audit.schema import GENESIS_HASH

    eventos, anterior = [], GENESIS_HASH
    for i in range(1, n + 1):
        e = _evento(tenant, i, anterior)
        eventos.append(e)
        anterior = e["event_hash_sha256"]
    return eventos


def test_uma_corrente_so_se_comporta_como_antes():
    uma = _corrente("tenant-unico")
    assert verify_chain(uma) is True
    assert verify_chains(uma) is True


def test_duas_correntes_validas_no_mesmo_arquivo_passam():
    """O caso real de 04/09: verify_chain reprova, verify_chains aprova."""
    duas = _corrente("tenant-demo", 4) + _corrente("titular-mateus", 3)
    assert verify_chain(duas) is False, "mono-tenant reprova, e é para reprovar"
    assert verify_chains(duas) is True, "cada corrente é íntegra — o arquivo está são"


def test_uma_corrente_adulterada_entre_duas_reprova_o_conjunto():
    """A garantia não pode afrouxar: mexer num elo derruba tudo."""
    duas = _corrente("tenant-demo", 4) + _corrente("titular-mateus", 3)
    duas[5]["action"] = "delete"  # muda o corpo sem re-selar
    assert verify_chains(duas) is False


def test_elo_faltando_no_meio_de_uma_das_correntes_reprova():
    a = _corrente("tenant-a", 4)
    b = _corrente("tenant-b", 3)
    assert verify_chains(a + b[:1] + b[2:]) is False


def test_ordem_das_linhas_no_arquivo_nao_importa():
    a, b = _corrente("tenant-a", 3), _corrente("tenant-b", 3)
    intercalado = [a[0], b[0], a[1], b[1], a[2], b[2]]
    assert verify_chains(intercalado) is True


def test_vazio_e_verdadeiro():
    assert verify_chains([]) is True


def test_a_corrente_real_do_repo_tem_todas_as_suas_correntes_integras():
    """O teste que teria pego o problema no dia em que ele nasceu."""
    p = Path(__file__).resolve().parents[2] / "reports" / "markets" / "eventos.jsonl"
    if not p.exists():
        pytest.skip("corrente real ausente")
    eventos = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    tenants = {e["tenant_id"] for e in eventos}
    assert verify_chains(eventos) is True, (
        f"{len(eventos)} eventos em {len(tenants)} corrente(s); alguma não fecha"
    )
