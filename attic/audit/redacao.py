# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Expurgo com recibo — apagar sem apagar a prova de que se apagou.

Apagar dado de uma plataforma auditável é o momento em que ela mais pode
mentir: some o registro, some a evidência, e ninguém sabe que houve remoção.
Aqui o expurgo é ele próprio um evento selado.

**Por que isto funciona sem quebrar a corrente.** A corrente guarda apenas o
``content_hash_sha256`` do conteúdo, nunca o conteúdo em claro — este vive nos
stores (``comparador.jsonl``, ``serie_p.jsonl``, …). Remover a linha do store
apaga o dado de verdade e **não toca em nenhum hash**: o encadeamento
permanece íntegro e a âncora on-chain, que compromete a raiz Merkle dos eventos,
continua válida. O que sobra é a prova de que algo existiu, sem revelar o quê —
que é exatamente a propriedade desejada quando o motivo do expurgo é jurídico.

Tentar em vez disso *remover o evento* e re-selar a corrente seria o pior dos
mundos: quebraria a âncora e faria a prova temporal acusar adulteração — a
plataforma passaria a testemunhar contra si mesma por ter feito a coisa certa.

O recibo registra o **hash do que foi removido**, e não o conteúdo: dá para
provar depois *que aquilo era aquilo* sem manter uma cópia do material que se
quis justamente eliminar.
"""

from __future__ import annotations

import fcntl
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import hash_json

# Motivos admitidos. Expurgo sem motivo declarado não entra: "por quê" é a parte
# que um auditor futuro mais precisa, e a que mais se perde com o tempo.
MOTIVO_TERCEIRO = "termos_de_terceiro"
MOTIVO_RETENCAO = "politica_de_retencao"
MOTIVO_TITULAR = "pedido_do_titular"
MOTIVOS = (MOTIVO_TERCEIRO, MOTIVO_RETENCAO, MOTIVO_TITULAR)


class RedacaoError(RuntimeError):
    """Expurgo malformado. Sempre levanta — apagar em silêncio é o que se evita."""


@contextmanager
def _trava(arquivo: Path) -> Iterator[None]:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.with_name(".lock-redacao").open("a+", encoding="utf-8") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)


def redigir(
    *,
    store: Path,
    campo_id: str,
    valor_id: str,
    motivo: str,
    justificativa: str,
    ator: str = "titular",
    sdk: Any | None = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Remove a linha ``campo_id == valor_id`` de *store* e SELA o recibo.

    Devolve o recibo com o hash do que saiu. Levanta se o motivo não for
    declarado, se a justificativa estiver vazia, ou se a linha não existir —
    expurgo de coisa inexistente costuma indicar que se está apagando errado.
    """
    if motivo not in MOTIVOS:
        raise RedacaoError(f"motivo deve ser um de {MOTIVOS}, veio {motivo!r}")
    if not store.exists():
        raise RedacaoError(f"store ausente: {store}")

    # O expurgo é ação sensível registrada: a exigência de justificativa passa
    # a ser a MESMA do resto do sistema, e o checkpoint é selado ANTES de
    # qualquer linha sair. Duas regras parecidas em lugares diferentes acabam
    # divergindo; uma só, não.
    from .checkpoint import CheckpointError
    from .checkpoint import registrar as registrar_checkpoint

    try:
        checkpoint = registrar_checkpoint(
            acao="expurgar",
            justificativa=justificativa,
            ator=ator,
            alvo=f"{store}:{campo_id}={valor_id}",
            sdk=sdk,
            eventos=eventos,
        )
    except CheckpointError as erro:
        raise RedacaoError(str(erro)) from erro

    with _trava(store):
        linhas = [json.loads(li) for li in store.read_text(encoding="utf-8").splitlines() if li.strip()]
        removidas = [li for li in linhas if str(li.get(campo_id)) == valor_id]
        if not removidas:
            raise RedacaoError(f"{store}: nenhuma linha com {campo_id}={valor_id!r} — nada a expurgar")

        recibo: dict[str, Any] = {
            "store": str(store),
            "campo_id": campo_id,
            "valor_id": valor_id,
            "linhas_removidas": len(removidas),
            # o HASH do que saiu, nunca o conteúdo: prova a identidade do
            # material sem manter cópia daquilo que se quis eliminar
            "hash_do_removido": [hash_json(li) for li in removidas],
            "motivo": motivo,
            "justificativa": justificativa,
            "checkpoint": checkpoint["recibo"],
            "metodo": (
                "linha removida do store; a corrente NÃO é alterada — ela guarda só o "
                "content_hash, então o encadeamento e a âncora on-chain seguem válidos. "
                "O evento original permanece como prova de que algo existiu, sem revelar o quê."
            ),
        }
        recibo["recibo_id"] = hash_json(
            {"store": recibo["store"], "valor_id": valor_id, "hash_do_removido": recibo["hash_do_removido"]}
        )

        selagem = None
        if sdk is not None:
            from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

            selagem = selar_registro(
                sdk,
                recibo,
                tipo_evento="data.redaction",
                recurso="redaction",
                correlation_id=f"expurgo:{recibo['recibo_id'][:32]}",
                eventos=eventos or EVENTOS_PADRAO,
            )

        restantes = [li for li in linhas if str(li.get(campo_id)) != valor_id]
        conteudo = "".join(json.dumps(li, ensure_ascii=False) + "\n" for li in restantes)
        store.write_text(conteudo, encoding="utf-8")

    return {"recibo": recibo, "selagem": selagem, "checkpoint": checkpoint}
