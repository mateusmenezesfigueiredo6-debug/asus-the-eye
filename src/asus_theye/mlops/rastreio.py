# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fatia 2 — rastreio de corridas de ML estilo MLflow, SELADO na cadeia.

O que a Databricks tem (MLflow) entra aqui como CONCEITO — Apache-2.0, zero
código copiado (``reports/provenance/MLflow-tracking.md``): corrida com
params/métricas/artefatos, registry de modelos com versões, e os papéis
campeão/desafiante. O que a Databricks NÃO tem, este módulo acrescenta: cada
registro vira evento selado na cadeia auditável (via genérica F2), com hash
canônico, dedupe por identidade e divergência DETECTADA — nunca escondida.

Também é a materialização do esquema ``ml_*`` legado (registry → versions →
runs → champion/challenger), que existia desenhado no banco e nunca foi
operado. Aqui ele opera no padrão do repo, endurecido pela revisão adversarial:

1. **Store versionado no repo** (``reports/mlops/*.jsonl``), append-only como
   a corrente F2: o histórico viaja com o repo e qualquer clone confere.
2. **Identidade = conteúdo DECLARADO.** ``modelo_id`` / ``modelo@versao`` /
   hash canônico de ``{modelo, versao, params, metricas, estado}`` da corrida —
   ``executada_em`` e artefatos ficam FORA da identidade (carregam relógio e
   telemetria; senão nenhuma reexecução deduplicaria). Reregistrar a mesma
   identidade = dedupe (primeiro registro vence); a MESMA identidade de
   modelo/versão com conteúdo diferente = ``MLOpsError``.
3. **Integridade referencial levanta.** Corrida exige versão registrada;
   versão exige modelo; promoção exige versão. UNKNOWN over guess — não se
   rastreia corrida de modelo fantasma. ``modelo_id``/``versao`` são slugs
   (sem ``@``): ``versao_id = modelo@versao`` nunca é ambíguo.
4. **Sela PRIMEIRO, apenda DEPOIS — sob trava.** A corrente é a canônica: se a
   selagem levanta, o store não ganha linha órfã; se o processo cair entre a
   selagem e o append, o próximo registro re-sela (dedupe na cadeia) e repara o
   arquivo. O read-check-append roda sob ``flock`` (``reports/mlops/.lock``,
   mesmo padrão de ``markets/live.py``) — sem corrida TOCTOU entre processos.
"""

from __future__ import annotations

import fcntl
import json
import math
import re
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import hash_json
from asus_theye.audit.sdk import AuditSDK

BASE_PADRAO = Path("reports/mlops")
PAPEIS = ("campeao", "desafiante")
ESTADOS_DE_CORRIDA = ("CONCLUIDA", "FALHOU")
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")
_SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class MLOpsError(RuntimeError):
    """Registro inválido, referência ausente ou divergência de conteúdo. Sempre levanta."""


# ------------------------------------------------------------------ entidades


@dataclass(frozen=True)
class Modelo:
    """ml_model_registry: um modelo com objetivo DECLARADO — sem objetivo não entra."""

    modelo_id: str
    nome: str
    area: str
    objetivo: str  # o que o modelo prevê/mede — número sem método não entra

    def as_dict(self) -> dict[str, Any]:
        return {"modelo_id": self.modelo_id, "nome": self.nome, "area": self.area, "objetivo": self.objetivo}


@dataclass(frozen=True)
class Versao:
    """ml_model_versions: uma versão nomeada do modelo, com origem declarada."""

    modelo_id: str
    versao: str
    origem: str  # de onde o código/método saiu (módulo, commit, artefato)

    def as_dict(self) -> dict[str, Any]:
        return {"modelo_id": self.modelo_id, "versao": self.versao, "origem": self.origem}


@dataclass(frozen=True)
class Corrida:
    """ml_prediction_runs + ml_model_metrics: uma execução com params, métricas e artefatos.

    A identidade da corrida é o hash canônico do conteúdo DECLARADO (modelo,
    versão, params, métricas, estado). ``executada_em`` e os artefatos ficam
    fora: carregam relógio e telemetria de parede — reexecutar com o MESMO
    resultado deduplica; qualquer diferença real (métrica, param) é corrida nova.
    """

    modelo_id: str
    versao: str
    params: dict[str, Any]
    metricas: dict[str, float]
    artefatos: list[dict[str, str]]  # [{"caminho": ..., "sha256": ...}]
    executada_em: str
    estado: str = "CONCLUIDA"

    def as_dict(self) -> dict[str, Any]:
        return {
            "modelo_id": self.modelo_id,
            "versao": self.versao,
            "params": self.params,
            "metricas": self.metricas,
            "artefatos": self.artefatos,
            "executada_em": self.executada_em,
            "estado": self.estado,
        }

    def identidade(self) -> dict[str, Any]:
        """O conteúdo que define QUEM é esta corrida — sem relógio, sem telemetria."""
        return {
            "modelo_id": self.modelo_id,
            "versao": self.versao,
            "params": self.params,
            "metricas": self.metricas,
            "estado": self.estado,
        }


# ------------------------------------------------------------------ store


def _linhas(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


@contextmanager
def _trava(base: Path) -> Iterator[None]:
    """Trava exclusiva do store (flock) — read-check-append sem TOCTOU entre processos."""
    base.mkdir(parents=True, exist_ok=True)
    with (base / ".lock").open("a+", encoding="utf-8") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)


def _procurar(arquivo: Path, chave: str, valor: str) -> dict[str, Any] | None:
    for linha in _linhas(arquivo):
        if linha.get(chave) == valor:
            return linha
    return None


def _apendar(arquivo: Path, registro: dict[str, Any]) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(registro, ensure_ascii=False) + "\n")


def _registrar_selando(
    base: Path,
    arquivo: str,
    registro: dict[str, Any],
    *,
    chave: str,
    sdk: AuditSDK | None,
    tipo_evento: str,
    correlation_id: str,
    occurred_at: str = "",
    eventos: Path | None = None,
    divergencia_por_conteudo: bool = True,
) -> dict[str, Any]:
    """O coração endurecido: trava → dedupe/divergência → SELA → apenda.

    Ordem deliberada (achados da revisão): a corrente é a canônica, então a
    selagem vem ANTES do append — selagem que levanta não deixa linha órfã no
    store, e queda entre selar e apendar se repara no próximo registro (o
    dedupe da cadeia devolve o mesmo evento e o arquivo ganha a linha que
    faltou). No dedupe, o que se sela é o registro JÁ armazenado — o conteúdo
    selado nunca diverge do arquivo.
    """
    caminho = base / arquivo
    with _trava(base):
        existente = _procurar(caminho, chave, registro[chave])
        if existente is not None and divergencia_por_conteudo and hash_json(existente) != hash_json(registro):
            raise MLOpsError(
                f"{registro[chave]}: já registrado em {arquivo} com conteúdo DIFERENTE — "
                "registro não se sobrescreve; corrija a identidade ou investigue a divergência"
            )
        selagem = _selar(
            sdk,
            existente if existente is not None else registro,
            tipo_evento=tipo_evento,
            correlation_id=correlation_id,
            occurred_at=occurred_at,
            eventos=eventos,
        )
        if existente is None:
            _apendar(caminho, registro)
    vigente = existente if existente is not None else registro
    return {"registro": vigente, "duplicate": existente is not None, "selagem": selagem}


def _selar(
    sdk: AuditSDK | None,
    registro: dict[str, Any],
    *,
    tipo_evento: str,
    correlation_id: str,
    occurred_at: str = "",
    eventos: Path | None = None,
) -> dict[str, Any] | None:
    """Sela via F2 quando há SDK — inclusive no dedupe local (auto-reparo da corrente)."""
    if sdk is None:
        return None
    from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

    return selar_registro(
        sdk,
        registro,
        tipo_evento=tipo_evento,
        recurso="ml",
        correlation_id=correlation_id,
        occurred_at=occurred_at,
        eventos=eventos or EVENTOS_PADRAO,
    )


# ------------------------------------------------------------------ validação


def _exige(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise MLOpsError(mensagem)


def _exige_slug(valor: str, campo: str) -> None:
    _exige(
        bool(_SLUG.fullmatch(valor)),
        f"{campo} {valor!r} inválido — use letras/dígitos/._- (sem '@': 'modelo@versao' precisa ser inambíguo)",
    )


def _exige_instante(valor: str, campo: str) -> None:
    """ISO 8601 COM timezone — o mesmo contrato do occurred_at da cadeia.

    Validar aqui, na porta, é o que garante que a selagem nunca estoura DEPOIS
    de decidido o registro (achado alta da revisão: timestamp frouxo passava e
    a EventValidationError deixava linha órfã no store).
    """
    try:
        instante = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except ValueError:
        instante = None
    _exige(
        instante is not None and instante.tzinfo is not None,
        f"{campo} {valor!r} inválido — exige ISO 8601 com timezone (ex.: 2026-08-19T12:00:00Z)",
    )


def _exige_finitos(obj: Any, campo: str) -> None:
    """NaN/Infinity não entram: o hash canônico (I-JSON) os rejeita — melhor na porta."""
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        _exige(math.isfinite(float(obj)), f"{campo}: valor não finito ({obj!r}) não entra — I-JSON não o representa")
    elif isinstance(obj, dict):
        for chave, valor in obj.items():
            _exige_finitos(valor, f"{campo}.{chave}")
    elif isinstance(obj, (list, tuple)):
        for indice, valor in enumerate(obj):
            _exige_finitos(valor, f"{campo}[{indice}]")


# ------------------------------------------------------------------ registro


def registrar_modelo(
    modelo: Modelo,
    *,
    base: Path = BASE_PADRAO,
    sdk: AuditSDK | None = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Registra o modelo no registry. Idempotente por ``modelo_id``."""
    for campo, valor in modelo.as_dict().items():
        _exige(bool(str(valor).strip()), f"modelo sem {campo!r} — modelo sem objetivo declarado não entra")
    _exige_slug(modelo.modelo_id, "modelo_id")
    return _registrar_selando(
        base,
        "modelos.jsonl",
        modelo.as_dict(),
        chave="modelo_id",
        sdk=sdk,
        tipo_evento="ml.model",
        correlation_id=f"ml:modelo:{modelo.modelo_id}",
        eventos=eventos,
    )


def registrar_versao(
    versao: Versao,
    *,
    base: Path = BASE_PADRAO,
    sdk: AuditSDK | None = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Registra a versão. Exige o modelo no registry; idempotente por ``modelo@versao``."""
    _exige_slug(versao.modelo_id, "modelo_id")
    _exige_slug(versao.versao, "versao")
    _exige(bool(versao.origem.strip()), f"{versao.modelo_id}@{versao.versao}: versão sem 'origem' declarada não entra")
    modelos = {linha["modelo_id"] for linha in _linhas(base / "modelos.jsonl")}
    _exige(
        versao.modelo_id in modelos,
        f"{versao.modelo_id}: modelo não registrado — registre-o antes da versão (integridade referencial)",
    )
    registro = versao.as_dict() | {"versao_id": f"{versao.modelo_id}@{versao.versao}"}
    return _registrar_selando(
        base,
        "versoes.jsonl",
        registro,
        chave="versao_id",
        sdk=sdk,
        tipo_evento="ml.model_version",
        correlation_id=f"ml:versao:{registro['versao_id']}",
        eventos=eventos,
    )


def _versao_existe(base: Path, modelo_id: str, versao: str) -> bool:
    return any(linha.get("versao_id") == f"{modelo_id}@{versao}" for linha in _linhas(base / "versoes.jsonl"))


def registrar_corrida(
    corrida: Corrida,
    *,
    base: Path = BASE_PADRAO,
    sdk: AuditSDK | None = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Registra a corrida e sela ``ml.run``. Identidade = hash do conteúdo declarado.

    ``executada_em``/artefatos ficam fora da identidade: no dedupe o primeiro
    registro vence (e é ELE que se re-sela — o conteúdo selado nunca diverge
    do arquivo).
    """
    _exige_slug(corrida.modelo_id, "modelo_id")
    _exige_slug(corrida.versao, "versao")
    _exige(corrida.estado in ESTADOS_DE_CORRIDA, f"estado {corrida.estado!r} não é um de {ESTADOS_DE_CORRIDA}")
    _exige_instante(corrida.executada_em, "executada_em")
    _exige(
        _versao_existe(base, corrida.modelo_id, corrida.versao),
        f"{corrida.modelo_id}@{corrida.versao}: versão não registrada — corrida de modelo fantasma não entra",
    )
    for nome, valor in corrida.metricas.items():
        _exige(
            isinstance(valor, (int, float)) and not isinstance(valor, bool),
            f"métrica {nome!r} deve ser numérica, veio {valor!r}",
        )
    _exige_finitos(corrida.metricas, "metricas")
    _exige_finitos(corrida.params, "params")
    for artefato in corrida.artefatos:
        _exige(bool(artefato.get("caminho")), "artefato sem 'caminho'")
        _exige(
            bool(_SHA256_HEX.fullmatch(str(artefato.get("sha256", "")))),
            f"artefato {artefato.get('caminho')!r} sem sha256 válido — artefato sem hash não é evidência",
        )
    registro = corrida.as_dict()
    registro["corrida_id"] = hash_json(corrida.identidade())
    return _registrar_selando(
        base,
        "corridas.jsonl",
        registro,
        chave="corrida_id",
        sdk=sdk,
        tipo_evento="ml.run",
        correlation_id=f"ml:corrida:{registro['corrida_id'][:32]}",
        occurred_at=corrida.executada_em,
        eventos=eventos,
        # corrida_id JÁ É o hash da identidade: mesmo id ⇒ mesma corrida;
        # executada_em/artefatos podem variar entre reexecuções (o 1º vence)
        divergencia_por_conteudo=False,
    )


def promover(
    *,
    modelo_id: str,
    versao: str,
    papel: str,
    motivo: str,
    promovido_em: str,
    base: Path = BASE_PADRAO,
    sdk: AuditSDK | None = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """ml_champion_challenger: promove uma versão a campeã/desafiante, com motivo.

    Promoção sem motivo não entra — é a régua "nenhum número sem método"
    aplicada a decisão de modelo.
    """
    _exige(papel in PAPEIS, f"papel {papel!r} não é um de {PAPEIS}")
    _exige(bool(motivo.strip()), f"{modelo_id}@{versao}: promoção sem 'motivo' não entra")
    _exige_instante(promovido_em, "promovido_em")
    _exige(
        _versao_existe(base, modelo_id, versao),
        f"{modelo_id}@{versao}: versão não registrada — não se promove o que não existe",
    )
    registro: dict[str, Any] = {
        "modelo_id": modelo_id,
        "versao": versao,
        "papel": papel,
        "motivo": motivo,
        "promovido_em": promovido_em,
    }
    registro["promocao_id"] = hash_json(registro)
    return _registrar_selando(
        base,
        "promocoes.jsonl",
        registro,
        chave="promocao_id",
        sdk=sdk,
        tipo_evento="ml.promotion",
        correlation_id=f"ml:promocao:{registro['promocao_id'][:32]}",
        occurred_at=promovido_em,
        eventos=eventos,
    )


def campeao_atual(modelo_id: str, *, base: Path = BASE_PADRAO) -> dict[str, Any] | None:
    """Última promoção a campeão do modelo (ordem do arquivo = ordem de decisão)."""
    campeas = [
        linha
        for linha in _linhas(base / "promocoes.jsonl")
        if linha.get("modelo_id") == modelo_id and linha.get("papel") == "campeao"
    ]
    return campeas[-1] if campeas else None
