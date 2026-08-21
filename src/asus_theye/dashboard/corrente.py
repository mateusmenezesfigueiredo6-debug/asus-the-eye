# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Painel /corrente — extrato navegável da cadeia auditável.

Mostra só o que pode sair para o navegador sem ferir a política do projeto:
hashes, sequências e metadados da corrente auditável. Nunca imprime conteúdo de
evento; o objetivo é inspecionar integridade, cobertura por âncoras e o tipo de
atividade registrada sem abrir o JSONL na mão.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import verify_chain

from .tema import pagina

BASE_PADRAO = Path("reports/markets")
EVENTOS_ARQ = "eventos.jsonl"
ANCORAS_ARQ = "ancoras.jsonl"

LEGENDA_TIPOS = {
    "market.settlement": "liquidação contra fonte oficial",
    "market.comparator": "divergência medida",
    "project.measurement": "medição do projeto",
    "project.authorship": "titularidade",
    "market.vintage": "consenso arquivado",
    "market.news_coverage": "cobertura noticiosa arquivada",
    "ml.run": "corrida de modelo",
    "market.retrospective_import": "reconstrução histórica INELEGÍVEL como previsão",
}


def _linhas_jsonl(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(linha) for linha in caminho.read_text(encoding="utf-8").splitlines() if linha.strip()]


def _int_honesto(valor: Any, padrao: int = 0) -> int:
    try:
        return int(valor)
    except (TypeError, ValueError):
        return padrao


def _verify_chain_honesto(eventos: list[dict[str, Any]]) -> str:
    if not eventos:
        return '<span class="muted">vazia</span>'
    try:
        ok = verify_chain(eventos)
    except Exception:  # noqa: BLE001 - painel deve degradar honestamente
        ok = False
    return '<span class="ok">ok</span>' if ok else '<span class="bad">falha</span>'


def _faixas_ancoradas(ancoras: list[dict[str, Any]]) -> list[tuple[int, int, str | None]]:
    faixas: list[tuple[int, int, str | None]] = []
    for linha in ancoras:
        manifest = linha.get("manifest", {})
        if "last_sequence" not in manifest:
            continue
        primeiro = _int_honesto(manifest.get("first_sequence", 1), 1)
        ultimo = _int_honesto(manifest["last_sequence"])
        tenant = manifest.get("tenant_id")
        faixas.append((primeiro, ultimo, str(tenant) if tenant is not None else None))
    return faixas


def _sequencia_ancorada(sequence: int, tenant_id: str | None, faixas: list[tuple[int, int, str | None]]) -> bool:
    for primeiro, ultimo, tenant_manifesto in faixas:
        if tenant_manifesto is not None and tenant_id is not None and tenant_manifesto != tenant_id:
            continue
        if primeiro <= sequence <= ultimo:
            return True
    return False


def _selo_ancora(sequence: int, tenant_id: str | None, faixas: list[tuple[int, int, str | None]]) -> str:
    if _sequencia_ancorada(sequence, tenant_id, faixas):
        return '<span class="ok">ancorada</span>'
    return '<span class="warn">sem âncora</span>'


def _linha_evento(evento: dict[str, Any], faixas: list[tuple[int, int, str | None]]) -> str:
    sequence = _int_honesto(evento.get("sequence", 0))
    tipo = html.escape(str(evento.get("event_type", "—")))
    event_hash = html.escape(str(evento.get("event_hash_sha256", ""))[:16])
    occurred_at = html.escape(str(evento.get("occurred_at", "—")))
    tenant_id = evento.get("tenant_id")
    return (
        f"<tr><td class='id'>{sequence}</td>"
        f"<td>{tipo}</td>"
        f"<td class='mono'>{event_hash}…</td>"
        f"<td>{occurred_at}</td>"
        f"<td>{_selo_ancora(sequence, str(tenant_id) if tenant_id is not None else None, faixas)}</td></tr>"
    )


def _legenda_tipos(tipos: list[str]) -> str:
    if not tipos:
        return '<p class="muted">Sem tipo de evento ainda — a legenda nasce quando a corrente nascer.</p>'
    itens = []
    for tipo in tipos:
        descricao = LEGENDA_TIPOS.get(tipo, "tipo registrado sem legenda curada ainda")
        itens.append(f"<li><code>{html.escape(tipo)}</code> = {html.escape(descricao)}</li>")
    return "<ul class='legend'>" + "".join(itens) + "</ul>"


def corrente_page(base: Path | None = None, *, estatico: bool = False) -> str:
    pasta = base if base is not None else BASE_PADRAO
    eventos = _linhas_jsonl(pasta / EVENTOS_ARQ)
    ancoras = _linhas_jsonl(pasta / ANCORAS_ARQ)
    tipos = sorted({str(evento.get("event_type", "—")) for evento in eventos})
    faixas = _faixas_ancoradas(ancoras)

    cards = f"""<section class="cards">
<div class="card"><div class="label">Eventos selados</div><div class="value">{len(eventos)}</div></div>
<div class="card"><div class="label">verify_chain</div><div class="value">{_verify_chain_honesto(eventos)}</div></div>
<div class="card"><div class="label">Tipos distintos</div><div class="value">{len(tipos)}</div></div>
<div class="card"><div class="label">Âncoras</div><div class="value">{len(ancoras)}</div></div>
</section>"""

    if not eventos:
        corpo = (
            cards + '<p class="muted">Corrente vazia. Nenhum evento selado ainda — o estado honesto é este até a '
            "primeira emissão auditável.</p>"
            + "<h2>Legendas por tipo</h2>"
            + _legenda_tipos([])
            + '<footer class="foot">conteúdo não sai daqui — a página mostra hashes e metadados, nunca o '
            "conteúdo dos eventos</footer>"
        )
        return pagina(
            titulo="ASUS THE EYE — Corrente",
            corpo="<h1>CORRENTE</h1><p class='lede'>o extrato navegável da cadeia auditável</p>" + corpo,
            rota="/corrente",
            estatico=estatico,
        )

    ultimos = sorted(eventos, key=lambda evento: _int_honesto(evento.get("sequence", 0)), reverse=True)[:50]
    linhas = "".join(_linha_evento(evento, faixas) for evento in ultimos)
    corpo = f"""{cards}
<h2>Últimos 50 eventos (mais recentes primeiro)</h2>
<div class="table-wrap"><table><thead>
<tr><th>sequência</th><th>tipo</th><th>event_hash</th><th>occurred_at</th><th>cobertura</th></tr>
</thead><tbody>{linhas}</tbody></table></div>
<h2>Legendas por tipo</h2>
{_legenda_tipos(tipos)}
<footer class="foot">conteúdo não sai daqui — a página mostra hashes e metadados,
nunca o conteúdo dos eventos</footer>"""
    return pagina(
        titulo="ASUS THE EYE — Corrente",
        corpo="<h1>CORRENTE</h1><p class='lede'>o extrato navegável da cadeia auditável</p>" + corpo,
        rota="/corrente",
        estatico=estatico,
    )


def register_corrente_routes(app: Any, base: Path | None = None) -> None:
    """Anexa GET /corrente a uma aplicação compatível com FastAPI."""
    try:
        from fastapi.responses import HTMLResponse
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install the 'dashboard' extra to register HTTP routes") from exc

    @app.get("/corrente", response_class=HTMLResponse)
    def get_corrente() -> str:
        return corrente_page(base)
