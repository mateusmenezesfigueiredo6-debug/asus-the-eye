"""Religa o motor quantico a plataforma — de problema-demo a problema real.

O motor QAOA da The Eye resolvia um portfolio inventado (demo_portfolio_v1:
seis itens com valor e peso arbitrarios). Este modulo monta o MESMO tipo de
problema com os dados que a plataforma agora produz de verdade:

  item      = nicho juridico
  valor     = demanda prevista x taxa de conversao medida x ticket medio
              (receita esperada se o nicho for atendido)
  peso      = esforco declarado para cobrir o nicho no mes
  capacidade= esforco disponivel

Isso e uma mochila 0/1: escolher o subconjunto de nichos que maximiza receita
esperada sem estourar a capacidade. E exatamente a classe de problema que o
QAOA formula como QUBO, e a razao pela qual o motor quantico existe no projeto.

HONESTIDADE SOBRE O PESO: a API expoe median_cycle_days por nicho, que seria o
proxy natural de esforco, mas o funil atual registra ciclo zero (as
oportunidades foram avancadas na mesma sessao). Enquanto esse dado nao for
real, o peso vem de esforco_relativo declarado na ontologia e o relatorio diz
isso em cada execucao. Peso inventado apresentado como medido seria o mesmo
erro que a plataforma combate.

Uso: python3 apps/comercial/alocacao_quantica.py [capacidade]
Saida: reports/commercial/alocacao.json
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
API = "http://localhost:8713"
PREVISAO = BASE / "reports/commercial/previsao.json"
ONT = json.loads((BASE / "apps/comercial/ontologia.json").read_text(encoding="utf-8"))
CAPACIDADE_PADRAO = 20.0
ESFORCO_PADRAO = 5.0


def metricas(nid: str) -> dict | None:
    try:
        with urllib.request.urlopen(f"{API}/api/metrics/{nid}", timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None


def montar_problema() -> dict:
    """Traduz o estado da plataforma num problema de mochila 0/1."""
    prev = json.loads(PREVISAO.read_text(encoding="utf-8"))
    por_nicho = {a["niche_id"]: a for a in prev["avaliacoes"]}

    itens, ignorados = [], []
    for n in ONT["nichos"]:
        nid = n["niche_id"]
        av = por_nicho.get(nid, {})
        m = metricas(nid)
        if not m or av.get("status") != "avaliado":
            ignorados.append({"niche_id": nid, "motivo": "sem previsao ou sem metrica"})
            continue
        if not m.get("sample_sufficient"):
            ignorados.append({"niche_id": nid,
                              "motivo": f"amostra insuficiente ({m.get('denominator')} < "
                                        f"{m.get('minimum_sample')})"})
            continue

        demanda = av["previsao"][0]
        conversao = m.get("win_rate") or 0.0
        ticket = m.get("average_ticket_brl") or 0.0
        valor = demanda * conversao * ticket / 1000.0     # em milhares de R$
        peso = float(n.get("esforco_relativo", ESFORCO_PADRAO))
        if valor <= 0:
            ignorados.append({"niche_id": nid, "motivo": "valor esperado zero"})
            continue
        itens.append({"niche_id": nid, "valor_kbrl": round(valor, 1), "peso": peso,
                      "demanda_prevista": demanda, "conversao": conversao,
                      "ticket_brl": ticket, "regime": av.get("regime")})

    return {"itens": itens, "ignorados": ignorados}


def resolver(itens: list[dict], capacidade: float) -> dict:
    """Busca exaustiva: com poucos nichos, o otimo exato e barato e verificavel."""
    melhor, melhor_valor = (), -1.0
    n = len(itens)
    for k in range(n + 1):
        for combo in combinations(range(n), k):
            peso = sum(itens[i]["peso"] for i in combo)
            if peso > capacidade:
                continue
            valor = sum(itens[i]["valor_kbrl"] for i in combo)
            if valor > melhor_valor:
                melhor, melhor_valor = combo, valor
    escolhidos = [itens[i]["niche_id"] for i in melhor]
    return {
        "escolhidos": escolhidos,
        "valor_esperado_kbrl": round(melhor_valor, 1),
        "peso_usado": sum(itens[i]["peso"] for i in melhor),
        "combinacoes_avaliadas": 2 ** n,
    }


def como_problema_benchmark(itens: list[dict], capacidade: float):
    """Converte a alocacao no BenchmarkProblem que o motor quantico consome.

    E esta funcao que religa o motor ao projeto: em vez de demo_portfolio_v1,
    o classico, o QUBO e o QAOA passam a disputar o MESMO problema que a
    plataforma precisa resolver, com valores vindos de demanda prevista,
    conversao medida e ticket real.
    """
    from asus_theye.problem import BenchmarkProblem
    return BenchmarkProblem(
        name="alocacao_nichos_v1",
        values=tuple(i["valor_kbrl"] for i in itens),
        weights=tuple(i["peso"] for i in itens),
        capacity=capacidade,
    )


def main(capacidade: float = CAPACIDADE_PADRAO) -> None:
    p = montar_problema()
    itens = p["itens"]
    if not itens:
        print("nenhum nicho com dado suficiente — problema nao montado")
        return

    sol = resolver(itens, capacidade)
    tem_ciclo_real = any(
        (metricas(i["niche_id"]) or {}).get("median_cycle_days", 0) > 0 for i in itens)

    saida = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "problema": "mochila 0/1 — quais nichos cobrir dentro da capacidade",
        "capacidade": capacidade,
        "itens": itens,
        "ignorados": p["ignorados"],
        "solucao_exata": sol,
        "peso_e_medido": tem_ciclo_real,
        "ressalva_peso": (
            "peso medido a partir do ciclo real" if tem_ciclo_real else
            "PESO DECLARADO, NAO MEDIDO: o funil registra ciclo zero, entao o "
            "esforco vem de valor fixo por nicho. A escolha e valida como "
            "exercicio de alocacao, nao como recomendacao operacional."),
        "pronto_para_qaoa": {
            "n_variaveis": len(itens),
            "formulacao": "QUBO por penalizacao da restricao de capacidade",
            "observacao": ("com este numero de variaveis a busca exaustiva da o "
                           "otimo em milissegundos; o QAOA so se justifica quando "
                           "a instancia crescer o bastante para isso deixar de valer"),
        },
    }
    problema = como_problema_benchmark(itens, capacidade)
    saida["problema_benchmark"] = {
        "name": problema.name,
        "n": len(problema.values),
        "values": list(problema.values),
        "weights": list(problema.weights),
        "capacity": problema.capacity,
        "como_usar": ("run_benchmark_suite(problem=como_problema_benchmark(itens, cap)) "
                      "faz classico, QUBO e QAOA disputarem este problema real"),
    }
    dest = BASE / "reports/commercial/alocacao.json"
    dest.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK alocacao.json — {len(itens)} nichos elegiveis, "
          f"{len(p['ignorados'])} fora")
    print(f"   capacidade {capacidade} · peso usado {sol['peso_usado']} · "
          f"{sol['combinacoes_avaliadas']} combinacoes")
    print(f"   escolhidos: {', '.join(sol['escolhidos']) or '(nenhum cabe)'}")
    print(f"   receita esperada: R$ {sol['valor_esperado_kbrl']:,.1f} mil")
    if not tem_ciclo_real:
        print("   RESSALVA: peso declarado, nao medido — ver ressalva_peso")


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else CAPACIDADE_PADRAO)
