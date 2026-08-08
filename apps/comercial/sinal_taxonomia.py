"""Sinal externo para as 145 areas da taxonomia — nao so o recorte de 15.

O vertical comercial opera 15 nichos. A taxonomia do projeto tem 145 areas em
22 grupos, e todas ja possuem alias PT-BR de alta confianca em
`data/legal-taxonomy/legal_area_aliases.json`. Isso permite medir demanda real
para a taxonomia inteira, e nao apenas para a fatia comercial.

ESCOLHA DO TERMO: cada area tem varios aliases e a escolha muda tudo. Medido:
"direito tributario" retorna 0 enquanto "tributario" retorna 7; "orcamento
publico" retorna 0 enquanto "lrf" retorna 275. Heuristica de tamanho falha.

O criterio adotado e consultar TODOS os aliases da area e ficar com o de maior
retorno, registrando a contagem de cada um. Isso custa mais consultas e entrega
dado auditavel: quem revisar ve por que aquele termo venceu.

SINALIZACAO DE RUIDO: area cuja contagem passa o percentil 95 provavelmente
casou com termo generico. Ela e marcada `suspeita_termo_generico` em vez de ser
descartada em silencio — quem decide se o termo serve e revisao humana.

Uso: python3 apps/comercial/sinal_taxonomia.py [dias]
Saida: reports/commercial/sinal_taxonomia.json
"""

import json
import statistics
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
TAX = json.loads((BASE / "data/legal-taxonomy/legal_areas.master.json").read_text(encoding="utf-8"))
ALIAS = json.loads((BASE / "data/legal-taxonomy/legal_area_aliases.json").read_text(encoding="utf-8"))
API = "https://api.queridodiario.ok.org.br/gazettes"
DIAS_PADRAO = 30


def aliases_de(area_id: str) -> list[str]:
    return ALIAS["aliases"].get(area_id) or []


def contar(termo: str, desde: str, tentativas: int = 3) -> tuple[int | None, str]:
    url = f"{API}?querystring={urllib.parse.quote(chr(34) + termo + chr(34))}&published_since={desde}&size=1"
    for n in range(tentativas):
        try:
            with urllib.request.urlopen(url, timeout=40) as r:
                return json.loads(r.read()).get("total_gazettes"), url
        except Exception:
            if n < tentativas - 1:
                time.sleep(1.5 * (n + 1))
    return None, url


def main(dias: int = DIAS_PADRAO) -> None:
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d")
    areas = TAX["areas"]
    print(f"coletando sinal de {len(areas)} areas, janela de {dias} dias")

    def uma(a):
        aliases = aliases_de(a["legal_area_id"])
        if not aliases:
            return {
                "legal_area_id": a["legal_area_id"],
                "name_en": a["name_en"],
                "group": a["group"],
                "termo": None,
                "mencoes": None,
                "erro": "sem alias",
            }
        por_alias, url_venc = {}, None
        for t in aliases:
            n, u = contar(t, desde)
            por_alias[t] = n
            if n is not None and n == max(v for v in por_alias.values() if v is not None):
                url_venc = u
        validos = {t: n for t, n in por_alias.items() if n is not None}
        if not validos:
            return {
                "legal_area_id": a["legal_area_id"],
                "name_en": a["name_en"],
                "group": a["group"],
                "termo": None,
                "mencoes": None,
                "por_alias": por_alias,
                "erro": "todas as consultas falharam",
            }
        vencedor = max(validos, key=lambda t: validos[t])
        return {
            "legal_area_id": a["legal_area_id"],
            "name_en": a["name_en"],
            "group": a["group"],
            "termo": vencedor,
            "mencoes": validos[vencedor],
            "por_alias": por_alias,
            "aliases_testados": len(aliases),
            "url": url_venc,
        }

    with ThreadPoolExecutor(max_workers=3) as pool:
        pontos = list(pool.map(uma, areas))

    validos = [p["mencoes"] for p in pontos if p.get("mencoes") is not None]
    corte = statistics.quantiles(validos, n=20)[18] if len(validos) >= 20 else None
    for p in pontos:
        m = p.get("mencoes")
        p["suspeita_termo_generico"] = bool(corte and m is not None and m > corte)

    por_grupo: dict[str, list] = {}
    for p in pontos:
        if p.get("mencoes") is not None:
            por_grupo.setdefault(p["group"], []).append(p["mencoes"])

    saida = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "janela_dias": dias,
        "fonte": "Querido Diario (Open Knowledge Brasil)",
        "criterio_termo": (
            "todos os aliases da area sao consultados; vence o de "
            "maior retorno; a contagem de cada um fica em por_alias"
        ),
        "corte_suspeita_p95": corte,
        "cobertura": f"{len(validos)}/{len(areas)}",
        "areas": sorted(pontos, key=lambda p: -(p.get("mencoes") or 0)),
        "por_grupo": {
            g: {"areas": len(v), "mencoes_totais": sum(v), "mediana": statistics.median(v)}
            for g, v in sorted(por_grupo.items())
        },
    }
    dest = BASE / "reports/commercial/sinal_taxonomia.json"
    dest.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")

    susp = sum(1 for p in pontos if p["suspeita_termo_generico"])
    print(f"OK {dest.name} — {len(validos)}/{len(areas)} com sinal, {susp} marcadas como termo possivelmente generico")
    print("\n  maiores demandas (sem as suspeitas):")
    limpos = [p for p in saida["areas"] if not p["suspeita_termo_generico"] and p.get("mencoes")]
    for p in limpos[:10]:
        print(f'    {p["mencoes"]:>6}  {p["legal_area_id"][:44]:<46} "{p["termo"]}"')
    print("\n  grupos por volume:")
    for g, v in sorted(saida["por_grupo"].items(), key=lambda x: -x[1]["mencoes_totais"])[:8]:
        print(f"    {v['mencoes_totais']:>8}  {g:<34} ({v['areas']} areas)")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else DIAS_PADRAO)
