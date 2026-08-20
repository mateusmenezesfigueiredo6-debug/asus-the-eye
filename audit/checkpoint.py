# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Checkpoints — ação sensível exige justificativa, e a justificativa vira evento.

O campo ``human_review_status`` existia no esquema desde o começo e nunca foi
lido por nada: todo evento nascia ``not_required``. Era a mesma doença que
``estado`` tinha antes de a medição passar a validá-lo — um campo que parece
governança mas não governa.

Aqui ele passa a governar. Uma ação sensível (publicar, ancorar on-chain,
espelhar, expurgar) **não acontece** sem justificativa, e a justificativa é
selada na corrente ANTES do efeito. Quem auditar depois não encontra só o que
foi feito: encontra o motivo declarado por quem fez, no momento em que fez, com
prova temporal.

**Por que antes e não depois.** Selar o motivo depois do efeito deixaria uma
janela em que o efeito existe sem justificativa — e é exatamente essa janela que
alguém usaria. Selando primeiro, uma falha no meio deixa um checkpoint sem
efeito (inofensivo e visível), nunca um efeito sem checkpoint.

Conceito lido em whitepaper de governança de terceiro e reimplementado de forma
independente; registro em ``reports/provenance/Palantir-governance-concepts.md``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

# O registro das ações que exigem justificativa. Estar aqui é o que torna a
# ação sensível — e a lista é código, não configuração solta, para que
# acrescentar uma ação seja um commit revisável.
#
# `minimo_de_caracteres` existe porque "ok" não é justificativa. O número é
# baixo de propósito: a trava é contra o vazio e o reflexo, não um exame.
ACOES_SENSIVEIS: dict[str, dict[str, Any]] = {
    "publicar": {
        "descricao": "publicar painéis ou artefatos fora da máquina do titular",
        "minimo_de_caracteres": 20,
    },
    "ancorar": {
        "descricao": "transmitir âncora on-chain — irreversível e com custo real",
        "minimo_de_caracteres": 20,
    },
    "espelhar": {
        "descricao": "enviar a corrente para infraestrutura de terceiro",
        "minimo_de_caracteres": 20,
    },
    "expurgar": {
        "descricao": "remover dado de um store versionado",
        "minimo_de_caracteres": 30,
    },
}

# O que o esquema de auditoria passa a registrar quando um checkpoint aprova.
REVISAO_APROVADA = "approved"


class CheckpointError(RuntimeError):
    """Ação sensível sem justificativa válida. Sempre levanta — a trava é fechada."""


def _validar(acao: str, justificativa: str, ator: str) -> dict[str, Any]:
    config = ACOES_SENSIVEIS.get(acao)
    if config is None:
        raise CheckpointError(
            f"ação {acao!r} não está no registro de sensíveis: {sorted(ACOES_SENSIVEIS)}. "
            "Acrescentar ação sensível é um commit revisável, não um parâmetro solto."
        )
    if not ator.strip():
        raise CheckpointError(f"{acao}: 'ator' obrigatório — justificativa sem autor não responsabiliza ninguém")

    limpa = justificativa.strip()
    minimo = int(config["minimo_de_caracteres"])
    if len(limpa) < minimo:
        raise CheckpointError(
            f"{acao}: justificativa precisa de ao menos {minimo} caracteres, veio {len(limpa)}. "
            f"Ação sensível ({config['descricao']}) sem motivo declarado não acontece."
        )
    return config


def registrar(
    *,
    acao: str,
    justificativa: str,
    ator: str,
    alvo: str = "",
    sdk: Any | None = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Valida e SELA o checkpoint. Levanta antes de qualquer efeito.

    Devolve o recibo. Sem ``sdk`` a validação acontece igual, mas nada é selado —
    útil em teste; em produção o chamador deve passar a auditoria, senão o
    checkpoint não deixa rastro e perde a razão de existir.
    """
    config = _validar(acao, justificativa, ator)
    recibo: dict[str, Any] = {
        "acao": acao,
        "descricao": str(config["descricao"]),
        "alvo": alvo,
        "ator": ator,
        "justificativa": justificativa.strip(),
        "metodo": (
            "checkpoint selado ANTES do efeito: falha no meio deixa checkpoint sem efeito "
            "(inofensivo e visível), nunca efeito sem checkpoint"
        ),
    }

    selagem = None
    if sdk is not None:
        from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

        from .schema import hash_json

        identidade = hash_json(recibo)
        selagem = selar_registro(
            sdk,
            recibo,
            tipo_evento="governance.checkpoint",
            recurso="checkpoint",
            correlation_id=f"checkpoint:{identidade[:32]}",
            eventos=eventos or EVENTOS_PADRAO,
        )
    return {"recibo": recibo, "selagem": selagem}


@contextmanager
def exigir(
    *,
    acao: str,
    justificativa: str,
    ator: str,
    alvo: str = "",
    sdk: Any | None = None,
    eventos: Path | None = None,
) -> Iterator[dict[str, Any]]:
    """Portão para envolver a ação sensível.

    Uso::

        with exigir(acao="ancorar", justificativa=..., ator=..., sdk=sdk):
            transmitir_ancora()

    O checkpoint é selado ao ENTRAR. Se a validação falhar, o corpo nunca roda —
    é isso que torna a trava fechada em vez de decorativa.
    """
    recibo = registrar(acao=acao, justificativa=justificativa, ator=ator, alvo=alvo, sdk=sdk, eventos=eventos)
    yield recibo


def protegido(acao: str) -> Callable[..., Any]:
    """Decorador que exige ``justificativa`` e ``ator`` como argumentos nomeados.

    Marca a função como sensível na própria assinatura: quem chamar sem os dois
    recebe :class:`CheckpointError` antes de qualquer efeito acontecer.
    """

    def envolver(funcao: Callable[..., Any]) -> Callable[..., Any]:
        def chamada(*args: Any, justificativa: str = "", ator: str = "", **kwargs: Any) -> Any:
            sdk = kwargs.get("sdk")
            registrar(acao=acao, justificativa=justificativa, ator=ator, alvo=funcao.__name__, sdk=sdk)
            return funcao(*args, **kwargs)

        chamada.__name__ = funcao.__name__
        chamada.__doc__ = funcao.__doc__
        chamada.__wrapped__ = funcao  # type: ignore[attr-defined]
        return chamada

    return envolver
