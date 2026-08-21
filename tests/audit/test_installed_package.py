# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testa que o pacote instalado (não-editável) consegue selar eventos.

O defeito original: ``sdk.py`` resolvia o caminho da migração via
``Path(__file__).parents[N]``, que só acerta no layout do repositório.
Instalado como pacote regular, esse caminho aponta para dentro de
``site-packages`` onde o arquivo não está, levantando ``FileNotFoundError``
e impedindo qualquer selagem.

Este teste comprova que a correção funciona em AMBOS os casos:
1. No repositório (editable install / dev): caminho via symlink.
2. Pacote instalado: caminho via ``importlib.resources``.
"""

from __future__ import annotations

import importlib.resources
from pathlib import Path

import pytest

from asus_theye.audit.schema import GENESIS_HASH, SCHEMA_VERSION, seal_event
from asus_theye.audit.sdk import SQLiteAuditStore


def test_migration_sql_legivel_via_importlib_resources() -> None:
    """O arquivo de migração deve ser legível independentemente do layout."""
    ref = importlib.resources.files("asus_theye").joinpath("migrations/0001_audit_ledger.sql")
    sql = ref.read_text(encoding="utf-8")
    assert "audit_events" in sql, "migração deve criar tabela audit_events"
    assert "CREATE TABLE IF NOT EXISTS audit_events" in sql


def test_sqliteauditstore_abre_sem_file_not_found_error() -> None:
    """SQLiteAuditStore não deve levantar FileNotFoundError na construção."""
    store = SQLiteAuditStore(":memory:")
    assert store.connection is not None


def test_selar_evento_com_store_em_memoria() -> None:
    """Selagem completa usando apenas o pacote instalado — sem deps do repo."""
    store = SQLiteAuditStore(":memory:")
    raw = {
        "schema_version": SCHEMA_VERSION,
        "event_id": "evt-instalado-01",
        "idempotency_key": "prova-instalado",
        "tenant_id": "tenant-test",
        "sequence": 1,
        "event_type": "document.created",
        "action": "create",
        "occurred_at": "2026-08-20T00:00:00Z",
        "recorded_at": "2026-08-20T00:00:01Z",
        "actor_type": "service",
        "actor_id_pseudonymous": "a" * 64,
        "actor_role": "writer",
        "source_system": "integration-test",
        "resource_type": "document",
        "resource_id_pseudonymous": "b" * 64,
        "resource_version": "1",
        "jurisdiction": "BR",
        "legal_area_ids": [],
        "classification": "restricted",
        "retention_policy_id": "audit-default-v1",
        "lawful_basis_reference": "test-only",
        "content_hash_sha256": "c" * 64,
        "metadata_hash_sha256": "d" * 64,
        "previous_event_hash_sha256": GENESIS_HASH,
        "correlation_id": "corr-01",
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
        "created_by_service": "integration-test",
        "build_version": "test",
    }
    sealed = seal_event(raw)
    receipt = store.append(sealed)
    assert "event_hash_sha256" in receipt
    event_hash = receipt["event_hash_sha256"]
    assert len(event_hash) == 64, "event_hash deve ser SHA-256 hex de 64 chars"
    # Imprime o hash como exigido pela prova no PR
    print(f"event_hash={event_hash}")


# --------------------------------------------------- os 11 caminhos de data/


# Todo arquivo que o PR passou a resolver via importlib.resources. A lista é
# explícita, e não derivada por varredura, porque um teste que descobre sozinho
# o que testar passa quando o arquivo some do pacote — que é exatamente a falha
# que este arquivo existe para pegar.
CAMINHOS_EMPACOTADOS = (
    "data/domains/mercados_preditivos.json",
    "data/domains/domains.json",
    "data/legal-taxonomy/legal_areas.master.json",
    "data/mistress-chart/projects.json",
    "data/source-graph/sources.json",
    "data/source-graph/source_categories.json",
    "data/source-graph/ranking_weights.json",
    "migrations/0001_audit_ledger.sql",
)


@pytest.mark.parametrize("relativo", CAMINHOS_EMPACOTADOS)
def test_dado_empacotado_e_legivel_instalado(relativo: str) -> None:
    """Cada caminho que o PR migrou tem de existir NO PACOTE, não no repositório.

    Sem isto, o portão provava um caminho de doze: a migração SQL. Uma wheel
    construída sem os arquivos de ``data/`` — o que acontece se o symlink estiver
    pendurado no momento do build, como no Dockerfile antigo — passava verde.
    """
    ref = importlib.resources.files("asus_theye").joinpath(relativo)
    assert ref.is_file(), f"ausente no pacote instalado: {relativo}"
    assert ref.read_text(encoding="utf-8").strip(), f"vazio no pacote: {relativo}"


def test_consumidores_reais_carregam_o_dado_empacotado() -> None:
    """Ler o arquivo não basta: os consumidores têm de funcionar de fato.

    São as três funções que o PR migrou e que a imagem Docker quebrava.
    """
    from asus_theye.commercial.niches import load_niches
    from asus_theye.markets.claim import load_areas

    assert load_areas(), "load_areas devolveu vazio com o pacote instalado"
    assert load_niches(), "load_niches devolveu vazio com o pacote instalado"


# ------------------------------------------- a medição que não se inventa


def test_chart_fora_da_arvore_declara_unknown_em_vez_de_zero() -> None:
    """A regressão mais cara que este PR quase introduziu.

    Com os dados vindo do pacote, ``build_chart`` deixava de morrer no primeiro
    ``read_text`` e passava a atravessar um ``_REPO_ROOT`` inexistente. Os
    ``except Exception`` engoliam tudo e o comando devolvia um painel completo
    com todos os projetos em 0% — e, com ``--publish``, isso era hasheado e
    SELADO na corrente.

    Pior que o painel todo zerado: o snapshot misturava número falso com número
    verdadeiro, porque a cobertura por nicho vem do dado empacotado e continua
    certa. Painel inteiro em zero alguém estranha; painel quase certo, não.
    """
    from asus_theye.chart.builder import _REPO_ROOT, build_chart

    snapshot = build_chart()

    if _REPO_ROOT is not None:
        # rodando da árvore de código: a medição é possível e tem de acontecer
        assert snapshot["medivel"] is True
        assert snapshot["medicao_impossivel"] is None
        assert all(p["evidence"]["completion_pct"] is not None for p in snapshot["projects"])
        return

    assert snapshot["medivel"] is False
    assert "medição impossível" in snapshot["medicao_impossivel"]
    for projeto in snapshot["projects"]:
        pct = projeto["evidence"]["completion_pct"]
        assert pct is None, f"{projeto['project_id']}: {pct!r} — zero fabricado é pior que UNKNOWN"
    assert snapshot["totals"]["projects_complete"] is None
    assert snapshot["totals"]["tests"] is None
    # e o que VEM do pacote continua correto — é justamente o que torna a
    # mistura perigosa, e por isso a asserção fica aqui, ao lado
    assert snapshot["totals"]["niches_covered"] > 0


# ------------------------------- um dado, um resolvedor, uma origem no hash


def test_resolvedor_prefere_o_vivo_e_declara_a_origem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Quem rodou a descoberta espera ver o resultado dela, não a foto do build."""
    from asus_theye._pkg_paths import ORIGEM_VIVO, dado_vivo_ou_empacotado

    destino = tmp_path / "data" / "source-graph"
    destino.mkdir(parents=True)
    (destino / "sources.json").write_text('{"sources": []}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    caminho, origem = dado_vivo_ou_empacotado("data", "source-graph", "sources.json")
    assert origem == ORIGEM_VIVO
    assert caminho.read_text(encoding="utf-8") == '{"sources": []}'


def test_resolvedor_cai_no_empacotado_e_diz_que_caiu(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem arquivo vivo, a foto do build serve — desde que ela se identifique."""
    from asus_theye._pkg_paths import ORIGEM_EMPACOTADO, dado_vivo_ou_empacotado

    monkeypatch.chdir(tmp_path)
    caminho, origem = dado_vivo_ou_empacotado("data", "source-graph", "sources.json")
    assert origem == ORIGEM_EMPACOTADO
    assert caminho.is_file()


def test_a_origem_das_fontes_viaja_no_snapshot() -> None:
    """Sem isto, dois snapshots de safras diferentes ficam indistinguíveis.

    A divergência é LATENTE, não visível hoje: a cópia empacotada e o arquivo
    vivo coincidem logo após um build. Ela aparece assim que a descoberta roda
    depois — e é justamente aí que um snapshot selado passaria a afirmar uma
    cobertura que não é a da árvore que o produziu.
    """
    from asus_theye._pkg_paths import ORIGEM_EMPACOTADO, ORIGEM_VIVO
    from asus_theye.chart.builder import _knowledge_section

    conhecimento = _knowledge_section()
    if conhecimento.get("available"):
        assert conhecimento["sources_origin"] in (ORIGEM_VIVO, ORIGEM_EMPACOTADO)
