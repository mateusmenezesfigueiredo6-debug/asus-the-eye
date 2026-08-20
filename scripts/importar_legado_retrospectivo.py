#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Importa as 40 liquidações legislativas legadas como retrospectivas.

O modo padrão é apenas uma simulação. A escrita exige ``--execute`` e nunca
altera o DuckDB de origem, aberto explicitamente em modo somente leitura.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import math
import os
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

STORE = Path("reports/markets/legado_retrospectivo.jsonl")
LOCK = Path("reports/markets/.lock-legado-retrospectivo")
SPEC = "reports/markets/M5_IMPORT_SPEC.md"
EXPECTED_ROWS = 40
EXPECTED_DB_SHA256 = "61ab92d4529071663d9c3715c634408d879fe9de829833355acf652d4bc0b5b5"
MOTIVO = "M5_IMPORT_SPEC: criado cerca de 11 dias após a votação; fonte oficial não comprovada no banco."

QUERY = """
SELECT
    m.id AS claim_id,
    m.produto AS legacy_product,
    m.etiqueta AS legacy_label,
    m.pergunta_leiga AS question,
    m.data_abertura AS created_at,
    m.data_limite AS deadline,
    m.fonte_resolucao AS declared_resolution_source,
    m.criterio_resolucao AS resolution_criterion,
    m.status AS legacy_status,
    c.timestamp AS quoted_at,
    c.probabilidade AS probability,
    c.metodo AS probability_method,
    r.timestamp AS resolved_at,
    r.resultado_real AS outcome,
    r.brier_do_contrato AS brier_do_contrato,
    r.fonte_confirmacao AS resolution_source
FROM mercados AS m
JOIN cotacoes AS c ON c.mercado_id = m.id
JOIN resolucoes AS r ON r.mercado_id = m.id
WHERE m.produto = 'voto_legislativo'
  AND m.status = 'LIQUIDADO'
ORDER BY m.id
"""


class ImportacaoError(RuntimeError):
    """O lote não satisfaz o contrato M5 ou não pode ser importado."""


def _sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as stream:
        for bloco in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _instante_com_timezone(valor: Any, campo: str, claim_id: str, *, adicionar_z: bool = False) -> str:
    texto = str(valor)
    try:
        instante = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ImportacaoError(f"{claim_id}: {campo} não é ISO 8601: {texto!r}") from exc
    if instante.tzinfo is None and adicionar_z:
        texto += "Z"
        instante = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    if instante.tzinfo is None:
        raise ImportacaoError(f"{claim_id}: {campo} não contém timezone: {texto!r}")
    return texto


def _ler_duckdb(caminho: Path) -> list[dict[str, Any]]:
    try:
        import duckdb
    except ImportError as exc:  # pragma: no cover - depende do ambiente de execução
        raise ImportacaoError("dependência duckdb ausente; instale o extra 'markets'") from exc

    try:
        with duckdb.connect(str(caminho), read_only=True) as conexao:
            cursor = conexao.execute(QUERY)
            colunas = [item[0] for item in cursor.description]
            return [dict(zip(colunas, linha, strict=True)) for linha in cursor.fetchall()]
    except Exception as exc:
        raise ImportacaoError(f"falha ao ler o DuckDB legado em modo somente leitura: {exc}") from exc


def _validar_e_normalizar(linhas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if len(linhas) != EXPECTED_ROWS:
        raise ImportacaoError(f"recorte M5 divergente: esperadas 40 linhas, encontradas {len(linhas)}")

    ids = [str(linha["claim_id"]) for linha in linhas]
    if len(set(ids)) != EXPECTED_ROWS:
        raise ImportacaoError("recorte M5 contém claim_id duplicado")

    registros: list[dict[str, Any]] = []
    for linha in linhas:
        claim_id = str(linha["claim_id"])
        nulos = [campo for campo, valor in linha.items() if valor is None]
        if nulos:
            raise ImportacaoError(f"{claim_id}: campos nulos no recorte M5: {', '.join(nulos)}")
        if linha["legacy_product"] != "voto_legislativo" or linha["legacy_status"] != "LIQUIDADO":
            raise ImportacaoError(f"{claim_id}: produto ou status diverge do recorte M5")

        try:
            probability = float(linha["probability"])
            outcome = int(linha["outcome"])
            brier = float(linha["brier_do_contrato"])
        except (TypeError, ValueError) as exc:
            raise ImportacaoError(f"{claim_id}: probability, outcome ou Brier inválido") from exc
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ImportacaoError(f"{claim_id}: probability fora de [0, 1]")
        if outcome not in (0, 1) or outcome != linha["outcome"]:
            raise ImportacaoError(f"{claim_id}: outcome não é inteiro binário")
        recomputado = (probability - outcome) ** 2
        if not math.isfinite(brier) or brier != recomputado:
            raise ImportacaoError(f"{claim_id}: Brier armazenado {brier!r} diverge de (p-outcome)² {recomputado!r}")

        created_at = _instante_com_timezone(linha["created_at"], "created_at", claim_id)
        quoted_at = _instante_com_timezone(linha["quoted_at"], "quoted_at", claim_id)
        resolved_at = _instante_com_timezone(linha["resolved_at"], "resolved_at", claim_id, adicionar_z=True)
        registros.append(
            {
                "claim_id": claim_id,
                "market_area_id": "voto-legislativo",
                "legacy_product": str(linha["legacy_product"]),
                "legacy_label": str(linha["legacy_label"]),
                "legacy_status": str(linha["legacy_status"]),
                "question": str(linha["question"]),
                "created_at": created_at,
                "quoted_at": quoted_at,
                "deadline": str(linha["deadline"]),
                "probability": probability,
                "probability_method": str(linha["probability_method"]),
                "declared_resolution_source": str(linha["declared_resolution_source"]),
                "resolution_criterion": str(linha["resolution_criterion"]),
                "outcome": outcome,
                "resolution_source": str(linha["resolution_source"]),
                "source_verification": "unknown",
                "resolved_at": resolved_at,
                "brier_do_contrato": brier,
                "historical_reconstruction": True,
                "forecast_eligible": False,
                "natureza": "RECONSTRUCAO_RETROSPECTIVA",
                "criado_apos_o_fato": True,
                "inelegivel_como_previsao": True,
                "motivo": MOTIVO,
            }
        )
    return registros


def _ler_store() -> dict[str, dict[str, Any]]:
    if not STORE.exists():
        return {}
    encontrados: dict[str, dict[str, Any]] = {}
    for numero, texto in enumerate(STORE.read_text(encoding="utf-8").splitlines(), start=1):
        if not texto.strip():
            continue
        try:
            registro = json.loads(texto)
            claim_id = str(registro["claim_id"])
        except (json.JSONDecodeError, KeyError) as exc:
            raise ImportacaoError(f"{STORE}:{numero}: registro JSONL inválido") from exc
        if claim_id in encontrados:
            raise ImportacaoError(f"{STORE}:{numero}: claim_id duplicado: {claim_id}")
        encontrados[claim_id] = registro
    return encontrados


def _preflight_store(registros: list[dict[str, Any]], existentes: dict[str, dict[str, Any]]) -> tuple[int, int]:
    novos = 0
    repetidos = 0
    for registro in registros:
        anterior = existentes.get(registro["claim_id"])
        if anterior is None:
            novos += 1
        elif anterior != registro:
            raise ImportacaoError(f"{registro['claim_id']}: store já contém o claim_id com conteúdo diferente")
        else:
            repetidos += 1
    return novos, repetidos


@contextmanager
def _trava_store() -> Iterator[None]:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    with LOCK.open("a+", encoding="utf-8") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)


def _executar(registros: list[dict[str, Any]]) -> tuple[int, int]:
    from asus_theye.markets.auditoria import abrir_auditoria, selar_registro

    with _trava_store():
        existentes = _ler_store()
        novos, repetidos = _preflight_store(registros, existentes)
        sdk = abrir_auditoria()
        for registro in registros:
            claim_id = registro["claim_id"]
            vigente = existentes.get(claim_id, registro)
            selar_registro(
                sdk,
                vigente,
                tipo_evento="market.retrospective_import",
                recurso="legacy_market",
                correlation_id=f"legado:{claim_id}",
                occurred_at=vigente["resolved_at"],
            )
            if claim_id not in existentes:
                with STORE.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(registro, ensure_ascii=False) + "\n")
        return novos, repetidos


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Importa o lote M5 legado como reconstruções retrospectivas inelegíveis."
    )
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--dry-run", action="store_true", help="valida e mostra ações, sem escrever (padrão)")
    modo.add_argument("--execute", action="store_true", help="sela e grava o lote validado")
    parser.add_argument("--json", action="store_true", help="emite uma única resposta JSON")
    return parser


def _resultado(
    *, modo: str, banco: Path, registros: list[dict[str, Any]], novos: int, repetidos: int
) -> dict[str, Any]:
    return {
        "status": "ok",
        "modo": modo,
        "banco": str(banco),
        "contratos_validados": len(registros),
        "novos": novos,
        "ja_presentes": repetidos,
        "selagens_planejadas": len(registros),
        "appends_planejados": novos,
        "escritas_realizadas": modo == "execute",
        "tipo_evento": "market.retrospective_import",
        "store": str(STORE),
        "natureza": "RECONSTRUCAO_RETROSPECTIVA",
        "inelegiveis_como_previsao": len(registros),
        "brier_medio": sum(item["brier_do_contrato"] for item in registros) / len(registros),
        "registros": registros,
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    banco_env = os.environ.get("ASUS_MARKETS_DB")
    try:
        if not banco_env:
            raise ImportacaoError("ASUS_MARKETS_DB não está definida")
        banco = Path(banco_env).expanduser()
        if not banco.is_file():
            raise ImportacaoError("ASUS_MARKETS_DB não aponta para um arquivo existente")
        hash_banco = _sha256(banco)
        if hash_banco != EXPECTED_DB_SHA256:
            raise ImportacaoError(
                f"snapshot DuckDB diverge do M5_IMPORT_SPEC (sha256 {hash_banco}; esperado {EXPECTED_DB_SHA256})"
            )

        registros = _validar_e_normalizar(_ler_duckdb(banco))
        existentes = _ler_store()
        novos, repetidos = _preflight_store(registros, existentes)
        if args.execute:
            novos, repetidos = _executar(registros)
            modo = "execute"
        else:
            modo = "dry-run"
        resultado = _resultado(
            modo=modo,
            banco=banco,
            registros=registros,
            novos=novos,
            repetidos=repetidos,
        )
    except ImportacaoError as exc:
        erro = {"status": "erro", "erro": str(exc)}
        print(json.dumps(erro, ensure_ascii=False) if args.json else f"ERRO: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(resultado, ensure_ascii=False))
    else:
        print(
            f"{modo}: {len(registros)} contratos validados; {novos} novos; "
            f"{repetidos} já presentes; 40 inelegíveis como previsão."
        )
        for registro in registros:
            acao = (
                "já presente; resselaria para auto-reparo"
                if registro["claim_id"] in existentes
                else "selaria e apenderia"
            )
            print(f"- {registro['claim_id']}: {acao}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
