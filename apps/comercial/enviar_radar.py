"""Entrega automática do Radar Jurídico — o produto operando sozinho.

Para cada assinante ativo/trial: gera a edição fresca de cada nicho assinado
e envia por e-mail (HTML no corpo).

SEGURANÇA DE CREDENCIAL: o script NUNCA contém senha. Ele lê SMTP de
~/.config/radar/env (arquivo que VOCÊ preenche). Sem credencial configurada,
roda em MODO CAIXA DE SAÍDA: grava cada e-mail pronto como .eml em
reports/commercial/outbox/ — nada é enviado, nada é perdido.

Formato de ~/.config/radar/env (chmod 600):
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USER=seu-email@gmail.com
    SMTP_PASS=senha-de-app-de-16-letras

Uso: python3 apps/comercial/enviar_radar.py            # entrega (ou outbox)
     python3 apps/comercial/enviar_radar.py --dry-run  # só mostra o plano
"""
import json
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE / "apps/comercial"))
from radar_juridico import gerar  # noqa: E402

ENV = Path.home() / ".config/radar/env"
OUTBOX = BASE / "reports/commercial/outbox"


def carregar_smtp() -> dict | None:
    if not ENV.exists():
        return None
    cfg = {}
    for linha in ENV.read_text().splitlines():
        if "=" in linha and not linha.strip().startswith("#"):
            k, v = linha.split("=", 1)
            cfg[k.strip()] = v.strip()
    obrigatorias = {"SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS"}
    if not obrigatorias <= cfg.keys():
        return None
    if "COLOQUE" in cfg["SMTP_PASS"] or not cfg["SMTP_PASS"]:
        return None  # placeholder ainda não preenchido → modo outbox
    return cfg


def montar_email(destinatario: str, nome: str, nicho: str, html: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = f"Radar Jurídico — {nicho} — edição {datetime.now().strftime('%d/%m/%Y')}"
    msg["To"] = destinatario
    msg.set_content(f"Olá {nome}, sua edição do Radar Jurídico ({nicho}) segue em HTML.")
    msg.add_alternative(html, subtype="html")
    return msg


def main(dry_run: bool = False) -> None:
    reg = json.loads((BASE / "apps/comercial/assinantes.json").read_text(encoding="utf-8"))
    ativos = [a for a in reg["assinantes"] if a["status"] in ("ativo", "trial")]
    smtp = carregar_smtp()
    modo = "SMTP real" if smtp else "OUTBOX (sem credencial — nada será enviado)"
    print(f"Assinantes: {len(ativos)} · modo: {modo}")

    enviados = 0
    for a in ativos:
        for nicho in a["nichos"]:
            if dry_run:
                print(f"  [plano] {a['email']} ← edição de {nicho}")
                continue
            caminho = gerar(nicho, 14)
            html = caminho.read_text(encoding="utf-8")
            msg = montar_email(a["email"], a["nome"], nicho, html)
            if smtp:
                try:
                    with smtplib.SMTP(smtp["SMTP_HOST"], int(smtp["SMTP_PORT"])) as s:
                        s.starttls()
                        s.login(smtp["SMTP_USER"], smtp["SMTP_PASS"])
                        s.send_message(msg, from_addr=smtp["SMTP_USER"])
                    print(f"  [ENVIADO] {a['email']} ← {nicho}")
                except smtplib.SMTPException as e:
                    smtp = None  # credencial falhou → resto do lote vai p/ outbox
                    print(f"  [!] SMTP falhou ({e.__class__.__name__}) — caindo para outbox")
            if not smtp:
                OUTBOX.mkdir(parents=True, exist_ok=True)
                dest = OUTBOX / f"{datetime.now().strftime('%Y%m%d')}_{nicho}_{a['email'].split('@')[0]}.eml"
                dest.write_bytes(bytes(msg))
                print(f"  [outbox] {dest.name}")
            enviados += 1
    print(f"Total: {enviados} edições {'planejadas' if dry_run else 'processadas'}")


if __name__ == "__main__":
    main(dry_run="--dry-run" in sys.argv)
