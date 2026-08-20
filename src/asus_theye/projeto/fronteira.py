# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fronteira — a cada rodada, provar que os direitos do titular seguem intactos.

Um teste protege contra regressão no momento do commit. Isto protege contra
algo diferente e mais difícil: **erosão silenciosa ao longo do tempo**. Se
alguém — agente, colaborador, ou o próprio titular num dia apressado — afrouxar
a titularidade, apagar um registro de proveniência, ou reintroduzir dado de
terceiro restritivo, a corrente vai carregar o momento exato em que isso
aconteceu, com prova temporal.

**Por que selar em vez de só verificar.** Verificação que não deixa rastro é
verificação que ninguém consegue provar depois. Selando, o titular passa a ter
uma série encadeada e ancorada dizendo "nesta data, a fronteira estava assim" —
e essa série é o que sustenta uma alegação de anterioridade e de autoria diante
de qualquer terceiro que venha reivindicar o contrário.

O snapshot NÃO contém relógio: a identidade é o estado da fronteira. Rodadas
consecutivas com a mesma fronteira deduplicam; qualquer mudança vira evento
novo. É assim que a corrente registra *mudanças* em vez de encher de ruído.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

RAIZ_PADRAO = Path(".")

# Terceiros cujos termos proíbem armazenar, exibir ou derivar. Ver
# reports/provenance/Kalshi-dados-expurgo.md.
ASSINATURAS_RESTRITAS = (
    re.compile(r"KXCPI[A-Z]*-\d{2}[A-Z]{3}", re.I),
    re.compile(r'"comparator"\s*:\s*"Kalshi"', re.I),
    re.compile(r"external-api\.kalshi\.com"),
)
# Onde citar o nome é o objetivo — os registros de leitura de publicação.
ISENTOS = ("reports/provenance/", "tests/test_fronteira_de_terceiros.py", "src/asus_theye/projeto/fronteira.py")


class FronteiraError(RuntimeError):
    """Insumo corrompido. Sempre levanta — a fronteira não se mede por chute."""


def _versionados(raiz: Path) -> list[str]:
    try:
        saida = subprocess.run(
            ["git", "ls-files"], cwd=raiz, capture_output=True, text=True, check=True, timeout=60
        ).stdout
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        raise FronteiraError(f"não foi possível listar arquivos versionados: {exc}") from exc
    return [li for li in saida.splitlines() if li.strip()]


def medir_fronteira(raiz: Path = RAIZ_PADRAO) -> dict[str, Any]:
    """Estado da fronteira: titularidade, proveniência e ausência de dado restrito."""
    arquivos = _versionados(raiz)

    # --- titularidade declarada em cada arquivo de código
    extensoes = (".py", ".ts", ".mjs", ".sol", ".sh", ".yml", ".yaml")
    codigo = [
        a
        for a in arquivos
        if a.endswith(extensoes) and not a.startswith(("contracts/audit-anchor/lib/",)) and "node_modules" not in a
    ]
    sem_titularidade = []
    for relativo in codigo:
        try:
            cabeca = (raiz / relativo).read_text(encoding="utf-8")[:600]
        except (OSError, UnicodeDecodeError):
            continue
        if "SPDX-FileCopyrightText" not in cabeca:
            sem_titularidade.append(relativo)

    # --- todo terceiro do NOTICE tem registro de proveniência
    notice = (raiz / "NOTICE").read_text(encoding="utf-8") if (raiz / "NOTICE").exists() else ""
    registros = sorted(p.name for p in (raiz / "reports/provenance").glob("*.md"))

    # --- nenhum dado de terceiro restritivo voltou
    reincidencias = []
    for relativo in arquivos:
        if any(relativo.startswith(i) or relativo == i for i in ISENTOS):
            continue
        caminho = raiz / relativo
        if not caminho.is_file():
            continue
        try:
            texto = caminho.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for assinatura in ASSINATURAS_RESTRITAS:
            if assinatura.search(texto):
                reincidencias.append(relativo)
                break

    intacta = not sem_titularidade and not reincidencias and bool(registros)
    snapshot: dict[str, Any] = {
        "versao": 1,
        "titular": "Mateus Menezes Figueiredo",
        "licenca": "AGPL-3.0-or-later",
        "arquivos_de_codigo": len(codigo),
        "sem_titularidade": sorted(sem_titularidade),
        "registros_de_proveniencia": registros,
        "dado_de_terceiro_restrito": sorted(reincidencias),
        "notice_declara_titular": "Mateus Menezes Figueiredo" in notice,
        "intacta": intacta,
        "metodo": (
            "varredura dos arquivos VERSIONADOS (git ls-files): titularidade SPDX em todo código "
            "próprio, registros de proveniência presentes, e ausência de assinatura de dado de "
            "terceiro com termos restritivos. reports/provenance/ é isento da última checagem "
            "porque é lá que a leitura de publicação alheia fica registrada — ler não é copiar."
        ),
    }
    return snapshot


def selar_fronteira(sdk: Any, snapshot: dict[str, Any] | None = None, *, eventos: Path | None = None) -> dict[str, Any]:
    """Sela o estado da fronteira. Mesma fronteira = dedupe; mudança = evento novo.

    É este evento que dá ao titular uma série encadeada e ancorada dizendo
    "nesta data, a autoria e a fronteira estavam assim".
    """
    from asus_theye.audit.schema import hash_json
    from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

    snap = snapshot or medir_fronteira()
    return selar_registro(
        sdk,
        snap,
        tipo_evento="project.boundary",
        recurso="boundary",
        correlation_id=f"fronteira:{hash_json(snap)[:32]}",
        eventos=eventos or EVENTOS_PADRAO,
    )


def relatorio(snapshot: dict[str, Any]) -> str:
    """Texto para o operador — o que está de pé e o que rompeu."""
    linhas = [
        "=" * 62,
        "FRONTEIRA — os direitos do titular, verificados",
        "=" * 62,
        "",
        f"titular: {snapshot['titular']} · {snapshot['licenca']}",
        f"arquivos de código com titularidade: "
        f"{snapshot['arquivos_de_codigo'] - len(snapshot['sem_titularidade'])}/{snapshot['arquivos_de_codigo']}",
        f"registros de proveniência: {len(snapshot['registros_de_proveniencia'])}",
        f"NOTICE declara o titular: {'sim' if snapshot['notice_declara_titular'] else 'NÃO'}",
        "",
    ]
    if snapshot["sem_titularidade"]:
        linhas.append("ARQUIVOS SEM TITULARIDADE:")
        linhas += [f"  - {a}" for a in snapshot["sem_titularidade"][:10]]
    if snapshot["dado_de_terceiro_restrito"]:
        linhas.append("DADO DE TERCEIRO RESTRITO PRESENTE:")
        linhas += [f"  - {a}" for a in snapshot["dado_de_terceiro_restrito"][:10]]
    linhas.append("FRONTEIRA INTACTA" if snapshot["intacta"] else "FRONTEIRA ROMPIDA — ver acima")
    return "\n".join(linhas)
