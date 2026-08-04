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
    for i, g in enumerate(leads, 1):
        exc = (g.get("excerpts") or [""])[0].replace("\n", " ").strip()
        cards += f"""<article class=lead>
<div class=protocolo><span class=num>Nº {i:03d}/{datetime.now().strftime('%Y')}</span>
<span class=onde>{g['territory_name']} · {g['state_code']}</span>
<span class=quando>{g['date']}</span></div>
<p>{exc[:380]}…</p>
<div class=acoes><a class=selo href="{g['url']}" target=_blank rel=noopener>
VERIFICAR NO PDF OFICIAL ↗</a></div>
</article>"""

    agora = datetime.now()
    fonte_nome = ONT["fonte_sinal_externo"]["nome"]
    fonte_op = ONT["fonte_sinal_externo"]["operador"]
    html = f"""<!doctype html><meta charset=utf-8><title>Radar Jurídico — {niche_id}</title>
<style>
:root{{--verde:#0E4B3A;--verde2:#0B3D30;--papel:#FAFAF7;--tinta:#1A1A18;
--cinza:#6B6B65;--linha:#DDDDD3;--carimbo:#B3261E;--branco:#FFFFFF}}
*{{box-sizing:border-box}}
body{{font-family:Georgia,'Times New Roman',serif;background:var(--papel);color:var(--tinta);
margin:0;line-height:1.55}}
.capa{{background:var(--verde);color:#EDF5F1;padding:34px 5vw 26px}}
.capa .orgao{{font-family:'Arial Narrow',Arial,sans-serif;font-size:13px;letter-spacing:4px;
text-transform:uppercase;opacity:.85}}
.capa h1{{font-family:'Arial Narrow',Arial,sans-serif;font-weight:700;text-transform:uppercase;
font-size:clamp(30px,6vw,46px);letter-spacing:1px;margin:6px 0 4px;text-wrap:balance}}
.capa .edicao{{font-family:'Courier New',monospace;font-size:13px;opacity:.9}}
main{{max-width:780px;margin:0 auto;padding:26px 5vw 60px}}
.sumario{{border:1px solid var(--linha);background:var(--branco);padding:16px 20px;margin:0 0 6px;
font-size:15.5px}}
.sumario b{{font-size:22px;color:var(--verde)}}
.lead{{background:var(--branco);border:1px solid var(--linha);border-left:4px solid var(--verde);
margin:16px 0;padding:0 20px 14px}}
.protocolo{{display:flex;gap:16px;flex-wrap:wrap;align-items:baseline;
border-bottom:1px dashed var(--linha);padding:12px 0 9px;font-family:'Courier New',monospace;
font-size:12.5px;color:var(--cinza)}}
.protocolo .num{{color:var(--verde);font-weight:700}}
.protocolo .onde{{color:var(--tinta)}}
.lead p{{font-size:14.5px;margin:12px 0 10px;max-width:65ch}}
.acoes{{text-align:right}}
.selo{{display:inline-block;font-family:'Arial Narrow',Arial,sans-serif;font-size:11.5px;
letter-spacing:1.5px;color:var(--carimbo);border:1.5px solid var(--carimbo);
padding:4px 10px;text-decoration:none;transform:rotate(-1deg)}}
.selo:hover,.selo:focus{{background:var(--carimbo);color:#fff;outline:2px solid var(--verde)}}
.rodape{{font-size:12px;color:var(--cinza);margin-top:30px;border-top:1px solid var(--linha);
padding-top:12px}}
@media(prefers-reduced-motion:no-preference){{.lead{{transition:box-shadow .15s}}
.lead:hover{{box-shadow:0 2px 10px rgba(14,75,58,.12)}}}}
</style>
<header class=capa>
<div class=orgao>Radar Jurídico · Inteligência de Diários Oficiais</div>
<h1>{nicho['objeto_juridico']}</h1>
<div class=edicao>EDIÇÃO DE {agora.strftime('%d/%m/%Y')} · JANELA {dias} DIAS ·
TERMO VIGIADO: "{termo.upper()}"</div>
</header>
<main>
<div class=sumario><b>{total:,}</b> atos oficiais mencionaram "{termo}" no período.
Os {len(leads)} mais relevantes seguem abaixo como protocolos — cada um verificável
no documento oficial de origem.</div>
{cards}
<div class=rodape>Fonte: {fonte_nome} ({fonte_op}) — diários oficiais municipais, acesso
público. Cada protocolo linka o PDF oficial de origem. Inteligência de mercado;
não constitui aconselhamento jurídico.</div>
</main>"""

    dest = BASE / f"reports/commercial/radar_{niche_id}.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    print(f"OK {dest} — {total:,} menções, {len(leads)} leads na edição")
    return dest


if __name__ == "__main__":
    nid = sys.argv[1] if len(sys.argv) > 1 else "recuperacao"
    dias = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    gerar(nid, dias)
