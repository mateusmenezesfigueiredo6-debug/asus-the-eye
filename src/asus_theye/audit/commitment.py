# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Commitment de prognóstico — o que sai de casa é C, nunca o número.

Por que HMAC com nonce e não sha256 puro (achado do auditor-de-sabotagem,
04/09/2026): um prognóstico eleitoral tem entropia baixíssima — ~13 candidatos
com probabilidade a 4 casas dá um espaço da ordem de 10^5 mensagens. Quem tem
sha256(prognóstico) enumera o espaço em milissegundos e lê o número. O
compromisso seria *binding* (não dá para trocar depois) mas não *hiding* (dá
para ler antes) — o oposto do que uma trava precisa. Com um nonce de 256 bits
que só o titular guarda, a força bruta deixa de existir: sem o nonce não há
como recomputar, e com ele qualquer um recomputa. O teste em
tests/audit/test_commitment.py prova as duas metades.

Regras que este módulo IMPÕE, não só documenta:
  1. serialização canônica congelada — chaves ordenadas, sem espaço, UTF-8,
     floats arredondados a CASAS. Alterar isto quebra toda revelação passada.
  2. nonce de NONCE_BYTES, novo a cada compromisso — nunca reusado.
  3. a data de abertura vai DENTRO do payload comprometido: escolher *quando*
     abrir é outra forma de seleção, e o commitment tem de fixar isso também.
  4. lote = Merkle sobre TODAS as corridas, com o número de folhas e o esquema
     de nomes no elo — comprometer 40 e revelar as 6 que acertaram fabrica um
     Brier; com n_folhas público, a revelação parcial é detectável.

O que este módulo NÃO faz: não impede egresso. Commitment registra; trava
impede (bind em loopback, publish_guard). São peças diferentes.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Any

NONCE_BYTES = 32
CASAS = 4
CHAVE_ABERTURA = "_abertura"

__all__ = [
    "CASAS",
    "CHAVE_ABERTURA",
    "NONCE_BYTES",
    "CommitmentError",
    "LoteDeCompromissos",
    "comprometer",
    "comprometer_lote",
    "raiz_merkle",
    "revelar",
    "revelar_lote",
    "serializar_canonico",
]


class CommitmentError(ValueError):
    """Entrada que tornaria o compromisso inverificável ou inseguro."""


def _arredondar(v: Any) -> Any:
    if isinstance(v, bool):
        return v
    if isinstance(v, float):
        return round(v, CASAS)
    if isinstance(v, dict):
        return {str(k): _arredondar(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_arredondar(x) for x in v]
    return v


def serializar_canonico(prognostico: dict[str, Any]) -> bytes:
    """A forma congelada. Mesmo conteúdo → mesmos bytes, sempre.

    NaN e infinito são rejeitados: json os aceitaria e a revelação nunca
    bateria, porque NaN != NaN.
    """
    if not isinstance(prognostico, dict):
        raise CommitmentError("prognóstico tem de ser dict")
    try:
        return json.dumps(
            _arredondar(prognostico),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except ValueError as e:  # allow_nan=False levanta ValueError
        raise CommitmentError(f"valor não serializável: {e}") from e


def comprometer(
    prognostico: dict[str, Any], nonce: bytes | None = None
) -> tuple[str, bytes]:
    """Devolve (C, nonce). Publica-se C; o nonce fica com o titular até a abertura."""
    if nonce is None:
        nonce = os.urandom(NONCE_BYTES)
    if not isinstance(nonce, (bytes, bytearray)) or len(nonce) < NONCE_BYTES:
        raise CommitmentError(f"nonce tem de ter ao menos {NONCE_BYTES} bytes")
    c = hmac.new(bytes(nonce), serializar_canonico(prognostico), hashlib.sha256).hexdigest()
    return c, bytes(nonce)


def revelar(compromisso: str, prognostico: dict[str, Any], nonce: bytes) -> bool:
    """Qualquer terceiro roda isto com (prognóstico, nonce) e o C publicado."""
    try:
        esperado, _ = comprometer(prognostico, nonce)
    except CommitmentError:
        return False
    return hmac.compare_digest(esperado, compromisso)


def raiz_merkle(folhas: list[str]) -> str:
    """Par a par, duplicando a última quando ímpar — o mesmo desenho de
    ~/.the-eye/ancorar_politica.py, para que a âncora externa já existente
    entenda esta raiz sem adaptação."""
    if not folhas:
        return "0" * 64
    nivel = sorted(folhas)
    while len(nivel) > 1:
        if len(nivel) % 2:
            nivel.append(nivel[-1])
        nivel = [
            hashlib.sha256((nivel[i] + nivel[i + 1]).encode()).hexdigest()
            for i in range(0, len(nivel), 2)
        ]
    return nivel[0]


@dataclass(frozen=True)
class LoteDeCompromissos:
    """O que vai para o elo da corrente. Não carrega prognóstico nem nonce."""

    data_calculo: str
    data_abertura: str
    n_folhas: int
    esquema_nomes: tuple[str, ...]
    compromissos: dict[str, str]
    raiz: str

    def payload(self) -> dict[str, Any]:
        return {
            "data_calculo": self.data_calculo,
            "data_abertura": self.data_abertura,
            "n_folhas": self.n_folhas,
            "esquema_nomes": list(self.esquema_nomes),
            "compromissos": dict(self.compromissos),
            "raiz_merkle": self.raiz,
            "serializacao": f"json sort_keys sem espaço utf-8 floats {CASAS} casas; "
            f"HMAC-SHA256(nonce {NONCE_BYTES}B, canônico); "
            f"{CHAVE_ABERTURA} injetada em cada corrida",
        }


def comprometer_lote(
    prognosticos: dict[str, dict[str, Any]],
    *,
    data_calculo: str,
    data_abertura: str,
) -> tuple[LoteDeCompromissos, dict[str, bytes]]:
    """Compromete TODAS as corridas de uma vez.

    A data de abertura entra em cada prognóstico antes do HMAC: quem revelar
    com outra data não bate. O esquema de nomes e n_folhas vão para o elo, então
    revelar menos corridas do que foram comprometidas fica visível.
    """
    if not prognosticos:
        raise CommitmentError("lote vazio não é compromisso")
    if not data_abertura or not data_calculo:
        raise CommitmentError("data_calculo e data_abertura são obrigatórias")
    compromissos: dict[str, str] = {}
    nonces: dict[str, bytes] = {}
    for nome in sorted(prognosticos):
        p = dict(prognosticos[nome])
        if CHAVE_ABERTURA in p and p[CHAVE_ABERTURA] != data_abertura:
            raise CommitmentError(f"{nome}: {CHAVE_ABERTURA} diverge da data do lote")
        p[CHAVE_ABERTURA] = data_abertura
        c, n = comprometer(p)
        compromissos[nome] = c
        nonces[nome] = n
    lote = LoteDeCompromissos(
        data_calculo=data_calculo,
        data_abertura=data_abertura,
        n_folhas=len(compromissos),
        esquema_nomes=tuple(sorted(compromissos)),
        compromissos=compromissos,
        raiz=raiz_merkle(list(compromissos.values())),
    )
    return lote, nonces


def revelar_lote(
    lote_payload: dict[str, Any],
    prognosticos: dict[str, dict[str, Any]],
    nonces: dict[str, bytes],
) -> dict[str, bool]:
    """Verifica cada corrida contra o elo publicado. Revelação parcial aparece
    como False nas corridas ausentes — nunca some silenciosamente."""
    resultado: dict[str, bool] = {}
    abertura = lote_payload["data_abertura"]
    for nome in lote_payload["esquema_nomes"]:
        if nome not in prognosticos or nome not in nonces:
            resultado[nome] = False
            continue
        p = dict(prognosticos[nome])
        p[CHAVE_ABERTURA] = abertura
        resultado[nome] = revelar(lote_payload["compromissos"][nome], p, nonces[nome])
    raiz_ok = raiz_merkle(list(lote_payload["compromissos"].values())) == lote_payload["raiz_merkle"]
    if not raiz_ok:
        resultado = {k: False for k in resultado}
    return resultado
