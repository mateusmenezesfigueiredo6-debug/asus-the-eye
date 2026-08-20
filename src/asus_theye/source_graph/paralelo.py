# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Coleta paralela por host — o paralelismo que o rate limit dá de graça.

O gargalo da missão: 1900 fontes × 3 s de intervalo por host ≈ 95 min de sono
num laço serial. Mas o limite é POR HOST — fontes em hosts distintos podem
correr ao mesmo tempo sem desrespeitar ninguém. Este módulo explora exatamente
isso, e nada além disso:

1. **Partição por host**: as tarefas são agrupadas por host, e cada host é
   processado por UM único worker, em série — a educação com cada servidor é
   idêntica à do laço serial (mesmo ``PoliteFetcher``, mesmo intervalo).
2. **Paralelismo só ENTRE hosts** (``ThreadPoolExecutor``, padrão que o repo já
   usa em ``apps/comercial``). Tempo total ≈ o host mais lento, não a soma.
3. **Erro isolado**: falha numa tarefa vira ``ResultadoTarefa(ok=False)`` e não
   derruba as demais — a coleta devolve o que conseguiu E o que falhou, nunca
   esconde nem aborta o lote inteiro.

Proveniência (política de reuso por licença): a ideia de agendador que
particiona trabalho e o executa por afinidade foi estudada do **Dask**
(BSD-3, ``dask/dask``) — nenhuma linha copiada; esta é a versão mínima do
conceito, na stdlib, para o caso específico de rate limit por host.
Ver ``reports/provenance/Dask-scheduler.md``.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

MAX_HOSTS_PADRAO = 8


class ColetaParalelaError(RuntimeError):
    """Entrada inválida para a coleta. Sempre levanta — nunca degrada."""


@dataclass(frozen=True)
class Tarefa:
    """Uma unidade de coleta: id estável, host (chave de partição) e o trabalho."""

    id: str
    host: str
    executar: Callable[[], Any]


@dataclass(frozen=True)
class ResultadoTarefa:
    """Desfecho de uma tarefa — sucesso com valor, ou falha com o erro nomeado."""

    id: str
    host: str
    ok: bool
    valor: Any = None
    erro: str = ""
    duracao_s: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "host": self.host,
            "ok": self.ok,
            "erro": self.erro,
            "duracao_s": round(self.duracao_s, 3),
        }


def _validar(tarefas: list[Tarefa]) -> None:
    ids = [t.id for t in tarefas]
    if len(set(ids)) != len(ids):
        raise ColetaParalelaError("ids de tarefa duplicados — cada tarefa precisa de id estável")
    for t in tarefas:
        if not t.id or not t.id.strip():
            raise ColetaParalelaError("tarefa sem id")
        if not t.host or not t.host.strip():
            raise ColetaParalelaError(f"{t.id}: tarefa sem host — o host é a chave da partição")


def _rodar_fila_do_host(fila: list[Tarefa]) -> list[ResultadoTarefa]:
    """Processa a fila de UM host em série — a educação por host é preservada."""
    resultados: list[ResultadoTarefa] = []
    for tarefa in fila:
        inicio = time.monotonic()
        try:
            valor = tarefa.executar()
            resultados.append(
                ResultadoTarefa(
                    id=tarefa.id, host=tarefa.host, ok=True, valor=valor, duracao_s=time.monotonic() - inicio
                )
            )
        except Exception as erro:  # noqa: BLE001 - erro isolado é a regra: nunca derruba o lote
            resultados.append(
                ResultadoTarefa(
                    id=tarefa.id,
                    host=tarefa.host,
                    ok=False,
                    erro=f"{type(erro).__name__}: {erro}",
                    duracao_s=time.monotonic() - inicio,
                )
            )
    return resultados


def executar_por_host(
    tarefas: Iterable[Tarefa],
    *,
    max_hosts: int = MAX_HOSTS_PADRAO,
) -> list[ResultadoTarefa]:
    """Executa as tarefas com paralelismo ENTRE hosts e série DENTRO do host.

    Devolve um resultado por tarefa, na ordem: hosts pela primeira aparição,
    e dentro do host a ordem original. ``max_hosts`` limita quantos hosts
    correm ao mesmo tempo (teto de conexões simultâneas, não de tarefas).
    """
    lista = list(tarefas)
    if not lista:
        return []
    if max_hosts < 1:
        raise ColetaParalelaError(f"max_hosts deve ser >= 1, veio {max_hosts}")
    _validar(lista)

    filas: dict[str, list[Tarefa]] = {}
    for tarefa in lista:
        filas.setdefault(tarefa.host, []).append(tarefa)

    with ThreadPoolExecutor(max_workers=min(max_hosts, len(filas))) as pool:
        futuros = {host: pool.submit(_rodar_fila_do_host, fila) for host, fila in filas.items()}
        por_host = {host: futuro.result() for host, futuro in futuros.items()}

    return [resultado for host in filas for resultado in por_host[host]]


def resumo(resultados: list[ResultadoTarefa]) -> dict[str, Any]:
    """Placar honesto da coleta: quantos ok, quantos falharam, e quais."""
    falhas = [r for r in resultados if not r.ok]
    return {
        "total": len(resultados),
        "ok": len(resultados) - len(falhas),
        "falhas": len(falhas),
        "hosts": len({r.host for r in resultados}),
        "falhas_detalhe": [f.as_dict() for f in falhas],
    }
