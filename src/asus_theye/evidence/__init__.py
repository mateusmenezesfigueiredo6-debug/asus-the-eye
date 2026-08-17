"""Ontologia de Evidência — objetos tipados, relações e linhagem verificável.

A camada que dá substância ao app "THE EYE — Evidência" (benchmark de
arquitetura: Palantir). Ver docs/architecture/ONTOLOGIA_EVIDENCIA.md.
"""

from __future__ import annotations

from asus_theye.evidence.entidades import TIPOS, No
from asus_theye.evidence.grafo import (
    Aresta,
    Grafo,
    GrafoError,
    construir_grafo,
    fontes_de,
    linhagem_ascendente,
)

__all__ = [
    "TIPOS",
    "Aresta",
    "Grafo",
    "GrafoError",
    "No",
    "construir_grafo",
    "fontes_de",
    "linhagem_ascendente",
]
