# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Atlas de CONHECIMENTO — camada de metadados consultável do super-cérebro.
(R7.5 alavanca C, 02/09/2026)

DISTINÇÃO QUE ESTE MÓDULO EXISTE PARA PRESERVAR (achado do explorador):
- `atlas_algoritmos.py` (Atlas v0) é o catálogo EXECUTÁVEL — id → adaptador
  statsforecast + proveniência. Só entra ali algoritmo com implementação
  instalada e benchmark. É o que o motor RODA.
- ESTE módulo é o catálogo de CONHECIMENTO — os ~654 nomes/algoritmos/fontes
  ranqueados que a casa ESTUDA (pessoas incluídas). É o que o motor CITA como
  proveniência de método, NUNCA o que ele executa. Pessoa (mestre) jamais vira
  modelo executável — por isso os dois catálogos ficam separados de propósito.

Fonte de dados: INDICE-MESTRE.csv (gerado por montar-indice-mestre.py, esquema
canônico de 13 colunas). O loader é FAIL-SOFT: se o índice não existir ainda
(ele nasce no shell), devolve um atlas vazio sem quebrar — o motor segue
funcionando sem a camada de conhecimento.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

CAMINHO_PADRAO = (
    Path.home() / "Área de trabalho" / "algoritmos" / "INDICE-MESTRE.csv"
)

CAMPOS = (
    "segmento", "id", "tipo", "nome", "autoria", "afiliacao_ou_org",
    "obra_ou_o_que_faz", "url", "licenca", "ano", "premios",
    "criticas_e_validade", "rank",
)


@dataclass(frozen=True)
class Entrada:
    """Uma linha do catálogo de conhecimento. `tipo` ∈ {pessoa, algoritmo, fonte}."""
    segmento: str
    id: str
    tipo: str
    nome: str
    autoria: str
    afiliacao_ou_org: str
    obra_ou_o_que_faz: str
    url: str
    licenca: str
    ano: str
    premios: str
    criticas_e_validade: str
    rank: str

    @property
    def rank_num(self) -> int:
        try:
            return int(self.rank)
        except (TypeError, ValueError):
            return 0

    @property
    def tem_critica(self) -> bool:
        """Regra da casa: achado sem crítica/validade declarada é suspeito."""
        return bool(self.criticas_e_validade.strip()) and \
            self.criticas_e_validade.strip() != "-"


class AtlasConhecimento:
    """Catálogo de conhecimento consultável. Somente leitura, agnóstico de domínio."""

    def __init__(self, entradas: list[Entrada]):
        self._entradas = entradas

    @classmethod
    def carregar(cls, caminho: Path | None = None) -> "AtlasConhecimento":
        caminho = caminho or CAMINHO_PADRAO
        if not caminho.exists():
            return cls([])  # fail-soft: índice ainda não gerado no shell
        entradas: list[Entrada] = []
        with open(caminho, encoding="utf-8", newline="") as f:
            leitor = csv.DictReader(f, delimiter=";")
            faltando = set(CAMPOS) - set(leitor.fieldnames or [])
            if faltando:
                raise ValueError(
                    f"INDICE-MESTRE.csv sem colunas canônicas: {sorted(faltando)}"
                )
            for linha in leitor:
                entradas.append(Entrada(**{c: (linha.get(c) or "").strip() for c in CAMPOS}))
        return cls(entradas)

    def __len__(self) -> int:
        return len(self._entradas)

    def por_segmento(self, segmento: str) -> list[Entrada]:
        return [e for e in self._entradas if e.segmento == segmento]

    def por_tipo(self, tipo: str) -> list[Entrada]:
        return [e for e in self._entradas if e.tipo == tipo]

    def topo(self, segmento: str | None = None, mínimo: int = 5) -> list[Entrada]:
        """Entradas com rank >= mínimo, as mais fortes primeiro."""
        alvo = self.por_segmento(segmento) if segmento else self._entradas
        return sorted(
            (e for e in alvo if e.rank_num >= mínimo),
            key=lambda e: e.rank_num, reverse=True,
        )

    def proveniencia(self, id_: str) -> Entrada | None:
        """Metadado de proveniência de um método para CITAR na calibração —
        nunca para executar. Devolve None se o id não estiver no catálogo."""
        for e in self._entradas:
            if e.id == id_:
                return e
        return None

    def sem_critica(self) -> list[Entrada]:
        """Auditoria de qualidade: entradas sem crítica/validade declarada."""
        return [e for e in self._entradas if not e.tem_critica]

    def segmentos(self) -> dict[str, int]:
        cont: dict[str, int] = {}
        for e in self._entradas:
            cont[e.segmento] = cont.get(e.segmento, 0) + 1
        return dict(sorted(cont.items()))
