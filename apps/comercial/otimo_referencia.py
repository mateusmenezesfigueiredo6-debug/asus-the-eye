"""Estima o otimo da instancia dificil — o alvo que qualquer metodo tem que bater.

A instancia: 138 areas da taxonomia, capacidade 10%, sinergia 3x, densidade
2,4%. Nela a busca local rapida (20 mil iteracoes, 26ms) achou 31.158 contra
29.696 do guloso.

Antes de gastar cota de QPU, e preciso saber quanto vale o otimo de verdade. Se
o recozimento longo achar 31.200, o ganho possivel acima da busca local rapida e
irrisorio e nenhum metodo caro se justifica. Se achar 34.000, ha espaco real.

METODO: multiplas partidas independentes de recozimento simulado, cada uma com
semente propria e muito mais iteracoes. O melhor valor encontrado e um LIMITE
INFERIOR do otimo, nunca o otimo provado — a distincao importa e o relatorio a
mantem.

CONVERGENCIA: se varias partidas independentes param no mesmo valor, isso e
evidencia (nao prova) de que o valor e o otimo ou esta perto dele. O relatorio
publica quantas partidas chegaram ao melhor.

Uso: python3 apps/comercial/otimo_referencia.py [partidas] [iteracoes]
Saida: reports/commercial/otimo_referencia.json
"""

import json
import math
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "apps/comercial"))

from qkp_taxonomia import carregar, guloso, sinergia, valor_de  # noqa: E402

CAP_PCT = 0.10
INTENSIDADE = 3.0
PARTIDAS_PADRAO = 12
ITERACOES_PADRAO = 400_000


def recozer(itens, s, cap, rng, iteracoes) -> tuple[set, float]:
    sel, _ = guloso(itens, s, cap)
    peso = sum(itens[i]["peso"] for i in sel)
    atual = valor_de(sel, itens, s)
    melhor_sel, melhor = set(sel), atual
    n = len(itens)
    t0 = max(1.0, atual * 0.05)
    t1 = t0 * 1e-4
    for k in range(iteracoes):
        temp = t0 * (t1 / t0) ** (k / iteracoes)
        i = rng.randrange(n)
        # troca: as vezes remove um e poe outro, o que atravessa vales que o
        # movimento simples de um bit nao atravessa quando a capacidade e apertada
        if i in sel:
            cand, novo_peso = sel - {i}, peso - itens[i]["peso"]
        else:
            cand, novo_peso = sel | {i}, peso + itens[i]["peso"]
            if novo_peso > cap:
                if not sel:
                    continue
                fora = rng.choice(tuple(sel))
                cand = (sel | {i}) - {fora}
                novo_peso = peso + itens[i]["peso"] - itens[fora]["peso"]
                if novo_peso > cap:
                    continue
        v = valor_de(cand, itens, s)
        delta = v - atual
        if delta > 0 or rng.random() < math.exp(delta / max(temp, 1e-9)):
            sel, peso, atual = cand, novo_peso, v
            if atual > melhor:
                melhor_sel, melhor = set(sel), atual
    return melhor_sel, melhor


def main(partidas: int = PARTIDAS_PADRAO, iteracoes: int = ITERACOES_PADRAO) -> None:
    itens = carregar()
    if not itens:
        print("sinal_taxonomia.json ausente")
        return
    cap = sum(i["peso"] for i in itens) * CAP_PCT
    s = sinergia(itens, INTENSIDADE)

    _, val_gu = guloso(itens, s, cap)
    print(
        f"instancia: {len(itens)} areas, capacidade {cap:.0f} ({CAP_PCT:.0%}), "
        f"sinergia {INTENSIDADE}x, {len(s)} arestas"
    )
    print(f"referencias: guloso {val_gu:,.0f}")
    print(f"rodando {partidas} partidas de {iteracoes:,} iteracoes\n")

    resultados = []
    t_total = time.perf_counter()
    for p in range(partidas):
        rng = random.Random(1000 + p)
        t = time.perf_counter()
        sel, val = recozer(itens, s, cap, rng, iteracoes)
        dt = time.perf_counter() - t
        resultados.append(
            {
                "partida": p,
                "valor": val,
                "areas": len(sel),
                "segundos": round(dt, 1),
                "selecao": sorted(itens[i]["id"] for i in sel),
            }
        )
        print(f"  partida {p:>2}: {val:>12,.0f}  ({dt:.1f}s)")
    t_total = time.perf_counter() - t_total

    melhor = max(r["valor"] for r in resultados)
    convergiram = sum(1 for r in resultados if abs(r["valor"] - melhor) < 0.5)
    pior = min(r["valor"] for r in resultados)
    dispersao = (melhor - pior) / melhor * 100

    print(f"\nmelhor encontrado: {melhor:,.0f}")
    print(f"  {convergiram}/{partidas} partidas chegaram nesse valor")
    print(f"  dispersao entre partidas: {dispersao:.2f}%")
    print(f"  ganho sobre o guloso: {(melhor / val_gu - 1) * 100:+.2f}%")
    print(f"  tempo total: {t_total:.0f}s")

    consenso = convergiram >= max(2, partidas // 2)
    saida = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "instancia": {
            "n": len(itens),
            "capacidade": cap,
            "capacidade_pct": CAP_PCT,
            "intensidade_sinergia": INTENSIDADE,
            "arestas": len(s),
        },
        "metodo": "recozimento simulado, partidas independentes com semente propria",
        "partidas": partidas,
        "iteracoes_por_partida": iteracoes,
        "guloso": round(val_gu, 1),
        "melhor_encontrado": round(melhor, 1),
        "e_limite_inferior_nao_otimo_provado": True,
        "partidas_que_convergiram": convergiram,
        "dispersao_pct": round(dispersao, 3),
        "ganho_sobre_guloso_pct": round((melhor / val_gu - 1) * 100, 2),
        "tempo_total_s": round(t_total, 1),
        "leitura": (
            "varias partidas independentes pararam no mesmo valor: evidencia de otimo ou vizinhanca dele"
            if consenso
            else "partidas divergiram: o espaco tem otimos locais distantes e o melhor "
            "valor aqui provavelmente esta abaixo do otimo"
        ),
        "alvo_para_metodo_quantico": (
            f"qualquer QAOA nesta instancia precisa superar {melhor:,.0f}, nao os "
            f"{val_gu:,.0f} do guloso. Vencer heuristica fraca nao prova nada."
        ),
        "resultados": resultados,
    }
    dest = BASE / "reports/commercial/otimo_referencia.json"
    dest.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nOK {dest.name}")
    print(f"  {saida['leitura']}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    main(int(args[0]) if args else PARTIDAS_PADRAO, int(args[1]) if len(args) > 1 else ITERACOES_PADRAO)
