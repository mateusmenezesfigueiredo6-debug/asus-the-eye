#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
# Abre o Codex com o handoff de hoje (tarefas de design/pesquisa, território
# do Codex — nunca src/). Uso: ./abrir-codex-hoje.sh
set -Eeuo pipefail
cd "$(dirname "$0")"
echo "== Handoff: docs/architecture/ (ontologia de Evidência + spec quântica 12-16 qubits) =="
echo "== Território do Codex: docs/, research/ | NÃO toca src/, apps/, tests/ =="
exec codex --search --sandbox workspace-write "$(cat PROMPT_CODEX_20260817.md)"
