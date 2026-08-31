# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""A trava que impede terceiro restritivo de voltar ao repositório.

Documento pode ser ignorado; agente pode receber ordem contrária; humano
esquece. Teste não. Este arquivo é a única defesa que roda sozinha a cada
commit e a cada rodada de CI, e por isso é ele — não o `AGENTS.md` — que de
fato mantém a decisão do titular de pé.

O que ele protege, concretamente: em 20/08/2026 os dados de mercado da Kalshi
foram expurgados porque os Data Terms of Use restringem o uso a pessoal e
não-comercial, excluem desenvolvimento de software e proíbem armazenar, exibir
e derivar. Um agente futuro — ou o próprio titular num dia apressado — poderia
reintroduzi-los sem perceber que está recriando a exposição. Aqui a suíte
quebra antes do commit.

**A fronteira que este teste NÃO cruza.** Ler publicações de pesquisa de
terceiros e reimplementar conceitos de forma independente continua permitido, e
é como nove absorções deste projeto nasceram. Por isso `reports/provenance/` é
explicitamente isento: é lá que a leitura fica registrada. Conceito não tem
dono; expressão e dado têm.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# Fontes cujos termos proíbem armazenar/exibir/derivar. Entrar nesta lista é um
# commit revisável, e sair dela exige que alguém tenha lido os termos de novo.
FONTES_PROIBIDAS = {
    "Kalshi": "Data Terms of Use: uso pessoal e não-comercial; exclui desenvolvimento de software",
    "Metaculus": "licença pessoal e não-comercial; redistribuição proibida",
    "Quandl": "proprietária",
    "Alpha Vantage": "proprietária",
}

# Assinaturas de DADO de mercado de terceiro — não de menção ao nome. Citar
# "Kalshi" em texto próprio é permitido e acontece o tempo todo nos registros
# de proveniência; guardar o preço deles não é.
ASSINATURAS_DE_DADO = (
    re.compile(r"KXCPI[A-Z]*-\d{2}[A-Z]{3}", re.I),  # ticker de contrato
    re.compile(r'"comparator"\s*:\s*"Kalshi"', re.I),  # observação armazenada
    re.compile(r"external-api\.kalshi\.com"),  # chamada ao endpoint de dados
    re.compile(r"trade-api/v2/markets"),
)

# Onde a leitura de publicação é registrada — citar o nome ali é o objetivo.
ISENTOS = ("reports/provenance/", "tests/test_fronteira_de_terceiros.py")


def _arquivos_versionados() -> list[Path]:
    saida = subprocess.run(
        ["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    return [RAIZ / li for li in saida if li.strip()]


def _isento(caminho: Path) -> bool:
    relativo = str(caminho.relative_to(RAIZ))
    return any(relativo.startswith(prefixo) or relativo == prefixo for prefixo in ISENTOS)


def test_nenhum_dado_de_fonte_proibida_voltou_ao_repositorio() -> None:
    """Se este teste falhar, alguém reintroduziu dado que os termos proíbem guardar.

    NÃO ignore. Não é falso positivo por citar um nome — as assinaturas casam
    com ticker, endpoint e observação armazenada, não com a palavra solta.
    """
    reincidencias: list[str] = []
    for arquivo in _arquivos_versionados():
        if _isento(arquivo) or not arquivo.is_file():
            continue
        try:
            texto = arquivo.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binário ou ilegível: não carrega dado tabular de terceiro
        for assinatura in ASSINATURAS_DE_DADO:
            achado = assinatura.search(texto)
            if achado:
                reincidencias.append(f"{arquivo.relative_to(RAIZ)}: {achado.group(0)!r}")

    assert not reincidencias, (
        "DADO DE TERCEIRO COM TERMOS RESTRITIVOS VOLTOU AO REPOSITÓRIO.\n"
        + "\n".join(f"  - {r}" for r in reincidencias)
        + "\n\nO expurgo de 20/08/2026 (PR #81, recibo data.redaction) removeu isto porque os "
        "termos proíbem armazenar, exibir e derivar. Reintroduzir recria a exposição jurídica "
        "do titular. Se a reintrodução for deliberada, a decisão é do titular e passa por "
        "editar FONTES_PROIBIDAS neste arquivo — não por ignorar o teste."
    )


def test_o_conector_da_fonte_proibida_continua_removido() -> None:
    """O módulo que buscava o dado ao vivo não pode reaparecer."""
    assert not (RAIZ / "src/asus_theye/markets/fonte_kalshi.py").exists(), (
        "fonte_kalshi.py voltou — era o conector que buscava dado sob termos restritivos"
    )


#: Como a casa nomeia a bolsa de referência. "Chaox" é o rótulo adotado em
#: 31/08/2026 por decisão do titular — não nomear concorrente em documento é
#: higiene jurídica. O nome anterior continua aceito aqui porque os registros de
#: proveniência (`reports/provenance/`) o preservam de propósito: eles são a
#: prova do expurgo, e prova que se reescreve não é prova.
NOMES_DA_REFERENCIA = ("Chaox", "Kalshi")


def test_a_politica_declara_a_fonte_como_proibida() -> None:
    """O documento e o teste têm de concordar; se divergirem, alguém mexeu num só.

    O teste aceita qualquer um dos nomes, mas exige que UM esteja lá. Aceitar
    ausência transformaria este teste em decoração: ele passaria com o documento
    vazio, que é exatamente o estado que ele existe para impedir.
    """
    politica = (RAIZ / "POLITICA_DIREITOS.md").read_text(encoding="utf-8")
    assert "PROIBIDA" in politica, (
        "POLITICA_DIREITOS.md deixou de declarar a fonte como proibida"
    )
    assert any(n in politica for n in NOMES_DA_REFERENCIA), (
        f"POLITICA_DIREITOS.md não nomeia a fonte proibida: {NOMES_DA_REFERENCIA}"
    )


def test_a_ordem_permanente_nao_manda_reverter_o_expurgo() -> None:
    """AGENTS.md é lido por agentes antes de trabalhar.

    A regra original dizia "Never delete anything Kalshi" sem exceção — um
    agente obediente reverteria o expurgo achando que estava certo. Este teste
    impede que a redação perigosa volte.
    """
    agentes = (RAIZ / "AGENTS.md").read_text(encoding="utf-8")
    assert "Never delete anything Kalshi.**" not in agentes, (
        "a ordem incondicional voltou ao AGENTS.md — ela mandaria um agente futuro "
        "reverter o expurgo e recriar a exposição jurídica do titular"
    )
    assert "Do not revert that purge" in agentes, "AGENTS.md deixou de registrar a decisão do titular"


def test_a_titularidade_do_expurgo_esta_registrada() -> None:
    """A proveniência do expurgo é a prova de que a remoção foi decisão consciente."""
    registro = RAIZ / "reports/provenance/Kalshi-dados-expurgo.md"
    assert registro.exists(), "o registro do expurgo sumiu — sem ele a remoção parece acidente"
    texto = registro.read_text(encoding="utf-8")
    assert "Mateus Menezes Figueiredo" in texto
    assert "data.redaction" in texto
