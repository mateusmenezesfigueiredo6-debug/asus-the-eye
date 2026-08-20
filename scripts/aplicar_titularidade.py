#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Carimba a titularidade em CADA arquivo-fonte (padrão SPDX).

Por que arquivo a arquivo: um NOTICE na raiz declara a obra, mas arquivos
viajam soltos — copiados, citados, vendidos em pedaços. O cabeçalho SPDX é o
padrão que ferramentas de compliance (e advogados) leem para saber de quem é
cada linha, mesmo fora do repositório.

Idempotente: rodar duas vezes não duplica. Preserva shebang e docstring.
"""

from __future__ import annotations

import sys
from pathlib import Path

TITULAR = "Mateus Menezes Figueiredo"
ANO = "2026"
LICENCA = "AGPL-3.0-or-later"
MARCA = "SPDX-FileCopyrightText"
# O comentário muda com a linguagem — carimbo que não compila não é carimbo.
COMENTARIO_POR_EXTENSAO = {
    ".py": "#",
    ".sh": "#",
    ".yml": "#",
    ".yaml": "#",
    ".ts": "//",
    ".mjs": "//",
    ".sol": "//",
}
EXTENSOES = tuple(COMENTARIO_POR_EXTENSAO)

# Todo diretório com código do titular. `contracts/audit-anchor/lib` fica de
# FORA por ser código de terceiro (OpenZeppelin/MIT) — carimbar obra alheia com
# o nome do titular seria o oposto do que este script existe para fazer.
ALVOS = ("src", "tests", "scripts", "apps", "infra", "contracts", "packages", "bin", ".github")
IGNORAR = ("__pycache__", ".venv", "node_modules", "contracts/audit-anchor/lib", "dist/")


def cabecalho(extensao: str) -> str:
    marcador = COMENTARIO_POR_EXTENSAO[extensao]
    return f"{marcador} {MARCA}: {ANO} {TITULAR}\n{marcador} SPDX-License-Identifier: {LICENCA}\n"


def arquivos_alvo(raiz: Path) -> list[Path]:
    achados: list[Path] = []
    for pasta in ALVOS:
        base = raiz / pasta
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if p.suffix not in EXTENSOES or not p.is_file():
                continue
            if any(ig in str(p) for ig in IGNORAR):
                continue
            achados.append(p)
    return achados


def carimbar(caminho: Path) -> bool:
    """Insere o cabeçalho se faltar. Devolve True se alterou.

    Se o arquivo JÁ declara uma licença (``SPDX-License-Identifier``), só a
    titularidade é acrescentada — a licença escolhida para aquele arquivo é
    preservada. Duas linhas de licença seriam ambíguas juridicamente e, em
    Solidity, quebram o compilador.
    """
    texto = caminho.read_text(encoding="utf-8")
    if MARCA in texto.split("\n\n")[0]:
        return False
    marcador = COMENTARIO_POR_EXTENSAO[caminho.suffix]
    if "SPDX-License-Identifier" in texto:
        cabeca = f"{marcador} {MARCA}: {ANO} {TITULAR}\n"
    else:
        cabeca = cabecalho(caminho.suffix)
    linhas = texto.splitlines(keepends=True)
    # shebang (se houver) continua sendo a primeira linha do arquivo
    corte = 1 if linhas and linhas[0].startswith("#!") else 0
    novo = "".join(linhas[:corte]) + cabeca + "".join(linhas[corte:])
    caminho.write_text(novo, encoding="utf-8")
    return True


def main() -> int:
    raiz = Path(__file__).resolve().parent.parent
    alvos = arquivos_alvo(raiz)
    conferir = "--conferir" in sys.argv
    sem_marca = [p for p in alvos if MARCA not in p.read_text(encoding="utf-8").split("\n\n")[0]]

    if conferir:
        if sem_marca:
            print(f"FALTA titularidade em {len(sem_marca)} arquivo(s):")
            for p in sem_marca[:10]:
                print(f"  {p.relative_to(raiz)}")
            print("\ncorrija com: python scripts/aplicar_titularidade.py")
            return 1
        print(f"titularidade declarada em {len(alvos)}/{len(alvos)} arquivos ✅")
        return 0

    alterados = sum(1 for p in alvos if carimbar(p))
    print(f"titularidade aplicada: {alterados} arquivo(s) carimbado(s) de {len(alvos)} alvos")
    print(f"  © {ANO} {TITULAR} — {LICENCA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
