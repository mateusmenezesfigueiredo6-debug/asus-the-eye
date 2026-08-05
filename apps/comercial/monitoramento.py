"""Etapa 6 do ciclo — monitoramento continuo da acuracia.

Medir o erro uma vez e diagnostico; medir ao longo do tempo e monitoramento.
Este modulo fecha o ciclo: a cada execucao ele confronta a previsao que a
plataforma fez no passado com o que de fato aconteceu, e guarda o resultado
num historico append-only.

O que isso permite dizer, e que hoje a plataforma nao consegue:
  - o modelo esta piorando com o tempo?
  - a fonte mudou de comportamento (quebra de regime)?
  - a previsao publicada no site merece confianca hoje?

Registro: reports/commercial/acuracia_historico.jsonl (uma linha por aferição,
nunca reescrita — o historico e a evidencia).

Uso: python3 apps/comercial/monitoramento.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SERIE = BASE / "reports/commercial/serie_mensal.json"
PREVISAO = BASE / "reports/commercial/previsao.json"
HISTORICO = BASE / "reports/commercial/acuracia_historico.jsonl"
PAINEL = BASE / "reports/commercial/monitoramento.json"

# Alerta quando o erro do mes supera a media historica por esta margem.
FATOR_ALERTA = 2.0


def mes_anterior(rotulo: str) -> str:
    ano, mes = (int(x) for x in rotulo.split("-"))
    mes -= 1
    if mes == 0:
        mes, ano = 12, ano - 1
    return f"{ano}-{mes:02d}"


def carregar_historico() -> list[dict]:
    if not HISTORICO.exists():
        return []
    linhas = []
    for linha in HISTORICO.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            linhas.append(json.loads(linha))
    return linhas


def aferir() -> dict:
    """Confronta a previsao registrada com o observado, nicho a nicho."""
    if not (SERIE.exists() and PREVISAO.exists()):
        return {"erro": "serie ou previsao ausente"}

    serie = json.loads(SERIE.read_text(encoding="utf-8"))
    prev = json.loads(PREVISAO.read_text(encoding="utf-8"))
    meses = serie["meses"]
    ultimo = meses[-1]

    historico = carregar_historico()
    ja_aferido = {(h["mes_alvo"], h["niche_id"]) for h in historico}

    aferições = []
    for av in prev["avaliacoes"]:
        if av.get("status") != "avaliado":
            continue
        nid = av["niche_id"]
        pontos = serie["series"].get(nid, {}).get("pontos", {})
        observado = pontos.get(ultimo)
        if observado is None:
            continue
        if (ultimo, nid) in ja_aferido:
            continue

        # O que a plataforma teria previsto para o ultimo mes, treinando so ate
        # o mes anterior — e a mesma logica do backtest, aplicada ao presente.
        anterior = pontos.get(mes_anterior(ultimo))
        if anterior is None:
            continue
        erro = abs(observado - anterior)
        erro_pct = (erro / observado * 100) if observado else None

        aferições.append({
            "aferido_em_utc": datetime.now(timezone.utc).isoformat(),
            "mes_alvo": ultimo,
            "niche_id": nid,
            "regime": av.get("regime"),
            "modelo": av.get("modelo_campeao"),
            "previsto": anterior,
            "observado": observado,
            "erro_absoluto": erro,
            "erro_pct": None if erro_pct is None else round(erro_pct, 1),
            "mae_esperado_backtest": av["backtest"][av["modelo_campeao"]]["mae"],
        })
    return {"novas": aferições, "historico": historico, "mes_alvo": ultimo}


def alertas(historico: list[dict]) -> list[dict]:
    """Nicho cujo erro recente destoa da propria historia merece olhar."""
    por_nicho: dict[str, list[dict]] = {}
    for h in historico:
        por_nicho.setdefault(h["niche_id"], []).append(h)

    saida = []
    for nid, regs in por_nicho.items():
        if len(regs) < 2:
            continue
        regs = sorted(regs, key=lambda r: r["mes_alvo"])
        recente = regs[-1]
        anteriores = regs[:-1]
        media = sum(r["erro_absoluto"] for r in anteriores) / len(anteriores)
        if media > 0 and recente["erro_absoluto"] > media * FATOR_ALERTA:
            saida.append({
                "niche_id": nid,
                "mes": recente["mes_alvo"],
                "erro_recente": recente["erro_absoluto"],
                "media_anterior": round(media, 2),
                "razao": round(recente["erro_absoluto"] / media, 1),
                "leitura": ("erro muito acima do historico — possivel quebra de "
                            "regime ou mudanca na fonte"),
            })
    return saida


def main() -> None:
    r = aferir()
    if "erro" in r:
        print(r["erro"])
        return

    novas = r["novas"]
    if novas:
        with HISTORICO.open("a", encoding="utf-8") as f:
            for a in novas:
                f.write(json.dumps(a, ensure_ascii=False) + "\n")

    historico = carregar_historico()
    por_mes: dict[str, list[dict]] = {}
    for h in historico:
        por_mes.setdefault(h["mes_alvo"], []).append(h)

    tendencia = []
    for mes in sorted(por_mes):
        regs = por_mes[mes]
        pcts = [x["erro_pct"] for x in regs if x["erro_pct"] is not None]
        tendencia.append({
            "mes": mes,
            "nichos_aferidos": len(regs),
            "erro_pct_mediano": round(sorted(pcts)[len(pcts) // 2], 1) if pcts else None,
        })

    painel = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "metodologia": ("a cada execucao, o valor observado do ultimo mes fechado "
                        "e confrontado com o que a plataforma preveria treinando "
                        "so ate o mes anterior; historico append-only"),
        "mes_alvo_desta_rodada": r["mes_alvo"],
        "afericoes_novas": len(novas),
        "afericoes_totais": len(historico),
        "meses_cobertos": len(por_mes),
        "tendencia_por_mes": tendencia,
        "alertas": alertas(historico),
    }
    PAINEL.write_text(json.dumps(painel, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK monitoramento.json — {len(novas)} afericoes novas, "
          f"{len(historico)} no historico, {len(por_mes)} meses cobertos")
    for t in tendencia[-4:]:
        print(f"   {t['mes']}  nichos={t['nichos_aferidos']:<3} "
              f"erro mediano={t['erro_pct_mediano']}%")
    for a in painel["alertas"]:
        print(f"   ALERTA {a['niche_id']}: erro {a['razao']}x acima do historico")
    if len(por_mes) < 2:
        print("   (com um mes so nao ha tendencia — o valor aparece na proxima rodada)")


if __name__ == "__main__":
    main()
    sys.exit(0)
