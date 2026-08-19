"""Nowcast desafiante do IPCA, reproduzível e sem imputação silenciosa.

Implementa o contrato de ``docs/architecture/NOWCAST_IPCA_SPEC.md``: coleta
cinco séries oficiais do SGS, transforma as duas séries diárias, ajusta ridge
em NumPy puro e avalia por walk-forward mensal. O módulo apenas produz uma
``Corrida`` e seu manifesto; registro, promoção e integração ao mercado ficam
deliberadamente fora daqui.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, TypeAlias, cast

import numpy as np
from numpy.typing import NDArray

from asus_theye.mlops.rastreio import Corrida
from asus_theye.net.http import HttpError, Transport, get_bytes

SERIES = (433, 7478, 189, 1, 432)
SERIES_DIARIAS = (1, 432)
FEATURES = {
    "R2": ("ipca_15", "igp_m"),
    "R4": ("ipca_15", "igp_m", "dolar_variacao", "selic_media"),
}
URL_SERIE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json"
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)  # NOWCAST_IPCA_SPEC.md, seção 4.1.
JANELA_TREINO = 120  # Dez anos mensais, conforme a seção 4.2 da spec.
MIN_RESIDUOS = 24  # Porta probabilística mínima da seção 4.3 da spec.
LIMIAR_IPCA = 0.5  # Claim operacional vigente: IPCA mensal >= 0,50%.
TIMEOUT = 30
MAX_BYTES = 10_000_000
ARTEFATOS_DIR = Path("reports/mlops/artefatos")
# Um primeiro Brier exige 120 meses de treino, 24 resíduos anteriores e o mês
# avaliado (seções 4.2 e 4.3). A coleta diária retrocede o necessário para isso.
MESES_MINIMOS_CORRIDA = JANELA_TREINO + MIN_RESIDUOS + 1
# Limite devolvido pela própria API SGS para séries diárias (HTTP 406).
ANOS_MAXIMOS_POR_CONSULTA_DIARIA = 10
MOTIVO_FOCUS_BLOQUEADO = (
    "Sem vintage Focus reproduzível no mesmo corte do modelo; dados revisados dariam vantagem informacional."
)

FloatArray: TypeAlias = NDArray[np.float64]


class NowcastError(RuntimeError):
    """Entrada, fonte ou cálculo inválido; a falha nunca vira sinal numérico."""


@dataclass(frozen=True)
class Snapshot:
    """Pontos de uma resposta SGS e o hash verificável do corpo bruto."""

    codigo: int
    url: str
    status_http: int
    coletado_em: str
    sha256: str
    pontos: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class Painel:
    """Inner join mensal completo, pronto para avaliação temporal."""

    meses: tuple[str, ...]
    alvo: FloatArray
    valores: dict[str, FloatArray]
    snapshots: tuple[Snapshot, ...]


@dataclass(frozen=True)
class AjusteRidge:
    """Ridge ajustado; coeficientes são expressos na escala original."""

    alpha: float
    intercepto: float
    coeficientes: FloatArray
    medias_treino: FloatArray
    desvios_treino: FloatArray

    def prever(self, x: FloatArray) -> FloatArray:
        """Aplica o ajuste a linhas na escala original."""
        matriz = np.asarray(x, dtype=np.float64)
        return np.asarray(self.intercepto + matriz @ self.coeficientes, dtype=np.float64)


@dataclass(frozen=True)
class Fold:
    """Uma previsão fora da amostra e toda a informação necessária à auditoria."""

    mes: str
    meses_treino: tuple[str, ...]
    alpha: float
    intercepto: float
    coeficientes: tuple[float, ...]
    medias_treino: tuple[float, ...]
    desvios_treino: tuple[float, ...]
    previsao: float
    observado: float
    residuo: float
    limiar: float
    probabilidade: float | None
    desfecho: int


def _mes(data_bcb: str) -> str:
    """Converte ``dd/mm/aaaa`` do SGS em ``aaaa-mm`` estrito."""
    partes = data_bcb.split("/")
    if len(partes) != 3 or any(not parte.isdigit() for parte in partes):
        raise NowcastError(f"data em formato inesperado do BCB: {data_bcb!r}")
    dia, mes, ano = partes
    try:
        datetime(int(ano), int(mes), int(dia))
    except ValueError as exc:
        raise NowcastError(f"data civil inválida do BCB: {data_bcb!r}") from exc
    return f"{ano}-{mes}"


def _urls_da_serie(codigo: int, hoje: date) -> tuple[str, ...]:
    base = URL_SERIE.format(codigo=codigo)
    if codigo not in SERIES_DIARIAS:
        return (base,)
    anos_necessarios = (MESES_MINIMOS_CORRIDA + 11) // 12
    inicio = date(hoje.year - anos_necessarios, 1, 1)
    urls: list[str] = []
    while inicio <= hoje:
        fim = min(date(inicio.year + ANOS_MAXIMOS_POR_CONSULTA_DIARIA - 1, 12, 31), hoje)
        urls.append(f"{base}&dataInicial={inicio.strftime('%d/%m/%Y')}&dataFinal={fim.strftime('%d/%m/%Y')}")
        inicio = date(fim.year + 1, 1, 1)
    return tuple(urls)


def _baixar_url(codigo: int, url: str, transport: Transport | None) -> Snapshot:
    try:
        resposta = get_bytes(
            url,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise NowcastError(f"série SGS {codigo} inalcançável: {exc}") from exc
    if resposta.status != 200:
        raise NowcastError(f"série SGS {codigo} respondeu HTTP {resposta.status} em {url}")
    try:
        bruto = json.loads(resposta.body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise NowcastError(f"série SGS {codigo} não devolveu JSON válido") from exc
    if not isinstance(bruto, list):
        raise NowcastError(f"série SGS {codigo} devolveu {type(bruto).__name__}, esperado lista")

    pontos: list[tuple[str, float]] = []
    for ponto in bruto:
        if not isinstance(ponto, dict) or "data" not in ponto or "valor" not in ponto:
            raise NowcastError(f"ponto inesperado na série SGS {codigo}: {ponto!r}")
        try:
            valor = float(str(ponto["valor"]).replace(",", "."))
        except ValueError as exc:
            raise NowcastError(f"valor não numérico na série SGS {codigo}: {ponto['valor']!r}") from exc
        if not np.isfinite(valor):
            raise NowcastError(f"valor não finito na série SGS {codigo}: {ponto['valor']!r}")
        pontos.append((str(ponto["data"]), valor))
    if not pontos:
        raise NowcastError(f"série SGS {codigo} vazia — resultado é UNKNOWN")
    coletado_em = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return Snapshot(codigo, url, resposta.status, coletado_em, hashlib.sha256(resposta.body).hexdigest(), tuple(pontos))


def _baixar_serie(codigo: int, transport: Transport | None) -> tuple[Snapshot, ...]:
    return tuple(_baixar_url(codigo, url, transport) for url in _urls_da_serie(codigo, date.today()))


def _mensal_direta(pontos: Sequence[tuple[str, float]], codigo: int) -> dict[str, float]:
    por_mes: dict[str, list[float]] = {}
    for data, valor in pontos:
        por_mes.setdefault(_mes(data), []).append(valor)
    mensal: dict[str, float] = {}
    for mes, valores in por_mes.items():
        if len(set(valores)) != 1:
            raise NowcastError(f"série mensal SGS {codigo} tem valores divergentes em {mes}: {valores}")
        mensal[mes] = valores[0]
    return mensal


def transformar_ptax_mensal(pontos: Sequence[tuple[str, float]]) -> dict[str, float]:
    """Média diária mensal e variação percentual contra o mês anterior (§3)."""
    por_mes: dict[str, list[float]] = {}
    for data, valor in pontos:
        por_mes.setdefault(_mes(data), []).append(valor)
    medias = {mes: float(np.mean(valores)) for mes, valores in por_mes.items()}
    meses = sorted(medias)
    resultado: dict[str, float] = {}
    for anterior, atual in zip(meses, meses[1:], strict=False):
        if _mes_seguinte(anterior) != atual:
            continue  # ausência mensal não é ponte nem imputação (§3 e §4.2).
        if medias[anterior] == 0:
            raise NowcastError(f"média cambial zero em {anterior}; variação indefinida")
        resultado[atual] = 100.0 * (medias[atual] / medias[anterior] - 1.0)
    return resultado


def transformar_selic_mensal(pontos: Sequence[tuple[str, float]]) -> dict[str, float]:
    """Média aritmética de todos os valores diários de cada mês (§3)."""
    por_mes: dict[str, list[float]] = {}
    for data, valor in pontos:
        por_mes.setdefault(_mes(data), []).append(valor)
    return {mes: float(np.mean(valores)) for mes, valores in por_mes.items()}


def _mes_seguinte(mes: str) -> str:
    ano, numero = (int(parte) for parte in mes.split("-"))
    return f"{ano + numero // 12:04d}-{numero % 12 + 1:02d}"


def _sao_meses_consecutivos(meses: Sequence[str]) -> bool:
    return all(_mes_seguinte(anterior) == atual for anterior, atual in zip(meses, meses[1:], strict=False))


def montar_painel(*, transport: Transport | None = None) -> Painel:
    """Coleta as cinco séries e faz inner join mensal, sem imputar ausências."""
    snapshots = tuple(snapshot for codigo in SERIES for snapshot in _baixar_serie(codigo, transport))
    por_codigo = {
        codigo: tuple(ponto for snapshot in snapshots if snapshot.codigo == codigo for ponto in snapshot.pontos)
        for codigo in SERIES
    }
    series_mensais = {
        "ipca": _mensal_direta(por_codigo[433], 433),
        "ipca_15": _mensal_direta(por_codigo[7478], 7478),
        "igp_m": _mensal_direta(por_codigo[189], 189),
        "dolar_variacao": transformar_ptax_mensal(por_codigo[1]),
        "selic_media": transformar_selic_mensal(por_codigo[432]),
    }
    meses = tuple(sorted(set.intersection(*(set(serie) for serie in series_mensais.values()))))
    valores = {
        nome: np.asarray([serie[mes] for mes in meses], dtype=np.float64)
        for nome, serie in series_mensais.items()
        if nome != "ipca"
    }
    return Painel(meses, np.asarray([series_mensais["ipca"][mes] for mes in meses]), valores, snapshots)


def ajustar_ridge(x: FloatArray, y: FloatArray, alpha: float) -> AjusteRidge:
    """Ajusta ridge fechado, padronizando somente com a amostra fornecida."""
    matriz = np.asarray(x, dtype=np.float64)
    alvo = np.asarray(y, dtype=np.float64)
    if matriz.ndim != 2 or alvo.ndim != 1 or matriz.shape[0] != alvo.shape[0] or matriz.shape[0] == 0:
        raise NowcastError("x e y precisam ser matriz/vetor não vazios com o mesmo número de linhas")
    if alpha < 0 or not np.isfinite(alpha) or not np.all(np.isfinite(matriz)) or not np.all(np.isfinite(alvo)):
        raise NowcastError("ridge exige alpha e dados finitos, com alpha não negativo")

    medias = np.mean(matriz, axis=0)
    desvios_observados = np.std(matriz, axis=0)
    # Coluna constante carrega zero informação; escala 1 a transforma em zeros
    # sem imputar valores nem dividir por zero.
    desvios = np.where(desvios_observados == 0.0, 1.0, desvios_observados)
    padronizada = (matriz - medias) / desvios
    media_alvo = float(np.mean(alvo))
    centrado = alvo - media_alvo
    identidade = np.eye(matriz.shape[1], dtype=np.float64)
    try:
        beta_padronizado = np.linalg.solve(padronizada.T @ padronizada + alpha * identidade, padronizada.T @ centrado)
    except np.linalg.LinAlgError as exc:
        raise NowcastError("sistema ridge singular; nenhum ajuste foi emitido") from exc
    coeficientes = beta_padronizado / desvios
    intercepto = media_alvo - float(medias @ coeficientes)
    return AjusteRidge(alpha, intercepto, coeficientes, medias, desvios)


def escolher_alpha_temporal(x: FloatArray, y: FloatArray, alphas: Sequence[float] = ALPHAS) -> float:
    """Escolhe alpha por validação temporal interna de uma etapa (§4.1)."""
    if len(y) < 2:
        raise NowcastError("validação temporal interna exige ao menos duas linhas")
    escores: list[tuple[float, float]] = []
    for alpha in alphas:
        erros = []
        # Usa todos os cortes internos possíveis; começar em 1 evita inventar
        # uma segunda janela de validação não declarada na spec.
        for corte in range(1, len(y)):
            ajuste = ajustar_ridge(x[:corte], y[:corte], float(alpha))
            erro = float(ajuste.prever(x[corte : corte + 1])[0] - y[corte])
            erros.append(erro * erro)
        escores.append((float(np.mean(erros)), float(alpha)))
    return min(escores)[1]  # empate determinístico favorece o menor alpha.


def probabilidade_laplace(residuos: Sequence[float], *, previsao: float, limiar: float) -> float | None:
    """Converte previsão em probabilidade pela regra empírica da seção 4.3."""
    if len(residuos) < MIN_RESIDUOS:
        return None
    corte = limiar - previsao
    sucessos = sum(float(residuo) >= corte for residuo in residuos)
    return (1.0 + sucessos) / (len(residuos) + 2.0)


def walk_forward(
    painel: Painel,
    especificacao: str,
    *,
    limiares: float | Mapping[str, float] = LIMIAR_IPCA,
) -> list[Fold]:
    """Executa folds de uma etapa com janela móvel de exatamente 120 meses."""
    nome = especificacao.upper()
    if nome not in FEATURES:
        raise NowcastError(f"especificação deve ser R2 ou R4, veio {especificacao!r}")
    if len(painel.meses) < JANELA_TREINO:
        return []  # Menos de 120 linhas completas é UNKNOWN (§4.2).
    x = np.column_stack([painel.valores[feature] for feature in FEATURES[nome]])
    folds: list[Fold] = []
    residuos_anteriores: list[float] = []
    for indice in range(JANELA_TREINO, len(painel.meses)):
        inicio = indice - JANELA_TREINO
        meses_do_fold = painel.meses[inicio : indice + 1]
        if not _sao_meses_consecutivos(meses_do_fold):
            # O inner join expõe o buraco; não o convertemos em uma janela de
            # 120 "linhas" que na verdade atravessaria mais de 120 meses (§4.2).
            continue
        x_treino, y_treino = x[inicio:indice], painel.alvo[inicio:indice]
        alpha = escolher_alpha_temporal(x_treino, y_treino)
        ajuste = ajustar_ridge(x_treino, y_treino, alpha)
        previsao = float(ajuste.prever(x[indice : indice + 1])[0])
        observado = float(painel.alvo[indice])
        residuo = observado - previsao
        mes = painel.meses[indice]
        limiar = float(limiares[mes] if isinstance(limiares, Mapping) else limiares)
        probabilidade = probabilidade_laplace(residuos_anteriores, previsao=previsao, limiar=limiar)
        folds.append(
            Fold(
                mes=mes,
                meses_treino=painel.meses[inicio:indice],
                alpha=alpha,
                intercepto=ajuste.intercepto,
                coeficientes=tuple(float(valor) for valor in ajuste.coeficientes),
                medias_treino=tuple(float(valor) for valor in ajuste.medias_treino),
                desvios_treino=tuple(float(valor) for valor in ajuste.desvios_treino),
                previsao=previsao,
                observado=observado,
                residuo=residuo,
                limiar=limiar,
                probabilidade=probabilidade,
                desfecho=int(observado >= limiar),
            )
        )
        residuos_anteriores.append(residuo)
    return folds


def _versao_pacote() -> str:
    try:
        return metadata.version("asus-the-eye")
    except metadata.PackageNotFoundError:  # pragma: no cover - instalação editável quebrada
        return "0.0.0"


def _fold_dict(
    fold: Fold, especificacao: str, features: Sequence[str], fontes: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "mes": fold.mes,
        "meses_treino": list(fold.meses_treino),
        # Corte da §1: fim do último dia útil do MÊS-ALVO — a previsão usa as
        # features contemporâneas de t (desenho autorizado), então o corte
        # registrado tem de ser t, não t-1 (achado confirmado da revisão:
        # corte gravado ≠ informação usada quebraria a reprodução do auditor).
        "corte_dados": fold.mes,
        "parametros": {
            "especificacao": especificacao,
            "janela_treino": JANELA_TREINO,
            "alphas_candidatos": list(ALPHAS),
            "features": list(features),
        },
        "alpha": fold.alpha,
        "intercepto": fold.intercepto,
        "coeficientes": dict(zip(features, fold.coeficientes, strict=True)),
        "medias_treino": dict(zip(features, fold.medias_treino, strict=True)),
        "desvios_treino": dict(zip(features, fold.desvios_treino, strict=True)),
        "fontes": list(fontes),
        "previsao": fold.previsao,
        "observado": fold.observado,
        "residuo": fold.residuo,
        "limiar": fold.limiar,
        "probabilidade": fold.probabilidade if fold.probabilidade is not None else "UNKNOWN",
        "desfecho": fold.desfecho,
    }


def corrida_do_nowcast(especificacao: str, *, transport: Transport | None = None) -> Corrida:
    """Coleta, avalia e materializa uma corrida local do nowcast desafiante."""
    nome = especificacao.upper()
    if nome not in FEATURES:
        raise NowcastError(f"especificação deve ser R2 ou R4, veio {especificacao!r}")
    painel = montar_painel(transport=transport)
    folds = walk_forward(painel, nome)
    avaliados = [fold for fold in folds if fold.probabilidade is not None]
    if not avaliados:
        raise NowcastError("UNKNOWN: não há 24 resíduos walk-forward anteriores para calcular Brier")
    probabilidades = [cast(float, fold.probabilidade) for fold in avaliados]
    brier = float(
        np.mean(
            [
                (probabilidade - fold.desfecho) ** 2
                for probabilidade, fold in zip(probabilidades, avaliados, strict=True)
            ]
        )
    )
    cobertura = len(avaliados) / len(folds) if folds else 0.0
    executada_em = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    fontes = [
        {
            "serie_sgs": snapshot.codigo,
            "url": snapshot.url,
            "status_http": snapshot.status_http,
            "coletado_em": snapshot.coletado_em,
            "sha256": snapshot.sha256,
        }
        for snapshot in painel.snapshots
    ]
    manifesto = {
        "modelo_id": "ipca-nowcast-linear",
        "versao": _versao_pacote(),
        "executada_em": executada_em,
        "especificacao": nome,
        "features": list(FEATURES[nome]),
        "janela_treino": JANELA_TREINO,
        "alphas": list(ALPHAS),
        "limiares": {"regra": "IPCA mensal >= limiar", "valor_fixo": LIMIAR_IPCA},
        "fontes": fontes,
        "folds": [_fold_dict(fold, nome, FEATURES[nome], fontes) for fold in folds],
        "metricas": {
            "n_meses": len(avaliados),
            "inicio": avaliados[0].mes,
            "fim": avaliados[-1].mes,
            "cobertura": cobertura,
            "brier_ridge": brier,
            "brier_focus": "BLOCKED",
            "motivo_brier_focus": MOTIVO_FOCUS_BLOQUEADO,
            "diferenca_pareada_media": "BLOCKED",
            "skill": "BLOCKED",
        },
        "limitacoes": [
            "O SGS não expõe published_at nem vintage; os hashes registram somente a resposta desta corrida.",
            MOTIVO_FOCUS_BLOQUEADO,
            "O desafiante permanece com peso zero até cumprir a porta prospectiva da seção 6 da spec.",
        ],
    }
    corpo = json.dumps(manifesto, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sha256 = hashlib.sha256(corpo).hexdigest()
    ARTEFATOS_DIR.mkdir(parents=True, exist_ok=True)
    caminho = ARTEFATOS_DIR / f"nowcast-ipca-{nome.lower()}-{sha256[:16]}.json"
    caminho.write_bytes(corpo)
    return Corrida(
        modelo_id="ipca-nowcast-linear",
        versao=_versao_pacote(),
        params={
            "janela": JANELA_TREINO,
            "alphas": list(ALPHAS),
            "features": list(FEATURES[nome]),
            "especificacao": nome,
            "limiares": [LIMIAR_IPCA],
        },
        metricas={"brier_ridge": brier, "n_meses": float(len(avaliados)), "cobertura": cobertura},
        artefatos=[{"caminho": str(caminho), "sha256": sha256}],
        executada_em=executada_em,
    )
