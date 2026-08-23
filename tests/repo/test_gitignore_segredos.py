# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""O .gitignore ignora DE VERDADE os padrões de segredo — regressão.

O bug que isto trava: `.gitignore` NÃO aceita comentário na mesma linha do
padrão. `*.key.*  # comentário` vira um padrão literal que não casa nada, e o
arquivo sensível volta a ser rastreado sem ninguém ver. Aqui perguntamos ao
próprio git (`check-ignore`), não ao texto do arquivo.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "caminho",
    [
        "reports/audit/anchor.key.QUEIMADA",  # sufixo não pode evadir *.key
        "reports/audit/qualquer.key",
        "infra/cloudflare/staging/.wrangler/cache/wrangler-account.json",
        "apps/site/.wrangler/cache/x.json",
    ],
)
def test_git_ignora_o_padrao(caminho: str) -> None:
    r = subprocess.run(
        ["git", "check-ignore", caminho],
        cwd=RAIZ,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"{caminho} NÃO é ignorado pelo .gitignore (returncode {r.returncode})"


def test_nenhum_segredo_rastreado() -> None:
    r = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True)
    rastreados = r.stdout.splitlines()
    ofensores = [f for f in rastreados if f.endswith(".key") or ".key." in f or "/.wrangler/" in f]
    assert not ofensores, f"segredo/cache rastreado no git: {ofensores}"
