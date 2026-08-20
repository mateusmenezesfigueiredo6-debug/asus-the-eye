# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Medição contínua — máquina de estados ABERTO → EM_RESOLUCAO → LIQUIDADO.

O elo que faltava entre "módulo correto" e "produto que mede": um registro de
mercados DENTRO do repositório (``reports/markets/``) e um laço de resolução que
busca a fonte oficial e liquida o que venceu. Regras estruturais:

1. **Nunca liquida antes do prazo.** Mercado cujo mês de referência ainda não
   terminou fica ABERTO e a fonte nem é consultada.
2. **Fonte sem publicação mantém estado intermediário.** Vencido mas sem valor
   publicado vira EM_RESOLUCAO, com a tentativa registrada — desempenho é
   UNKNOWN, nunca um palpite de desfecho.
3. **LIQUIDADO é terminal e append-only, com escrita em ordem segura.** O
   registro é persistido ANTES do apêndice em ``resolucoes.jsonl``, e o apêndice
   é idempotente (recusa claim_id repetido). Assim, queda entre as duas escritas
   deixa um LIQUIDADO sem linha — que o passo de reparo reconstrói — e nunca o
   contrário (linha duplicada, que corromperia o ledger em silêncio).
4. **Nunca se emite previsão do passado.** Ao liquidar, o próximo mercado é o
   primeiro mês que AINDA NÃO terminou — emitir pergunta sobre período já
   decidido seria previsão de mentira.
5. **O critério é derivado do limiar, nunca digitado.** Texto e número não podem
   divergir; divergência no registro levanta em vez de medir a coisa errada.

A emissão aceita uma :class:`Probabilidade` do gerador WPAM (M1): com sinais
reais de fonte nomeada o mercado nasce fora do 0,50 cego e carrega o bloco
``gerador`` (pesos, fontes, prior) no registro. Sem sinais — ou com a fonte de
sinais fora do ar — nasce no limiar de máxima incerteza (p = 0,50), dito como
tal: falha de sinal NUNCA bloqueia a emissão nem vira convicção inventada.
"""

from __future__ import annotations

import fcntl
import json
import re
from calendar import monthrange
from collections.abc import Callable
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from asus_theye.markets.claim import make_claim
from asus_theye.markets.fonte_bcb import FonteBCBError
from asus_theye.markets.gerador import Probabilidade
from asus_theye.markets.resolution import resolve
from asus_theye.markets.scoring import brier_score

ESTADOS = ("ABERTO", "EM_RESOLUCAO", "LIQUIDADO")
STORE_PADRAO = Path("reports/markets/registro.json")
MES_RE = re.compile(r"\d{4}-(0[1-9]|1[0-2])")
AREA_DESTE_RESOLVEDOR = "macroeconomia"
SERIE_DESTE_RESOLVEDOR = 433

# Registry das áreas RESOLVÍVEIS por este laço: série oficial + moldes de
# pergunta/critério (o texto é DERIVADO do limiar — regra 5). Área fora do
# registry nunca liquida: fonte errada não mede nada. O fetcher de cada área é
# INJETADO na chamada (a suíte roda offline; a CLI liga os conectores reais).
AREAS_RESOLVIVEIS: dict[str, dict[str, Any]] = {
    "macroeconomia": {
        "serie": 433,
        "prefixo": "MACRO-01",
        "pergunta": "A inflação oficial (IPCA) de {mes} fica em {limiar:.2f}% ou mais?",
        "criterio": "IPCA mensal >= {limiar:.2f}%",
        "indicador": "IPCA mensal",
        "unidade": "percentual_mensal",
    },
    "juros": {
        "serie": 432,
        "prefixo": "JUROS-01",
        "pergunta": "A meta da Selic vigente ao fim de {mes} fica em {limiar:.2f}% a.a. ou mais?",
        "criterio": "Selic meta (fim do mês) >= {limiar:.2f}% a.a.",
        "indicador": "Selic meta (fim do mês)",
        "unidade": "percentual_anual",
    },
    "cambio": {
        "serie": 1,
        "prefixo": "CAMBIO-01",
        "pergunta": "O dólar PTAX (venda) ao fim de {mes} fica em R$ {limiar:.2f} ou mais?",
        "criterio": "PTAX venda (último do mês) >= R$ {limiar:.2f}",
        "indicador": "PTAX venda (último do mês)",
        "unidade": "brl",
    },
}

CAMPOS_OBRIGATORIOS = (
    "claim_id",
    "market_area_id",
    "question",
    "deadline",
    "probability",
    "created_at",
    "mes_referencia",
    "limiar",
    "criterio",
    "serie_sgs",
    "estado",
    "tentativas",
)

# Busca o valor oficial do mês: recebe mes_referencia ("aaaa-mm"), devolve o
# valor publicado ou None. Injetável para a suíte rodar offline.
Fetcher = Callable[[str], float | None]

# Sela uma liquidação na cadeia auditável: recebe a linha do ledger e devolve o
# recibo ({"duplicate": bool, ...}). Injetável; deve ser idempotente por claim_id.
Auditor = Callable[[dict[str, Any]], dict[str, Any]]

# Gera a probabilidade WPAM do mês a emitir: recebe (mes_referencia, limiar) e
# devolve a Probabilidade com proveniência. Injetável; falha aqui NUNCA bloqueia
# a emissão — o mercado nasce no prior honesto e a ação diz por quê.
GeradorDeSinais = Callable[[str, float], Probabilidade]


class LiveMarketError(RuntimeError):
    """Registro corrompido ou transição inválida. Sempre levanta."""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _criterio(limiar: float, area: str = AREA_DESTE_RESOLVEDOR) -> str:
    """Texto do critério DERIVADO do número e da área — nunca digitado à mão."""
    config = AREAS_RESOLVIVEIS.get(area)
    if config is None:
        raise LiveMarketError(f"área {area!r} fora do registry de resolvíveis: {sorted(AREAS_RESOLVIVEIS)}")
    return str(config["criterio"]).format(limiar=float(limiar))


def _regra_da_area(area: str, limiar: float, mes_referencia: str, fonte: str) -> dict[str, Any]:
    """Regra estruturada e EXECUTÁVEL da área — a mesma que liquida o claim.

    O texto do critério continua existindo para leitura humana, mas quem decide
    o desfecho é :func:`asus_theye.markets.regra.avaliar` sobre este bloco. Ter
    uma só implementação do comparador é o que impede prosa e desfecho de
    divergirem em silêncio.
    """
    from asus_theye.markets.regra import montar_regra

    config = AREAS_RESOLVIVEIS.get(area)
    if config is None:
        raise LiveMarketError(f"área {area!r} fora do registry de resolvíveis: {sorted(AREAS_RESOLVIVEIS)}")
    return montar_regra(
        fonte=fonte,
        serie=int(config["serie"]),
        indicador=str(config["indicador"]),
        periodo_referencia=mes_referencia,
        limiar=float(limiar),
        unidade=str(config["unidade"]),
    )


def _fim_do_mes(mes_referencia: object) -> date:
    if not isinstance(mes_referencia, str) or not MES_RE.fullmatch(mes_referencia):
        raise LiveMarketError(
            f"mes_referencia deve ser 'aaaa-mm' (mês 01-12, zero à esquerda), veio {mes_referencia!r}"
        )
    ano, mes = (int(parte) for parte in mes_referencia.split("-"))
    return date(ano, mes, monthrange(ano, mes)[1])


def _mes_seguinte(mes_referencia: str) -> str:
    ano, mes = (int(parte) for parte in mes_referencia.split("-"))
    if mes == 12:
        return f"{ano + 1}-01"
    return f"{ano}-{mes + 1:02d}"


def _validar_mercado(mercado: dict[str, Any]) -> None:
    if mercado.get("estado") not in ESTADOS:
        raise LiveMarketError(f"{mercado.get('claim_id')}: estado inválido {mercado.get('estado')!r}")
    faltando = [campo for campo in CAMPOS_OBRIGATORIOS if campo not in mercado]
    if faltando:
        raise LiveMarketError(f"{mercado.get('claim_id')}: campos ausentes no registro: {faltando}")
    _fim_do_mes(mercado["mes_referencia"])  # valida formato do mês
    limiar = mercado["limiar"]
    if isinstance(limiar, bool) or not isinstance(limiar, (int, float)):
        raise LiveMarketError(f"{mercado['claim_id']}: limiar deve ser numérico, veio {limiar!r}")
    if not isinstance(mercado["tentativas"], list):
        raise LiveMarketError(f"{mercado['claim_id']}: tentativas deve ser lista")
    esperado = _criterio(float(limiar), str(mercado["market_area_id"]))
    if mercado["criterio"] != esperado:
        raise LiveMarketError(
            f"{mercado['claim_id']}: criterio {mercado['criterio']!r} não bate com o limiar "
            f"{limiar} (esperado {esperado!r}) — texto e número não podem divergir"
        )


def carregar_registro(store: Path) -> dict[str, Any]:
    if not store.exists():
        return {"versao": 1, "mercados": []}
    registro = json.loads(store.read_text(encoding="utf-8"))
    for mercado in registro.get("mercados", []):
        _validar_mercado(mercado)
    return registro


def salvar_registro(store: Path, registro: dict[str, Any]) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _caminho_resolucoes(store: Path) -> Path:
    return store.with_name("resolucoes.jsonl")


def _claim_ids_registrados(store: Path) -> set[str]:
    destino = _caminho_resolucoes(store)
    if not destino.exists():
        return set()
    ids: set[str] = set()
    for linha in destino.read_text(encoding="utf-8").splitlines():
        if linha.strip():
            ids.add(str(json.loads(linha).get("claim_id")))
    return ids


def _apendar_resolucao(store: Path, linha: dict[str, Any]) -> bool:
    """Apêndice idempotente: recusa claim_id já registrado. Devolve se gravou."""
    if linha["claim_id"] in _claim_ids_registrados(store):
        return False
    destino = _caminho_resolucoes(store)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(linha, ensure_ascii=False) + "\n")
    return True


def _linha_de_resolucao(mercado: dict[str, Any]) -> dict[str, Any]:
    """Linha do ledger, auditável sozinha: dá para recomputar desfecho e Brier."""
    return {
        "claim_id": mercado["claim_id"],
        "market_area_id": mercado["market_area_id"],
        "outcome": mercado["outcome"],
        "resolution_source": mercado["resolution_source"],
        "resolved_at": mercado["resolved_at"],
        # O relógio do mundo, ao lado do relógio do nosso processo. É contra
        # este que a calibração re-ancora o horizonte — nunca contra o deadline.
        "determination_date": mercado.get("determination_date", ""),
        "determination_basis": mercado.get("determination_basis", ""),
        "valor_observado": mercado["valor_observado"],
        "probability": mercado["probability"],
        "brier_do_contrato": mercado["brier_do_contrato"],
        "criterio": mercado["criterio"],
        "mes_referencia": mercado["mes_referencia"],
        "limiar": mercado["limiar"],
        "max_uncertainty": mercado.get("max_uncertainty", False),
    }


def emitir_macro(
    registro: dict[str, Any],
    mes_referencia: str,
    *,
    agora: str | None = None,
    limiar: float = 0.5,
    probabilidade: Probabilidade | None = None,
) -> dict[str, Any] | None:
    """Emite o mercado macro do mês, se ainda não existir.

    Sem ``probabilidade``, nasce em p = 0,50 (limiar de máxima incerteza —
    comportamento histórico). Com uma :class:`Probabilidade` do gerador WPAM,
    nasce na probabilidade gerada e carrega o bloco ``gerador`` completo
    (pesos, fontes, prior) — a proveniência auditável da convicção.
    Devolve o mercado emitido, ou ``None`` se o mês já tem mercado.
    """
    return emitir_area(
        registro,
        AREA_DESTE_RESOLVEDOR,
        mes_referencia,
        limiar=limiar,
        agora=agora,
        probabilidade=probabilidade,
    )


def emitir_area(
    registro: dict[str, Any],
    area: str,
    mes_referencia: str,
    *,
    limiar: float,
    agora: str | None = None,
    probabilidade: Probabilidade | None = None,
) -> dict[str, Any] | None:
    """Emite o mercado do mês para QUALQUER área do registry de resolvíveis.

    Pergunta e critério saem do molde da área com o limiar DECLARADO — texto e
    número nunca divergem. Área fora do registry levanta. Devolve ``None`` se o
    mês já tem mercado da área.
    """
    config = AREAS_RESOLVIVEIS.get(area)
    if config is None:
        raise LiveMarketError(f"área {area!r} fora do registry de resolvíveis: {sorted(AREAS_RESOLVIVEIS)}")
    claim_id = f"{config['prefixo']}::{mes_referencia}"
    if any(m["claim_id"] == claim_id for m in registro["mercados"]):
        return None
    criado = agora or _agora()
    fim = _fim_do_mes(mes_referencia)
    claim = make_claim(
        claim_id=claim_id,
        market_area_id=area,
        question=str(config["pergunta"]).format(mes=mes_referencia, limiar=float(limiar)),
        deadline=fim.isoformat(),
        # sem sinais: limiar de máxima incerteza (desenho do gerador, declarado)
        probability=0.5 if probabilidade is None else float(probabilidade.valor),
        created_at=criado,
    )
    mercado = {
        **claim.as_dict(),
        "mes_referencia": mes_referencia,
        "limiar": float(limiar),
        "criterio": _criterio(limiar, area),
        "serie_sgs": int(config["serie"]),
        "regra": _regra_da_area(area, limiar, mes_referencia, claim.resolution_source),
        "estado": "ABERTO",
        "tentativas": [],
    }
    if probabilidade is not None:
        mercado["gerador"] = probabilidade.as_dict()  # a convicção com proveniência
    registro["mercados"].append(mercado)
    return mercado


def _primeiro_mes_nao_terminado(depois_de: str, hoje: date) -> str:
    """Primeiro mês após ``depois_de`` cujo fim ainda não passou.

    Nunca se emite pergunta sobre período já decidido — isso seria previsão do
    passado. Se o laço ficou meses parado, os meses perdidos são pulados.
    """
    mes = _mes_seguinte(depois_de)
    while _fim_do_mes(mes) < hoje:
        mes = _mes_seguinte(mes)
    return mes


def resolver_pendentes(
    fetcher: Fetcher,
    *,
    store: Path = STORE_PADRAO,
    hoje: date | None = None,
    emitir_seguinte: bool = True,
    auditor: Auditor | None = None,
    gerador_de_sinais: GeradorDeSinais | None = None,
    fetchers_por_area: dict[str, Fetcher] | None = None,
) -> list[dict[str, Any]]:
    """Percorre o registro e aplica a máquina de estados. Devolve as ações.

    Cada ação: ``{"claim_id", "acao": "liquidado"|"em_resolucao"|"aguardando"|
    "emitido"|"reparado"|"selado"|"auditoria_falhou"|"erro", ...detalhes}``.
    Erros de fonte em um mercado não abortam os demais. A ordem de escrita por
    mercado é: registro em disco primeiro, apêndice no ledger depois
    (idempotente) — ver docstring do módulo. Com ``auditor``, toda liquidação é
    selada na cadeia auditável ao fim da rodada (varredura idempotente: cobre a
    liquidação recém-feita E qualquer LIQUIDADO antigo ainda não selado).
    """
    hoje = hoje or datetime.now(timezone.utc).date()

    # Trava exclusiva pela rodada inteira: duas rodadas simultâneas fariam
    # last-writer-wins no registro (podendo reverter um LIQUIDADO) e uma
    # corrida TOCTOU no apêndice. Falha rápido, nunca espera em silêncio.
    store.parent.mkdir(parents=True, exist_ok=True)
    trava = (store.with_name(".lock")).open("w")
    try:
        fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        trava.close()
        raise LiveMarketError("outra rodada de resolução em andamento (trava ocupada)") from exc
    try:
        return _resolver_pendentes_travado(
            fetcher,
            store=store,
            hoje=hoje,
            emitir_seguinte=emitir_seguinte,
            auditor=auditor,
            gerador_de_sinais=gerador_de_sinais,
            fetchers_por_area=fetchers_por_area,
        )
    finally:
        fcntl.flock(trava, fcntl.LOCK_UN)
        trava.close()


def _resolver_pendentes_travado(
    fetcher: Fetcher,
    *,
    store: Path,
    hoje: date,
    emitir_seguinte: bool,
    auditor: Auditor | None,
    gerador_de_sinais: GeradorDeSinais | None = None,
    fetchers_por_area: dict[str, Fetcher] | None = None,
) -> list[dict[str, Any]]:
    registro = carregar_registro(store)
    acoes: list[dict[str, Any]] = []
    # O fetcher posicional continua sendo o da macroeconomia (compat histórica);
    # as demais áreas entram pelo mapa. Área sem fetcher AQUI nunca liquida.
    fetchers = {AREA_DESTE_RESOLVEDOR: fetcher} | (fetchers_por_area or {})

    # Passo de reparo: LIQUIDADO sem linha no ledger (queda entre as duas
    # escritas) tem a linha reconstruída a partir do próprio registro.
    ja_registrados = _claim_ids_registrados(store)
    for mercado in registro["mercados"]:
        if mercado["estado"] == "LIQUIDADO" and mercado["claim_id"] not in ja_registrados:
            if _apendar_resolucao(store, _linha_de_resolucao(mercado)):
                acoes.append(
                    {
                        "claim_id": mercado["claim_id"],
                        "acao": "reparado",
                        "motivo": "linha do ledger reconstruída após queda entre escritas",
                    }
                )

    for mercado in registro["mercados"]:
        if mercado["estado"] == "LIQUIDADO":
            continue  # terminal: a fonte nem é consultada de novo

        # Cada área liquida SÓ contra a própria série/fetcher do registry: um
        # fetcher trocado mediria contra a fonte errada. Nunca degrada.
        area = str(mercado["market_area_id"])
        config = AREAS_RESOLVIVEIS.get(area)
        fetcher_da_area = fetchers.get(area)
        if config is None or fetcher_da_area is None:
            raise LiveMarketError(
                f"{mercado['claim_id']}: área {area!r} sem resolvedor "
                f"(registry: {sorted(AREAS_RESOLVIVEIS)}; fetchers: {sorted(fetchers)})"
            )
        if int(mercado["serie_sgs"]) != int(config["serie"]):
            raise LiveMarketError(
                f"{mercado['claim_id']}: série {mercado['serie_sgs']!r} não é a da área "
                f"{area!r} (SGS {config['serie']}) — fonte errada nunca liquida"
            )

        mes = mercado["mes_referencia"]
        if hoje <= _fim_do_mes(mes):
            acoes.append(
                {"claim_id": mercado["claim_id"], "acao": "aguardando", "motivo": f"mês {mes} ainda não terminou"}
            )
            continue

        try:
            valor = fetcher_da_area(mes)
        except FonteBCBError as erro:
            # erro de fonte em UM mercado não pode abortar os demais nem
            # deixar escrita pela metade
            acoes.append({"claim_id": mercado["claim_id"], "acao": "erro", "motivo": str(erro)})
            continue

        if valor is None:
            mercado["estado"] = "EM_RESOLUCAO"
            mercado["tentativas"].append(_agora())
            salvar_registro(store, registro)
            acoes.append(
                {
                    "claim_id": mercado["claim_id"],
                    "acao": "em_resolucao",
                    "motivo": "fonte oficial ainda não publicou o mês — desfecho é UNKNOWN, não palpite",
                    "tentativas": len(mercado["tentativas"]),
                }
            )
            continue

        # liquidação: reconstrói a afirmação (a fonte vem da área, doutrina intacta)
        claim = make_claim(
            claim_id=mercado["claim_id"],
            market_area_id=mercado["market_area_id"],
            question=mercado["question"],
            deadline=mercado["deadline"],
            probability=mercado["probability"],
            created_at=mercado["created_at"],
        )
        # O desfecho vem da REGRA, não de um comparador escrito aqui. Claim
        # antigo sem bloco `regra` tem a sua derivada da área na hora — a regra
        # é função do limiar e da área, então derivar não inventa nada.
        from asus_theye.markets.regra import avaliar

        regra = mercado.get("regra") or _regra_da_area(
            mercado["market_area_id"], float(mercado["limiar"]), str(mercado["mes_referencia"]), claim.resolution_source
        )
        decidido = avaliar(regra, float(valor))
        if decidido is None:  # defesa: valor ausente jamais chega aqui como desfecho
            raise LiveMarketError(
                f"{mercado['claim_id']}: regra devolveu UNKNOWN com valor presente — insumo corrompido"
            )
        outcome = decidido
        resolucao = resolve(claim, outcome=outcome, source=claim.resolution_source)
        brier = brier_score([(claim.probability, outcome)])

        mercado["estado"] = "LIQUIDADO"
        mercado["valor_observado"] = float(valor)
        mercado["outcome"] = outcome
        mercado["brier_do_contrato"] = brier
        mercado["resolved_at"] = resolucao.resolved_at
        # QUANDO o desfecho ficou determinado, distinto de quando NÓS rodamos.
        # A base viaja junto porque muda o que a data significa.
        mercado["determination_date"] = resolucao.determination_date
        mercado["determination_basis"] = resolucao.determination_basis
        # ordem segura: registro em disco ANTES do apêndice no ledger
        salvar_registro(store, registro)
        _apendar_resolucao(store, _linha_de_resolucao(mercado))
        acoes.append(
            {
                "claim_id": mercado["claim_id"],
                "acao": "liquidado",
                "outcome": outcome,
                "valor_observado": float(valor),
                "brier_do_contrato": brier,
                "fonte": resolucao.resolution_source,
                "max_uncertainty": bool(mercado.get("max_uncertainty", False)),
            }
        )

        if emitir_seguinte:
            # A resolução acima já está persistida e no ledger: falha na emissão
            # não pode desfazê-la nem duplicá-la — por isso o guarda amplo aqui.
            try:
                proximo = _primeiro_mes_nao_terminado(mes, hoje)
                probabilidade = None
                motivo_sem_sinal = ""
                # sinais WPAM existem hoje só para a pergunta do IPCA; as demais
                # áreas nascem no prior honesto até terem gerador próprio
                if gerador_de_sinais is not None and area == AREA_DESTE_RESOLVEDOR:
                    # Falha de sinal NUNCA bloqueia a emissão: o mercado nasce
                    # no prior honesto e a ação diz por quê (UNKNOWN over guess).
                    try:
                        probabilidade = gerador_de_sinais(proximo, 0.5)
                    except Exception as erro_sinal:  # noqa: BLE001 - fallback declarado
                        probabilidade = None
                        motivo_sem_sinal = f"; sinais indisponíveis ({erro_sinal})"
                # cada área re-emite a si mesma, com o PRÓPRIO limiar do mercado liquidado
                emitido = emitir_area(
                    registro, area, proximo, limiar=float(mercado["limiar"]), probabilidade=probabilidade
                )
            except Exception as erro:  # noqa: BLE001 - emissão nunca pode orfanar a resolução
                emitido = None
                acoes.append({"claim_id": f"MACRO-01::{mes}", "acao": "nao_emitido", "motivo": str(erro)})
            if emitido is not None:
                salvar_registro(store, registro)
                if probabilidade is not None and not probabilidade.max_uncertainty:
                    motivo = (
                        f"emitido em p={emitido['probability']:.4f} pelo gerador WPAM "
                        f"(fontes: {', '.join(probabilidade.fontes)})"
                    )
                else:
                    motivo = (
                        "próximo mês não-terminado entra no limiar de "
                        f"máxima incerteza (p=0,50) — sem sinal, sem convicção{motivo_sem_sinal}"
                    )
                acoes.append({"claim_id": emitido["claim_id"], "acao": "emitido", "motivo": motivo})

    salvar_registro(store, registro)

    # Varredura de selagem: todo LIQUIDADO vira evento na cadeia auditável.
    # Idempotente (o auditor deduplica por claim_id), então cobre tanto a
    # liquidação desta rodada quanto backfill de liquidações antigas. Falha de
    # auditoria é VISÍVEL (ação própria) mas nunca desfaz nem aborta a medição.
    if auditor is not None:
        for mercado in registro["mercados"]:
            if mercado["estado"] != "LIQUIDADO":
                continue
            try:
                recibo = auditor(_linha_de_resolucao(mercado))
            except Exception as erro:  # noqa: BLE001 - auditoria não pode derrubar a medição
                acoes.append({"claim_id": mercado["claim_id"], "acao": "auditoria_falhou", "motivo": str(erro)})
                continue
            if not recibo.get("duplicate"):
                acoes.append(
                    {
                        "claim_id": mercado["claim_id"],
                        "acao": "selado",
                        "event_hash": str(recibo.get("event_hash_sha256", ""))[:16],
                    }
                )
            elif recibo.get("export_reparado"):
                acoes.append(
                    {
                        "claim_id": mercado["claim_id"],
                        "acao": "export_reparado",
                        "motivo": "evento já selado estava ausente do export versionado — reapendado",
                    }
                )

    return acoes
