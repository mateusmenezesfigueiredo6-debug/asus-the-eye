# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Contrato de esquema do store de mercados (``reports/markets/``) — versão 1.

O store vivo é JSONL/JSON puro escrito por ``live.py`` e vizinhos, e até hoje o
único guarda era ``live._validar_mercado`` — que cobre SÓ o ``registro.json``.
Os outros nove arquivos não tinham contrato nenhum: um campo renomeado num
writer quebraria um reader semanas depois, em silêncio. Este módulo é a fonte
única do contrato, e ``validar_store()`` é o verificador que a suíte executa
contra o store REAL a cada rodada de testes.

Decisão de desenho (F1 do plano de 01/09/2026): **JSONL continua canônico**;
DuckDB permanece ponte de leitura. Este contrato é o que uma migração futura
(v2) terá de declarar que muda — ver ``migrations/0002_markets_store_v1.md``.

O que o contrato exige, por arquivo:

- campos OBRIGATÓRIOS por linha (o núcleo que os readers consomem — writers
  podem acrescentar campos novos sem quebrar o contrato: acrescentar é
  compatível, remover/renomear não é);
- probabilidades em [0, 1]; hashes com o comprimento certo;
- ``registro.json`` validado pelo guarda que já existe (``_validar_mercado``),
  nunca por uma cópia dele;
- ``eventos.jsonl`` verificado pela corrente (``verify_chain``) e pelo schema
  de 37 campos (``validate_event``) — reuso, não reimplementação;
- arquivo ``*.jsonl``/``*.json`` DESCONHECIDO na raiz do store é violação:
  ninguém cria tabela nova sem declarar aqui.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VERSAO_DO_STORE = 1

BASE_PADRAO = Path("reports/markets")

# Campos que os READERS de cada arquivo consomem hoje. Medido no store real em
# 01/09/2026 e conferido contra os writers. Acrescentar campo novo num writer
# NÃO exige mudar aqui (compatível); remover ou renomear EXIGE migração.
CAMPOS_POR_ARQUIVO: dict[str, frozenset[str]] = {
    "resolucoes.jsonl": frozenset(
        {
            "claim_id", "market_area_id", "outcome", "resolution_source",
            "resolved_at", "determination_date", "determination_basis",
            "valor_observado", "probability", "brier_do_contrato",
            "criterio", "mes_referencia",
        }
    ),
    "serie_p.jsonl": frozenset(
        {
            "claim_id", "market_area_id", "observado_em", "probability",
            "deadline", "horizonte_dias", "origem", "metodo", "ponto_id",
        }
    ),
    "vintage_focus.jsonl": frozenset(
        {
            "mes_referencia", "indicador", "mediana", "data_do_boletim",
            "fonte", "capturado_em", "metodo", "vintage_id",
        }
    ),
    "comparador.jsonl": frozenset(
        {
            "claim_id", "our_probability", "comparator", "comparator_price",
            "divergence", "recorded_at",
        }
    ),
    "cobertura_gdelt.jsonl": frozenset(
        {
            "pais_fips", "eventos", "tom_medio", "arquivo", "md5_do_arquivo",
            "observado_em", "suficiente", "licenca",
        }
    ),
    "legado_retrospectivo.jsonl": frozenset(
        {
            "claim_id", "market_area_id", "question", "created_at",
            "deadline", "probability",
        }
    ),
    "ancoras.jsonl": frozenset({"manifest", "ancora", "registrado_em"}),
    "artefatos.jsonl": frozenset({"id", "fonte", "sha256", "retrieved_at", "caminho"}),
}

# Probabilidades: nome do campo -> arquivo(s) onde ele é fração de [0, 1].
_CAMPOS_DE_PROBABILIDADE: dict[str, frozenset[str]] = {
    "probability": frozenset({"resolucoes.jsonl", "serie_p.jsonl", "legado_retrospectivo.jsonl"}),
    "our_probability": frozenset({"comparador.jsonl"}),
    "comparator_price": frozenset({"comparador.jsonl"}),
}

# Arquivos da raiz do store com tratamento próprio (não são tabelas JSONL).
_TRATAMENTO_PROPRIO = frozenset({"registro.json", "eventos.jsonl", "contrato.json"})


def _linhas(caminho: Path) -> list[tuple[int, dict[str, Any] | None, str]]:
    """(nº da linha, objeto ou None se não parseia, erro)."""
    saida: list[tuple[int, dict[str, Any] | None, str]] = []
    for n, bruto in enumerate(caminho.read_text(encoding="utf-8").splitlines(), start=1):
        if not bruto.strip():
            continue
        try:
            saida.append((n, json.loads(bruto), ""))
        except json.JSONDecodeError as erro:
            saida.append((n, None, str(erro)))
    return saida


def _validar_tabela(caminho: Path, obrigatorios: frozenset[str]) -> list[str]:
    violacoes: list[str] = []
    for n, linha, erro in _linhas(caminho):
        if linha is None:
            violacoes.append(f"{caminho.name}:{n}: JSON inválido — {erro}")
            continue
        faltando = sorted(obrigatorios - linha.keys())
        if faltando:
            violacoes.append(f"{caminho.name}:{n}: campos ausentes {faltando}")
        for campo, onde in _CAMPOS_DE_PROBABILIDADE.items():
            if caminho.name not in onde or campo not in linha:
                continue
            valor = linha[campo]
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not 0.0 <= float(valor) <= 1.0:
                violacoes.append(f"{caminho.name}:{n}: {campo}={valor!r} fora de [0, 1]")
        sha = linha.get("sha256")
        if caminho.name == "artefatos.jsonl" and (not isinstance(sha, str) or len(sha) != 64):
            violacoes.append(f"{caminho.name}:{n}: sha256 com comprimento {len(str(sha))}, esperado 64")
    return violacoes


def _validar_registro(caminho: Path) -> list[str]:
    from asus_theye.markets.live import LiveMarketError, _validar_mercado

    try:
        registro = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        return [f"{caminho.name}: JSON inválido — {erro}"]
    violacoes: list[str] = []
    versao = registro.get("versao")
    if versao != VERSAO_DO_STORE:
        violacoes.append(f"{caminho.name}: versao={versao!r}, contrato atual é {VERSAO_DO_STORE}")
    for mercado in registro.get("mercados", []):
        try:
            _validar_mercado(mercado)
        except LiveMarketError as erro:
            violacoes.append(f"{caminho.name}: {erro}")
    return violacoes


def _validar_eventos(caminho: Path) -> list[str]:
    from asus_theye.audit.schema import validate_event
    from asus_theye.audit.verifier import verify_chain

    violacoes: list[str] = []
    eventos: list[dict[str, Any]] = []
    for n, linha, erro in _linhas(caminho):
        if linha is None:
            violacoes.append(f"{caminho.name}:{n}: JSON inválido — {erro}")
            continue
        try:
            validate_event(linha)
        except Exception as falha:  # noqa: BLE001 - o schema levanta tipos próprios
            violacoes.append(f"{caminho.name}:{n}: {falha}")
        eventos.append(linha)
    if eventos and not violacoes and not verify_chain(eventos):
        violacoes.append(f"{caminho.name}: corrente NÃO verifica (hash ou encadeamento)")
    return violacoes


def validar_store(base: Path = BASE_PADRAO) -> list[str]:
    """Valida o store inteiro contra o contrato v1. Devolve as violações.

    Lista vazia = store íntegro. Cada violação é uma linha humana com
    ``arquivo:linha`` na frente — pronta para ir num relatório ou num assert.
    """
    if not base.exists():
        return [f"{base}: store não existe"]
    violacoes: list[str] = []
    for caminho in sorted(base.iterdir()):
        nome = caminho.name
        if caminho.is_dir() or nome.startswith(".") or nome.endswith(".lock"):
            continue  # subpastas (cobertura/, vintage/) e travas têm dono próprio
        if caminho.suffix not in {".json", ".jsonl"}:
            continue  # o contrato rege TABELAS; docs (.md) e chave.fingerprint
            # (a impressão digital que auditoria.py manda versionar junto da
            # corrente) não são tabelas
        if nome == "registro.json":
            violacoes.extend(_validar_registro(caminho))
        elif nome == "eventos.jsonl":
            violacoes.extend(_validar_eventos(caminho))
        elif nome in CAMPOS_POR_ARQUIVO:
            violacoes.extend(_validar_tabela(caminho, CAMPOS_POR_ARQUIVO[nome]))
        elif nome in _TRATAMENTO_PROPRIO:
            continue  # contrato.json: metadado de deploy, sem tabela
        else:
            violacoes.append(
                f"{nome}: arquivo fora do contrato do store — tabela nova exige "
                "declaração em esquema_store.CAMPOS_POR_ARQUIVO (e migração se mudar as existentes)"
            )
    return violacoes
