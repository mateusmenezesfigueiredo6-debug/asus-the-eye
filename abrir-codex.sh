#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
# Abre o Codex ja com o prompt de trabalho conjunto carregado.
# Uso: ./abrir-codex.sh
set -Eeuo pipefail
cd "$(dirname "$0")"

echo "== Coordenacao =="
grep -A4 "^| Agente" COORDENACAO.md | head -6
echo
echo "== Abrindo Codex com o prompt de trabalho conjunto =="
exec codex --search --sandbox workspace-write "$(cat PROMPT_CODEX.txt)"
