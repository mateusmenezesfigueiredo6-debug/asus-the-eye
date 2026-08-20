"""L2 — publica lote + âncora no D1 para o verificador público servir a raiz.

O ciclo do Ledger termina aqui: a âncora existe on-chain (F3/L1), mas o
``GET /root/AAAA-MM-DD`` do verificador público lê ``audit_anchors`` unido a
``audit_batches`` no D1 — sem esses dois registros, a raiz que qualquer um
deveria conferir simplesmente não aparece.

Regras herdadas do resto da plataforma:

1. **Lote antes de âncora.** O worker recusa âncora de lote desconhecido; aqui
   a ordem é sempre ``POST /batches`` → ``POST /anchors``.
2. **A corrente é conferida antes** (``verify_chain`` dentro de
   ``lote_da_corrente``): não se publica raiz de corrente quebrada.
3. **Idempotente.** Reenviar a mesma âncora devolve ``deduplicated`` — rodar
   duas vezes não duplica raiz.
4. **Falha alto.** Recusa do worker vira exceção; publicar "quase" seria pior
   que não publicar.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from asus_theye.audit.anchor import ANCORAS_PADRAO, EVENTOS_PADRAO, TENANT_PADRAO, lote_da_corrente
from asus_theye.audit.remote_ledger import _ledger_token

_TIMEOUT = 30


class PublicacaoError(RuntimeError):
    """Worker recusou, está fora do ar ou a âncora local não existe. Sempre levanta."""


def _post(ledger_url: str, rota: str, corpo: dict[str, Any]) -> dict[str, Any]:
    headers = {"content-type": "application/json", "user-agent": "asus-theye-audit-client/0.2"}
    token = _ledger_token()
    if token:
        headers["authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{ledger_url.rstrip('/')}{rota}", data=json.dumps(corpo).encode("utf-8"), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            recibo: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
            return recibo
    except urllib.error.HTTPError as exc:
        detalhe = exc.read().decode("utf-8", errors="replace")[:500]
        raise PublicacaoError(f"worker recusou {rota}: HTTP {exc.code}: {detalhe}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise PublicacaoError(f"worker inalcançável em {rota}: {exc}") from exc


def publicar(
    ledger_url: str,
    *,
    ancoras: Path = ANCORAS_PADRAO,
    eventos: Path = EVENTOS_PADRAO,
    tenant: str = TENANT_PADRAO,
    postar: Any = None,
) -> dict[str, Any]:
    """Publica o lote e a âncora mais recentes no D1. ``postar`` é injetável (testes)."""
    if not ancoras.exists():
        raise PublicacaoError(f"nenhuma âncora local em {ancoras} — ancore antes (markets-anchor --execute)")
    linhas = [json.loads(li) for li in ancoras.read_text(encoding="utf-8").splitlines() if li.strip()]
    if not linhas:
        raise PublicacaoError(f"{ancoras} está vazio")
    registro = linhas[-1]
    manifest = registro["manifest"]
    info = registro["ancora"]

    enviar = postar or (lambda rota, corpo: _post(ledger_url, rota, corpo))

    # A corrente canônica vive no repo, não no D1 (lá há espelhos de resumo):
    # o lote entra por /batches/external, que registra o manifesto e marca
    # status 'external' — o worker NUNCA finge hospedar os eventos. A régua do
    # /batches nativo (provas conferidas contra audit_events) fica intacta.
    lote = lote_da_corrente(eventos, tenant=tenant)
    if lote["manifest"]["merkle_root"] != manifest["merkle_root"]:
        raise PublicacaoError(
            "a raiz do lote recomputado não bate com a âncora local "
            f"({lote['manifest']['merkle_root'][:16]}… ≠ {manifest['merkle_root'][:16]}…) — "
            "a corrente mudou depois de ancorar; ancore de novo antes de publicar"
        )
    # publica o manifesto DA ÂNCORA (o recomputado só serviu para conferir a
    # raiz): batch_id é uuid novo a cada build — publicar o recomputado deixaria
    # a âncora órfã de lote
    recibo_lote = enviar("/batches/external", {"manifest": manifest})

    # o D1 dedupa lote por merkle_root: se a raiz já estava lá com outro
    # batch_id (uuid é local, a RAIZ é a identidade real), a âncora tem de
    # apontar para o batch_id vigente NO LEDGER, não para o local
    batch_id_no_ledger = str(recibo_lote.get("batch_id") or manifest["batch_id"])
    recibo_ancora = enviar(
        "/anchors",
        {
            "batch_id": batch_id_no_ledger,
            "chain_id": int(info["chain_id"]),
            "contract_address": info["contrato"],
            "tx_hash": info["tx_hash"],
            "block_number": info.get("block_number"),
            "block_hash": info.get("block_hash"),
            "confirmations": 1,
            "status": "confirmed",
            "anchored_at": info.get("anchored_at") or registro.get("registrado_em") or "",
        },
    )
    return {
        "merkle_root": manifest["merkle_root"],
        "tx_hash": info["tx_hash"],
        "lote": recibo_lote,
        "ancora": recibo_ancora,
        "metodo": "POST /batches (com provas) → POST /anchors; idempotente por tx_hash/batch_id",
    }
