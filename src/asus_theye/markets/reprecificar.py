# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reprecificação — mover ``p`` de um mercado aberto, com prova de por quê.

Sem isto a probabilidade nasce uma vez e nunca mais se move: a série p(t) é uma
reta por construção, a curva de calibração não tem o que medir, e o produto é
uma lista de perguntas em vez de um mercado preditivo. O Focus é atualizado
semanalmente por ~100 instituições e o IPCA-15 sai no meio do mês — ignorar os
dois entre emissão e liquidação é jogar fora a informação que chega.

**Por que reprecificar mercado aberto é legítimo aqui, e não trapaça.** Numa
plataforma opaca, mexer no preço depois de aberto é exatamente como se fabrica
histórico favorável. Aqui é o contrário: o valor antigo permanece na corrente,
o novo entra como evento próprio com a proveniência do sinal que o justificou, e
a trajetória mostra a mudança. Quem auditar vê **quando** mudamos de ideia e
**por causa de quê**. Silêncio seria a trapaça; o registro é a honestidade.

O que esta função **recusa**:

- reprecificar claim já LIQUIDADO — mudar a previsão depois do desfecho é
  fabricar acerto, e é a única forma de fraude que este módulo poderia
  viabilizar. Por isso a checagem vem antes de tudo;
- reprecificar sem proveniência — número novo sem fonte nomeada não entra;
- gravar a mudança sem selar — a alteração e o seu motivo viajam juntos.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REGISTRO_PADRAO = Path("reports/markets/registro.json")

# Movimento menor que isto não vira evento. Não é arredondamento: é evitar que
# ruído numérico do gerador encha a corrente de eventos sem informação, o que
# tornaria a trajetória ilegível justamente para quem quer auditá-la.
MOVIMENTO_MINIMO = 0.005


class ReprecificacaoError(RuntimeError):
    """Reprecificação inválida. Sempre levanta — preço não muda em silêncio."""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def reprecificar(
    *,
    claim_id: str,
    probabilidade: Any,
    motivo: str,
    store: Path = REGISTRO_PADRAO,
    sdk: Any | None = None,
    eventos: Path | None = None,
    agora: str | None = None,
) -> dict[str, Any]:
    """Move ``p`` de um claim ABERTO e sela a mudança com a proveniência do sinal.

    ``probabilidade`` é a :class:`~asus_theye.markets.gerador.Probabilidade` que
    justifica o novo valor — ela carrega o sinal, a fonte e o método.
    """
    if not store.exists():
        raise ReprecificacaoError(f"registro de mercados ausente: {store}")
    if not motivo.strip():
        raise ReprecificacaoError(f"{claim_id}: motivo obrigatório — preço não muda sem explicação")

    registro = json.loads(store.read_text(encoding="utf-8"))
    mercado = next((m for m in registro.get("mercados", []) if m.get("claim_id") == claim_id), None)
    if mercado is None:
        raise ReprecificacaoError(f"{claim_id}: claim não existe no registro")

    estado = str(mercado.get("estado", "")).upper()
    if estado == "LIQUIDADO":
        raise ReprecificacaoError(
            f"{claim_id}: já LIQUIDADO — mudar a previsão depois do desfecho é fabricar acerto. "
            "A trajetória de um claim termina quando o mundo responde."
        )

    anterior = float(mercado["probability"])
    novo = float(probabilidade.valor)
    if not 0.0 <= novo <= 1.0:
        raise ReprecificacaoError(f"{claim_id}: probabilidade fora de [0,1], veio {novo!r}")

    movimento = abs(novo - anterior)
    if movimento < MOVIMENTO_MINIMO:
        return {
            "reprecificado": False,
            "motivo": f"movimento {movimento:.4f} abaixo do mínimo {MOVIMENTO_MINIMO} — nada a registrar",
            "probability": anterior,
            "selagem": None,
        }

    proveniencia = probabilidade.as_dict()
    mudanca = {
        "claim_id": claim_id,
        "probabilidade_anterior": anterior,
        "probabilidade_nova": novo,
        "movimento": round(novo - anterior, 6),
        "motivo": motivo.strip(),
        "gerador": proveniencia,
        "reprecificado_em": agora or _agora(),
        "metodo": (
            "reprecificação de mercado ABERTO: o valor anterior permanece na corrente, o novo entra "
            "como evento próprio com a proveniência do sinal. Quem auditar vê quando mudamos de ideia "
            "e por causa de quê — o silêncio é que seria trapaça."
        ),
    }

    # sela ANTES de gravar: falha no meio deixa evento sem efeito (visível e
    # inofensivo), nunca efeito sem evento
    selagem = None
    if sdk is not None:
        from asus_theye.audit.schema import hash_json
        from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

        selagem = selar_registro(
            sdk,
            mudanca,
            tipo_evento="market.repricing",
            recurso="market",
            correlation_id=f"reprecificacao:{hash_json(mudanca)[:32]}",
            occurred_at=str(mudanca["reprecificado_em"]),
            eventos=eventos or EVENTOS_PADRAO,
        )

    mercado["probability"] = novo
    mercado["max_uncertainty"] = abs(novo - 0.5) <= 0.001
    mercado["gerador"] = proveniencia
    mercado.setdefault("reprecificacoes", []).append(
        {k: mudanca[k] for k in ("probabilidade_anterior", "probabilidade_nova", "motivo", "reprecificado_em")}
    )
    store.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"reprecificado": True, "mudanca": mudanca, "selagem": selagem}
