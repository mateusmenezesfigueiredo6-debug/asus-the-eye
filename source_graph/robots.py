# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cache de robots.txt sobre urllib.robotparser (stdlib, zero dependência).

A checagem não é um parâmetro que se desliga: não existe ``respect_robots=False``
neste módulo. O caso legítimo de APIs cujo robots.txt proíbe ``/`` para crawlers
mas cujos termos publicados autorizam uso programático é tratado no fetcher por
``access_basis="api_terms:<url>"``, com a base da autorização gravada em cada
resultado e em cada evento — nunca por um silêncio.
"""

from __future__ import annotations

import urllib.robotparser
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import urlsplit, urlunsplit

CACHE_TTL_SECONDS = 86_400  # 24 h


@dataclass
class _Entry:
    parser: urllib.robotparser.RobotFileParser | None
    fetched_at: float
    had_file: bool


@dataclass
class RobotsCache:
    """Cache por netloc, com TTL. ``fetch_text`` é injetável para teste offline."""

    fetch_text: Callable[[str], str | None]  # None = host sem robots.txt
    clock: Callable[[], float]
    ttl_seconds: int = CACHE_TTL_SECONDS
    _entries: dict[str, _Entry] = field(default_factory=dict)

    def _robots_url(self, url: str) -> tuple[str, str]:
        parts = urlsplit(url)
        return parts.netloc, urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))

    def _entry(self, url: str) -> _Entry:
        netloc, robots_url = self._robots_url(url)
        now = float(self.clock())
        cached = self._entries.get(netloc)
        if cached is not None and (now - cached.fetched_at) < self.ttl_seconds:
            return cached

        text = self.fetch_text(robots_url)
        if text is None:
            entry = _Entry(parser=None, fetched_at=now, had_file=False)
        else:
            parser = urllib.robotparser.RobotFileParser()
            parser.parse(text.splitlines())
            entry = _Entry(parser=parser, fetched_at=now, had_file=True)
        self._entries[netloc] = entry
        return entry

    def allowed(self, url: str, user_agent: str) -> tuple[bool, str]:
        """(permitido, base da decisão).

        Sem robots.txt é permitido — é a semântica do padrão, e o motivo fica
        registrado como ``no_robots_file`` em vez de virar um "sim" anônimo.
        """
        entry = self._entry(url)
        if not entry.had_file or entry.parser is None:
            return True, "no_robots_file"
        return (True, "robots_allowed") if entry.parser.can_fetch(user_agent, url) else (False, "robots_disallowed")
