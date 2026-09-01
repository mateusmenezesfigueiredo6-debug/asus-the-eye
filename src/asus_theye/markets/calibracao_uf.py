# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Calibração por Unidade da Federação: os 297 pontos, cabeados no modelo.

Resolve o problema descrito no plano do titular: com só o agregado nacional de
2022 (7 candidatos), a inferência conformal tem granularidade de 1/8 = 12,5%, e
95% de cobertura é **matematicamente impossível** — precisaria de 19 pontos.
Estimando por Unidade da Federação (na linha de Zheng, Li, Song & Jiang,
arXiv:2511.03555 — acertaram 44 de 44 estados nos EUA em 2024), os mesmos dados
de 2022 viram 27 UFs × 11 candidatos = **297 pontos**.

────────────────────────────────────────────────────────────────────────────
O QUE ISTO NÃO É, dito antes de qualquer fórmula

Estes 297 pontos são resíduos de **2022**, e a trava que corrigimos hoje
proíbe reaplicar parâmetro de um ciclo a outro sem declarar — foi o defeito do
beta 8,5 que o titular recusou duas vezes. Este módulo não infringe essa regra
porque não estima um parâmetro para 2026: ele mede uma coisa diferente e mais
estável, que é **quanto um número NACIONAL pode errar quando aplicado a um
estado específico**. É heterogeneidade geográfica do Brasil, não comportamento
de um candidato — e há boa razão para achar que isso muda mais devagar entre
ciclos do que a fatia de voto de cada nome.

Por isso toda faixa que sai daqui é produzida com
``conformal.intervalo(..., permutavel=False)`` — **indicativa**, nunca
garantida. A garantia da inferência conformal exige que o caso novo seja
intercambiável com a calibração, e misturar o campo eleitoral de 2026 com
resíduos de 2022 é, por definição, não ser o mesmo caso.
────────────────────────────────────────────────────────────────────────────

A CONTA. Para cada UF, aplica-se a fatia NACIONAL agregada de cada candidato e
mede-se o erro contra o resultado REAL daquela UF:

    resíduo(uf, candidato) = |fatia_nacional[candidato] − fatia_real[uf][candidato]|

297 desses resíduos, medidos em 30/08/2026: erro médio 2,38 pp, mediana
0,10 pp, pior estado 26,37 pp. A mediana baixa e o pior caso alto não se
contradizem — dizem que metade dos estados segue a média nacional de perto e um
punhado se desvia com força (histórico: Nordeste e Sul se moveram em direções
opostas em 2018 e 2022). A faixa de 95% precisa ser larga o bastante para cobrir
esse punhado: por isso ±17,82 pp, não um número pequeno.
"""

from __future__ import annotations

import json
import pathlib

from asus_theye.markets.conformal import ConformalError, Intervalo, intervalo
from asus_theye.markets.modelo_2026 import Modelo2026

#: Diferença entre a soma das 27 UFs e o boletim nacional de 2022 — é o voto
#: no exterior, que não tem UF. Conferido, não assumido: 117.935.194 vs
#: 118.229.719 = 294.525, e a proporção bate com o eleitorado consular.
VOTO_EXTERIOR_2022 = 294_525


class CalibracaoUFError(ConformalError):
    """Falha ao ler ou processar a base de calibração por UF."""


def carregar_uf2022(caminho: pathlib.Path | str) -> dict:
    """Lê o arquivo bruto de 27 UFs (TSE, ele2022/544, 1º turno)."""
    p = pathlib.Path(caminho)
    if not p.exists():
        raise CalibracaoUFError(f"base de UF não encontrada: {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise CalibracaoUFError(f"base de UF não é JSON válido: {exc}") from exc


def _fatia_nacional(dados_uf: dict) -> dict[str, float]:
    """Agrega os votos das 27 UFs por candidato e normaliza. Só leitura."""
    totais: dict[str, int] = {}
    for uf, v in dados_uf.items():
        cand = v.get("cand")
        if not isinstance(cand, dict):
            raise CalibracaoUFError(f"UF {uf!r} sem candidatos em formato esperado")
        for nome, c in cand.items():
            vap = c.get("vap")
            if not isinstance(vap, int):
                raise CalibracaoUFError(f"UF {uf!r}, candidato {nome!r}: vap ausente ou inválido")
            totais[nome] = totais.get(nome, 0) + vap
    soma = sum(totais.values())
    if soma <= 0:
        raise CalibracaoUFError("soma nacional de votos não positiva")
    return {k: v / soma for k, v in totais.items()}


def residuos_nacional_para_uf(dados_uf: dict) -> list[float]:
    """Os 297 resíduos: erro de aplicar o número nacional a cada estado.

    Fração, não percentual (0–0,2637, não 0–26,37) — a mesma escala que
    :class:`Modelo2026` usa em toda parte, evitando o exato defeito de escala
    0-1 vs 0-100 que a varredura estrutural de 30/08/2026 apontou entre
    ``fonte_tse`` e ``modelo_eleitoral``.
    """
    fatia_nac = _fatia_nacional(dados_uf)
    residuos: list[float] = []
    for uf, v in dados_uf.items():
        cand = v.get("cand", {})
        for nome, c in cand.items():
            previsto = fatia_nac.get(nome)
            if previsto is None:
                continue
            pvap = c.get("pvap")
            if not isinstance(pvap, (int, float)):
                raise CalibracaoUFError(f"UF {uf!r}, candidato {nome!r}: pvap ausente ou inválido")
            real = pvap / 100
            residuos.append(abs(previsto - real))
    if len(residuos) < 2:
        raise CalibracaoUFError(f"poucos resíduos calculados: {len(residuos)}")
    return residuos


def faixas_indicativas(
    modelo: Modelo2026, residuos: list[float], *, alpha: float = 0.05
) -> dict[str, Intervalo]:
    """Uma faixa indicativa por candidato, a partir da ordem que o modelo sustenta.

    Usa ``modelo.fatias(magnitude=False)`` — a leitura de ordem, não a
    magnitude encolhida — porque é essa a leitura que a evidência viva de hoje
    já sustenta. A faixa em volta dela é sempre ``permutavel=False``: nasce de
    resíduos de 2022, não de resultado do ciclo corrente.
    """
    centros = modelo.fatias(magnitude=False)
    return {
        candidato: intervalo(centro, residuos, alpha=alpha, permutavel=False)
        for candidato, centro in centros.items()
    }
