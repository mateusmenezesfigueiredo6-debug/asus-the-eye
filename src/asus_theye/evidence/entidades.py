"""Entidades da ontologia de Evidência — nós tipados sobre o que já existe.

Cada entidade é um NÓ com ``tipo`` + ``id`` estável, projetado sobre os
artefatos versionados que já são a fonte da verdade (``reports/markets/*``).
Não há banco novo nem dado duplicado: a ontologia é uma camada de relações.

Ver docs/architecture/ONTOLOGIA_EVIDENCIA.md. A disciplina de modelagem
(entidade tipada + relações explícitas + linhagem) foi absorvida de
OpenMetadata/DataHub (Apache-2.0); nenhuma linha de código deles é usada.
``Artefato`` e ``Recibo`` estão na spec mas são transitórios (não materializados
a partir do dado atual): entram quando houver artefato/recibo persistido.
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

TIPOS = (FONTE, MERCADO, RESOLUCAO, EVENTO, LOTE, ANCORA, COMPARADOR)

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
