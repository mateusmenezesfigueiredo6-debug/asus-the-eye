"""Testes do espelho da corrente no ledger remoto — sem rede, sempre."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from asus_theye.audit.sync_ledger import SyncError, corpo_do_espelho, sincronizar


def _corrente_valida(tmp: Path) -> Path:
    """Sela 2 eventos reais numa corrente temporária (via SDK, como na produção)."""
    from asus_theye.markets.auditoria import abrir_auditoria, selar_registro

    eventos = tmp / "eventos.jsonl"
    sdk = abrir_auditoria(
        tmp / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=eventos,
        fingerprint=tmp / "chave.fingerprint",
    )
    for indice in (1, 2):
        selar_registro(
            sdk,
            {"n": indice},
            tipo_evento="market.settlement",
            recurso="market",
            correlation_id=f"claim-{indice}",
            eventos=eventos,
        )
    return eventos


def test_corpo_do_espelho_respeita_o_contrato_do_worker(tmp_path: Path) -> None:
    eventos = _corrente_valida(tmp_path)
    evento = json.loads(eventos.read_text(encoding="utf-8").splitlines()[0])
    corpo = corpo_do_espelho(evento)
    # contrato: 6 campos, os 5 primeiros strings não vazias <= 256
    assert set(corpo) == {
        "tenant_id",
        "idempotency_key",
        "event_type",
        "resource_type",
        "resource_id_pseudonymous",
        "payload",
    }
    for campo in ("tenant_id", "idempotency_key", "event_type", "resource_type", "resource_id_pseudonymous"):
        assert isinstance(corpo[campo], str) and 0 < len(corpo[campo]) <= 256
    assert corpo["payload"]["event_hash_sha256"] == evento["event_hash_sha256"]
    assert corpo["idempotency_key"] == f"espelho-{evento['event_hash_sha256'][:32]}"


def test_sincronizar_publica_em_ordem_e_reporta_dedupe(tmp_path: Path) -> None:
    eventos = _corrente_valida(tmp_path)
    publicados: list[dict[str, Any]] = []

    def fake_publish(corpo: dict[str, Any], url: str) -> dict[str, Any]:
        publicados.append(corpo)
        return {"sequence": len(publicados), "deduplicated": False}

    placar = sincronizar("https://ledger.exemplo", eventos=eventos, publicar=fake_publish)
    assert placar["eventos_locais"] == 2 and placar["novos"] == 2 and placar["dedupe"] == 0
    ordem = [corpo["payload"]["sequence"] for corpo in publicados]
    assert ordem == sorted(ordem)  # espelho sobe na ordem da corrente

    # segunda rodada: worker deduplica tudo → novos == 0 (idempotência)
    def fake_dedupe(corpo: dict[str, Any], url: str) -> dict[str, Any]:
        return {"sequence": 1, "deduplicated": True}

    placar2 = sincronizar("https://ledger.exemplo", eventos=eventos, publicar=fake_dedupe)
    assert placar2["novos"] == 0 and placar2["dedupe"] == 2


def test_corrente_quebrada_nao_se_espelha(tmp_path: Path) -> None:
    eventos = _corrente_valida(tmp_path)
    linhas = eventos.read_text(encoding="utf-8").splitlines()
    adulterado = json.loads(linhas[0])
    adulterado["content_hash_sha256"] = "f" * 64  # quebra o hash selado
    eventos.write_text(json.dumps(adulterado) + "\n" + linhas[1] + "\n", encoding="utf-8")
    with pytest.raises(SyncError, match="não verifica"):
        sincronizar("https://ledger.exemplo", eventos=eventos, publicar=lambda c, u: {})


def test_corrente_ausente_levanta(tmp_path: Path) -> None:
    with pytest.raises(SyncError, match="ausente"):
        sincronizar("https://ledger.exemplo", eventos=tmp_path / "nada.jsonl", publicar=lambda c, u: {})
