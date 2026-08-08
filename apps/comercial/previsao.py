"""Etapas 3 e 4 do ciclo — previsao de demanda juridica e backtest honesto.

O que a plataforma promete ao dizer "preditiva" tem que ser medido, nao afirmado.
Este modulo:

  1. Le a serie mensal por nicho (serie_historica.py).
  2. Preve os proximos meses com tres metodos, do mais burro ao menos burro.
  3. Faz backtest de origem movel: treina ate o mes t, preve t+1, compara com o
     observado, repete. Erro medido em MAE e MAPE.
  4. Declara o vencedor POR NICHO. Se nenhum modelo bate a media movel simples,
     o veredito e "sem ganho preditivo" — e isso e publicado como esta.

Metodos (implementados em numpy puro, sem dependencia pesada):
  ingenuo   — repete o ultimo valor. O piso: qualquer modelo tem que bater isso.
  media3    — media dos ultimos 3 meses. Robusto a ruido mensal.
  holt      — suavizacao exponencial com tendencia (nivel + inclinacao).

Uso: python3 apps/comercial/previsao.py [horizonte_meses]
Saida: reports/commercial/previsao.json
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[2]
SERIE = BASE / "reports/commercial/serie_mensal.json"
MIN_PONTOS = 12  # menos que isso nao sustenta backtest
JANELA_TESTE = 6  # ultimos meses reservados para avaliacao
HORIZONTE_PADRAO = 3


# ---------------------------------------------------------------- metodos
def ingenuo(y: np.ndarray, h: int) -> np.ndarray:
    return np.repeat(y[-1], h)


def media3(y: np.ndarray, h: int) -> np.ndarray:
    return np.repeat(y[-3:].mean(), h)


def holt(y: np.ndarray, h: int, alfa: float = 0.5, beta: float = 0.3) -> np.ndarray:
    """Suavizacao exponencial com tendencia (Holt linear)."""
    nivel, incl = float(y[0]), float(y[1] - y[0]) if len(y) > 1 else 0.0
    for valor in y[1:]:
        nivel_ant = nivel
        nivel = alfa * float(valor) + (1 - alfa) * (nivel + incl)
        incl = beta * (nivel - nivel_ant) + (1 - beta) * incl
    return np.array([max(0.0, nivel + (k + 1) * incl) for k in range(h)])


METODOS = {"ingenuo": ingenuo, "media3": media3, "holt": holt}


# ---------------------------------------------------------------- avaliacao
def mae(real: np.ndarray, prev: np.ndarray) -> float:
    return float(np.mean(np.abs(real - prev)))


def mape(real: np.ndarray, prev: np.ndarray) -> float | None:
    naozero = real != 0
    if not naozero.any():
        return None
    return float(np.mean(np.abs((real[naozero] - prev[naozero]) / real[naozero])) * 100)


def backtest(y: np.ndarray, nome: str) -> dict:
    """Origem movel: treina ate t, preve t+1, anda um mes, repete."""
    metodo = METODOS[nome]
    reais, previstos = [], []
    inicio = len(y) - JANELA_TESTE
    for t in range(inicio, len(y)):
        treino = y[:t]
        if len(treino) < 3:
            continue
        previstos.append(float(metodo(treino, 1)[0]))
        reais.append(float(y[t]))
    if not reais:
        return {"avaliado": False}
    r, p = np.array(reais), np.array(previstos)
    return {
        "avaliado": True,
        "n": len(r),
        "mae": round(mae(r, p), 2),
        "mape": None if mape(r, p) is None else round(mape(r, p), 1),
    }


def avaliar_nicho(nid: str, pontos: dict, meses: list[str], h: int) -> dict:
    serie = [pontos.get(m) for m in meses]
    observados = sum(1 for v in serie if v is not None)
    if observados < MIN_PONTOS:
        return {
            "niche_id": nid,
            "status": "serie_insuficiente",
            "pontos_validos": observados,
            "minimo": MIN_PONTOS,
            "nota": "sem historico bastante para prever — nada e afirmado",
        }

    # Mes faltante NO MEIO e interpolado, nunca descartado: descartar
    # comprimiria a linha do tempo. Buraco ANTES do primeiro mes observado e
    # cortado — interpolar ali inventaria historico que nunca foi medido.
    tem_todos = [v is not None for v in serie]
    primeiro = tem_todos.index(True)
    serie = serie[primeiro:]
    tem = np.array([v is not None for v in serie])
    idx = np.arange(len(serie), dtype=float)
    y = np.interp(idx, idx[tem], np.array([v for v in serie if v is not None], dtype=float))
    lacunas = int((~tem).sum())
    resultados = {nome: backtest(y, nome) for nome in METODOS}
    validos = {n: r for n, r in resultados.items() if r.get("avaliado")}
    if not validos:
        return {"niche_id": nid, "status": "backtest_impossivel"}

    campeao = min(validos, key=lambda n: validos[n]["mae"])
    piso = validos.get("media3", validos["ingenuo"])["mae"]
    ganho = round((piso - validos[campeao]["mae"]) / piso * 100, 1) if piso else 0.0
    # Tres regimes distintos, cada um com consequencia pratica diferente.
    regime = {
        "holt": ("tendencia", "ha sinal de tendencia: o modelo com inclinacao vence a media simples"),
        "ingenuo": (
            "passeio_aleatorio",
            "serie sem memoria util: o ultimo valor e o melhor previsor, prever adiante nao agrega",
        ),
        "media3": ("estavel", "serie estavel em torno da media: nao ha tendencia a extrair"),
    }[campeao]
    houve_ganho = campeao == "holt" and ganho > 0

    return {
        "niche_id": nid,
        "status": "avaliado",
        "pontos_observados": observados,
        "meses_interpolados": lacunas,
        "ultimo_observado": float(y[-1]),
        "backtest": validos,
        "modelo_campeao": campeao,
        "ganho_sobre_piso_pct": ganho,
        "regime": regime[0],
        "veredito": regime[1],
        "ganho_preditivo": houve_ganho,
        "previsao": [round(float(v), 1) for v in METODOS[campeao](y, h)],
        "horizonte_meses": h,
    }


def main(h: int = HORIZONTE_PADRAO) -> None:
    if not SERIE.exists():
        print("serie_mensal.json ausente — rode serie_historica.py primeiro")
        return
    dados = json.loads(SERIE.read_text(encoding="utf-8"))
    meses = dados["meses"]

    avaliacoes = [avaliar_nicho(nid, s["pontos"], meses, h) for nid, s in dados["series"].items()]
    avaliados = [a for a in avaliacoes if a["status"] == "avaliado"]
    com_ganho = [a for a in avaliados if a.get("ganho_preditivo")]

    saida = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "metodologia": (
            "backtest de origem movel; erro em MAE e MAPE; campeao so vale se bater a media movel de 3 meses"
        ),
        "janela_teste_meses": JANELA_TESTE,
        "resumo": {
            "nichos": len(avaliacoes),
            "avaliados": len(avaliados),
            "com_ganho_preditivo": len(com_ganho),
            "regimes": {
                r: sum(1 for a in avaliados if a.get("regime") == r)
                for r in ("tendencia", "passeio_aleatorio", "estavel")
            },
            "sem_serie": sum(1 for a in avaliacoes if a["status"] == "serie_insuficiente"),
        },
        "avaliacoes": sorted(avaliacoes, key=lambda a: a.get("ganho_sobre_piso_pct", -999), reverse=True),
    }
    dest = BASE / "reports/commercial/previsao.json"
    dest.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK {dest.name}")
    print(f"   {len(avaliados)}/{len(avaliacoes)} nichos avaliados · {len(com_ganho)} com ganho preditivo real")
    for a in avaliados[:10]:
        print(
            f"   {a['niche_id']:<20} {a['regime']:<16} campeao={a['modelo_campeao']:<8} "
            f"MAE={a['backtest'][a['modelo_campeao']]['mae']:<7} "
            f"prev={a['previsao'][0]}"
        )


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else HORIZONTE_PADRAO)
