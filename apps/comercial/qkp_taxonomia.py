"""QKP na escala da taxonomia — 145 areas, o primeiro problema grande do projeto.

Ate aqui toda instancia era pequena: 9 nichos (512 combinacoes), 15 nichos
(32 mil). A busca exaustiva resolvia em milissegundos e nenhum metodo quantico
tinha o que fazer. Com 145 areas a conta muda de natureza: 2^145 combinacoes e
um numero maior que a quantidade de atomos observaveis. Exaustivo morre aqui.

  maximizar  sum(v_i x_i) + sum(s_ij x_i x_j)
  sujeito a  sum(w_i x_i) <= C,   x in {0,1},   i = 1..145

O QUE E VALOR AQUI — E O QUE NAO E: para as 145 areas so existe demanda medida
(mencoes em diarios oficiais). Nao existe conversao nem ticket, que so foram
medidos para o recorte comercial. Entao `valor` e PROXY DE DEMANDA, nao receita
esperada. Nenhum numero deste modulo deve ser lido como reais.

ESTRUTURA DA SINERGIA: cada area pertence a exatamente UM grupo, entao o
acoplamento e bloco-diagonal — pares so dentro do mesmo grupo. Isso e mais
facil que uma QKP densa geral, e o relatorio mede a densidade para nao deixar
essa vantagem implicita.

Uso: python3 apps/comercial/qkp_taxonomia.py [capacidade_pct] [sinergia]
Saida: reports/commercial/qkp_taxonomia.json
"""
import json
import random
import sys
import time
from itertools import combinations
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SINAL = BASE / "reports/commercial/sinal_taxonomia.json"
CAP_PCT_PADRAO = 0.30
SINERGIA_PADRAO = 0.15
SEMENTE = 42


def carregar() -> list[dict]:
    if not SINAL.exists():
        return []
    d = json.loads(SINAL.read_text(encoding="utf-8"))
    itens = []
    for a in d["areas"]:
        m = a.get("mencoes")
        if m is None:
            continue
        itens.append({
            "id": a["legal_area_id"],
            "grupo": a["group"],
            "valor": float(m),
            "peso": 1.0,
            "termo": a.get("termo"),
            "suspeita": a.get("suspeita_termo_generico", False),
        })
    return itens


def sinergia(itens: list[dict], intensidade: float) -> dict[tuple[int, int], float]:
    """Bloco-diagonal: par so existe dentro do mesmo grupo."""
    s = {}
    for i, j in combinations(range(len(itens)), 2):
        if itens[i]["grupo"] != itens[j]["grupo"]:
            continue
        base = min(itens[i]["valor"], itens[j]["valor"])
        if base > 0:
            s[(i, j)] = base * intensidade
    return s


def valor_de(sel: set, itens, s) -> float:
    v = sum(itens[i]["valor"] for i in sel)
    v += sum(p for (i, j), p in s.items() if i in sel and j in sel)
    return v


def guloso(itens, s, cap) -> tuple[set, float]:
    ordem = sorted(range(len(itens)), key=lambda i: itens[i]["valor"] / itens[i]["peso"],
                   reverse=True)
    sel, usado = set(), 0.0
    for i in ordem:
        if usado + itens[i]["peso"] <= cap:
            sel.add(i)
            usado += itens[i]["peso"]
    return sel, valor_de(sel, itens, s)


def busca_local(itens, s, cap, sel0: set, rng, iteracoes=20000) -> tuple[set, float]:
    """Recozimento simulado — a referencia classica seria para QKP grande."""
    sel = set(sel0)
    peso = sum(itens[i]["peso"] for i in sel)
    atual = valor_de(sel, itens, s)
    melhor_sel, melhor = set(sel), atual
    n = len(itens)
    t0, t1 = max(1.0, atual * 0.02), 0.01
    for k in range(iteracoes):
        temp = t0 * (t1 / t0) ** (k / iteracoes)
        i = rng.randrange(n)
        if i in sel:
            novo_peso = peso - itens[i]["peso"]
            cand = sel - {i}
        else:
            novo_peso = peso + itens[i]["peso"]
            if novo_peso > cap:
                continue
            cand = sel | {i}
        v = valor_de(cand, itens, s)
        if v > atual or rng.random() < pow(2.718, (v - atual) / max(temp, 1e-9)):
            sel, peso, atual = cand, novo_peso, v
            if atual > melhor:
                melhor_sel, melhor = set(sel), atual
    return melhor_sel, melhor


def main(cap_pct: float = CAP_PCT_PADRAO, intensidade: float = SINERGIA_PADRAO) -> None:
    itens = carregar()
    if not itens:
        print("sinal_taxonomia.json ausente ou vazio — rode sinal_taxonomia.py antes")
        return

    n = len(itens)
    cap = sum(i["peso"] for i in itens) * cap_pct
    s = sinergia(itens, intensidade)
    pares_possiveis = n * (n - 1) // 2
    densidade = len(s) / pares_possiveis
    grupos = {}
    for i in itens:
        grupos[i["grupo"]] = grupos.get(i["grupo"], 0) + 1

    print(f"QKP na taxonomia: {n} areas, {len(grupos)} grupos")
    print(f"  capacidade {cap:.0f} de {sum(i['peso'] for i in itens):.0f} ({cap_pct:.0%})")
    print(f"  pares com sinergia: {len(s):,} de {pares_possiveis:,} "
          f"(densidade {densidade:.1%}) — bloco-diagonal por grupo")
    print(f"  espaco de busca: 2^{n} — exaustivo impossivel")
    print()

    rng = random.Random(SEMENTE)
    t = time.perf_counter()
    sel_gu, val_gu = guloso(itens, s, cap)
    t_gu = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    sel_bl, val_bl = busca_local(itens, s, cap, sel_gu, rng)
    t_bl = (time.perf_counter() - t) * 1000

    ganho = (val_bl / val_gu - 1) * 100 if val_gu else 0
    print(f"  guloso      : {val_gu:>12,.0f} em {t_gu:>8.2f}ms  ({len(sel_gu)} areas)")
    print(f"  busca local : {val_bl:>12,.0f} em {t_bl:>8.0f}ms  ({len(sel_bl)} areas)"
          f"  ganho {ganho:+.2f}%")

    # Ate onde o simulador quantico chegaria nesta instancia?
    limite_sim = 30
    print()
    print(f"  QAOA em simulador: impossivel — {n} qubits exigiria 2^{n} amplitudes; "
          f"o limite pratico e ~{limite_sim} qubits")
    print(f"  QAOA em QPU real: {n} qubits cabe em hardware de 127-156 qubits "
          f"(IBM Heron), mas EXIGE autorizacao e queima cota")

    por_grupo_sel = {}
    for i in sel_bl:
        g = itens[i]["grupo"]
        por_grupo_sel[g] = por_grupo_sel.get(g, 0) + 1

    saida = {
        "problema": "QKP na taxonomia completa (145 areas)",
        "n": n,
        "grupos": len(grupos),
        "capacidade": cap,
        "capacidade_pct": cap_pct,
        "intensidade_sinergia": intensidade,
        "valor_e_proxy_de_demanda": True,
        "ressalva_valor": (
            "valor = mencoes em diarios oficiais (demanda). Conversao e ticket so "
            "existem para o recorte comercial de 15 nichos, entao nenhum numero "
            "aqui e receita esperada."),
        "sinergia": {
            "origem": "co-participacao em grupo da taxonomia (dado estrutural)",
            "pares": len(s),
            "pares_possiveis": pares_possiveis,
            "densidade": round(densidade, 4),
            "estrutura": ("bloco-diagonal: cada area pertence a um unico grupo, "
                          "entao nao ha aresta entre grupos. Isso e mais facil que "
                          "uma QKP densa geral."),
        },
        "exaustivo_viavel": False,
        "solucao_gulosa": {"valor": round(val_gu, 1), "areas": len(sel_gu),
                           "tempo_ms": round(t_gu, 2)},
        "solucao_busca_local": {"valor": round(val_bl, 1), "areas": len(sel_bl),
                                "tempo_ms": round(t_bl, 1),
                                "ganho_sobre_guloso_pct": round(ganho, 2),
                                "selecionadas": sorted(itens[i]["id"] for i in sel_bl)},
        "distribuicao_por_grupo": dict(sorted(por_grupo_sel.items(),
                                              key=lambda x: -x[1])),
        "quantico": {
            "simulador_viavel": False,
            "motivo_simulador": f"{n} qubits exigiria 2^{n} amplitudes",
            "qpu_real_cabe": n <= 156,
            "hardware_compativel": "IBM Heron (127-156 qubits)",
            "exige_autorizacao": True,
            "observacao": ("esta e a primeira instancia do projeto grande demais "
                           "para exaustivo E para simulacao quantica, e ao mesmo "
                           "tempo dentro do alcance de hardware real"),
        },
    }
    dest = BASE / "reports/commercial/qkp_taxonomia.json"
    dest.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOK {dest.name}")
    print("  grupos mais representados na solucao:")
    for g, c in sorted(por_grupo_sel.items(), key=lambda x: -x[1])[:6]:
        print(f"    {c:>3} areas  {g}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(float(args[0]) if args else CAP_PCT_PADRAO,
         float(args[1]) if len(args) > 1 else SINERGIA_PADRAO)
