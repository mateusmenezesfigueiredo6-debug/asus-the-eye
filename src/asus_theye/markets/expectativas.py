# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Expectativas fail-closed para ingestão de indicadores macroeconômicos.

Cada indicador declara a faixa plausível de valores mensais. A função
:func:`verificar` é chamada *antes* de qualquer escrita: se qualquer
expectativa falhar ela levanta :class:`ExpectativaViolada` e o store
permanece intacto.

Regra: ``None`` sempre significa UNKNOWN (dado ainda não publicado).
Um valor ``None`` aprovado por uma expectativa que aceite ausência é
diferente de ausência mascarada por zero.  Zero como substituto de
``None`` é proibido.

Conceito baseado em *Data Quality Expectations* (documentação pública
de sistemas de qualidade de dados, 2016-2024).  Esta implementação é
independente: lida a ideia, reimplementada do zero com stdlib apenas.
Proveniência: ``reports/provenance/C10-expectativas-e-frescor.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ExpectativaViolada(ValueError):
    """Expectativa de qualidade violada.  Nada deve ser escrito após este levante."""


@dataclass(frozen=True)
class FaixaNumerica:
    """Faixa plausível para um indicador numérico mensal.

    Args:
        minimo: menor valor aceitável (inclusive).
        maximo: maior valor aceitável (inclusive).
        permite_none: se ``True``, ``None`` é aceito (UNKNOWN — dado ainda
            não publicado).  ``False`` exige valor presente.
    """

    minimo: float
    maximo: float
    permite_none: bool = True

    def validar(self, nome: str, valor: Any) -> None:
        """Valida *valor* contra a faixa.  Levanta :class:`ExpectativaViolada` se falhar."""
        if valor is None:
            if not self.permite_none:
                raise ExpectativaViolada(
                    f"{nome}: valor ausente (None) não é permitido — a expectativa exige valor presente"
                )
            return
        if isinstance(valor, bool):
            raise ExpectativaViolada(f"{nome}: bool não é aceito como valor numérico, recebeu {valor!r}")
        if not isinstance(valor, (int, float)):
            raise ExpectativaViolada(
                f"{nome}: tipo inválido {type(valor).__name__!r}; esperado int ou float, recebeu {valor!r}"
            )
        num = float(valor)
        if not (self.minimo <= num <= self.maximo):
            raise ExpectativaViolada(f"{nome}: {num} fora da faixa plausível [{self.minimo}, {self.maximo}]")


# ---------------------------------------------------------------------------
# Faixas declaradas por indicador
# ---------------------------------------------------------------------------

#: Variação mensal do IPCA em pontos percentuais.
#: Fora de [-5, 15] é resposta suspeita, não dado.
IPCA_MENSAL: FaixaNumerica = FaixaNumerica(minimo=-5.0, maximo=15.0)

#: Meta da Selic em pontos percentuais anuais.
#: Historicamente entre 2% e 26,5%; margem conservadora [-1, 100].
SELIC_META: FaixaNumerica = FaixaNumerica(minimo=-1.0, maximo=100.0)

#: PTAX venda (R$/USD).
#: Nunca foi inferior a 0,5 nem superior a 20 no registro histórico.
PTAX_VENDA: FaixaNumerica = FaixaNumerica(minimo=0.5, maximo=20.0)

#: IPCA-15 (prévia) — mesma natureza do IPCA mensal.
IPCA15_MENSAL: FaixaNumerica = FaixaNumerica(minimo=-5.0, maximo=15.0)

#: INPC mensal — mesma faixa plausível do IPCA.
INPC_MENSAL: FaixaNumerica = FaixaNumerica(minimo=-5.0, maximo=15.0)

#: IGP-M mensal — mais volátil que o IPCA (deflações e picos maiores).
IGPM_MENSAL: FaixaNumerica = FaixaNumerica(minimo=-10.0, maximo=20.0)

#: IBC-Br — índice de atividade (base 2002=100); faixa histórica larga.
IBCBR_INDICE: FaixaNumerica = FaixaNumerica(minimo=50.0, maximo=300.0)


# ---------------------------------------------------------------------------
# Registro central de expectativas
# ---------------------------------------------------------------------------

#: Mapeamento de ``nome_indicador -> FaixaNumerica`` usado por :func:`verificar`.
EXPECTATIVAS: dict[str, FaixaNumerica] = {
    "ipca_mensal": IPCA_MENSAL,
    "selic_meta": SELIC_META,
    "ptax_venda": PTAX_VENDA,
    "ipca15_mensal": IPCA15_MENSAL,
    "inpc_mensal": INPC_MENSAL,
    "igpm_mensal": IGPM_MENSAL,
    "ibcbr_indice": IBCBR_INDICE,
}


@dataclass
class ResultadoVerificacao:
    """Resultado da verificação de expectativas para um lote de valores."""

    violacoes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violacoes


def verificar(indicadores: dict[str, Any]) -> ResultadoVerificacao:
    """Verifica *indicadores* contra as expectativas declaradas.

    Deve ser chamada **antes** de qualquer escrita.  Se houver violações
    levanta :class:`ExpectativaViolada` com todas as mensagens concatenadas.

    Args:
        indicadores: dicionário ``{nome: valor}`` onde ``nome`` deve estar
            presente em :data:`EXPECTATIVAS`.  Chaves desconhecidas levantam
            imediatamente.

    Returns:
        :class:`ResultadoVerificacao` (sem violações); nunca retorna com
        violações — levanta antes.
    """
    resultado = ResultadoVerificacao()
    for nome, valor in indicadores.items():
        expectativa = EXPECTATIVAS.get(nome)
        if expectativa is None:
            resultado.violacoes.append(f"{nome}: indicador desconhecido — adicione-o a EXPECTATIVAS antes de ingerir")
            continue
        try:
            expectativa.validar(nome, valor)
        except ExpectativaViolada as exc:
            resultado.violacoes.append(str(exc))

    if resultado.violacoes:
        mensagem = "; ".join(resultado.violacoes)
        raise ExpectativaViolada(mensagem)

    return resultado
