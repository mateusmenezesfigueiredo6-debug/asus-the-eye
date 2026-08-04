"""RADAR JURIDICO — o produto vendavel da plataforma de direito.

Relatorio periodico de leads reais extraidos dos diarios oficiais municipais
(Querido Diario) para um nicho juridico.

Qualidade do lead e o produto. O gerador nao entrega excerto bruto: para cada
nicho com padrao definido na ontologia, ele EXTRAI a entidade nomeada no ato
(empresa em recuperacao, executado fiscal, imovel desapropriado), DESCARTA
texto padrao de edital (exigencia de certidao negativa nao e lead) e DEDUPLICA
por entidade. O que sobra e o que um advogado usaria.

Uso: python3 apps/comercial/radar_juridico.py <niche_id> [dias]
Saida: reports/commercial/radar_<niche_id>.html
"""
import html as html_mod
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
ONT = json.loads((BASE / "apps/comercial/ontologia.json").read_text(encoding="utf-8"))
API = ONT["fonte_sinal_externo"]["api"]
MAX_LEADS = 12


def _limpar(texto: str) -> str:
    return " ".join(texto.split())


def _chave(nome: str) -> str:
    """Normaliza para deduplicar: sem acento, sem pontuacao, sem sufixo societario."""
    n = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().upper()
    # Sufixo societario aparece como S/A, S.A., SA ou S A — normalizar antes de
    # remover, senao a mesma empresa entra duas vezes na edicao.
    n = re.sub(r"[/.]", " ", n)
    n = re.sub(r"\b(LTDA|EIRELI|EPP|ME|S\s*A|SA)\b", " ", n)
    return re.sub(r"[^A-Z0-9]", "", n)[:28]


CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-\d{2}\b")


def sem_dado_pessoal(trecho: str) -> bool:
    """Edicao publica nao carrega CPF. Ato de origem segue linkado."""
    return not CPF.search(trecho)


def extrair(nicho: dict, gazettes: list) -> list[dict]:
    """Devolve leads com entidade identificada, sem ruido e sem repeticao."""
    rx_ent = nicho.get("regex_entidade")
    rx_ruido = nicho.get("regex_ruido")
    entidade = re.compile(rx_ent) if rx_ent else None
    ruido = re.compile(rx_ruido, re.I) if rx_ruido else None

    leads, vistos = [], set()
    for g in gazettes:
        for bruto in g.get("excerpts") or []:
            trecho = _limpar(bruto)
            if ruido and ruido.search(trecho):
                continue
            if not sem_dado_pessoal(trecho):
                continue
            nome = None
            if entidade:
                m = entidade.search(trecho)
                if not m:
                    continue
                nome = _limpar(m.group(1)).strip(" -–.,")
                if len(nome) < 5:
                    continue
            # Deduplicacao vale para todo nicho: com entidade, pela entidade;
            # sem entidade, pelo proprio texto — senao a edicao repete o mesmo
            # ato publicado em varios municipios.
            k = _chave(nome) if nome else _chave(trecho[:80])
            if k in vistos:
                continue
            vistos.add(k)
            leads.append({
                "entidade": nome,
                "trecho": trecho,
                "municipio": g["territory_name"],
                "uf": g["state_code"],
                "data": g["date"],
                "url": g["url"],
            })
            break  # um lead por publicacao
    return leads[:MAX_LEADS]


def buscar(nicho: dict, dias: int) -> tuple[list, int]:
    termo = nicho.get("busca_lead") or nicho["termo_sinal"]
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%d")
    url = (f"{API}?querystring={urllib.parse.quote(chr(34) + termo + chr(34))}"
           f"&published_since={desde}&size=60&excerpt_size=340&number_of_excerpts=2")
    payload = json.loads(urllib.request.urlopen(url, timeout=40).read())
    return payload.get("gazettes", []), payload.get("total_gazettes", 0)


def render(nicho: dict, leads: list, total: int, dias: int) -> str:
    termo = nicho.get("busca_lead") or nicho["termo_sinal"]
    e = html_mod.escape
    cards = ""
    for i, ld in enumerate(leads, 1):
        titulo = e(ld["entidade"]) if ld["entidade"] else f"{e(ld['municipio'])} / {e(ld['uf'])}"
        cards += f"""<article class=lead>
<div class=cab><span class=num>{i:02d}</span><h2>{titulo}</h2></div>
<div class=onde>{e(ld['municipio'])} · {e(ld['uf'])} · publicado em {e(ld['data'])}</div>
<p>{e(ld['trecho'][:330])}…</p>
<a class=selo href="{e(ld['url'])}" target=_blank rel=noopener>Conferir no diario oficial</a>
</article>"""
    if not leads:
        cards = ("<article class=lead><p>Nenhum caso novo com entidade identificada "
                 "nesta janela. Nao preenchemos a edicao com ruido: quando nao ha lead, "
                 "a edicao vem curta.</p></article>")

    agora = datetime.now()
    fonte = ONT["fonte_sinal_externo"]
    return f"""<!doctype html><html lang=pt-BR><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Radar Juridico — {e(nicho['objeto_juridico'])}</title>
<style>
:root{{--verde:#0E4B3A;--papel:#FAFAF7;--tinta:#1A1A18;--cinza:#6B6B65;
--linha:#E3E1D8;--carimbo:#B3261E;--branco:#FFF}}
*{{box-sizing:border-box}}
body{{font-family:Georgia,'Times New Roman',serif;background:var(--papel);
color:var(--tinta);margin:0;line-height:1.6}}
.capa{{background:var(--verde);color:#EDF5F1;padding:40px 6vw 30px}}
.orgao{{font-family:'Arial Narrow',Arial,sans-serif;font-size:12px;letter-spacing:4px;
text-transform:uppercase;opacity:.8}}
.capa h1{{font-family:'Arial Narrow',Arial,sans-serif;font-weight:700;
text-transform:uppercase;font-size:clamp(28px,6vw,44px);line-height:1.05;
margin:10px 0 8px;text-wrap:balance}}
.linha-edicao{{font-family:'Courier New',monospace;font-size:12.5px;opacity:.9}}
main{{max-width:760px;margin:0 auto;padding:0 6vw 60px}}
.sumario{{background:var(--branco);border:1px solid var(--linha);
border-left:4px solid var(--verde);padding:16px 20px;margin:24px 0 8px;font-size:15px}}
.sumario b{{color:var(--verde)}}
.lead{{background:var(--branco);border:1px solid var(--linha);
margin:14px 0;padding:18px 22px 16px}}
.cab{{display:flex;gap:12px;align-items:baseline}}
.num{{font-family:'Courier New',monospace;font-size:13px;color:var(--carimbo);
font-weight:700;padding-top:3px}}
.lead h2{{font-family:'Arial Narrow',Arial,sans-serif;text-transform:uppercase;
font-size:19px;letter-spacing:.5px;margin:0;color:var(--verde);text-wrap:balance}}
.onde{{font-family:'Arial Narrow',Arial,sans-serif;font-size:13px;color:var(--cinza);
margin:4px 0 0;padding-left:26px;letter-spacing:.5px}}
.lead p{{font-size:14px;color:#3A3A36;margin:12px 0 14px;padding-left:26px;
border-left:2px solid var(--linha);max-width:62ch}}
.selo{{display:inline-block;margin-left:26px;font-family:'Arial Narrow',Arial,sans-serif;
font-size:11.5px;letter-spacing:1.5px;text-transform:uppercase;color:var(--carimbo);
border:1.5px solid var(--carimbo);padding:5px 12px;text-decoration:none}}
.selo:hover,.selo:focus{{background:var(--carimbo);color:#fff}}
.rodape{{font-size:12px;color:var(--cinza);margin-top:32px;
border-top:1px solid var(--linha);padding-top:14px;max-width:62ch}}
</style>
<header class=capa>
<div class=orgao>Radar Juridico — Diarios Oficiais do Brasil</div>
<h1>{e(nicho['objeto_juridico'])}</h1>
<div class=linha-edicao>EDICAO DE {agora.strftime('%d/%m/%Y')} ·
JANELA DE {dias} DIAS · EXPRESSAO: "{e(termo.upper())}"</div>
</header>
<main>
<div class=sumario><b>{len(leads)} casos com parte identificada</b>, apurados
entre {total:,} publicacoes que citaram a expressao no periodo. Exigencias de
certidao e texto padrao de edital foram descartados — aqui so entra ato que
nomeia alguem.</div>
{cards}
<div class=rodape>Fonte: {e(fonte['nome'])} ({e(fonte['operador'])}), diarios
oficiais municipais de acesso publico. Cada caso remete ao PDF de origem para
conferencia. Inteligencia de mercado; nao constitui aconselhamento juridico.</div>
</main></html>"""


def gerar(niche_id: str, dias: int = 14) -> Path:
    nicho = next(n for n in ONT["nichos"] if n["niche_id"] == niche_id)
    gazettes, total = buscar(nicho, dias)
    leads = extrair(nicho, gazettes)
    dest = BASE / f"reports/commercial/radar_{niche_id}.html"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(render(nicho, leads, total, dias), encoding="utf-8")
    print(f"OK {dest.name} — {len(leads)} leads com entidade / {total:,} publicacoes")
    return dest


if __name__ == "__main__":
    nid = sys.argv[1] if len(sys.argv) > 1 else "recuperacao"
    gerar(nid, int(sys.argv[2]) if len(sys.argv) > 2 else 14)
