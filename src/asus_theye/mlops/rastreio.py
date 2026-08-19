"""Fatia 2 — rastreio de corridas de ML estilo MLflow, SELADO na cadeia.

O que a Databricks tem (MLflow) entra aqui como CONCEITO — Apache-2.0, zero
código copiado (``reports/provenance/MLflow-tracking.md``): corrida com
params/métricas/artefatos, registry de modelos com versões, e os papéis
campeão/desafiante. O que a Databricks NÃO tem, este módulo acrescenta: cada
registro vira evento selado na cadeia auditável (via genérica F2), com hash
canônico, dedupe por identidade e divergência DETECTADA — nunca escondida.

Também é a materialização do esquema ``ml_*`` legado (registry → versions →
runs → champion/challenger), que existia desenhado no banco e nunca foi
operado. Aqui ele opera no padrão do repo:

1. **Store versionado no repo** (``reports/mlops/*.jsonl``), append-only como
   a corrente F2: o histórico viaja com o repo e qualquer clone confere.
2. **Identidade = conteúdo.** ``modelo_id`` / ``modelo@versao`` / hash
   canônico da corrida. Reregistrar o mesmo conteúdo = dedupe; a MESMA
   identidade com conteúdo diferente = ``MLOpsError``.
3. **Integridade referencial levanta.** Corrida exige versão registrada;
   versão exige modelo; promoção exige versão. UNKNOWN over guess — não se
   rastreia corrida de modelo fantasma.
4. **Selagem por padrão.** Com um ``AuditSDK`` aberto, cada registro sela
   ``ml.model`` / ``ml.model_version`` / ``ml.run`` / ``ml.promotion`` por
   :func:`~asus_theye.markets.auditoria.selar_registro` — e a selagem roda
   MESMO no dedupe local, para reparar uma corrente que perdeu o evento
   (queda entre o append no arquivo e a selagem).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import hash_json
from asus_theye.audit.sdk import AuditSDK

BASE_PADRAO = Path("reports/mlops")
PAPEIS = ("campeao", "desafiante")
ESTADOS_DE_CORRIDA = ("CONCLUIDA", "FALHOU")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")


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

    A identidade da corrida é o hash canônico do próprio conteúdo — reexecutar
    com resultado byte-idêntico não gera evento novo (nada de spam na cadeia);
    qualquer diferença real (métrica, artefato, param) é corrida nova.
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


# ------------------------------------------------------------------ store


def _linhas(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def _apendar_unico(arquivo: Path, registro: dict[str, Any], *, chave: str) -> bool:
    """Apenda se a identidade é nova. Devolve ``True`` no dedupe; divergência levanta."""
    for linha in _linhas(arquivo):
        if linha.get(chave) == registro[chave]:
            if hash_json(linha) != hash_json(registro):
                raise MLOpsError(
                    f"{registro[chave]}: já registrado em {arquivo.name} com conteúdo DIFERENTE — "
                    "registro não se sobrescreve; corrija a identidade ou investigue a divergência"
                )
            return True
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return False


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


def _exige(condicao: bool, mensagem: str) -> None:
    if not condicao:
        raise MLOpsError(mensagem)


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
    registro = modelo.as_dict()
    duplicate = _apendar_unico(base / "modelos.jsonl", registro, chave="modelo_id")
    selagem = _selar(
        sdk, registro, tipo_evento="ml.model", correlation_id=f"ml:modelo:{modelo.modelo_id}", eventos=eventos
    )
    return {"registro": registro, "duplicate": duplicate, "selagem": selagem}


def registrar_versao(
    versao: Versao,
    *,
    base: Path = BASE_PADRAO,
    sdk: AuditSDK | None = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Registra a versão. Exige o modelo no registry; idempotente por ``modelo@versao``."""
    _exige(bool(versao.versao.strip()), "versão vazia não identifica nada")
    _exige(bool(versao.origem.strip()), f"{versao.modelo_id}@{versao.versao}: versão sem 'origem' declarada não entra")
    modelos = {linha["modelo_id"] for linha in _linhas(base / "modelos.jsonl")}
    _exige(
        versao.modelo_id in modelos,
        f"{versao.modelo_id}: modelo não registrado — registre-o antes da versão (integridade referencial)",
    )
    registro = versao.as_dict() | {"versao_id": f"{versao.modelo_id}@{versao.versao}"}
    duplicate = _apendar_unico(base / "versoes.jsonl", registro, chave="versao_id")
    correlacao = f"ml:versao:{registro['versao_id']}"
    selagem = _selar(sdk, registro, tipo_evento="ml.model_version", correlation_id=correlacao, eventos=eventos)
    return {"registro": registro, "duplicate": duplicate, "selagem": selagem}


def _versao_existe(base: Path, modelo_id: str, versao: str) -> bool:
    return any(linha.get("versao_id") == f"{modelo_id}@{versao}" for linha in _linhas(base / "versoes.jsonl"))


def registrar_corrida(
    corrida: Corrida,
    *,
    base: Path = BASE_PADRAO,
    sdk: AuditSDK | None = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Registra a corrida e sela ``ml.run``. Identidade = hash canônico do conteúdo."""
    _exige(corrida.estado in ESTADOS_DE_CORRIDA, f"estado {corrida.estado!r} não é um de {ESTADOS_DE_CORRIDA}")
    _exige(bool(corrida.executada_em.strip()), "corrida sem 'executada_em' — execução real tem quando")
    _exige(
        _versao_existe(base, corrida.modelo_id, corrida.versao),
        f"{corrida.modelo_id}@{corrida.versao}: versão não registrada — corrida de modelo fantasma não entra",
    )
    for nome, valor in corrida.metricas.items():
        _exige(
            isinstance(valor, (int, float)) and not isinstance(valor, bool),
            f"métrica {nome!r} deve ser numérica, veio {valor!r}",
        )
    for artefato in corrida.artefatos:
        _exige(bool(artefato.get("caminho")), "artefato sem 'caminho'")
        _exige(
            bool(_SHA256_HEX.match(str(artefato.get("sha256", "")))),
            f"artefato {artefato.get('caminho')!r} sem sha256 válido — artefato sem hash não é evidência",
        )
    registro = corrida.as_dict()
    registro["corrida_id"] = hash_json(corrida.as_dict())
    duplicate = _apendar_unico(base / "corridas.jsonl", registro, chave="corrida_id")
    selagem = _selar(
        sdk,
        registro,
        tipo_evento="ml.run",
        correlation_id=f"ml:corrida:{registro['corrida_id'][:32]}",
        occurred_at=corrida.executada_em,
        eventos=eventos,
    )
    return {"registro": registro, "duplicate": duplicate, "selagem": selagem}


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
    _exige(bool(promovido_em.strip()), "promoção sem 'promovido_em' — decisão real tem quando")
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
    duplicate = _apendar_unico(base / "promocoes.jsonl", registro, chave="promocao_id")
    selagem = _selar(
        sdk,
        registro,
        tipo_evento="ml.promotion",
        correlation_id=f"ml:promocao:{registro['promocao_id'][:32]}",
        occurred_at=promovido_em,
        eventos=eventos,
    )
    return {"registro": registro, "duplicate": duplicate, "selagem": selagem}


def campeao_atual(modelo_id: str, *, base: Path = BASE_PADRAO) -> dict[str, Any] | None:
    """Última promoção a campeão do modelo (ordem do arquivo = ordem de decisão)."""
    campeas = [
        linha
        for linha in _linhas(base / "promocoes.jsonl")
        if linha.get("modelo_id") == modelo_id and linha.get("papel") == "campeao"
    ]
    return campeas[-1] if campeas else None
