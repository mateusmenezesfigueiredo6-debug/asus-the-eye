# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Diagnóstico honesto da plataforma em um comando, sem rede."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from asus_theye.audit.anchor import eventos_sem_ancora
from asus_theye.audit.schema import verify_chain
from asus_theye.markets.auditoria import _fingerprint
from asus_theye.markets.live import carregar_registro

TITULAR = "Mateus Menezes Figueiredo"


def _item(ok: bool, detalhe: str, como_corrigir: str) -> dict[str, Any]:
    return {"ok": ok, "detalhe": detalhe, "como_corrigir": como_corrigir}


def _ler_jsonl(caminho: Path) -> list[dict[str, Any]]:
    eventos: list[dict[str, Any]] = []
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), start=1):
        if not linha.strip():
            continue
        valor = json.loads(linha)
        if not isinstance(valor, dict):
            raise ValueError(f"{caminho}:{numero} não é um objeto JSON")
        eventos.append(valor)
    return eventos


def _ler_chave_local(caminho: Path) -> bytes:
    try:
        return bytes.fromhex(caminho.read_text(encoding="utf-8").strip())
    except ValueError as exc:
        raise ValueError(f"{caminho} não contém hex válido") from exc


def _resumo_corrente(eventos_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]] | None]:
    if not eventos_path.exists():
        return (
            _item(
                False,
                f"corrente ausente: {eventos_path}",
                "gere ou recupere reports/markets/eventos.jsonl antes de validar a plataforma",
            ),
            None,
        )
    try:
        eventos = _ler_jsonl(eventos_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return (
            _item(
                False,
                f"corrente ilegível: {exc}",
                "corrija o JSONL versionado e mantenha um objeto JSON por linha em reports/markets/eventos.jsonl",
            ),
            None,
        )
    ok = verify_chain(eventos)
    return (
        _item(
            ok,
            f"{len(eventos)} evento(s); verify_chain={'ok' if ok else 'falhou'}",
            "ressincronize a corrente a partir de uma cópia íntegra "
            "ou investigue o evento com hash/encadeamento corrompido",
        ),
        eventos,
    )


def _resumo_chave(chave_path: Path, fingerprint_path: Path) -> dict[str, Any]:
    if not chave_path.exists():
        return _item(
            False,
            f"chave ausente: {chave_path}",
            "restaure reports/audit/pseudonimos.key da máquina de origem; nunca gere outra para a mesma corrente",
        )
    if not fingerprint_path.exists():
        return _item(
            False,
            f"fingerprint ausente: {fingerprint_path}",
            "recupere reports/markets/chave.fingerprint versionado junto da corrente original",
        )
    try:
        atual = _fingerprint(_ler_chave_local(chave_path))
        gravada = fingerprint_path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        return _item(
            False,
            f"não foi possível ler a chave/fingerprint: {exc}",
            "corrija o arquivo da chave (hex) e a fingerprint versionada, sem expor a chave em logs",
        )
    ok = bool(gravada) and atual == gravada
    if not gravada:
        detalhe = f"fingerprint vazia; chave ativa {atual[:16]}…"
    elif ok:
        detalhe = f"impressão {atual[:16]}… confere"
    else:
        detalhe = f"impressão ativa {atual[:16]}… difere da versionada {gravada[:16]}…"
    return _item(
        ok,
        detalhe,
        "copie a chave original da corrente ou defina THE_EYE_AUDIT_KEY "
        "com a chave correta antes de selar novos eventos",
    )


def _resumo_prova_temporal(eventos_path: Path, ancoras_path: Path) -> dict[str, Any]:
    if not eventos_path.exists():
        return _item(
            False,
            "corrente ausente; lacuna temporal não pôde ser medida",
            "gere ou recupere reports/markets/eventos.jsonl antes de medir a lacuna de âncora",
        )
    try:
        lacuna = eventos_sem_ancora(eventos_path, ancoras_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return _item(
            False,
            f"não foi possível medir a lacuna temporal: {exc}",
            "corrija reports/markets/eventos.jsonl e reports/markets/ancoras.jsonl para JSONL legível",
        )
    return _item(
        lacuna == 0,
        f"{lacuna} evento(s) sem âncora pública",
        "rode asus-theye markets-anchor quando a lacuna justificar prova temporal nova",
    )


def _resumo_mercados(registro_path: Path) -> dict[str, Any]:
    if not registro_path.exists():
        return _item(
            False,
            f"registro ausente: {registro_path}",
            "gere ou recupere reports/markets/registro.json para medir mercados vivos e vencidos",
        )
    try:
        registro = carregar_registro(registro_path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        return _item(
            False,
            f"registro ilegível: {exc}",
            "corrija reports/markets/registro.json para o formato esperado pelo resolvedor",
        )
    hoje = datetime.now(timezone.utc).date()
    vivos = 0
    vencidos_sem_liquidar = 0
    for mercado in registro.get("mercados", []):
        estado = str(mercado.get("estado"))
        if estado != "LIQUIDADO":
            vivos += 1
            try:
                deadline = date.fromisoformat(str(mercado["deadline"]))
            except (KeyError, TypeError, ValueError) as exc:
                return _item(
                    False,
                    f"deadline inválido em {mercado.get('claim_id', '?')}: {exc}",
                    "corrija o campo deadline (YYYY-MM-DD) no registro de mercados antes de rodar o resolvedor",
                )
            if deadline < hoje:
                vencidos_sem_liquidar += 1
    return _item(
        vencidos_sem_liquidar == 0,
        f"{vivos} vivo(s); {vencidos_sem_liquidar} vencido(s) sem liquidar",
        "rode asus-theye markets-resolve para liquidar vencidos ou entender por que ainda estão abertos",
    )


def _resumo_espelho(eventos_path: Path, eventos: list[dict[str, Any]] | None) -> dict[str, Any]:
    if not eventos_path.exists():
        return _item(
            False,
            f"espelho local ausente: {eventos_path}",
            "gere ou recupere reports/markets/eventos.jsonl; a checagem remota fica para asus-theye verificar-espelho",
        )
    if eventos is None:
        return _item(
            False,
            "espelho local ilegível",
            "corrija reports/markets/eventos.jsonl para JSONL válido antes de verificar o espelho remoto",
        )
    return _item(
        True,
        f"{eventos_path} legível ({len(eventos)} evento(s))",
        "nenhuma ação necessária",
    )


def _resumo_titularidade(raiz: Path) -> dict[str, Any]:
    notice = raiz / "NOTICE"
    authors = raiz / "AUTHORS"
    faltando = [str(caminho.name) for caminho in (notice, authors) if not caminho.exists()]
    if faltando:
        return _item(
            False,
            f"arquivo(s) ausente(s): {', '.join(faltando)}",
            "mantenha NOTICE e AUTHORS versionados na raiz nomeando o titular da obra",
        )
    try:
        textos = {notice.name: notice.read_text(encoding="utf-8"), authors.name: authors.read_text(encoding="utf-8")}
    except OSError as exc:
        return _item(
            False, f"não foi possível ler NOTICE/AUTHORS: {exc}", "corrija a leitura dos arquivos de titularidade"
        )
    sem_titular = [nome for nome, texto in textos.items() if TITULAR not in texto]
    ok = not sem_titular
    detalhe = "titular nomeado em NOTICE e AUTHORS" if ok else f"titular ausente em: {', '.join(sem_titular)}"
    return _item(
        ok,
        detalhe,
        f"garanta que NOTICE e AUTHORS citem explicitamente {TITULAR}",
    )


def _resumo_backup(backup_dir: Path) -> dict[str, Any]:
    candidatos = sorted(backup_dir.glob("the-eye-chaves-*.tar.gz.gpg"), key=lambda caminho: caminho.stat().st_mtime)
    if not candidatos:
        return _item(
            False,
            f"nenhum backup encontrado em {backup_dir}",
            "gere um pacote the-eye-chaves-*.tar.gz.gpg e copie-o para o diretório oficial de backups",
        )
    ultimo = candidatos[-1]
    quando = datetime.fromtimestamp(ultimo.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return _item(
        True,
        f"último backup: {ultimo.name} ({quando})",
        "nenhuma ação necessária",
    )


def diagnosticar(base: Path = Path("reports")) -> dict[str, dict[str, Any]]:
    """Varre os artefatos locais e devolve um quadro honesto do estado da plataforma."""
    eventos_path = base / "markets" / "eventos.jsonl"
    ancoras_path = base / "markets" / "ancoras.jsonl"
    chave_path = base / "audit" / "pseudonimos.key"
    fingerprint_path = base / "markets" / "chave.fingerprint"
    registro_path = base / "markets" / "registro.json"

    corrente, eventos = _resumo_corrente(eventos_path)
    return {
        "corrente": corrente,
        "chave": _resumo_chave(chave_path, fingerprint_path),
        "prova_temporal": _resumo_prova_temporal(eventos_path, ancoras_path),
        "mercados": _resumo_mercados(registro_path),
        "espelho": _resumo_espelho(eventos_path, eventos),
        "titularidade": _resumo_titularidade(base.parent),
        "backup": _resumo_backup(Path.home() / "Área de trabalho" / "organizado" / "Backups" / "the-eye-chaves"),
    }
