# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Etapa 2 do ciclo — serie historica de demanda juridica por nicho.

Reconstroi, a partir do Querido Diario, a contagem mensal de publicacoes que
citam a expressao de cada nicho. Essa serie e a materia-prima da previsao
(etapa 3) e do backtest (etapa 4).

Cada ponto guarda a janela consultada e a URL exata, para auditoria.

Uso: python3 apps/comercial/serie_historica.py [meses]
Saida: reports/commercial/serie_mensal.json
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
ONT = json.loads((BASE / "apps/comercial/ontologia.json").read_text(encoding="utf-8"))
API = ONT["fonte_sinal_externo"]["api"]
MESES_PADRAO = 36


def meses_ate(hoje: date, quantos: int) -> list[tuple[str, str, str]]:
    """Devolve [(rotulo, inicio, fim)] dos ultimos `quantos` meses fechados."""
    janelas = []
    ano, mes = hoje.year, hoje.month
    for _ in range(quantos):
        mes -= 1
        if mes == 0:
            mes, ano = 12, ano - 1
        ini = date(ano, mes, 1)
        # published_until e INCLUSIVO: usar o dia 1 do mes seguinte contaria
        # esse dia em dois meses. O fim e o ultimo dia do proprio mes.
        prox = date(ano + (mes == 12), (mes % 12) + 1, 1)
        fim = prox - timedelta(days=1)
        janelas.append((f"{ano}-{mes:02d}", ini.isoformat(), fim.isoformat()))
    return list(reversed(janelas))


def contar(termo: str, ini: str, fim: str, tentativas: int = 4) -> tuple[int | None, str]:
    """Consulta com retentativa e espera crescente — a API limita rajadas."""
    url = (
        f"{API}?querystring={urllib.parse.quote(chr(34) + termo + chr(34))}"
        f"&published_since={ini}&published_until={fim}&size=1"
    )
    for n in range(tentativas):
        try:
            payload = json.loads(urllib.request.urlopen(url, timeout=40).read())
            return payload.get("total_gazettes"), url
        except Exception:
            if n < tentativas - 1:
                time.sleep(1.5 * (n + 1))
    return None, url


def coletar(quantos: int = MESES_PADRAO) -> dict:
    janelas = meses_ate(date.today(), quantos)
    tarefas = [(n, j) for n in ONT["nichos"] for j in janelas]

    def uma(par):
        nicho, (rotulo, ini, fim) = par
        termo = nicho.get("busca_lead") or nicho["termo_sinal"]
        total, url = contar(termo, ini, fim)
        return nicho["niche_id"], rotulo, total, url

    with ThreadPoolExecutor(max_workers=3) as pool:
        brutos = list(pool.map(uma, tarefas))

    series: dict[str, dict] = {}
    for nid, rotulo, total, url in brutos:
        s = series.setdefault(nid, {"pontos": {}, "urls": {}})
        s["pontos"][rotulo] = total
        s["urls"][rotulo] = url

    saida = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "fonte": ONT["fonte_sinal_externo"]["nome"],
        "granularidade": "mensal",
        "meses": [j[0] for j in janelas],
        "series": series,
    }
    dest = BASE / "reports/commercial/serie_mensal.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")

    completos = sum(1 for s in series.values() if all(v is not None for v in s["pontos"].values()))
    print(f"OK {dest.name} — {len(series)} nichos x {len(janelas)} meses ({completos} series completas)")
    for nid, s in list(series.items())[:5]:
        vals = [s["pontos"][m] for m in saida["meses"][-6:]]
        print(f"   {nid:<20} ultimos 6 meses: {vals}")
    return saida


if __name__ == "__main__":
    coletar(int(sys.argv[1]) if len(sys.argv) > 1 else MESES_PADRAO)
