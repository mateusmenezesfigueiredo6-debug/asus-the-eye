# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Frescor (staleness) por fonte: detecta quando um dado está mais velho
que o esperado pela periodicidade declarada.

Cada fonte de dados declara quantos dias depois da data de referência ela
normalmente publica o dado.  :func:`fontes_obsoletas` recebe um dicionário
``{nome_indicador: data_mais_recente}`` e devolve a lista das fontes cujo
dado está desatualizado em relação à data de hoje.

O ``asus-theye doutor`` usa este módulo para avisar quando o BCB (ou outra
fonte) não publicou dentro do prazo esperado.

Conceito baseado em *Data Freshness / Staleness Monitoring* (documentação
pública de pipelines de dados, 2018-2024).  Esta implementação é
independente: lida a ideia, reimplementada do zero com stdlib apenas.
Proveniência: ``reports/provenance/C10-expectativas-e-frescor.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class DeclaracaoFrescor:
    """Periodicidade esperada para uma fonte.

    Args:
        nome: identificador da fonte (ex.: ``"ipca_mensal"``).
        periodicidade_dias: número máximo de dias após a data de referência
            dentro dos quais o dado deve estar disponível.
        descricao: texto livre para exibir em relatórios.
    """

    nome: str
    periodicidade_dias: int
    descricao: str = ""


#: Declarações de frescor por indicador.
DECLARACOES: dict[str, DeclaracaoFrescor] = {
    "ipca_mensal": DeclaracaoFrescor(
        nome="ipca_mensal",
        periodicidade_dias=35,
        descricao="IBGE publica o IPCA geralmente até o 12.° dia útil do mês seguinte (~35 dias corridos)",
    ),
    "selic_meta": DeclaracaoFrescor(
        nome="selic_meta",
        periodicidade_dias=35,
        descricao="BCB publica a meta Selic após cada reunião do COPOM; ciclo ~45 dias mas no pior caso 35",
    ),
    "ptax_venda": DeclaracaoFrescor(
        nome="ptax_venda",
        periodicidade_dias=3,
        descricao="BCB publica a PTAX diariamente em dias úteis; máximo 3 dias em fins de semana/feriados",
    ),
}


@dataclass(frozen=True)
class FonteObsoleta:
    """Fonte cujo dado mais recente está mais velho que o esperado."""

    nome: str
    data_mais_recente: date | None
    periodicidade_dias: int
    dias_de_atraso: int
    descricao: str


def fontes_obsoletas(
    dados_recentes: dict[str, date | None],
    *,
    hoje: date | None = None,
    declaracoes: dict[str, DeclaracaoFrescor] | None = None,
) -> list[FonteObsoleta]:
    """Devolve a lista de fontes com dado mais velho que o esperado.

    Args:
        dados_recentes: ``{nome_indicador: data_da_ultima_publicacao}``.
            ``None`` indica que nunca houve publicação ou o dado é
            desconhecido — sempre conta como obsoleto.
        hoje: data de referência para o cálculo (padrão: hoje UTC).
        declaracoes: mapeamento de declarações; padrão: :data:`DECLARACOES`.

    Returns:
        Lista de :class:`FonteObsoleta` para as fontes em atraso.
    """
    if hoje is None:
        hoje = date.today()
    if declaracoes is None:
        declaracoes = DECLARACOES

    obsoletas: list[FonteObsoleta] = []
    for nome, ultima in dados_recentes.items():
        decl = declaracoes.get(nome)
        if decl is None:
            continue
        if ultima is None:
            obsoletas.append(
                FonteObsoleta(
                    nome=nome,
                    data_mais_recente=None,
                    periodicidade_dias=decl.periodicidade_dias,
                    dias_de_atraso=decl.periodicidade_dias + 1,
                    descricao=decl.descricao,
                )
            )
            continue
        limite = ultima + timedelta(days=decl.periodicidade_dias)
        if hoje > limite:
            obsoletas.append(
                FonteObsoleta(
                    nome=nome,
                    data_mais_recente=ultima,
                    periodicidade_dias=decl.periodicidade_dias,
                    dias_de_atraso=(hoje - ultima).days - decl.periodicidade_dias,
                    descricao=decl.descricao,
                )
            )

    return obsoletas
