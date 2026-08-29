# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Raiz comum das falhas de conector de fonte oficial.

Cada conector nasceu com a sua própria exceção (``FonteBCBError``,
``FontePTAXError``, ``FonteSelicError``…), todas herdando direto de
``RuntimeError``. O efeito colateral só apareceu com a segunda fonte: quem
resolve mercados captura a exceção **por mercado**, para que a falha de um
não aborte os demais — e capturava apenas a do BCB. Uma falha da PTAX
escapava do laço inteiro e derrubava a rodada, levando junto os mercados que
teriam resolvido bem.

A correção é uma raiz comum. Cada conector mantém a sua exceção nomeada (a
mensagem de erro continua dizendo qual fonte falhou), mas todas passam a ser
``FonteError`` — então quem resolve captura uma coisa só, e conector novo já
nasce coberto sem ninguém precisar lembrar de editar o ``except``.
"""

from __future__ import annotations


class FonteError(RuntimeError):
    """Falha ao ler uma fonte oficial de resolução.

    Levantar isto significa "não consegui apurar", nunca "o valor é zero".
    Período que a fonte ainda não publicou é ``None`` (UNKNOWN) no retorno do
    conector — não é erro e não passa por aqui.
    """
