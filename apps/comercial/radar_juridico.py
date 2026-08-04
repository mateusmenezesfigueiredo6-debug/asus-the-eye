"""RADAR JURÍDICO — o produto vendável da plataforma de direito.

Relatório semanal de leads reais extraídos dos diários oficiais municipais
(Querido Diário) para um nicho jurídico. Cada lead vem com data, município,
excerto do ato oficial e link para o PDF original — verificável pelo cliente.

Modelo de negócio: assinatura por nicho/região para escritórios de advocacia.
Exemplos de lead por nicho:
  recuperacao  → empresas em recuperação judicial (leads para insolvência)
  tributario   → execuções fiscais (leads para tributaristas)
  imobiliario  → desapropriações (leads para imobiliaristas)

Uso: python3 apps/comercial/radar_juridico.py <niche_id> [dias]
Saída: reports/commercial/radar_<niche_id>.html
"""
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
ONT = json.loads((BASE / "apps/comercial/ontologia.json").read_text(encoding="utf-8"))
API = ONT["fonte_sinal_externo"]["api"]


def gerar(niche_id: str, dias: int = 14) -> Path:
    nicho = next(n for n in ONT["nichos"] if n["niche_id"] == niche_id)
    termo = nicho["termo_sinal"]
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d")
    url = (f"{API}?querystring={urllib.parse.quote(chr(34)+termo+chr(34))}"
           f"&published_since={desde}&size=20&excerpt_size=380&number_of_excerpts=1")
    payload = json.loads(urllib.request.urlopen(url, timeout=30).read())
    total = payload.get("total_gazettes", 0)
    leads = payload.get("gazettes", [])

    cards = ""
    for g in leads:
        exc = (g.get("excerpts") or [""])[0].replace("\n", " ").strip()
        cards += f"""<div class=lead>
<div class=meta><b>{g['territory_name']} / {g['state_code']}</b> · {g['date']}</div>
<p>{exc[:380]}…</p>
<a href="{g['url']}" target=_blank>ver ato oficial completo (PDF) →</a></div>"""

    agora = datetime.now()
    html = f"""<!doctype html><meta charset=utf-8><title>Radar Jurídico — {niche_id}</title>
<style>
body{{font-family:Georgia,serif;max-width:820px;margin:0 auto;padding:32px;background:#fcfbf8;color:#1a1a1a}}
h1{{font-size:26px;margin-bottom:0}} .tag{{color:#8a6d1a;font-size:13px;letter-spacing:1px}}
.resumo{{background:#f4efe2;border-left:4px solid #8a6d1a;padding:14px 18px;margin:20px 0;font-size:15px}}
.lead{{background:#fff;border:1px solid #e2dccc;border-radius:8px;padding:16px 20px;margin:14px 0}}
.lead p{{font-size:14px;line-height:1.6;color:#333}}
.meta{{font-size:13px;color:#8a6d1a}}
a{{color:#8a6d1a}} .rodape{{font-size:12px;color:#777;margin-top:28px;border-top:1px solid #e2dccc;padding-top:12px}}
</style>
<div class=tag>RADAR JURÍDICO · EDIÇÃO {agora.strftime('%d/%m/%Y')}</div>
<h1>{nicho['objeto_juridico'].capitalize()}</h1>
<div class=resumo><b>{total:,}</b> menções a "{termo}" em diários oficiais municipais nos últimos {dias} dias.
Abaixo, os {len(leads)} atos mais relevantes — cada um com link para o documento oficial original.</div>
{cards}
<div class=rodape>Fonte: {ONT['fonte_sinal_externo']['nome']} \
({ONT['fonte_sinal_externo']['operador']}) — diários oficiais municipais, acesso público.
Relatório gerado automaticamente pela plataforma ASUS · cada lead é verificável no PDF oficial linkado.
Este material é inteligência de mercado, não constitui aconselhamento jurídico.</div>"""

    dest = BASE / f"reports/commercial/radar_{niche_id}.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    print(f"OK {dest} — {total:,} menções, {len(leads)} leads na edição")
    return dest


if __name__ == "__main__":
    nid = sys.argv[1] if len(sys.argv) > 1 else "recuperacao"
    dias = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    gerar(nid, dias)
