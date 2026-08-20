# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Entidades da ontologia de Evidência — nós tipados sobre o que já existe.

Cada entidade é um NÓ com ``tipo`` + ``id`` estável, projetado sobre os
artefatos versionados que já são a fonte da verdade (``reports/markets/*``).
Não há banco novo nem dado duplicado: a ontologia é uma camada de relações.

Ver docs/architecture/ONTOLOGIA_EVIDENCIA.md. A disciplina de modelagem
(entidade tipada + relações explícitas + linhagem) foi absorvida de
OpenMetadata/DataHub (Apache-2.0); nenhuma linha de código deles é usada.

L3 completou a spec: ``Artefato`` materializa de ``reports/markets/
artefatos.jsonl`` (dado bruto de Fonte oficial, com sha256 e retrieved_at) e
``Recibo`` materializa do RESULTADO REAL da verificação da corrente no momento
da montagem do grafo — estados ``valid|not_anchored|tampered`` como no
verificador público. Recibo atesta; dado não deriva dele.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Tipos de nó (enum fechado — nó de tipo desconhecido levanta no grafo).
FONTE = "Fonte"
MERCADO = "Mercado"
RESOLUCAO = "Resolucao"
EVENTO = "EventoSelado"
LOTE = "LoteMerkle"
ANCORA = "Ancora"
COMPARADOR = "Comparador"
ARTEFATO = "Artefato"
RECIBO = "Recibo"

TIPOS = (FONTE, MERCADO, RESOLUCAO, EVENTO, LOTE, ANCORA, COMPARADOR, ARTEFATO, RECIBO)

# Estados de Recibo — os mesmos que o verificador público devolve.
ESTADOS_DE_RECIBO = ("valid", "not_anchored", "anchor_unconfirmed", "tampered", "invalid")

Chave = tuple[str, str]  # (tipo, id)


@dataclass(frozen=True)
class No:
    """Um nó da ontologia: tipo do enum fechado, id estável, rótulo e dados."""

    tipo: str
    id: str
    rotulo: str
    dados: dict[str, Any] = field(default_factory=dict)

    @property
    def chave(self) -> Chave:
        return (self.tipo, self.id)

    def as_dict(self) -> dict[str, Any]:
        return {"tipo": self.tipo, "id": self.id, "rotulo": self.rotulo, "dados": self.dados}


def fonte(nome: str) -> No:
    return No(tipo=FONTE, id=nome, rotulo=nome)


def mercado(claim_id: str, *, area: str, pergunta: str, estado: str, probabilidade: float) -> No:
    return No(
        tipo=MERCADO,
        id=claim_id,
        rotulo=claim_id,
        dados={"area": area, "pergunta": pergunta, "estado": estado, "probabilidade": probabilidade},
    )


def resolucao(claim_id: str, *, outcome: int, brier: float, fonte_nome: str) -> No:
    # id próprio (res:) para não colidir com o Mercado de mesmo claim_id
    return No(
        tipo=RESOLUCAO,
        id=f"res:{claim_id}",
        rotulo=claim_id,
        dados={"outcome": outcome, "brier_do_contrato": brier, "fonte": fonte_nome},
    )


def evento(event_id: str, *, sequence: int, event_hash: str, correlation_id: str) -> No:
    return No(
        tipo=EVENTO,
        id=event_id,
        rotulo=f"seq {sequence}",
        dados={"sequence": sequence, "event_hash_sha256": event_hash, "correlation_id": correlation_id},
    )


def lote(batch_id: str, *, merkle_root: str, first_sequence: int, last_sequence: int) -> No:
    return No(
        tipo=LOTE,
        id=batch_id,
        rotulo=merkle_root[:16],
        dados={"merkle_root": merkle_root, "first_sequence": first_sequence, "last_sequence": last_sequence},
    )


def ancora(tx_hash: str, *, chain_id: int, contrato: str, block_number: int | None) -> No:
    return No(
        tipo=ANCORA,
        id=tx_hash,
        rotulo=tx_hash[:16],
        dados={"chain_id": chain_id, "contrato": contrato, "block_number": block_number},
    )


def comparador(nome: str = "Kalshi") -> No:
    return No(tipo=COMPARADOR, id=nome, rotulo=nome)


def artefato(artefato_id: str, *, fonte_nome: str, sha256: str, retrieved_at: str, descricao: str) -> No:
    """Dado bruto obtido de uma Fonte oficial, com hash — a evidência primária."""
    return No(
        tipo=ARTEFATO,
        id=artefato_id,
        rotulo=descricao or artefato_id,
        dados={"fonte": fonte_nome, "sha256": sha256, "retrieved_at": retrieved_at, "descricao": descricao},
    )


def recibo(estado: str, *, verificacoes: dict[str, Any]) -> No:
    """Resultado REAL de uma verificação da corrente (estados do verificador público)."""
    if estado not in ESTADOS_DE_RECIBO:
        raise ValueError(f"estado de Recibo desconhecido: {estado!r} (esperado um de {ESTADOS_DE_RECIBO})")
    return No(
        tipo=RECIBO,
        id=f"recibo:{estado}",
        rotulo=f"verificação: {estado}",
        dados={"estado": estado, "verificacoes": verificacoes},
    )
