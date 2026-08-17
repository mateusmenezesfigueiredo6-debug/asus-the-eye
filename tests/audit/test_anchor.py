"""Testes da F3: o contrato TheEyeAuditAnchor e o módulo de ancoragem.

Cobre o que contracts/audit-anchor/TEST_STATUS.md sempre pediu — autorização,
duplicatas de lote/raiz, pause, parâmetros zero/ inválidos, evento completo e
readback — num EVM em memória (eth-tester), sem rede e sem broadcast.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

web3 = pytest.importorskip("web3")
pytest.importorskip("solcx")
pytest.importorskip("eth_tester")

from web3 import EthereumTesterProvider, Web3  # noqa: E402

from asus_theye.audit.anchor import (  # noqa: E402
    AncoragemError,
    _guardas_de_broadcast,
    compilar_contrato,
    lote_da_corrente,
    parametros_do_contrato,
    registrar_ancora,
)
from asus_theye.audit.sdk import AuditSDK, SQLiteAuditStore  # noqa: E402


@pytest.fixture(scope="module")
def contrato() -> dict:
    return compilar_contrato()


@pytest.fixture
def cadeia(contrato: dict):
    w3 = Web3(EthereumTesterProvider())
    admin, operador, intruso = w3.eth.accounts[:3]
    fabrica = w3.eth.contract(abi=contrato["abi"], bytecode=contrato["bytecode"])
    tx = fabrica.constructor(0, admin, operador).transact({"from": admin})
    endereco = w3.eth.get_transaction_receipt(tx)["contractAddress"]
    instancia = w3.eth.contract(address=endereco, abi=contrato["abi"])
    return w3, instancia, admin, operador, intruso


PARAMS = {
    "batchId": b"\x01" * 32,
    "merkleRoot": b"\x02" * 32,
    "manifestHash": b"\x03" * 32,
    "firstSequence": 1,
    "lastSequence": 3,
    "eventCount": 3,
    "schemaVersion": 1,
}


def _anchor(instancia, de, **overrides):
    params = {**PARAMS, **overrides}
    return instancia.functions.anchorBatch(*params.values()).transact({"from": de})


# --------------------------------------------------------------- contrato


def test_ancora_e_le_de_volta_todos_os_campos(cadeia) -> None:
    w3, instancia, _admin, operador, _ = cadeia
    tx = _anchor(instancia, operador)
    recibo = w3.eth.get_transaction_receipt(tx)
    assert recibo["status"] == 1
    ancora = instancia.functions.getAnchor(PARAMS["batchId"]).call()
    assert bytes(ancora[0]) == PARAMS["merkleRoot"]
    assert bytes(ancora[1]) == PARAMS["manifestHash"]
    assert tuple(ancora[2:6]) == (1, 3, 3, 1)  # first, last, count, schemaVersion
    assert ancora[6] > 0  # anchoredAt
    assert ancora[7] == operador  # anchoredBy
    # índice reverso raiz -> lote
    assert bytes(instancia.functions.batchByRoot(PARAMS["merkleRoot"]).call()) == PARAMS["batchId"]


def test_evento_batch_anchored_completo(cadeia) -> None:
    w3, instancia, _admin, operador, _ = cadeia
    tx = _anchor(instancia, operador)
    logs = instancia.events.BatchAnchored().process_receipt(w3.eth.get_transaction_receipt(tx))
    assert len(logs) == 1
    argumentos = logs[0]["args"]
    assert bytes(argumentos["batchId"]) == PARAMS["batchId"]
    assert bytes(argumentos["merkleRoot"]) == PARAMS["merkleRoot"]
    assert argumentos["eventCount"] == 3 and argumentos["anchoredBy"] == operador


def test_sem_anchor_role_reverte(cadeia) -> None:
    _w3, instancia, _admin, _operador, intruso = cadeia
    with pytest.raises(Exception, match="AccessControl|revert"):
        _anchor(instancia, intruso)


def test_lote_duplicado_e_raiz_duplicada_revertem(cadeia) -> None:
    _w3, instancia, _admin, operador, _ = cadeia
    _anchor(instancia, operador)
    with pytest.raises(Exception, match="BatchAlreadyAnchored|revert"):
        _anchor(instancia, operador, merkleRoot=b"\x09" * 32)
    with pytest.raises(Exception, match="RootAlreadyAnchored|revert"):
        _anchor(instancia, operador, batchId=b"\x08" * 32)


@pytest.mark.parametrize(
    "override,erro",
    [
        ({"batchId": b"\x00" * 32}, "ZeroBatchId"),
        ({"merkleRoot": b"\x00" * 32}, "ZeroMerkleRoot"),
        ({"manifestHash": b"\x00" * 32}, "ZeroManifestHash"),
        ({"schemaVersion": 0}, "InvalidSchemaVersion"),
        ({"firstSequence": 5, "lastSequence": 3}, "InvalidSequenceRange"),
        ({"eventCount": 7}, "InvalidEventCount"),
        ({"eventCount": 0}, "InvalidEventCount"),
    ],
)
def test_parametros_invalidos_revertem(cadeia, override: dict, erro: str) -> None:
    _w3, instancia, _admin, operador, _ = cadeia
    with pytest.raises(Exception, match=f"{erro}|revert"):
        _anchor(instancia, operador, **override)


def test_pause_bloqueia_e_unpause_restaura(cadeia) -> None:
    _w3, instancia, admin, operador, _ = cadeia
    instancia.functions.pause().transact({"from": admin})
    with pytest.raises(Exception, match="EnforcedPause|revert"):
        _anchor(instancia, operador)
    instancia.functions.unpause().transact({"from": admin})
    _anchor(instancia, operador)  # volta a funcionar


def test_pause_exige_admin(cadeia) -> None:
    _w3, instancia, _admin, operador, _ = cadeia
    with pytest.raises(Exception, match="AccessControl|revert"):
        instancia.functions.pause().transact({"from": operador})


# --------------------------------------------------------------- módulo de ancoragem


def _corrente_de_teste(tmp_path: Path, n: int = 2) -> Path:
    store = SQLiteAuditStore(tmp_path / "sdk.db")
    sdk = AuditSDK(store, pseudonymization_key=b"chave-de-teste-32-bytes-ok!!", service="t", build_version="0")
    eventos = tmp_path / "eventos.jsonl"
    with eventos.open("w", encoding="utf-8") as arquivo:
        for indice in range(n):
            recibo = sdk.record(
                tenant_id="tenant-demo",
                event_type="market.settlement",
                action="settle",
                correlation_id=f"c-{indice}",
                actor_id="t",
                resource_id=f"m-{indice}",
                content={"i": indice},
            )
            selado = next(e for e in store.events("tenant-demo") if e["event_id"] == recibo["event_id"])
            arquivo.write(json.dumps(selado) + "\n")
    return eventos


def test_lote_da_corrente_constroi_e_mapeia_para_o_abi(tmp_path: Path) -> None:
    eventos = _corrente_de_teste(tmp_path, n=3)
    batch = lote_da_corrente(eventos)
    manifest = batch["manifest"]
    assert manifest["event_count"] == 3 and manifest["first_sequence"] == 1
    params = parametros_do_contrato(manifest)
    assert len(params["batchId"]) == 32 and len(params["merkleRoot"]) == 32
    assert params["eventCount"] == 3 and params["schemaVersion"] == 1


def test_lote_recusa_corrente_adulterada(tmp_path: Path) -> None:
    eventos = _corrente_de_teste(tmp_path, n=2)
    linhas = [json.loads(li) for li in eventos.read_text(encoding="utf-8").strip().splitlines()]
    linhas[0]["content_hash_sha256"] = "0" * 64
    eventos.write_text("\n".join(json.dumps(li) for li in linhas) + "\n", encoding="utf-8")
    with pytest.raises(AncoragemError, match="não verifica"):
        lote_da_corrente(eventos)


def test_guardas_recusam_sem_gate_e_fora_da_base_sepolia(monkeypatch: pytest.MonkeyPatch) -> None:
    class W3Falso:
        class eth:  # noqa: N801 - imita a interface do web3
            chain_id = 1  # mainnet

    with pytest.raises(AncoragemError, match="--execute"):
        _guardas_de_broadcast(W3Falso(), executar=False)
    monkeypatch.delenv("THE_EYE_ANCHOR_EXECUTE", raising=False)
    with pytest.raises(AncoragemError, match="THE_EYE_ANCHOR_EXECUTE"):
        _guardas_de_broadcast(W3Falso(), executar=True)
    monkeypatch.setenv("THE_EYE_ANCHOR_EXECUTE", "1")
    with pytest.raises(AncoragemError, match="Mainnet|recusada"):
        _guardas_de_broadcast(W3Falso(), executar=True)


def test_registrar_ancora_escreve_batches_anchors_e_artefato(tmp_path: Path) -> None:
    eventos = _corrente_de_teste(tmp_path, n=2)
    batch = lote_da_corrente(eventos)
    tx_info = {
        "modo": "teste",
        "chain_id": 84532,
        "contrato": "0x" + "ab" * 20,
        "tx_hash": "0x" + "cd" * 32,
        "block_number": 123,
        "block_hash": "0x" + "ef" * 32,
    }
    db = tmp_path / "ledger.db"
    registrar_ancora(db, batch, tx_info, ancoras=tmp_path / "ancoras.jsonl")

    store = SQLiteAuditStore(db)
    lote = store.connection.execute("SELECT status, merkle_root FROM audit_batches").fetchone()
    assert lote[0] == "anchored" and lote[1] == batch["manifest"]["merkle_root"]
    ancora = store.connection.execute("SELECT chain_id, status, tx_hash FROM audit_anchors").fetchone()
    assert ancora[0] == 84532 and ancora[1] == "confirmed"
    linha = json.loads((tmp_path / "ancoras.jsonl").read_text(encoding="utf-8").strip())
    assert linha["ancora"]["tx_hash"] == tx_info["tx_hash"]
