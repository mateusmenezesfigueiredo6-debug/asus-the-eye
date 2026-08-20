"""F3 — ancoragem do lote Merkle no contrato TheEyeAuditAnchor (Base Sepolia).

O elo que nunca existiu em execução: nenhum código escrevia em ``audit_anchors``.
Este módulo fecha o ciclo ``batch Merkle → âncora on-chain → registro local``:

1. **Compila o contrato vendorado** (solc 0.8.x + OpenZeppelin fixado em
   ``contracts/audit-anchor/lib/``) — sem rede na compilação além do binário do
   solc, que o py-solc-x baixa do release oficial uma única vez.
2. **Constrói o lote da corrente versionada** (``reports/markets/eventos.jsonl``,
   verificada antes) com o mesmo ``build_batch`` do núcleo — árvore Keccak-256
   com separação de domínio, manifesto e uma prova de inclusão por evento.
3. **Ensaia TUDO offline primeiro**: o modo padrão faz deploy + ``anchorBatch``
   num EVM em memória (eth-tester). O broadcast real é gated três vezes:
   ``--execute`` + ``THE_EYE_ANCHOR_EXECUTE=1`` + chain-id obrigatoriamente
   84532 (Base Sepolia). Mainnet é recusada por construção.
4. **Registra a âncora onde ela nunca foi escrita**: ``audit_batches`` +
   ``audit_anchors`` no SQLite local, e o artefato versionado
   ``reports/markets/ancoras.jsonl`` (manifesto + tx + bloco) — a prova viaja
   com o repo, como no F2.

Mapeamento para o ABI estreito do contrato:
- ``batchId``    = SHA-256 do ``batch_id`` (uuid) do manifesto — bytes32
- ``merkleRoot`` = raiz Keccak-256 do lote — bytes32
- ``manifestHash`` = SHA-256 canônico do manifesto — bytes32
- ``schemaVersion`` = componente MAJOR de ``schema_version`` (\"1.0.0\" → 1)

A chave do operador NUNCA entra no repo: ``THE_EYE_ANCHOR_PK`` ou um arquivo
local gerado uma vez (``reports/audit/anchor.key``, coberto por ``*.key`` no
.gitignore). Fundear a carteira (faucet de testnet) é ato do dono.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any

from asus_theye.audit.batching import build_batch
from asus_theye.audit.schema import verify_chain
from asus_theye.audit.sdk import utc_now

CHAIN_ID_BASE_SEPOLIA = 84532
RPC_PADRAO = "https://sepolia.base.org"
GATE_ENV = "THE_EYE_ANCHOR_EXECUTE"
PK_ENV = "THE_EYE_ANCHOR_PK"
PK_PADRAO = Path("reports/audit/anchor.key")
EVENTOS_PADRAO = Path("reports/markets/eventos.jsonl")
ANCORAS_PADRAO = Path("reports/markets/ancoras.jsonl")
CONTRATO_PADRAO = Path("reports/markets/contrato.json")
FONTE_SOL = Path("contracts/audit-anchor/src/TheEyeAuditAnchor.sol")
OZ_LIB = Path("contracts/audit-anchor/lib/openzeppelin-contracts")
SOLC_VERSAO = "0.8.26"
TENANT_PADRAO = "tenant-demo"


class AncoragemError(RuntimeError):
    """Compilação, lote, gate ou transação falhou. Sempre levanta — nunca finge âncora."""


# ------------------------------------------------------------------ contrato


def compilar_contrato(fonte: Path = FONTE_SOL, oz: Path = OZ_LIB) -> dict[str, Any]:
    """Compila o TheEyeAuditAnchor com o OpenZeppelin vendorado. Devolve abi+bytecode."""
    try:
        import solcx
    except ImportError as exc:  # pragma: no cover - extra ausente
        raise AncoragemError("py-solc-x não instalado (extra [anchor])") from exc

    if not fonte.exists():
        raise AncoragemError(f"contrato não encontrado: {fonte}")
    if not (oz / "contracts").exists():
        raise AncoragemError(
            f"OpenZeppelin não vendorado em {oz} — baixe o release oficial (ver contracts/audit-anchor/TEST_STATUS.md)"
        )

    if SOLC_VERSAO not in [str(v) for v in solcx.get_installed_solc_versions()]:
        solcx.install_solc(SOLC_VERSAO)  # download único do binário oficial

    compilado = solcx.compile_files(
        [str(fonte)],
        output_values=["abi", "bin"],
        solc_version=SOLC_VERSAO,
        import_remappings=[f"@openzeppelin/contracts/={oz}/contracts/"],
        allow_paths=[str(fonte.parent.parent)],
        optimize=True,
        optimize_runs=200,
    )
    chave = next((k for k in compilado if k.endswith(":TheEyeAuditAnchor")), None)
    if chave is None:
        raise AncoragemError(f"TheEyeAuditAnchor não saiu da compilação: {list(compilado)}")
    return {"abi": compilado[chave]["abi"], "bytecode": "0x" + compilado[chave]["bin"]}


# ------------------------------------------------------------------ lote


def lote_da_corrente(
    eventos: Path = EVENTOS_PADRAO,
    *,
    tenant: str = TENANT_PADRAO,
    previous_batch_root: str | None = None,
) -> dict[str, Any]:
    """Constrói o lote Merkle da corrente versionada — verificando-a antes."""
    if not eventos.exists():
        raise AncoragemError(f"corrente versionada ausente: {eventos}")
    selados = [json.loads(linha) for linha in eventos.read_text(encoding="utf-8").splitlines() if linha.strip()]
    selados = [evento for evento in selados if evento.get("tenant_id") == tenant]
    if not selados:
        raise AncoragemError(f"nenhum evento do tenant {tenant!r} em {eventos}")
    if not verify_chain(selados):
        raise AncoragemError(f"{eventos}: a corrente não verifica — nada será ancorado")
    return build_batch(sorted(selados, key=lambda e: int(e["sequence"])), previous_batch_root)


def parametros_do_contrato(manifest: dict[str, Any]) -> dict[str, Any]:
    """Traduz o manifesto para o ABI estreito do contrato (documentado no topo)."""
    return {
        "batchId": hashlib.sha256(str(manifest["batch_id"]).encode("utf-8")).digest(),
        "merkleRoot": bytes.fromhex(manifest["merkle_root"]),
        "manifestHash": bytes.fromhex(manifest["manifest_hash_sha256"]),
        "firstSequence": int(manifest["first_sequence"]),
        "lastSequence": int(manifest["last_sequence"]),
        "eventCount": int(manifest["event_count"]),
        "schemaVersion": int(str(manifest["schema_version"]).split(".")[0]),
    }


# ------------------------------------------------------------------ carteira


def carteira(caminho: Path = PK_PADRAO) -> Any:
    """Conta do operador: ``THE_EYE_ANCHOR_PK`` ou chave local gerada uma vez.

    A chave nunca entra no repo (``*.key`` no .gitignore). Fundear é ato do dono.
    """
    from eth_account import Account

    env = os.environ.get(PK_ENV, "")
    if env:
        return Account.from_key(env)
    if caminho.exists():
        return Account.from_key(caminho.read_text(encoding="utf-8").strip())
    conta = Account.create()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conta.key.hex() + "\n", encoding="utf-8")
    os.chmod(caminho, 0o600)
    return conta


# ------------------------------------------------------------------ ensaio offline


def ensaiar_offline(batch: dict[str, Any]) -> dict[str, Any]:
    """Deploy + anchorBatch num EVM em memória. Prova o caminho inteiro sem rede."""
    try:
        from web3 import EthereumTesterProvider, Web3
    except ImportError as exc:  # pragma: no cover - extra ausente
        raise AncoragemError("web3/eth-tester não instalados (extra [anchor])") from exc

    contrato = compilar_contrato()
    w3 = Web3(EthereumTesterProvider())
    operador = w3.eth.accounts[0]
    fabrica = w3.eth.contract(abi=contrato["abi"], bytecode=contrato["bytecode"])
    tx = fabrica.constructor(0, operador, operador).transact({"from": operador})
    endereco = w3.eth.get_transaction_receipt(tx)["contractAddress"]
    instancia = w3.eth.contract(address=endereco, abi=contrato["abi"])

    params = parametros_do_contrato(batch["manifest"])
    tx2 = instancia.functions.anchorBatch(*params.values()).transact({"from": operador})
    recibo = w3.eth.get_transaction_receipt(tx2)
    ancora = instancia.functions.getAnchor(params["batchId"]).call()
    if int(ancora[6]) == 0:  # anchoredAt
        raise AncoragemError("ensaio falhou: getAnchor devolveu âncora vazia")
    return {
        "modo": "ensaio-offline",
        "contrato": endereco,
        "gas_deploy": int(w3.eth.get_transaction_receipt(tx)["gasUsed"]),
        "gas_anchor": int(recibo["gasUsed"]),
        "merkle_root": batch["manifest"]["merkle_root"],
        "anchored_at_onchain": int(ancora[6]),
    }


# ------------------------------------------------------------------ broadcast real


def _guardas_de_broadcast(w3: Any, executar: bool) -> None:
    if not executar:
        raise AncoragemError("broadcast requer --execute")
    if os.environ.get(GATE_ENV) != "1":
        raise AncoragemError(f"broadcast requer {GATE_ENV}=1 (decisão explícita do dono)")
    chain_id = int(w3.eth.chain_id)
    if chain_id != CHAIN_ID_BASE_SEPOLIA:
        raise AncoragemError(
            f"chain-id {chain_id} recusada: só Base Sepolia ({CHAIN_ID_BASE_SEPOLIA}). "
            "Mainnet é proibida por política do projeto."
        )


def ancorar_na_base_sepolia(
    batch: dict[str, Any],
    *,
    executar: bool,
    rpc: str = RPC_PADRAO,
    caminho_pk: Path = PK_PADRAO,
    contrato_registro: Path = CONTRATO_PADRAO,
) -> dict[str, Any]:
    """Deploy (se preciso) + anchorBatch na Base Sepolia. Todos os gates ativos."""
    from web3 import HTTPProvider, Web3

    w3 = Web3(HTTPProvider(rpc, request_kwargs={"timeout": 60}))
    if not w3.is_connected():
        raise AncoragemError(f"RPC inalcançável: {rpc}")
    _guardas_de_broadcast(w3, executar)

    conta = carteira(caminho_pk)
    saldo = w3.eth.get_balance(conta.address)
    if saldo == 0:
        raise AncoragemError(
            f"carteira {conta.address} sem saldo na Base Sepolia. Fundeie via faucet "
            "(ex.: faucet do Coinbase Developer Platform ou Alchemy) e rode de novo."
        )

    contrato = compilar_contrato()
    if contrato_registro.exists():
        endereco = json.loads(contrato_registro.read_text(encoding="utf-8"))["address"]
    else:
        fabrica = w3.eth.contract(abi=contrato["abi"], bytecode=contrato["bytecode"])
        tx = fabrica.constructor(0, conta.address, conta.address).build_transaction(
            {
                "from": conta.address,
                # "pending": conta o que já está na mempool — imune ao lag de
                # RPC público balanceado (um nó atrasado devolveria nonce velho
                # e a 2ª tx colidiria com "nonce too low")
                "nonce": w3.eth.get_transaction_count(conta.address, "pending"),
                "chainId": CHAIN_ID_BASE_SEPOLIA,
            }
        )
        assinada = conta.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(assinada.raw_transaction)
        recibo = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        endereco = recibo["contractAddress"]
        contrato_registro.parent.mkdir(parents=True, exist_ok=True)
        contrato_registro.write_text(
            json.dumps(
                {
                    "address": endereco,
                    "chain_id": CHAIN_ID_BASE_SEPOLIA,
                    "deploy_tx": tx_hash.hex(),
                    "deployed_at": utc_now(),
                    "solc": SOLC_VERSAO,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    instancia = w3.eth.contract(address=endereco, abi=contrato["abi"])
    params = parametros_do_contrato(batch["manifest"])
    tx = instancia.functions.anchorBatch(*params.values()).build_transaction(
        {
            "from": conta.address,
            "nonce": w3.eth.get_transaction_count(conta.address, "pending"),
            "chainId": CHAIN_ID_BASE_SEPOLIA,
        }
    )
    assinada = conta.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(assinada.raw_transaction)
    recibo = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if int(recibo["status"]) != 1:
        raise AncoragemError(f"anchorBatch revertida: tx {tx_hash.hex()}")

    return {
        "modo": "base-sepolia",
        "chain_id": CHAIN_ID_BASE_SEPOLIA,
        "contrato": endereco,
        "tx_hash": tx_hash.hex(),
        "block_number": int(recibo["blockNumber"]),
        "block_hash": recibo["blockHash"].hex(),
        "operador": conta.address,
    }


# ------------------------------------------------------------------ registro local


def registrar_ancora(
    db: Path,
    batch: dict[str, Any],
    tx_info: dict[str, Any],
    *,
    ancoras: Path = ANCORAS_PADRAO,
) -> dict[str, Any]:
    """Escreve onde nunca foi escrito: audit_batches + audit_anchors + artefato versionado."""
    from asus_theye.audit.sdk import SQLiteAuditStore

    manifest = batch["manifest"]
    store = SQLiteAuditStore(db)
    with store.connection:
        store.connection.execute(
            """INSERT OR IGNORE INTO audit_batches
               (batch_id,tenant_id,schema_version,first_sequence,last_sequence,event_count,
                merkle_root,previous_batch_root,manifest_hash_sha256,manifest_json,status,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                manifest["batch_id"],
                manifest["tenant_id"],
                manifest["schema_version"],
                manifest["first_sequence"],
                manifest["last_sequence"],
                manifest["event_count"],
                manifest["merkle_root"],
                manifest["previous_batch_root"],
                manifest["manifest_hash_sha256"],
                json.dumps(manifest, ensure_ascii=False),
                "anchored",
                manifest["generated_at"],
            ),
        )
        store.connection.execute(
            """INSERT INTO audit_anchors
               (anchor_id,batch_id,chain_id,contract_address,tx_hash,block_number,block_hash,
                confirmations,status,anchored_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                str(uuid.uuid4()),
                manifest["batch_id"],
                tx_info["chain_id"],
                tx_info["contrato"],
                tx_info["tx_hash"],
                tx_info.get("block_number"),
                tx_info.get("block_hash"),
                1,
                "confirmed",
                utc_now(),
            ),
        )
    linha = {"manifest": manifest, "ancora": tx_info, "registrado_em": utc_now()}
    ancoras.parent.mkdir(parents=True, exist_ok=True)
    with ancoras.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return linha
