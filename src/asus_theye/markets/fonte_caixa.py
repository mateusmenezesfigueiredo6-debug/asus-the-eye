# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: Loterias Caixa — Mega-Sena, Quina, Lotofácil, Lotomania.

Loteria é o evento que mais brasileiro acompanha por semana, o resultado sai
minutos depois do sorteio e não muda mais. Isso lhe dá qualidade de liquidação
comparável à de um índice oficial: número sorteado não se retifica.

POR QUE QUATRO E NÃO UMA. A Mega-Sena sorteia 3 vezes por semana; Quina e
Lotofácil, 6. Como o ativo que estamos construindo é a série de acerto medido
(Brier), e ela só cresce com contrato LIQUIDADO, a frequência de sorteio é o
que determina a velocidade de acumulação. Quatro loterias multiplicam por
cinco o número de desfechos por semana, com o mesmo conector.

O QUE NÃO COTAMOS, E POR QUÊ. "Vai acumular?" é a pergunta óbvia e está fora:
nos 45 concursos de Mega-Sena lidos da própria API, acumulou em 82,2% deles —
nasceria fora da faixa de exibição da casa (28..72¢) e não informaria nada.
Pelo mesmo critério ficou de fora "2 ou mais pares na Quina" (76,7% em 30
concursos). Os limiares em uso saíram da MEDIANA de 30 concursos reais lidos
de cada loteria, e todos caem entre 50% e 67% de frequência histórica.

A FAIXA QUE COTAMOS É A SECUNDÁRIA, não a principal. Acertar tudo quase sempre
dá zero ganhador — número que não varia não informa. A segunda faixa tem
dezenas ou centenas de ganhadores e mexe de concurso para concurso.

PERÍODO É O DIA DO SORTEIO. A API é indexada por número de concurso, não por
data, então o conector lê o concurso corrente e só devolve valor se a
``dataApuracao`` for exatamente o dia pedido. Dia sem sorteio — ou sorteio que
ainda não aconteceu — é ``None`` (UNKNOWN), nunca um palpite sobre o concurso
errado.

RESSALVA DE PROCEDÊNCIA, dita na cara: este endpoint é o backend que alimenta
``loterias.caixa.gov.br`` e **não é uma API pública documentada**. A fonte legal
do resultado é o portal da Caixa; o JSON é espelho técnico, substituível. Se o
layout mudar, este módulo levanta em vez de adivinhar.
"""

from __future__ import annotations

import json
import re

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

URL_LOTERIA = "https://servicebus2.caixa.gov.br/portaldeloterias/api/{loteria}"
MAX_BYTES = 400_000
TIMEOUT = 30

#: As loterias que este conector lê, com o que caracteriza cada uma. A tabela
#: existe para o conector RECUSAR resultado impossível: Lotofácil sorteia 15
#: dezenas de 1 a 25 e Lotomania sorteia 20 de 0 a 99 — validar todas contra a
#: régua da Mega-Sena (6 de 1 a 60) aceitaria lixo numas e rejeitaria dado bom
#: nas outras. O zero da Lotomania é o caso que prova o ponto: é dezena
#: legítima lá e impossível em qualquer outra.
#: Faixas conferidas ao vivo em 30/08/2026, uma requisição por loteria.
LOTERIAS: dict[str, dict] = {
    "megasena":   {"dezenas": 6,  "minimo": 1, "maximo": 60, "secundaria": "5 acertos"},
    "quina":      {"dezenas": 5,  "minimo": 1, "maximo": 80, "secundaria": "4 acertos"},
    "lotofacil":  {"dezenas": 15, "minimo": 1, "maximo": 25, "secundaria": "14 acertos"},
    "lotomania":  {"dezenas": 20, "minimo": 0, "maximo": 99, "secundaria": "19 acertos"},
    "duplasena":  {"dezenas": 6,  "minimo": 1, "maximo": 50, "secundaria": "5 acertos"},
    "timemania":  {"dezenas": 7,  "minimo": 1, "maximo": 80, "secundaria": "6 acertos"},
    "diadesorte": {"dezenas": 7,  "minimo": 1, "maximo": 31, "secundaria": "6 acertos"},
    # O Super Sete não sorteia dezenas de um volante único: são 7 COLUNAS
    # independentes, cada uma de 0 a 9. Por isso repete — em 20 concursos
    # lidos, 19 tinham dígito repetido (95%). A regra "todas distintas", que
    # é correta em todas as outras, rejeitaria quase todo sorteio válido aqui.
    # Mesmo tipo de erro do zero da Lotomania: régua de uma loteria aplicada
    # a outra.
    "supersete":  {"dezenas": 7,  "minimo": 0, "maximo": 9,  "secundaria": "6 acertos",
                   "permite_repetida": True},
}

#: Dia do sorteio, ``aaaa-mm-dd``. Estrito: o dia é o que amarra o contrato ao
#: concurso, e uma data reformatada em silêncio ligaria o mercado a outro sorteio.
DIA_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")

class FonteCaixaError(FonteError):
    """Resposta inesperada da Caixa. Sempre levanta — nunca degrada em valor."""


def _config(loteria: str) -> dict:
    cfg = LOTERIAS.get(loteria)
    if cfg is None:
        raise FonteCaixaError(f"loteria {loteria!r} fora do registro: {sorted(LOTERIAS)}")
    return cfg


def _dia_br(dia: str) -> str:
    """``aaaa-mm-dd`` -> ``dd/mm/aaaa``, o formato que a Caixa publica."""
    if not isinstance(dia, str) or not DIA_RE.match(dia):
        raise FonteCaixaError(f"dia do sorteio em formato inesperado: {dia!r}")
    ano, mes, d = dia.split("-")
    return f"{d}/{mes}/{ano}"


def _concurso(dia: str, *, loteria: str = "megasena", transport: Transport | None = None) -> dict | None:
    """Concurso apurado em ``dia``, ou ``None`` se ainda não houve."""
    _config(loteria)
    esperado = _dia_br(dia)
    url = URL_LOTERIA.format(loteria=loteria)
    try:
        response = get_bytes(
            url,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteCaixaError(f"fonte inalcançável: {exc}") from exc
    if response.status != 200:
        raise FonteCaixaError(f"Caixa respondeu HTTP {response.status} em {url}")

    try:
        dados = json.loads(response.body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FonteCaixaError(f"resposta da Caixa não é JSON válido ({exc})") from exc
    if not isinstance(dados, dict):
        raise FonteCaixaError(f"resposta da Caixa em formato inesperado: {type(dados).__name__}")
    if "dataApuracao" not in dados or "listaDezenas" not in dados:
        raise FonteCaixaError(f"resposta da Caixa sem os campos esperados: {sorted(dados)[:8]}")

    # O concurso corrente ainda não é o do dia pedido: o sorteio não aconteceu.
    if str(dados["dataApuracao"]).strip() != esperado:
        return None
    return dados


def _dezenas(concurso: dict, loteria: str = "megasena") -> list[int]:
    cfg = _config(loteria)
    bruto = concurso.get("listaDezenas")
    if not isinstance(bruto, list) or len(bruto) != cfg["dezenas"]:
        raise FonteCaixaError(
            f"{loteria}: esperava {cfg['dezenas']} dezenas sorteadas, veio {bruto!r}"
        )
    try:
        dezenas = [int(str(d).strip()) for d in bruto]
    except ValueError as exc:
        raise FonteCaixaError(f"dezena não numérica no resultado: {bruto!r}") from exc
    if any(not cfg["minimo"] <= d <= cfg["maximo"] for d in dezenas):
        raise FonteCaixaError(
            f"{loteria}: dezena fora do volante {cfg['minimo']}..{cfg['maximo']}: {dezenas!r}"
        )
    if not cfg.get("permite_repetida") and len(set(dezenas)) != cfg["dezenas"]:
        raise FonteCaixaError(f"{loteria}: dezena repetida no mesmo sorteio: {dezenas!r}")
    return dezenas


def soma_das_dezenas(dia: str, *, loteria: str = "megasena",
                     transport: Transport | None = None) -> float | None:
    """Soma das dezenas sorteadas no concurso apurado em ``dia``."""
    concurso = _concurso(dia, loteria=loteria, transport=transport)
    if concurso is None:
        return None
    return float(sum(_dezenas(concurso, loteria)))


def dezenas_pares(dia: str, *, loteria: str = "megasena",
                  transport: Transport | None = None) -> float | None:
    """Quantas das dezenas sorteadas são pares."""
    concurso = _concurso(dia, loteria=loteria, transport=transport)
    if concurso is None:
        return None
    return float(sum(1 for d in _dezenas(concurso, loteria) if d % 2 == 0))


def ganhadores_da_quina(dia: str, *, loteria: str = "megasena",
                        transport: Transport | None = None) -> float | None:
    """Apostas premiadas na faixa SECUNDÁRIA do concurso apurado em ``dia``.

    A faixa principal (acertar tudo) quase sempre dá zero — não informa nada.
    A secundária tem dezenas ou centenas de ganhadores e varia de verdade.
    O nome da função ficou por compatibilidade: na Mega-Sena a secundária É a
    quina.
    """
    concurso = _concurso(dia, loteria=loteria, transport=transport)
    if concurso is None:
        return None
    faixas = concurso.get("listaRateioPremio")
    if not isinstance(faixas, list) or not faixas:
        raise FonteCaixaError(f"resultado sem as faixas de premiação: {faixas!r}")
    for faixa in faixas:
        if not isinstance(faixa, dict):
            raise FonteCaixaError(f"faixa de premiação em formato inesperado: {faixa!r}")
        if str(faixa.get("descricaoFaixa", "")).strip() == _config(loteria)["secundaria"]:
            ganhadores = faixa.get("numeroDeGanhadores")
            if isinstance(ganhadores, bool) or not isinstance(ganhadores, int):
                raise FonteCaixaError(f"número de ganhadores não inteiro: {ganhadores!r}")
            if ganhadores < 0:
                raise FonteCaixaError(f"número de ganhadores negativo: {ganhadores!r}")
            return float(ganhadores)
    raise FonteCaixaError(
        f"faixa {_config(loteria)['secundaria']!r} não veio no resultado — a Caixa mudou os rótulos: "
        f"{[f.get('descricaoFaixa') for f in faixas]}"
    )
