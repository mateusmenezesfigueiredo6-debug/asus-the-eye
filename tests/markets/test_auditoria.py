"""Testes da F2: a liquidação sela um evento real na cadeia auditável.

Tudo offline e efêmero: SQLite em tmp_path, chave gerada localmente.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from asus_theye.audit.schema import verify_chain, verify_event
from asus_theye.markets.auditoria import (
    AuditoriaError,
    abrir_auditoria,
    cabeca_da_corrente,
    carregar_chave,
    selar_liquidacao,
)
from asus_theye.markets.live import emitir_macro, resolver_pendentes, salvar_registro

HOJE = date(2026, 8, 17)

LINHA = {
    "claim_id": "MACRO-01::2026-07",
    "market_area_id": "macroeconomia",
    "outcome": 0,
    "resolution_source": "api.bcb.gov.br (SGS)",
    "resolved_at": "2026-08-17T15:17:37Z",
    "valor_observado": 0.07,
    "probability": 0.5,
    "brier_do_contrato": 0.25,
    "criterio": "IPCA mensal >= 0.50%",
    "mes_referencia": "2026-07",
    "limiar": 0.5,
    "max_uncertainty": True,
}


CHAVE_TESTE = b"chave-de-teste-32-bytes-ok!!"


def sdk_efemero(tmp_path: Path, *, db: str = "ledger.db", chave: bytes = CHAVE_TESTE):
    return abrir_auditoria(
        tmp_path / db,
        chave=chave,
        eventos=tmp_path / "eventos.jsonl",
        fingerprint=tmp_path / "chave.fingerprint",
    )


# --------------------------------------------------------------- selagem


def test_selar_liquidacao_poe_a_cadeia_em_1(tmp_path: Path) -> None:
    sdk = sdk_efemero(tmp_path)
    assert cabeca_da_corrente(sdk) == 0  # a cadeia nasce vazia
    recibo = selar_liquidacao(sdk, LINHA, eventos=tmp_path / "eventos.jsonl")
    assert recibo["duplicate"] is False
    assert cabeca_da_corrente(sdk) == 1  # head_sequence saiu de 0


def test_evento_exportado_e_verificavel_sem_o_banco(tmp_path: Path) -> None:
    sdk = sdk_efemero(tmp_path)
    eventos = tmp_path / "eventos.jsonl"
    selar_liquidacao(sdk, LINHA, eventos=eventos)
    selado = json.loads(eventos.read_text(encoding="utf-8").strip())
    assert verify_event(selado), (
        "o evento de 37 campos obrigatórios (38 no schema JSON, + hash de selagem no arquivo) "
        "verifica sozinho (hash + esquema)"
    )
    assert verify_chain([selado]), "e encadeia a partir do gênesis"
    assert selado["event_type"] == "market.settlement"
    assert selado["sequence"] == 1


def test_selagem_e_idempotente_por_claim_id(tmp_path: Path) -> None:
    sdk = sdk_efemero(tmp_path)
    eventos = tmp_path / "eventos.jsonl"
    selar_liquidacao(sdk, LINHA, eventos=eventos)
    recibo2 = selar_liquidacao(sdk, LINHA, eventos=eventos)
    assert recibo2["duplicate"] is True
    assert cabeca_da_corrente(sdk) == 1
    assert len(eventos.read_text(encoding="utf-8").strip().splitlines()) == 1


def test_duas_liquidacoes_encadeiam(tmp_path: Path) -> None:
    sdk = sdk_efemero(tmp_path)
    eventos = tmp_path / "eventos.jsonl"
    selar_liquidacao(sdk, LINHA, eventos=eventos)
    segunda = {**LINHA, "claim_id": "MACRO-01::2026-08", "mes_referencia": "2026-08"}
    selar_liquidacao(sdk, segunda, eventos=eventos)
    selados = [json.loads(li) for li in eventos.read_text(encoding="utf-8").strip().splitlines()]
    assert [evento["sequence"] for evento in selados] == [1, 2]
    assert verify_chain(selados)
    assert selados[1]["previous_event_hash_sha256"] == selados[0]["event_hash_sha256"]


# --------------------------------------------------------------- fiação no laço


def test_laco_sela_a_liquidacao_e_faz_backfill(tmp_path: Path) -> None:
    registro = {"versao": 1, "mercados": []}
    emitir_macro(registro, "2026-07", agora="2026-07-01T00:00:00Z")
    store = tmp_path / "registro.json"
    salvar_registro(store, registro)
    sdk = sdk_efemero(tmp_path)

    def auditor(linha: dict) -> dict:
        return selar_liquidacao(sdk, linha, eventos=tmp_path / "eventos.jsonl")

    acoes = resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE, emitir_seguinte=False, auditor=auditor)
    assert [a["acao"] for a in acoes] == ["liquidado", "selado"]
    assert cabeca_da_corrente(sdk) == 1
    # segunda rodada: nada novo a selar (idempotência) e nada re-liquidado
    acoes2 = resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE, emitir_seguinte=False, auditor=auditor)
    assert all(a["acao"] not in ("selado", "liquidado") for a in acoes2)
    assert cabeca_da_corrente(sdk) == 1


def test_falha_de_auditoria_e_visivel_mas_nao_desfaz_a_medicao(tmp_path: Path) -> None:
    registro = {"versao": 1, "mercados": []}
    emitir_macro(registro, "2026-07", agora="2026-07-01T00:00:00Z")
    store = tmp_path / "registro.json"
    salvar_registro(store, registro)

    def auditor_quebrado(linha: dict) -> dict:
        raise AuditoriaError("banco de auditoria indisponível")

    acoes = resolver_pendentes(
        lambda mes: 0.07, store=store, hoje=HOJE, emitir_seguinte=False, auditor=auditor_quebrado
    )
    assert [a["acao"] for a in acoes] == ["liquidado", "auditoria_falhou"]
    # a medição em si está intacta no disco
    linhas = (store.with_name("resolucoes.jsonl")).read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 1


# --------------------------------------------------------------- chave


def test_chave_e_gerada_uma_vez_e_estavel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("THE_EYE_AUDIT_KEY", raising=False)
    caminho = tmp_path / "pseudonimos.key"
    chave1 = carregar_chave(caminho)
    chave2 = carregar_chave(caminho)
    assert chave1 == chave2 and len(chave1) == 32
    assert caminho.exists()


def test_chave_do_ambiente_tem_precedencia(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THE_EYE_AUDIT_KEY", "chave-vinda-do-ambiente-ok")
    assert carregar_chave(tmp_path / "nao-criado.key") == b"chave-vinda-do-ambiente-ok"
    assert not (tmp_path / "nao-criado.key").exists()


def test_chave_curta_do_ambiente_levanta(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("THE_EYE_AUDIT_KEY", "curta")
    with pytest.raises(AuditoriaError, match="16 bytes"):
        carregar_chave()


def test_chave_corrompida_no_arquivo_levanta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("THE_EYE_AUDIT_KEY", raising=False)
    caminho = tmp_path / "pseudonimos.key"
    caminho.write_text("isto-nao-e-hex", encoding="utf-8")
    with pytest.raises(AuditoriaError, match="corrompida"):
        carregar_chave(caminho)


# ------------------------------------------------- achados da revisão adversarial


def test_export_perdido_e_reparado_na_rodada_seguinte(tmp_path: Path) -> None:
    """BLOQUEADOR corrigido: queda entre o commit SQLite e o append do export
    não perde o evento — a próxima selagem (duplicate) repara o arquivo."""
    sdk = sdk_efemero(tmp_path)
    eventos = tmp_path / "eventos.jsonl"
    selar_liquidacao(sdk, LINHA, eventos=eventos)
    eventos.unlink()  # simula o export perdido após o commit
    recibo = selar_liquidacao(sdk, LINHA, eventos=eventos)
    assert recibo["duplicate"] is True and recibo.get("export_reparado") is True
    selado = json.loads(eventos.read_text(encoding="utf-8").strip())
    assert selado["sequence"] == 1 and verify_event(selado)


def test_clone_fresco_nao_bifurca_ressincroniza_do_export(tmp_path: Path) -> None:
    """BLOQUEADOR corrigido: banco apagado + corrente versionada presente →
    o banco é ressincronizado do arquivo; selar de novo é duplicate, nunca fork."""
    sdk1 = sdk_efemero(tmp_path)
    eventos = tmp_path / "eventos.jsonl"
    selar_liquidacao(sdk1, LINHA, eventos=eventos)
    # "clone fresco": outro banco, MESMA corrente versionada e mesma chave
    sdk2 = sdk_efemero(tmp_path, db="ledger2.db")
    assert cabeca_da_corrente(sdk2) == 1, "abrir já ressincroniza o banco do export"
    recibo = selar_liquidacao(sdk2, LINHA, eventos=eventos)
    assert recibo["duplicate"] is True
    selados = [json.loads(li) for li in eventos.read_text(encoding="utf-8").strip().splitlines()]
    assert [evento["sequence"] for evento in selados] == [1], "sem seq duplicada no arquivo"
    assert verify_chain(selados)


def test_chave_trocada_e_recusada_pela_impressao_digital(tmp_path: Path) -> None:
    sdk1 = sdk_efemero(tmp_path)
    selar_liquidacao(sdk1, LINHA, eventos=tmp_path / "eventos.jsonl")
    with pytest.raises(AuditoriaError, match="chave"):
        sdk_efemero(tmp_path, db="ledger2.db", chave=b"outra-chave-de-32-bytes-!!!!")


def test_divergencia_de_conteudo_no_dedupe_levanta(tmp_path: Path) -> None:
    sdk = sdk_efemero(tmp_path)
    eventos = tmp_path / "eventos.jsonl"
    selar_liquidacao(sdk, LINHA, eventos=eventos)
    adulterada = {**LINHA, "outcome": 1, "valor_observado": 9.99}
    with pytest.raises(AuditoriaError, match="diverge"):
        selar_liquidacao(sdk, adulterada, eventos=eventos)


def test_corrente_versionada_adulterada_recusa_abrir(tmp_path: Path) -> None:
    sdk1 = sdk_efemero(tmp_path)
    eventos = tmp_path / "eventos.jsonl"
    selar_liquidacao(sdk1, LINHA, eventos=eventos)
    selado = json.loads(eventos.read_text(encoding="utf-8").strip())
    selado["content_hash_sha256"] = "0" * 64  # adultera
    eventos.write_text(json.dumps(selado) + "\n", encoding="utf-8")
    with pytest.raises(AuditoriaError, match="não verifica"):
        sdk_efemero(tmp_path, db="ledger2.db")


def test_content_hash_do_evento_bate_com_a_linha_publicada(tmp_path: Path) -> None:
    """Tie-out: o hash selado é exatamente o hash da linha do resolucoes.jsonl."""
    from asus_theye.audit.schema import hash_json

    registro = {"versao": 1, "mercados": []}
    emitir_macro(registro, "2026-07", agora="2026-07-01T00:00:00Z")
    store = tmp_path / "registro.json"
    salvar_registro(store, registro)
    sdk = sdk_efemero(tmp_path)

    def auditor(linha: dict) -> dict:
        return selar_liquidacao(sdk, linha, eventos=tmp_path / "eventos.jsonl")

    resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE, emitir_seguinte=False, auditor=auditor)
    linha_publicada = json.loads((store.with_name("resolucoes.jsonl")).read_text(encoding="utf-8").strip())
    selado = json.loads((tmp_path / "eventos.jsonl").read_text(encoding="utf-8").strip())
    assert selado["content_hash_sha256"] == hash_json(linha_publicada)


def test_rodadas_simultaneas_sao_recusadas_pela_trava(tmp_path: Path) -> None:
    import fcntl

    from asus_theye.markets.live import LiveMarketError

    registro = {"versao": 1, "mercados": []}
    emitir_macro(registro, "2026-07", agora="2026-07-01T00:00:00Z")
    store = tmp_path / "registro.json"
    salvar_registro(store, registro)
    trava = (store.with_name(".lock")).open("w")
    fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)  # simula outra rodada viva
    try:
        with pytest.raises(LiveMarketError, match="andamento"):
            resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE)
    finally:
        fcntl.flock(trava, fcntl.LOCK_UN)
        trava.close()
