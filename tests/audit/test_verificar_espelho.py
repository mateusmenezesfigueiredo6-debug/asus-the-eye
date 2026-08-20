"""Testes de verificar_espelho — sem rede, sempre."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from asus_theye.audit.sync_ledger import RECURSO_ESPELHO
from asus_theye.audit.verificar_espelho import CorrenteBrokenError, verificar


def _corrente_valida(tmp: Path, n: int = 2) -> Path:
    from asus_theye.markets.auditoria import abrir_auditoria, selar_registro

    eventos = tmp / "eventos.jsonl"
    sdk = abrir_auditoria(
        tmp / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=eventos,
        fingerprint=tmp / "chave.fingerprint",
    )
    for i in range(1, n + 1):
        selar_registro(
            sdk,
            {"n": i},
            tipo_evento="market.settlement",
            recurso="market",
            correlation_id=f"claim-{i}",
            eventos=eventos,
        )
    return eventos


def _espelhos_para_corrente(eventos_path: Path) -> list[dict[str, Any]]:
    """Constrói entradas remotas falsas para cada evento local."""
    linhas = [ln for ln in eventos_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    result = []
    for ln in linhas:
        ev = json.loads(ln)
        result.append(
            {
                "resource_type": RECURSO_ESPELHO,
                "idempotency_key": f"espelho-{ev['event_hash_sha256'][:32]}",
            }
        )
    return result


def test_tudo_espelhado_zero_faltantes(tmp_path: Path) -> None:
    eventos = _corrente_valida(tmp_path)
    espelhos = _espelhos_para_corrente(eventos)

    def buscar(url: str, tenant: str) -> dict[str, Any]:
        return {"tenant_id": tenant, "events": espelhos}

    rel = verificar("http://fake", eventos=eventos, tenant="t", buscar=buscar)
    assert rel["locais"] == 2
    assert rel["espelhos_remotos"] == 2
    assert rel["faltantes_na_janela"] == []
    assert rel["janela_parcial"] is False
    assert rel["verifica_local"] is True


def test_espelho_a_menos_reporta_faltante(tmp_path: Path) -> None:
    eventos = _corrente_valida(tmp_path, n=2)
    espelhos = _espelhos_para_corrente(eventos)
    # remover o segundo espelho
    espelhos_parciais = espelhos[:1]

    def buscar(url: str, tenant: str) -> dict[str, Any]:
        return {"tenant_id": tenant, "events": espelhos_parciais}

    rel = verificar("http://fake", eventos=eventos, tenant="t", buscar=buscar)
    assert rel["locais"] == 2
    assert rel["espelhos_remotos"] == 1
    assert len(rel["faltantes_na_janela"]) == 1
    assert rel["janela_parcial"] is False


def test_corrente_quebrada_levanta(tmp_path: Path) -> None:
    eventos = _corrente_valida(tmp_path, n=2)
    # corromper a segunda linha: trocar o hash
    linhas = eventos.read_text(encoding="utf-8").splitlines()
    ev = json.loads(linhas[1])
    ev["event_hash_sha256"] = "0" * 64
    linhas[1] = json.dumps(ev)
    eventos.write_text("\n".join(linhas), encoding="utf-8")

    def buscar(url: str, tenant: str) -> dict[str, Any]:
        return {"tenant_id": tenant, "events": []}

    with pytest.raises(CorrenteBrokenError):
        verificar("http://fake", eventos=eventos, tenant="t", buscar=buscar)


def test_janela_parcial_honesta(tmp_path: Path) -> None:
    """Se local > 50, janela_parcial deve ser True."""
    eventos = _corrente_valida(tmp_path, n=2)
    espelhos = _espelhos_para_corrente(eventos)

    def buscar(url: str, tenant: str) -> dict[str, Any]:
        return {"tenant_id": tenant, "events": espelhos}

    # simula "locais > 50" injetando uma corrente falsa maior
    # na prática fazemos monkey-patch leve: usamos n=2 mas forçamos a janela
    # através do campo de retorno — testamos a lógica de flag com n real = 2
    # e _JANELA_REMOTA reduzida a 1.
    import asus_theye.audit.verificar_espelho as mod

    original = mod._JANELA_REMOTA
    try:
        mod._JANELA_REMOTA = 1  # type: ignore[attr-defined]
        rel = verificar("http://fake", eventos=eventos, tenant="t", buscar=buscar)
    finally:
        mod._JANELA_REMOTA = original

    assert rel["janela_parcial"] is True


def test_arquivo_ausente_levanta(tmp_path: Path) -> None:
    def buscar(url: str, tenant: str) -> dict[str, Any]:
        return {"tenant_id": tenant, "events": []}

    with pytest.raises(FileNotFoundError):
        verificar("http://fake", eventos=tmp_path / "nao_existe.jsonl", tenant="t", buscar=buscar)
