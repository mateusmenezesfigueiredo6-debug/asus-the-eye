"""Colheita de sinal externo real por nicho — padrão Palantir: dado com linhagem.

Consulta o Querido Diário (API aberta, diários oficiais municipais) com o termo
de cada nicho da ontologia e registra o volume de menções como proxy de demanda
jurídica real. Cada medição carrega proveniência completa: fonte, URL, termo,
timestamp UTC e SHA-256 do payload — auditável de ponta a ponta.

Uso: python3 apps/comercial/sinal_externo.py
Saída: reports/commercial/sinais_externos.json
"""
import hashlib
import json
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
ONTOLOGIA = json.loads((BASE / "apps/comercial/ontologia.json").read_text(encoding="utf-8"))
API = ONTOLOGIA["fonte_sinal_externo"]["api"]


JANELA_DIAS = 30  # janela recente: evita o teto de 10.000 da API e mede demanda ATUAL


def medir(nicho: dict) -> dict:
    termo = nicho["termo_sinal"]
    from datetime import timedelta
    desde = (datetime.now(timezone.utc) - timedelta(days=JANELA_DIAS)).strftime("%Y-%m-%d")
    url = (f"{API}?querystring={urllib.parse.quote(termo)}"
           f"&published_since={desde}&size=1")
    try:
        raw = urllib.request.urlopen(url, timeout=25).read()
        payload = json.loads(raw)
        total = payload.get("total_gazettes", 0)
        return {
            "niche_id": nicho["niche_id"],
            "termo": termo,
            "mencoes_diarios_oficiais": total,
            "proveniencia": {
                "fonte": ONTOLOGIA["fonte_sinal_externo"]["nome"],
                "url_consulta": url,
                "coletado_em_utc": datetime.now(timezone.utc).isoformat(),
                "sha256_payload": hashlib.sha256(raw).hexdigest(),
            },
        }
    except Exception as e:  # sinal indisponível é registrado, nunca inventado
        return {"niche_id": nicho["niche_id"], "termo": termo,
                "mencoes_diarios_oficiais": None, "erro": str(e)[:80]}


def main() -> None:
    with ThreadPoolExecutor(max_workers=8) as pool:
        sinais = list(pool.map(medir, ONTOLOGIA["nichos"]))
    ok = [s for s in sinais if s["mencoes_diarios_oficiais"] is not None]
    out = {
        "gerado_em_utc": datetime.now(timezone.utc).isoformat(),
        "fonte": ONTOLOGIA["fonte_sinal_externo"],
        "cobertura": f"{len(ok)}/{len(sinais)} nichos com sinal",
        "sinais": sorted(sinais, key=lambda s: -(s["mencoes_diarios_oficiais"] or 0)),
    }
    dest = BASE / "reports/commercial/sinais_externos.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK {dest} — {out['cobertura']}")
    for s in out["sinais"][:5]:
        print(f"   {s['niche_id']:<20} {s['mencoes_diarios_oficiais']}")


if __name__ == "__main__":
    main()
