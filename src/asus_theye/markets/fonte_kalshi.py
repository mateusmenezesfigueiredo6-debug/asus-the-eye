"""Conector do COMPARADOR: preço público da Kalshi (nunca fonte de resolução).

API pública verificada em ``docs/architecture/KALSHI_COMPARATOR_API.md``
(lote C do Codex, 19/08/2026): ``GET /markets/{ticker}`` responde sem
autenticação em ``external-api.kalshi.com/trade-api/v2``. Regras deste client:

1. **Só dados públicos, só leitura.** Endpoints de conta/ordem exigem chave e
   NÃO são alternativa aceitável — este produto não opera na Kalshi, compara.
2. **Preço = strings decimais ``*_dollars``** (os campos inteiros de centavos
   foram removidos em jan/2026). Parsing via ``Decimal`` — float prematuro
   arredonda errado.
3. **A probabilidade implícita declarada é o MEIO do spread** quando bid e ask
   existem ((bid+ask)/2 — o last pode estar defasado em mercado ilíquido);
   sem os dois lados, cai para ``last_price``. O método viaja no resultado.
4. **Mercado inexistente (404) → ``None``**; resposta malformada → levanta.
   Mercado fora de negociação (status ≠ active) vem marcado — quem decide se
   a observação vale é o chamador, com o status na mão.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from asus_theye.net.http import HttpError, Transport, get_bytes

URL_BASE = "https://external-api.kalshi.com/trade-api/v2"
MAX_BYTES = 200_000
TIMEOUT = 30


class FonteKalshiError(RuntimeError):
    """Resposta inesperada do comparador. Sempre levanta — preço não se inventa."""


@dataclass(frozen=True)
class PrecoComparador:
    """Observação pública de um mercado da Kalshi, com o método do preço declarado."""

    ticker: str
    title: str
    status: str
    close_time: str
    yes_bid: float | None
    yes_ask: float | None
    last_price: float | None
    probabilidade_implicita: float
    metodo_do_preco: str  # "meio do spread (bid+ask)/2" ou "last_price (sem os dois lados)"

    def as_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "title": self.title,
            "status": self.status,
            "close_time": self.close_time,
            "yes_bid": self.yes_bid,
            "yes_ask": self.yes_ask,
            "last_price": self.last_price,
            "probabilidade_implicita": self.probabilidade_implicita,
            "metodo_do_preco": self.metodo_do_preco,
        }


def _decimal_ou_none(mercado: dict[str, Any], campo: str) -> Decimal | None:
    bruto = mercado.get(campo)
    if bruto in (None, ""):
        return None
    try:
        valor = Decimal(str(bruto))
    except InvalidOperation as exc:
        raise FonteKalshiError(f"{campo} não decimal na resposta da Kalshi: {bruto!r}") from exc
    if not Decimal("0") <= valor <= Decimal("1"):
        raise FonteKalshiError(f"{campo} fora de [0,1] (dólares por contrato): {bruto!r}")
    return valor


def preco_kalshi(ticker: str, *, transport: Transport | None = None) -> PrecoComparador | None:
    """Preço público do mercado ``ticker`` — ou ``None`` se o mercado não existe.

    Levanta :class:`FonteKalshiError` para malformação ou HTTP inesperado.
    """
    if not ticker.strip():
        raise FonteKalshiError("ticker vazio")
    url = f"{URL_BASE}/markets/{ticker}"
    try:
        response = get_bytes(
            url, headers={"Accept": "application/json"}, timeout=TIMEOUT, max_bytes=MAX_BYTES, transport=transport
        )
    except HttpError as exc:
        raise FonteKalshiError(f"comparador inalcançável: {exc}") from exc
    if response.status == 404:
        return None
    if response.status != 200:
        raise FonteKalshiError(f"comparador respondeu HTTP {response.status} em {url}")
    try:
        mercado = json.loads(response.body.decode("utf-8"))["market"]
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        raise FonteKalshiError(f"resposta da Kalshi em formato inesperado ({exc})") from exc
    if not isinstance(mercado, dict) or not mercado.get("ticker"):
        raise FonteKalshiError(f"objeto 'market' inesperado: {type(mercado).__name__}")

    bid = _decimal_ou_none(mercado, "yes_bid_dollars")
    ask = _decimal_ou_none(mercado, "yes_ask_dollars")
    last = _decimal_ou_none(mercado, "last_price_dollars")
    if bid is not None and ask is not None:
        implicita = (bid + ask) / 2
        metodo = "meio do spread (bid+ask)/2 — last pode defasar em mercado ilíquido"
    elif last is not None:
        implicita = last
        metodo = "last_price (sem os dois lados do livro)"
    else:
        raise FonteKalshiError(f"{ticker}: sem bid/ask nem last_price — não há preço público a observar")

    return PrecoComparador(
        ticker=str(mercado["ticker"]),
        title=str(mercado.get("title", "")),
        status=str(mercado.get("status", "")),
        close_time=str(mercado.get("close_time", "")),
        yes_bid=float(bid) if bid is not None else None,
        yes_ask=float(ask) if ask is not None else None,
        last_price=float(last) if last is not None else None,
        probabilidade_implicita=round(float(implicita), 6),
        metodo_do_preco=metodo,
    )
