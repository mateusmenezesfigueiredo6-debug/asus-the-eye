"""Testes do coletor paralelo por host — as garantias que importam.

Determinísticos: os "trabalhos" são funções locais com sleeps mínimos; nenhum
teste toca a rede.
"""

from __future__ import annotations

import threading
import time

import pytest

from asus_theye.source_graph.paralelo import (
    ColetaParalelaError,
    ResultadoTarefa,
    Tarefa,
    executar_por_host,
    resumo,
)


def tarefa(id: str, host: str, fn) -> Tarefa:
    return Tarefa(id=id, host=host, executar=fn)


# ------------------------------------------------------- paralelismo entre hosts


def test_hosts_distintos_correm_em_paralelo() -> None:
    """3 hosts × 0,15 s cada: em série seriam ~0,45 s; em paralelo ~0,15 s."""
    dormir = 0.15

    def trabalho() -> str:
        time.sleep(dormir)
        return "ok"

    tarefas = [tarefa(f"t{i}", f"host-{i}.ex", trabalho) for i in range(3)]
    inicio = time.monotonic()
    resultados = executar_por_host(tarefas)
    duracao = time.monotonic() - inicio
    assert all(r.ok for r in resultados)
    assert duracao < dormir * 2.5, f"esperado ~{dormir}s (paralelo), levou {duracao:.2f}s"


def test_dentro_do_host_e_serial_sem_sobreposicao() -> None:
    """Duas tarefas do MESMO host nunca se sobrepõem (a educação é preservada)."""
    execucoes: list[tuple[str, float, float]] = []
    trava = threading.Lock()

    def trabalho(nome: str):
        def fn() -> str:
            inicio = time.monotonic()
            time.sleep(0.05)
            with trava:
                execucoes.append((nome, inicio, time.monotonic()))
            return nome

        return fn

    tarefas = [
        tarefa("a1", "mesmo-host.ex", trabalho("a1")),
        tarefa("a2", "mesmo-host.ex", trabalho("a2")),
        tarefa("b1", "outro-host.ex", trabalho("b1")),
    ]
    executar_por_host(tarefas)
    mesmas = sorted((e for e in execucoes if e[0].startswith("a")), key=lambda e: e[1])
    assert len(mesmas) == 2
    _, _inicio1, fim1 = mesmas[0]
    _, inicio2, _fim2 = mesmas[1]
    assert inicio2 >= fim1, "a segunda tarefa do host começou antes da primeira terminar"


# ------------------------------------------------------- isolamento de erro


def test_erro_em_uma_tarefa_nao_derruba_as_outras() -> None:
    def quebra() -> None:
        raise ValueError("fonte fora do ar")

    tarefas = [
        tarefa("ok-1", "h1.ex", lambda: 42),
        tarefa("mau", "h1.ex", quebra),
        tarefa("ok-2", "h2.ex", lambda: 7),
    ]
    resultados = executar_por_host(tarefas)
    por_id = {r.id: r for r in resultados}
    assert por_id["ok-1"].ok and por_id["ok-1"].valor == 42
    assert por_id["ok-2"].ok and por_id["ok-2"].valor == 7
    assert not por_id["mau"].ok
    assert "ValueError" in por_id["mau"].erro and "fonte fora do ar" in por_id["mau"].erro


def test_resumo_conta_e_detalha_falhas() -> None:
    resultados = [
        ResultadoTarefa(id="a", host="h1", ok=True, valor=1),
        ResultadoTarefa(id="b", host="h2", ok=False, erro="X: boom"),
    ]
    r = resumo(resultados)
    assert r["total"] == 2 and r["ok"] == 1 and r["falhas"] == 1 and r["hosts"] == 2
    assert r["falhas_detalhe"][0]["id"] == "b"


# ------------------------------------------------------- ordem e guardas


def test_ordem_por_host_e_preservada() -> None:
    tarefas = [
        tarefa("a1", "h1.ex", lambda: 1),
        tarefa("b1", "h2.ex", lambda: 2),
        tarefa("a2", "h1.ex", lambda: 3),
    ]
    ids = [r.id for r in executar_por_host(tarefas)]
    assert ids == ["a1", "a2", "b1"]  # hosts pela 1ª aparição; série dentro do host


def test_lista_vazia_devolve_vazio() -> None:
    assert executar_por_host([]) == []


@pytest.mark.parametrize(
    "tarefas,erro",
    [
        ([Tarefa(id="x", host="h", executar=lambda: 1), Tarefa(id="x", host="h", executar=lambda: 2)], "duplicados"),
        ([Tarefa(id="", host="h", executar=lambda: 1)], "sem id"),
        ([Tarefa(id="a", host="", executar=lambda: 1)], "sem host"),
    ],
)
def test_entradas_invalidas_levantam(tarefas: list, erro: str) -> None:
    with pytest.raises(ColetaParalelaError, match=erro):
        executar_por_host(tarefas)


def test_max_hosts_invalido_levanta() -> None:
    with pytest.raises(ColetaParalelaError, match="max_hosts"):
        executar_por_host([Tarefa(id="a", host="h", executar=lambda: 1)], max_hosts=0)


# ------------------------------------------------------- fetcher thread-safe


def test_wait_for_slot_respeita_intervalo_sob_concorrencia() -> None:
    """N threads no MESMO host: os carimbos saem espaçados >= intervalo."""
    from asus_theye.source_graph.fetcher import FetchPolicy, PoliteFetcher

    politica = FetchPolicy(user_agent="teste (t@ex.com)", min_interval_seconds=0.05)
    fetcher = PoliteFetcher(policy=politica, connector_id="t", license_id="CC0")
    carimbos: list[float] = []
    trava = threading.Lock()

    def bate() -> None:
        fetcher._wait_for_slot("https://mesmo-host.ex/x")
        with trava:
            carimbos.append(time.monotonic())

    fios = [threading.Thread(target=bate) for _ in range(4)]
    for f in fios:
        f.start()
    for f in fios:
        f.join()
    carimbos.sort()
    # pares consecutivos: N carimbos → N-1 intervalos (strict=False é deliberado)
    intervalos = [b - a for a, b in zip(carimbos, carimbos[1:], strict=False)]
    assert len(intervalos) == 3
    assert all(i >= 0.04 for i in intervalos), f"slots furados sob concorrência: {intervalos}"
