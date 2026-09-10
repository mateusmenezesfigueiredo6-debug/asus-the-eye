# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Painel /garantias — o estado das oito garantias do titular, medido, num só lugar.

Ordem do titular (04/09/2026): "tudo no documento e no dash blockchain com
alertas de uso". Este painel é a parte "dash": corrente, vigia de acesso,
sentinela, e-mail, permissões, rede, vermelhos e âncoras — cada um com o
número medido e a data. Estático, sem script, sem rede: pode abrir em qualquer
navegador sem que nada saia da máquina. Nunca imprime CPF nem conteúdo de elo.

A coleta (`coletar`) roda comandos locais; a renderização (`garantias_page`)
recebe o snapshot pronto — assim o teste renderiza sem tocar o sistema.
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .tema import pagina

FINGERPRINT = "3e1ec5903edafb477a8c0f1b75dd09d667c5d9aa1557e76c1641324ed6e7d3f5"
TITULAR = "Mateus Menezes Figueiredo"


def _cmd(*args: str, timeout: int = 10) -> str:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:  # noqa: BLE001 — painel nunca cai por comando ausente
        return ""


def _linhas(p: Path) -> int:
    try:
        return sum(1 for _ in p.open("rb"))
    except OSError:
        return 0


def _sha(p: Path) -> str | None:
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def coletar(home: Path | None = None, *, rodar_comandos: bool = True) -> dict[str, Any]:
    """Lê o estado real. Só leitura; nada é alterado."""
    H = home or Path.home()
    E = H / ".the-eye"
    motor = H / "pegasus/asus_the_eye"
    ledger = motor / "reports/benchmark/ledger.jsonl"

    # corrente
    integra: str = "não verificado"
    ultimos: list[dict[str, Any]] = []
    if ledger.exists():
        try:
            from asus_theye.audit.ledger import verify_ledger

            integra = "íntegra" if verify_ledger(ledger) else "QUEBRADA"
        except Exception:  # noqa: BLE001
            integra = "não verificado"
        try:
            for l in ledger.read_text(encoding="utf-8").splitlines()[-6:]:
                e = json.loads(l)
                ultimos.append({"seq": e.get("sequence"), "ts": str(e.get("timestamp", ""))[:19], "event": e.get("event", "")})
        except Exception:  # noqa: BLE001
            pass

    # serviços
    vigia = _cmd("systemctl", "--user", "is-active", "the-eye-vigia-acesso") if rodar_comandos else "?"
    sentinela = _cmd("systemctl", "--user", "is-active", "the-eye-sentinela") if rodar_comandos else "?"
    vlog = E / "vigia-acesso.log"
    vtxt = vlog.read_text(encoding="utf-8", errors="ignore") if vlog.exists() else ""
    baseline = next((l for l in reversed(vtxt.splitlines()) if "baseline" in l), "")

    # e-mail
    fila = len(list((E / "emails-pendentes").glob("*.eml.txt"))) if (E / "emails-pendentes").exists() else 0

    # permissões e rede
    protegidos = [E, H / "Área de trabalho/PORTAL-CIVICO-2026", H / "Área de trabalho/AGENTES-THE-EYE", H / ".claude/agents"]
    abertos = 0
    for raiz in protegidos:
        if raiz.exists():
            for p in raiz.rglob("*"):
                try:
                    # lstat: symlink de venv para /usr/bin é 755 lá, não aqui
                    if p.is_file() and not p.is_symlink() and (p.lstat().st_mode & 0o077):
                        abertos += 1
                except OSError:
                    pass
    fora: list[str] = []
    if rodar_comandos:
        for l in _cmd("ss", "-tln").splitlines()[1:]:
            partes = l.split()
            if len(partes) >= 4 and not partes[3].startswith(("127.", "[::1]")):
                fora.append(partes[3])
    portas_eye = [l.split()[3] for l in _cmd("ss", "-tln").splitlines()[1:] if rodar_comandos and any(f":{p}" in l for p in ("3210", "3211", "3220", "3230", "3240", "3250"))]

    # vermelhos
    conn = motor / "data/source-graph/connectors.json"
    ligados = total = 0
    if conn.exists():
        try:
            cs = json.loads(conn.read_text())["connectors"]
            total, ligados = len(cs), sum(1 for c in cs if c.get("enabled"))
        except Exception:  # noqa: BLE001
            pass

    # âncoras e termo
    ots = bool(shutil.which("ots")) or (motor / ".venv/bin/ots").exists()
    onchain = os.environ.get("AUTORIZADO_ONCHAIN") == "1"
    ult_ancora = next((u for u in reversed(ultimos) if "ancor" in u["event"]), None)
    termo = next(iter((H / "Área de trabalho/PORTAL-CIVICO-2026").glob("TERMO-*.md")), None) if (H / "Área de trabalho/PORTAL-CIVICO-2026").exists() else None

    achados_p = E / "garantias-achados.json"
    achados = json.loads(achados_p.read_text()) if achados_p.exists() else None

    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "corrente": {"elos": _linhas(ledger), "integridade": integra, "ultimos": ultimos,
                     "vigilia": _linhas(E / "vigilia-blockchain.jsonl"), "sessoes": _linhas(E / "registro-sessoes.jsonl")},
        "vigia": {"estado": vigia, "baseline": baseline[-60:], "imediatos": vtxt.count("IMEDIATO"), "digests": vtxt.count(" digest ")},
        "sentinela": sentinela,
        "email": {"smtp": (E / "smtp.env").exists(), "fila": fila},
        "permissoes": {"abertos": abertos},
        "rede": {"fora_loopback": fora, "portas_eye": portas_eye},
        "vermelhos": {"conectores_ligados": ligados, "conectores_total": total},
        "ancoras": {"ots_instalado": ots, "onchain_autorizada": onchain, "ultima": ult_ancora},
        "termo": {"arquivo": termo.name if termo else None, "sha256": _sha(termo) if termo else None},
        "achados": achados,
    }


def _cor(ok: bool | None) -> str:
    return "#2e7d32" if ok else ("#c62828" if ok is False else "#9e9e9e")


def _card(titulo: str, valor: str, ok: bool | None, nota: str = "") -> str:
    return (
        f'<div class="card" style="border-left:5px solid {_cor(ok)}"><div class="t">{html.escape(titulo)}</div>'
        f'<div class="v">{html.escape(valor)}</div><div class="n">{html.escape(nota)}</div></div>'
    )


def garantias_page(s: dict[str, Any]) -> str:
    c, v, e, r, a, t = s["corrente"], s["vigia"], s["email"], s["rede"], s["ancoras"], s["termo"]
    cards = [
        _card("Corrente", f'{c["elos"]} elos · {c["integridade"]}', c["integridade"] == "íntegra", f'vigília {c["vigilia"]} · sessões {c["sessoes"]}'),
        _card("Vigia de acesso", v["estado"], v["estado"] == "active", f'{v["imediatos"]} imediatos · {v["digests"]} digests · {v["baseline"]}'),
        _card("Sentinela de portas", s["sentinela"], s["sentinela"] == "active", "vigia portas fora de loopback"),
        _card("E-mail de alerta", "configurado" if e["smtp"] else "SEM smtp.env", e["smtp"], f'{e["fila"]} alerta(s) na fila' + ("" if e["smtp"] else " — só o titular preenche")),
        _card("Permissões", f'{s["permissoes"]["abertos"]} arquivo(s) legível(is) por outros', s["permissoes"]["abertos"] == 0, "conjunto protegido: .the-eye, PORTAL-CIVICO, AGENTES, agents"),
        _card("Portas THE EYE", ", ".join(r["portas_eye"]) or "nenhuma de pé", all(p.startswith("127.") for p in r["portas_eye"]) if r["portas_eye"] else None, f'{len(r["fora_loopback"])} porta(s) do sistema fora de loopback'),
        _card("Conectores ligados", f'{s["vermelhos"]["conectores_ligados"]}/{s["vermelhos"]["conectores_total"]}', s["vermelhos"]["conectores_ligados"] == 0, "estágio 1 exige zero — ligar é ato do titular"),
        _card("Âncora externa", ("OTS instalado" if a["ots_instalado"] else "OTS ausente") + " · on-chain " + ("autorizada" if a["onchain_autorizada"] else "não autorizada"), None, f'última: elo {a["ultima"]["seq"]} {a["ultima"]["ts"]}' if a["ultima"] else "nenhum elo de ancoragem nos últimos 6"),
        _card("Termo de exclusividade", t["arquivo"] or "ainda não redigido", bool(t["arquivo"]), (t["sha256"] or "")[:32] + ("…" if t["sha256"] else "aguarda parecer jurídico")),
    ]
    elos = "".join(f'<tr><td>{u["seq"]}</td><td>{html.escape(u["ts"])}</td><td>{html.escape(u["event"])}</td></tr>' for u in reversed(c["ultimos"]))
    fora = "".join(f"<li>{html.escape(p)}</li>" for p in r["fora_loopback"]) or "<li>nenhuma</li>"
    ach = ""
    if s["achados"]:
        linhas = "".join(
            f'<tr><td style="color:{_cor(x.get("gravidade") == "verde")}">{html.escape(x.get("gravidade", ""))}</td>'
            f'<td>{html.escape(x.get("dimensao", ""))}</td><td>{html.escape(x.get("titulo", ""))}</td>'
            f'<td>{html.escape(x.get("quem_resolve", ""))}</td><td><code>{html.escape(x.get("comando") or "")}</code></td></tr>'
            for x in s["achados"]
        )
        ach = f"<h2>Achados da auditoria (8 dimensões, refutados por 2 céticos)</h2><table><tr><th>grav.</th><th>dimensão</th><th>achado</th><th>quem</th><th>comando</th></tr>{linhas}</table>"
    corpo = f"""
<style>.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}}.card{{background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px 12px}}.card .t{{font-size:11px;color:#555;text-transform:uppercase}}.card .v{{font-size:16px;font-weight:700;margin:4px 0}}.card .n{{font-size:11px;color:#666}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{border:1px solid #ddd;padding:4px 6px;text-align:left}}th{{background:#eef3fb}}code{{font-size:11px}}</style>
<p><b>Titular:</b> {TITULAR} · <b>fingerprint:</b> <code>{FINGERPRINT}</code> · gerado {html.escape(s["gerado_em"])} · estático, sem script, sem rede</p>
<div class="grid">{"".join(cards)}</div>
<h2>Últimos elos (sem conteúdo)</h2><table><tr><th>seq</th><th>quando</th><th>evento</th></tr>{elos}</table>
<h2>Portas do sistema fora de loopback</h2><ul>{fora}</ul>
{ach}
<p style="font-size:11px;color:#666">O que vale como prova: a corrente (hash encadeado) prova ordem e integridade local; a âncora externa (OpenTimestamps sobre Bitcoin, ou carimbo ICP-Brasil) prova a data para quem não confia nesta máquina; o termo prova as condições de uso — e só vincula quem o aceita.</p>
"""
    return pagina(titulo="ASUS THE EYE — Garantias", corpo="<h1>GARANTIAS</h1><p class='lede'>as oito garantias do titular, medidas</p>" + corpo, rota="/garantias", estatico=True)


def gerar(destino: Path | None = None) -> Path:
    destino = destino or Path("dist/garantias.html")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(garantias_page(coletar()), encoding="utf-8")
    destino.chmod(0o600)
    return destino


if __name__ == "__main__":
    print(gerar())
