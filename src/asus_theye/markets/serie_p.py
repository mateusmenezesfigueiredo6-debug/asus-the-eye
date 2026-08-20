# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Série histórica de p(t) — o que se acreditava, e QUANDO se acreditava.

Sem isto, ``probability`` no registro é só o valor de agora: quando o claim
liquida, o histórico inteiro se perde e sobra um número sem trajetória. Brier
sem horizonte não significa quase nada — o mesmo 0,50 vale coisas muito
diferentes a três meses e na véspera. Este módulo grava a trajetória.

**Por que o relógio ENTRA na identidade aqui.** O padrão da casa
(:mod:`asus_theye.markets.comparador`, mlops) exclui o relógio da identidade de
propósito: mesma medição não vira evento novo. Numa série temporal a regra se
inverte — o ponto É o par (valor, momento). Deduplicar por valor apagaria o fato
de que ``p`` ficou parado em 0,50 por trinta dias, e esse fato é justamente uma
das coisas que a calibração precisa enxergar. A identidade é, então,
``(claim_id, observado_em)``: **um ponto por claim por dia**, o que mantém o cron
idempotente sem mentir sobre a trajetória.

**Dois horizontes, não um.** O ponto guarda ``horizonte_dias`` medido contra o
``deadline`` do contrato, porque é o único horizonte que existe no momento da
observação. Mas o horizonte que a calibração deve usar é o medido contra a data
em que a fonte de fato publicou (``determination_date``), conhecida só na
liquidação. Por isso o ponto guarda ``deadline`` e ``observado_em`` crus: quem
calcula calibração re-ancora depois, sem precisar reescrever a série.
"""

from __future__ import annotations

import fcntl
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from asus_theye.audit.schema import hash_json
from asus_theye.audit.sdk import AuditSDK

SERIE_PADRAO = Path("reports/markets/serie_p.jsonl")
REGISTRO_PADRAO = Path("reports/markets/registro.json")

# De onde veio o número. "registro" = o p vigente no registro de mercados;
# origens novas (gerador WPAM, ajuste manual) se declaram ao gravar.
ORIGEM_REGISTRO = "registro"


class SerieError(RuntimeError):
    """Ponto inválido ou claim inexistente. Sempre levanta — série não chuta."""


@contextmanager
def _trava(arquivo: Path) -> Iterator[None]:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    with arquivo.with_name(".lock-serie-p").open("a+", encoding="utf-8") as lockfile:
        fcntl.flock(lockfile, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lockfile, fcntl.LOCK_UN)


def _linhas(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def _hoje() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _mercados(store: Path) -> list[dict[str, Any]]:
    if not store.exists():
        raise SerieError(f"registro de mercados ausente: {store}")
    return json.loads(store.read_text(encoding="utf-8")).get("mercados", [])


def _ponto(mercado: dict[str, Any], observado_em: str, probability: float, origem: str) -> dict[str, Any]:
    try:
        deadline = date.fromisoformat(str(mercado["deadline"]))
        observado = date.fromisoformat(observado_em)
    except (ValueError, TypeError, KeyError) as exc:
        raise SerieError(f"{mercado.get('claim_id')}: datas inválidas para o ponto ({exc})") from exc
    if not 0.0 <= probability <= 1.0:
        raise SerieError(f"{mercado.get('claim_id')}: probability fora de [0,1], veio {probability!r}")

    registro = {
        "claim_id": str(mercado["claim_id"]),
        "market_area_id": str(mercado.get("market_area_id", "")),
        "observado_em": observado_em,
        "probability": float(probability),
        "deadline": str(mercado["deadline"]),
        # horizonte contra o DEADLINE — o único conhecível agora. Negativo
        # significa observação depois do prazo (claim vencido sem liquidar).
        "horizonte_dias": (deadline - observado).days,
        "origem": origem,
        "metodo": (
            "ponto da série p(t); horizonte medido contra o deadline do contrato. "
            "A calibração deve RE-ANCORAR contra determination_date quando ele existir — "
            "o relógio que importa é o da publicação da fonte, não o do fechamento."
        ),
    }
    # identidade inclui o dia de propósito: um ponto por claim por dia
    registro["ponto_id"] = hash_json({"claim_id": registro["claim_id"], "observado_em": observado_em})
    return registro


def registrar_ponto(
    *,
    claim_id: str,
    probability: float | None = None,
    observado_em: str | None = None,
    origem: str = ORIGEM_REGISTRO,
    store: Path = REGISTRO_PADRAO,
    arquivo: Path = SERIE_PADRAO,
    sdk: AuditSDK | None = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Grava e SELA um ponto de p(t). Mesmo claim no mesmo dia = dedupe.

    ``probability`` ausente usa o valor vigente no registro de mercados — o caso
    do cron, que fotografa o que a plataforma acredita hoje.
    """
    dia = observado_em or _hoje()
    mercado = next((m for m in _mercados(store) if m.get("claim_id") == claim_id), None)
    if mercado is None:
        raise SerieError(f"{claim_id}: claim não existe no registro — série de mercado fantasma não entra")

    p = float(mercado["probability"]) if probability is None else float(probability)
    registro = _ponto(mercado, dia, p, origem)

    with _trava(arquivo):
        existente = next((li for li in _linhas(arquivo) if li.get("ponto_id") == registro["ponto_id"]), None)
        vigente = existente if existente is not None else registro
        selagem = None
        if sdk is not None:
            from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

            selagem = selar_registro(
                sdk,
                vigente,
                tipo_evento="market.probability_point",
                recurso="probability_point",
                correlation_id=f"serie:{registro['ponto_id'][:32]}",
                occurred_at=f"{dia}T00:00:00Z",
                eventos=eventos or EVENTOS_PADRAO,
            )
        if existente is None:
            with arquivo.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(registro, ensure_ascii=False) + "\n")
    return {"registro": vigente, "duplicate": existente is not None, "selagem": selagem}


def registrar_vivos(
    *,
    observado_em: str | None = None,
    store: Path = REGISTRO_PADRAO,
    arquivo: Path = SERIE_PADRAO,
    sdk: AuditSDK | None = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Fotografa p(t) de TODO claim ainda não liquidado — a chamada do cron.

    Claim liquidado não entra: sua trajetória acabou, e continuar gravando
    pontos depois do desfecho inventaria história.
    """
    resultados = []
    for mercado in _mercados(store):
        if str(mercado.get("estado", "")).upper() == "LIQUIDADO":
            continue
        resultados.append(
            registrar_ponto(
                claim_id=str(mercado["claim_id"]),
                observado_em=observado_em,
                store=store,
                arquivo=arquivo,
                sdk=sdk,
                eventos=eventos,
            )
        )
    novos = sum(1 for r in resultados if not r["duplicate"])
    return {
        "pontos": resultados,
        "novos": novos,
        "duplicados": len(resultados) - novos,
        "metodo": "um ponto por claim vivo por dia; claim LIQUIDADO não recebe ponto novo",
    }


def serie_do_claim(claim_id: str, *, arquivo: Path = SERIE_PADRAO) -> list[dict[str, Any]]:
    """A trajetória de um claim, em ordem cronológica."""
    pontos = [li for li in _linhas(arquivo) if li.get("claim_id") == claim_id]
    return sorted(pontos, key=lambda li: str(li.get("observado_em", "")))


def reancorar(
    claim_id: str,
    *,
    determination_date: str,
    determination_basis: str,
    arquivo: Path = SERIE_PADRAO,
) -> dict[str, Any]:
    """Recalcula o horizonte da série contra a data em que o desfecho ficou determinado.

    É o achado que motivou guardar ``observado_em`` cru: o horizonte gravado no
    ponto é medido contra o ``deadline`` do contrato, que é um proxy — o prazo
    de fechamento pode estar longe do momento em que a fonte de fato publicou o
    número. Medir calibração contra o relógio errado embute viés.

    Nada é reescrito: a série permanece como foi selada, e o horizonte
    re-ancorado é **derivado** na leitura. História selada não se corrige à mão.

    Base ``desconhecida`` (dado legado) devolve ``confiavel=False``: sem saber
    quando a fonte publicou, o horizonte re-ancorado é ficção com aparência de
    número, e a calibração precisa poder excluir estes pontos.
    """
    from asus_theye.markets.resolution import BASES_CONFIAVEIS

    try:
        determinada = date.fromisoformat(determination_date)
    except (ValueError, TypeError) as exc:
        raise SerieError(f"determination_date deve ser data ISO (YYYY-MM-DD), veio {determination_date!r}") from exc

    confiavel = determination_basis in BASES_CONFIAVEIS
    pontos = []
    for ponto in serie_do_claim(claim_id, arquivo=arquivo):
        observado = date.fromisoformat(str(ponto["observado_em"]))
        pontos.append(
            ponto
            | {
                "horizonte_reancorado_dias": (determinada - observado).days,
                "determination_date": determination_date,
                "determination_basis": determination_basis,
            }
        )
    return {
        "claim_id": claim_id,
        "pontos": pontos,
        "confiavel": confiavel,
        "metodo": (
            f"horizonte re-ancorado contra determination_date={determination_date} "
            f"(base {determination_basis!r}); derivado na leitura, a série selada não muda. "
            + (
                "Base confiável — pode entrar na calibração por horizonte."
                if confiavel
                else "Base DESCONHECIDA (legado): não use este horizonte para calibrar."
            )
        ),
    }
