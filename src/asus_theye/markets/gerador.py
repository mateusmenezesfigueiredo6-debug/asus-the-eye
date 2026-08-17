"""Gerador de probabilidade — modelo de ajuste ponderado (WPAM).

Corrige a falha de desenho que a própria doutrina apontou: hoje todo mercado
nasce em p = 0,50 (limiar de máxima incerteza), e nesse limiar o produto não
demonstra skill nem funcionando. Aqui a probabilidade parte de um prior estável
e se MOVE conforme sinais ponderados de fonte nomeada — mas só quando há sinal.

Fórmula (média ponderada com pseudo-contagem):

    p = (p_inicial · peso_inicial + peso_sim) / (peso_inicial + peso_sim + peso_nao)

- ``p_inicial`` = prior neutro (0,50);
- ``peso_inicial`` = quanto o prior resiste — pseudo-contagem que estabiliza o
  início; quanto maior, mais evidência é preciso para mover a probabilidade;
- ``peso_sim`` / ``peso_nao`` = evidência ponderada a favor de SIM / de NÃO,
  cada parcela com FONTE nomeada (a doutrina exige proveniência).

Invariante que preserva a honestidade: sem nenhum sinal
(``peso_sim = peso_nao = 0``) o resultado é exatamente ``p_inicial`` — ou seja,
0,50 e ``max_uncertainty = True``, igual ao gerador atual. O modelo só afirma
uma probabilidade diferente de 0,50 quando há evidência medida por trás; nunca
inventa convicção. UNKNOWN over guess continua valendo.

Proveniência (licença): a estrutura WPAM (prior ponderado por pseudo-contagem,
com p_inicial = 0,50 embutido no numerador e denominador para estabilidade) foi
ESTUDADA de SocialPredict — Open Prediction Markets, licença MIT
(© 2024 Open Prediction Markets), commit 3d978faac6b3391d5b6a9af4aa37a283d48699a7,
arquivo backend/internal/domain/math/probabilities/wpam. A fórmula matemática
é de domínio público (média ponderada de Laplace/Beta); esta é uma
reimplementação independente em Python, adaptada do contexto de mercado de
apostas para o de previsão contra fonte oficial (a evidência substitui as
apostas), sob a AGPL-3.0 do projeto. Ver reports/provenance/SocialPredict-WPAM.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

PRIOR_NEUTRO = 0.5
PESO_INICIAL_PADRAO = 10.0  # pseudo-contagem do prior; > exige mais evidência p/ mover
UNCERTAINTY_TOLERANCE = 1e-9


class GeradorError(RuntimeError):
    """Entrada inválida para o gerador. Sempre levanta — nunca degrada em palpite."""


@dataclass(frozen=True)
class Sinal:
    """Evidência ponderada a favor de um lado, com fonte nomeada (obrigatória)."""

    direcao: str  # "sim" ou "nao"
    peso: float  # > 0
    fonte: str  # proveniência — a doutrina não aceita sinal anônimo


@dataclass(frozen=True)
class Probabilidade:
    """Resultado do gerador: a probabilidade e como ela foi obtida."""

    valor: float
    p_inicial: float
    peso_inicial: float
    peso_sim: float
    peso_nao: float
    max_uncertainty: bool
    fontes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "valor": self.valor,
            "p_inicial": self.p_inicial,
            "peso_inicial": self.peso_inicial,
            "peso_sim": self.peso_sim,
            "peso_nao": self.peso_nao,
            "max_uncertainty": self.max_uncertainty,
            "fontes": self.fontes,
        }


def _validar(p_inicial: float, peso_inicial: float, sinais: list[Sinal]) -> None:
    if isinstance(p_inicial, bool) or not isinstance(p_inicial, (int, float)) or not 0.0 <= float(p_inicial) <= 1.0:
        raise GeradorError(f"p_inicial deve estar em [0,1], veio {p_inicial!r}")
    if isinstance(peso_inicial, bool) or not isinstance(peso_inicial, (int, float)) or float(peso_inicial) <= 0.0:
        raise GeradorError(f"peso_inicial deve ser > 0 (pseudo-contagem do prior), veio {peso_inicial!r}")
    for i, sinal in enumerate(sinais):
        if sinal.direcao not in ("sim", "nao"):
            raise GeradorError(f"sinal {i}: direcao deve ser 'sim' ou 'nao', veio {sinal.direcao!r}")
        if isinstance(sinal.peso, bool) or not isinstance(sinal.peso, (int, float)) or float(sinal.peso) <= 0.0:
            raise GeradorError(f"sinal {i}: peso deve ser > 0, veio {sinal.peso!r}")
        if not sinal.fonte or not sinal.fonte.strip():
            raise GeradorError(f"sinal {i}: fonte é obrigatória — sinal sem proveniência não entra")


def gerar_probabilidade(
    sinais: list[Sinal] | None = None,
    *,
    p_inicial: float = PRIOR_NEUTRO,
    peso_inicial: float = PESO_INICIAL_PADRAO,
) -> Probabilidade:
    """Probabilidade WPAM a partir de sinais ponderados. Sem sinal → p_inicial.

    O resultado carrega ``max_uncertainty=True`` quando fica no limiar (≈ 0,50),
    e as fontes de todos os sinais usados (proveniência auditável).
    """
    sinais = sinais or []
    _validar(p_inicial, peso_inicial, sinais)

    peso_sim = sum(float(s.peso) for s in sinais if s.direcao == "sim")
    peso_nao = sum(float(s.peso) for s in sinais if s.direcao == "nao")

    numerador = float(p_inicial) * float(peso_inicial) + peso_sim
    denominador = float(peso_inicial) + peso_sim + peso_nao
    valor = numerador / denominador  # denominador >= peso_inicial > 0, nunca zero

    return Probabilidade(
        valor=round(valor, 6),
        p_inicial=float(p_inicial),
        peso_inicial=float(peso_inicial),
        peso_sim=round(peso_sim, 6),
        peso_nao=round(peso_nao, 6),
        max_uncertainty=abs(valor - 0.5) <= UNCERTAINTY_TOLERANCE,
        fontes=sorted({s.fonte for s in sinais}),
    )
