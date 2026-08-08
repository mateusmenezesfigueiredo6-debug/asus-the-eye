"""Ate que tamanho o QAOA passa a valer a pena? Medicao, nao torcida.

O problema real da plataforma tem 9 nichos e o classico ganha: empata em
qualidade e e ~37x mais rapido. A pergunta natural e onde isso vira.

METODOLOGIA E SUA RESSALVA: acima de 9 itens nao existe dado real. Os itens
extras sao amostrados da MESMA distribuicao dos 9 medidos (valor e peso), com
semente fixa. Isso serve para estudar o comportamento do ALGORITMO conforme n
cresce; nao serve para decidir negocio. Um numero derivado daqui nunca deve
aparecer como recomendacao de alocacao.

O QUE E COMPARADO:
  exaustivo  — o que o engine chama de "classico": testa 2^n combinacoes
  guloso     — ordena por valor/peso e enche a mochila (classico de verdade)
  dinamico   — programacao dinamica, otimo exato em tempo pseudo-polinomial
  QAOA       — simulador local

A comparacao honesta nao e QAOA contra exaustivo. E QAOA contra o MELHOR
classico disponivel. Vencer a forca bruta nao prova nada: forca bruta e a pior
forma de resolver mochila.

Uso: python3 apps/comercial/escalada_qaoa.py [n_max]
Saida: reports/benchmark/alocacao/escalada.json
"""

import json
import random
import sys
import time
from itertools import combinations
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "apps/comercial"))
sys.path.insert(0, str(BASE / "src"))

from alocacao_quantica import montar_problema  # noqa: E402

SEMENTE = 42
N_MAX_PADRAO = 22
LIMITE_EXAUSTIVO_S = 30.0


def exaustivo(valores, pesos, cap):
    n = len(valores)
    melhor = 0.0
    for k in range(n + 1):
        for combo in combinations(range(n), k):
            if sum(pesos[i] for i in combo) <= cap:
                melhor = max(melhor, sum(valores[i] for i in combo))
    return melhor


def guloso(valores, pesos, cap):
    ordem = sorted(range(len(valores)), key=lambda i: valores[i] / pesos[i], reverse=True)
    total, usado = 0.0, 0.0
    for i in ordem:
        if usado + pesos[i] <= cap:
            total += valores[i]
            usado += pesos[i]
    return total


def dinamico(valores, pesos, cap):
    """Otimo exato. Pesos sao escalados para inteiro (grade de 0,5)."""
    escala = 2
    c = int(cap * escala)
    ws = [int(p * escala) for p in pesos]
    tabela = [0.0] * (c + 1)
    for v, w in zip(valores, ws, strict=True):
        for cap_atual in range(c, w - 1, -1):
            tabela[cap_atual] = max(tabela[cap_atual], tabela[cap_atual - w] + v)
    return tabela[c]


def cronometrar(fn, *args):
    t = time.perf_counter()
    r = fn(*args)
    return r, (time.perf_counter() - t) * 1000


def instancia(base_valores, base_pesos, n, rng):
    """Cresce a instancia amostrando da distribuicao real medida."""
    v = list(base_valores)
    p = list(base_pesos)
    while len(v) < n:
        v.append(rng.choice(base_valores) * rng.uniform(0.6, 1.4))
        p.append(rng.choice(base_pesos))
    return v[:n], p[:n]


def main(n_max: int = N_MAX_PADRAO, com_qaoa: bool = True) -> None:
    reais = montar_problema()["itens"]
    if not reais:
        print("sem dado real para ancorar a distribuicao")
        return
    base_v = [i["valor_kbrl"] for i in reais]
    base_p = [i["peso"] for i in reais]
    n_real = len(base_v)
    rng = random.Random(SEMENTE)

    from asus_theye.benchmark.qaoa_benchmark import run_qaoa_benchmark
    from asus_theye.problem import BenchmarkProblem

    linhas = []
    print(f"ancorado em {n_real} nichos reais; acima disso a instancia e sintetica\n")
    print(f"{'n':>3} {'exaustivo':>12} {'guloso':>9} {'dinamico':>10} {'QAOA':>9}  {'qualidade QAOA':>15}")
    print("-" * 68)

    for n in range(n_real, n_max + 1):
        v, p = instancia(base_v, base_p, n, rng)
        cap = sum(p) * 0.4

        if 2**n <= 2**24:
            otimo_ex, t_ex = cronometrar(exaustivo, v, p, cap)
        else:
            otimo_ex, t_ex = None, None
        _, t_gu = cronometrar(guloso, v, p, cap)
        otimo_dp, t_dp = cronometrar(dinamico, v, p, cap)

        if com_qaoa:
            prob = BenchmarkProblem(name=f"escala_{n}", values=tuple(v), weights=tuple(p), capacity=cap)
            t = time.perf_counter()
            try:
                score_q = run_qaoa_benchmark(prob, shots=1024, layers=2, seed=SEMENTE).get("score", 0.0)
            except Exception:
                score_q = 0.0
            t_qa = (time.perf_counter() - t) * 1000
        else:
            score_q, t_qa = None, None

        qualidade = (score_q / otimo_dp * 100) if (otimo_dp and score_q) else None
        linhas.append(
            {
                "n": n,
                "sintetico": n > n_real,
                "capacidade": round(cap, 1),
                "exaustivo_ms": None if t_ex is None else round(t_ex, 2),
                "guloso_ms": round(t_gu, 3),
                "dinamico_ms": round(t_dp, 3),
                "qaoa_ms": None if t_qa is None else round(t_qa, 1),
                "otimo": round(otimo_dp, 1),
                "qaoa_score": None if score_q is None else round(score_q, 1),
                "qaoa_qualidade_pct": None if qualidade is None else round(qualidade, 2),
                "exaustivo_bate_dinamico": (None if otimo_ex is None else abs(otimo_ex - otimo_dp) < 0.5),
            }
        )
        ex = "estourou" if t_ex is None else f"{t_ex:>10.1f}ms"
        qa = "  (pulado)" if t_qa is None else f"{t_qa:>7.0f}ms"
        q = "        —" if qualidade is None else f"{qualidade:>13.2f}%"
        print(f"{n:>3} {ex:>12} {t_gu:>7.3f}ms {t_dp:>8.3f}ms {qa}  {q}")

    dest = BASE / "reports/benchmark/alocacao/escalada.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(
            {
                "metodologia": (
                    f"itens acima de {n_real} sao sinteticos, amostrados da "
                    f"distribuicao real com semente {SEMENTE}; servem para "
                    "estudar o algoritmo, nunca para decidir alocacao"
                ),
                "n_real": n_real,
                "linhas": linhas,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nOK {dest}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else N_MAX_PADRAO, com_qaoa="--sem-qaoa" not in sys.argv)
