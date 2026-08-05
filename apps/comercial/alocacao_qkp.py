"""Alocacao com dependencia entre nichos — mochila QUADRATICA (QKP).

A alocacao anterior era mochila 0/1 simples: cada nicho valia por si. Isso
tinha um problema pratico e um teorico.

Pratico: nichos nao sao independentes. Cobrir tributario e societario ao mesmo
tempo aproveita a mesma base de fontes, o mesmo tipo de cliente e a mesma
expertise. Tratar como independentes subestima o valor do conjunto.

Teorico: mochila simples tem algoritmo classico pseudo-polinomial (programacao
dinamica resolve n=26 em 0,17ms). Nao ha janela para metodo quantico. A mochila
QUADRATICA nao tem essa saida — a DP nao se aplica quando o valor de um item
depende de quais outros foram escolhidos.

  maximizar  sum(v_i x_i) + sum(s_ij x_i x_j)
  sujeito a  sum(w_i x_i) <= C,   x in {0,1}

DE ONDE VEM A SINERGIA s_ij — E O QUE NAO INVENTAMOS:
`data/legal-taxonomy/legal_area_relationships.json` declara explicitamente que
so contem "structural group membership derived from the source list" e que
"cross-area doctrinal links require legal review before addition".

Entao a sinergia usada aqui e APENAS estrutural: dois nichos ganham termo
quadratico quando compartilham grupo da taxonomia. Vinculo doutrinario entre
areas nao entra ate passar por revisao juridica. A intensidade da sinergia e um
parametro declarado, nao medido — e o relatorio diz isso.

Uso: python3 apps/comercial/alocacao_qkp.py [capacidade] [sinergia_pct]
Saida: reports/commercial/alocacao_qkp.json
"""
import json
import sys
import time
from itertools import combinations
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "apps/comercial"))

from alocacao_quantica import montar_problema  # noqa: E402

TAXONOMIA = json.loads(
    (BASE / "data/legal-taxonomy/legal_areas.master.json").read_text(encoding="utf-8"))
COMERCIAIS = json.loads(
    (BASE / "data/commercial/niches.json").read_text(encoding="utf-8"))
CAPACIDADE_PADRAO = 20.0
SINERGIA_PADRAO = 0.15   # 15% do menor valor do par, por grupo compartilhado


def grupos_por_nicho() -> dict[str, set[str]]:
    """Grupos da taxonomia que cada nicho comercial toca. Dado real."""
    area_grupo = {a["legal_area_id"]: a["group"] for a in TAXONOMIA["areas"]}
    nichos = COMERCIAIS if isinstance(COMERCIAIS, list) else COMERCIAIS.get("niches", [])
    return {
        n["niche_id"]: {area_grupo[i] for i in n.get("legal_area_ids", []) if i in area_grupo}
        for n in nichos
    }


def matriz_sinergia(itens: list[dict], intensidade: float) -> dict:
    """s_ij > 0 quando i e j compartilham grupo estrutural."""
    gpn = grupos_por_nicho()
    s: dict[tuple[int, int], float] = {}
    detalhe = []
    for i, j in combinations(range(len(itens)), 2):
        a, b = itens[i]["niche_id"], itens[j]["niche_id"]
        comuns = gpn.get(a, set()) & gpn.get(b, set())
        if not comuns:
            continue
        base = min(itens[i]["valor_kbrl"], itens[j]["valor_kbrl"])
        peso_sinergia = base * intensidade * len(comuns)
        s[(i, j)] = peso_sinergia
        detalhe.append({"par": [a, b], "grupos_compartilhados": sorted(comuns),
                        "sinergia_kbrl": round(peso_sinergia, 1)})
    return {"matriz": s, "detalhe": sorted(detalhe, key=lambda d: -d["sinergia_kbrl"])}


def valor_total(sel: tuple, itens: list[dict], s: dict) -> float:
    v = sum(itens[i]["valor_kbrl"] for i in sel)
    v += sum(peso for (i, j), peso in s.items() if i in sel and j in sel)
    return v


def resolver_exato(itens, s, cap):
    melhor, melhor_v = (), -1.0
    n = len(itens)
    for k in range(n + 1):
        for combo in combinations(range(n), k):
            if sum(itens[i]["peso"] for i in combo) > cap:
                continue
            v = valor_total(combo, itens, s)
            if v > melhor_v:
                melhor, melhor_v = combo, v
    return melhor, melhor_v


def resolver_guloso(itens, s, cap):
    """Guloso por valor/peso, ignorando sinergia — o erro que a QKP expoe."""
    ordem = sorted(range(len(itens)),
                   key=lambda i: itens[i]["valor_kbrl"] / itens[i]["peso"], reverse=True)
    sel, usado = [], 0.0
    for i in ordem:
        if usado + itens[i]["peso"] <= cap:
            sel.append(i)
            usado += itens[i]["peso"]
    return tuple(sel), valor_total(tuple(sel), itens, s)


def todos_os_nichos(elegiveis: list[dict]) -> list[dict]:
    """Inclui nichos sem amostra suficiente, com valor marcado como estimado.

    Serve para estudar a ESTRUTURA do acoplamento, nunca para decidir: um nicho
    sem amostra nao tem conversao medida, e o valor dele aqui e placeholder.
    """
    por_id = {i["niche_id"]: i for i in elegiveis}
    piso = min(i["valor_kbrl"] for i in elegiveis)
    nichos = COMERCIAIS if isinstance(COMERCIAIS, list) else COMERCIAIS.get("niches", [])
    saida = []
    for n in nichos:
        nid = n["niche_id"]
        if nid in por_id:
            saida.append({**por_id[nid], "valor_estimado": False})
        else:
            saida.append({"niche_id": nid, "valor_kbrl": piso, "peso": 5.0,
                          "valor_estimado": True})
    return saida


def main(capacidade: float = CAPACIDADE_PADRAO,
         intensidade: float = SINERGIA_PADRAO,
         incluir_sem_amostra: bool = False) -> None:
    itens = montar_problema()["itens"]
    if not itens:
        print("sem dado real para montar o problema")
        return
    if incluir_sem_amostra:
        itens = todos_os_nichos(itens)
        estimados = sum(1 for i in itens if i.get("valor_estimado"))
        print(f"MODO ESTRUTURA: {len(itens)} nichos, {estimados} com valor "
              f"estimado (sem amostra) — nao serve para decidir\n")

    sin = matriz_sinergia(itens, intensidade)
    s = sin["matriz"]
    n = len(itens)
    densidade = len(s) / (n * (n - 1) / 2) if n > 1 else 0

    t = time.perf_counter()
    sel_ex, val_ex = resolver_exato(itens, s, capacidade)
    t_ex = (time.perf_counter() - t) * 1000
    t = time.perf_counter()
    sel_gu, val_gu = resolver_guloso(itens, s, capacidade)
    t_gu = (time.perf_counter() - t) * 1000

    # Quanto a sinergia muda a decisao? Compara com a mochila linear.
    lin_sel, lin_val = resolver_exato(itens, {}, capacidade)
    mudou = set(sel_ex) != set(lin_sel)

    nomes = lambda sel: [itens[i]["niche_id"] for i in sel]  # noqa: E731
    print(f"QKP com {n} nichos, capacidade {capacidade}, sinergia {intensidade:.0%}")
    print(f"  pares com grupo compartilhado: {len(s)}/{n*(n-1)//2} "
          f"(densidade {densidade:.0%})")
    print()
    print(f"  otimo QKP    : {val_ex:>12,.1f} em {t_ex:>7.1f}ms  {nomes(sel_ex)}")
    print(f"  guloso       : {val_gu:>12,.1f} em {t_gu:>7.3f}ms  "
          f"({(val_gu/val_ex*100):.2f}% do otimo)")
    print(f"  mochila linear: {lin_val:>11,.1f}          {nomes(lin_sel)}")
    print()
    print(f"  a sinergia MUDA a escolha: {mudou}")

    saida = {
        "problema": "mochila quadratica (QKP) — nichos com sinergia estrutural",
        "n": n,
        "inclui_nichos_sem_amostra": incluir_sem_amostra,
        "n_com_valor_estimado": sum(1 for i in itens if i.get("valor_estimado")),
        "capacidade": capacidade,
        "intensidade_sinergia": intensidade,
        "origem_da_sinergia": (
            "co-participacao em grupo da taxonomia "
            "(data/legal-taxonomy/legal_area_relationships.json). Esse arquivo "
            "declara conter apenas pertencimento estrutural; vinculo doutrinario "
            "entre areas exige revisao juridica e NAO foi incluido."),
        "intensidade_e_declarada_nao_medida": True,
        "pares_com_sinergia": len(s),
        "densidade": round(densidade, 3),
        "solucao_qkp": {"escolhidos": nomes(sel_ex), "valor": round(val_ex, 1),
                        "tempo_ms": round(t_ex, 2)},
        "solucao_gulosa": {"escolhidos": nomes(sel_gu), "valor": round(val_gu, 1),
                           "pct_do_otimo": round(val_gu / val_ex * 100, 2)},
        "solucao_linear_sem_sinergia": {"escolhidos": nomes(lin_sel),
                                        "valor": round(lin_val, 1)},
        "sinergia_muda_a_decisao": mudou,
        "por_que_importa": (
            "mochila linear tem DP pseudo-polinomial e nao abre espaco para "
            "metodo quantico; a QKP nao tem DP equivalente porque o valor de um "
            "item depende de quais outros entraram"),
        "top_sinergias": sin["detalhe"][:8],
    }
    dest = BASE / "reports/commercial/alocacao_qkp.json"
    dest.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOK {dest.name}")
    for d in sin["detalhe"][:4]:
        print(f"   {d['par'][0]} + {d['par'][1]}: "
              f"{'/'.join(d['grupos_compartilhados'])} -> R$ {d['sinergia_kbrl']:,.0f} mil")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cap = float(args[0]) if args else CAPACIDADE_PADRAO
    inten = float(args[1]) if len(args) > 1 else SINERGIA_PADRAO
    main(cap, inten, incluir_sem_amostra="--estrutura" in sys.argv)
