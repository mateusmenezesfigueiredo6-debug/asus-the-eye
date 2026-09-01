# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Vintage do Focus — arquiva o consenso COMO ELE ERA, no dia em que era.

O problema que isto resolve: comparar o nowcast contra o Focus exige o Focus
que existia NO CORTE da previsão, não o revisado depois. Dados revisados dão
vantagem informacional artificial — por isso a spec do nowcast marca o Brier
comparativo como ``BLOCKED`` enquanto não houver vintage reproduzível.

Vintage não se fabrica retroativamente: o boletim de hoje só existe hoje. Cada
rodada arquiva o consenso vigente com ``sha256`` e sela na corrente auditável.
Em alguns meses existe série legítima; sem começar, nunca existe.

Doutrina de sempre: fonte oficial nomeada (BCB/Olinda), UNKNOWN over guess
(mês sem boletim → ``None``, nunca zero), resposta malformada LEVANTA.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asus_theye.markets.sinais_ipca import SinaisError, mediana_focus_ipca
from asus_theye.net.http import Transport

BASE_PADRAO = Path("reports/markets")
PASTA_VINTAGE = "vintage"
INDICE = "vintage_focus.jsonl"


class VintageError(RuntimeError):
    """Falha ao arquivar o vintage. Sempre levanta — consenso não se inventa."""


@contextmanager
def _trava(base: Path) -> Iterator[None]:
    base.mkdir(parents=True, exist_ok=True)
    with (base / ".lock-vintage").open("a+", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _linhas(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def arquivar_vintage(
    mes_referencia: str,
    *,
    base: Path = BASE_PADRAO,
    transport: Transport | None = None,
    sdk: Any = None,
    eventos: Path | None = None,
    agora: str | None = None,
) -> dict[str, Any]:
    """Arquiva o consenso Focus vigente para ``mes_referencia`` (``aaaa-mm``).

    Devolve ``{"registro": …, "duplicate": bool, "selagem": …}``. Quando o
    Olinda não tem linha para o mês, devolve ``{"registro": None, …}`` — a
    ausência é registrada como fato, não como zero.

    Identidade = ``(mes_referencia, data_do_boletim, mediana)``: o mesmo
    boletim arquivado duas vezes deduplica; boletim novo é vintage novo.
    """
    try:
        focus = mediana_focus_ipca(mes_referencia, transport=transport)
    except SinaisError as erro:
        raise VintageError(f"Focus indisponível para {mes_referencia}: {erro}") from erro

    capturado_em = agora or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if focus is None:
        return {
            "registro": None,
            "duplicate": False,
            "selagem": None,
            "motivo": "boletim ainda não publicado para o mês",
        }

    mediana, data_boletim = focus
    conteudo = {
        "mes_referencia": mes_referencia,
        "indicador": "IPCA",
        "mediana": float(mediana),
        "data_do_boletim": str(data_boletim),
        "fonte": "api.bcb.gov.br/olinda (ExpectativaMercadoMensais)",
        "capturado_em": capturado_em,
        "metodo": "mediana das expectativas de mercado vigente na captura — vintage, não revisado",
    }
    identidade = json.dumps(
        {"mes": mes_referencia, "boletim": str(data_boletim), "mediana": float(mediana)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    conteudo["vintage_id"] = hashlib.sha256(identidade).hexdigest()

    with _trava(base):
        indice = base / INDICE
        existente = next((li for li in _linhas(indice) if li.get("vintage_id") == conteudo["vintage_id"]), None)
        vigente: dict[str, Any] = existente if existente is not None else conteudo

        selagem = None
        if sdk is not None:
            from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

            selagem = selar_registro(
                sdk,
                vigente,
                tipo_evento="market.vintage",
                recurso="vintage",
                correlation_id=f"vintage:{vigente['vintage_id'][:32]}",
                occurred_at=str(vigente.get("capturado_em") or ""),
                eventos=eventos or EVENTOS_PADRAO,
            )

        if existente is None:
            # snapshot bruto ao lado do índice: o artefato que prova o número
            pasta = base / PASTA_VINTAGE
            pasta.mkdir(parents=True, exist_ok=True)
            bruto = json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n"
            (pasta / f"focus-{mes_referencia}-{str(data_boletim)[:10]}.json").write_text(bruto, encoding="utf-8")
            with indice.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(conteudo, ensure_ascii=False) + "\n")

    return {"registro": vigente, "duplicate": existente is not None, "selagem": selagem}


def serie_vintage(mes_referencia: str | None = None, *, base: Path = BASE_PADRAO) -> list[dict[str, Any]]:
    """Vintages arquivados, opcionalmente de um mês — em ordem de captura."""
    linhas = _linhas(base / INDICE)
    if mes_referencia is not None:
        linhas = [li for li in linhas if li.get("mes_referencia") == mes_referencia]
    return sorted(linhas, key=lambda li: str(li.get("capturado_em", "")))
