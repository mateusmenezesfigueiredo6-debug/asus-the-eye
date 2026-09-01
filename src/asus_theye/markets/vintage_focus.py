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
    return _gravar_vintage(conteudo, base=base, sdk=sdk, eventos=eventos)


def reconstruir_vintage(
    mes_referencia: str,
    corte: str,
    *,
    base: Path = BASE_PADRAO,
    transport: Transport | None = None,
    sdk: Any = None,
    eventos: Path | None = None,
    agora: str | None = None,
) -> dict[str, Any]:
    """Reconstrói o vintage de ``mes_referencia`` como ele era no dia ``corte``.

    Isto NÃO viola a doutrina "vintage não se fabrica retroativamente" — a
    doutrina proíbe usar dado REVISADO como se fosse da época. O arquivo do
    Olinda é datado na origem: cada linha é a pesquisa Focus como registrada
    naquele dia, imutável depois (o mesmo desenho dos real-time datasets
    ALFRED/Philly Fed que a literatura de nowcast usa como padrão-ouro).
    Reconstruir = ler o registro da época no arquivo oficial.

    O que muda em relação à captura ao vivo é a ROTULAGEM, nunca o número:
    ``metodo`` declara reconstrução e o corte; ``capturado_em`` é o instante
    REAL desta execução (relógio não se falsifica). A identidade de
    deduplicação é a mesma — se a captura ao vivo já arquivou o mesmo boletim,
    a reconstrução converge para o registro existente em vez de duplicar.
    """
    from asus_theye.markets.sinais_ipca import mediana_focus_ipca_no_corte

    try:
        focus = mediana_focus_ipca_no_corte(mes_referencia, corte, transport=transport)
    except SinaisError as erro:
        raise VintageError(f"Focus indisponível para {mes_referencia} no corte {corte}: {erro}") from erro

    capturado_em = agora or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if focus is None:
        return {
            "registro": None,
            "duplicate": False,
            "selagem": None,
            "motivo": f"Olinda sem pesquisa para o mês até o corte {corte}",
        }

    mediana, data_boletim = focus
    conteudo = {
        "mes_referencia": mes_referencia,
        "indicador": "IPCA",
        "mediana": float(mediana),
        "data_do_boletim": str(data_boletim),
        "fonte": "api.bcb.gov.br/olinda (ExpectativaMercadoMensais)",
        "capturado_em": capturado_em,
        "metodo": (
            "mediana reconstruída do arquivo datado do Olinda — última pesquisa "
            f"com Data <= corte {corte}; reconstrução rotulada, não é captura ao vivo"
        ),
    }
    return _gravar_vintage(conteudo, base=base, sdk=sdk, eventos=eventos)


def _gravar_vintage(
    conteudo: dict[str, Any],
    *,
    base: Path,
    sdk: Any,
    eventos: Path | None,
) -> dict[str, Any]:
    """Identidade, deduplicação, snapshot bruto, índice e selagem — caminho único.

    Captura ao vivo e reconstrução gravam pelo MESMO funil: a identidade é
    ``(mes, boletim, mediana)``, então os dois caminhos convergem para um
    registro só quando falam do mesmo boletim.
    """
    identidade = json.dumps(
        {
            "mes": conteudo["mes_referencia"],
            "boletim": str(conteudo["data_do_boletim"]),
            "mediana": float(conteudo["mediana"]),
        },
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
            nome = f"focus-{conteudo['mes_referencia']}-{str(conteudo['data_do_boletim'])[:10]}.json"
            (pasta / nome).write_text(bruto, encoding="utf-8")
            with indice.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(conteudo, ensure_ascii=False) + "\n")

    return {"registro": vigente, "duplicate": existente is not None, "selagem": selagem}


def serie_vintage(mes_referencia: str | None = None, *, base: Path = BASE_PADRAO) -> list[dict[str, Any]]:
    """Vintages arquivados, opcionalmente de um mês — em ordem de captura."""
    linhas = _linhas(base / INDICE)
    if mes_referencia is not None:
        linhas = [li for li in linhas if li.get("mes_referencia") == mes_referencia]
    return sorted(linhas, key=lambda li: str(li.get("capturado_em", "")))
