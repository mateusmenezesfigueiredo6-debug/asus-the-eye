# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Relatórios em Markdown da plataforma."""

from .anual import relatorio_anual
from .mensal import relatorio_mensal

__all__ = ["relatorio_anual", "relatorio_mensal"]
