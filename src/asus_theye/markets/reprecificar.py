# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reprecificação — mover ``p`` de um mercado aberto, com prova de por quê.

Sem isto a probabilidade nasce uma vez e nunca mais se move: a série p(t) é uma
reta por construção, a curva de calibração não tem o que medir, e o produto é
uma lista de perguntas em vez de um mercado preditivo. O Focus é atualizado
semanalmente por ~100 instituições e o IPCA-15 sai no meio do mês — ignorar os
dois entre emissão e liquidação é jogar fora a informação que chega.

**Por que reprecificar mercado aberto é legítimo aqui, e não trapaça.** Numa
plataforma opaca, mexer no preço depois de aberto é exatamente como se fabrica
histórico favorável. Aqui é o contrário: o valor antigo permanece na corrente,
o novo entra como evento próprio com a proveniência do sinal que o justificou, e
a trajetória mostra a mudança. Quem auditar vê **quando** mudamos de ideia e
**por causa de quê**. Silêncio seria a trapaça; o registro é a honestidade.

O que esta função **recusa**:

- reprecificar claim já LIQUIDADO — mudar a previsão depois do desfecho é
  fabricar acerto, e é a única forma de fraude que este módulo poderia
  viabilizar. Por isso a checagem vem antes de tudo;
- reprecificar sem proveniência — número novo sem fonte nomeada não entra;
- gravar a mudança sem selar — a alteração e o seu motivo viajam juntos.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REGISTRO_PADRAO = Path("reports/markets/registro.json")

# Movimento menor que isto não vira evento. Não é arredondamento: é evitar que
# ruído numérico do gerador encha a corrente de eventos sem informação, o que
# tornaria a trajetória ilegível justamente para quem quer auditá-la.
MOVIMENTO_MINIMO = 0.005


class ReprecificacaoError(RuntimeError):
    """Reprecificação inválida. Sempre levanta — preço não muda em silêncio."""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def reprecificar(
    *,
    claim_id: str,
    probabilidade: Any,
    motivo: str,
    store: Path = REGISTRO_PADRAO,
    sdk: Any | None = None,
    eventos: Path | None = None,
    agora: str | None = None,
) -> dict[str, Any]:
    """Move ``p`` de um claim ABERTO e sela a mudança com a proveniência do sinal.

    ``probabilidade`` é a :class:`~asus_theye.markets.gerador.Probabilidade` que
    justifica o novo valor — ela carrega o sinal, a fonte e o método.
    """
    if not store.exists():
        raise ReprecificacaoError(f"registro de mercados ausente: {store}")
    if not motivo.strip():
        raise ReprecificacaoError(f"{claim_id}: motivo obrigatório — preço não muda sem explicação")

    registro = json.loads(store.read_text(encoding="utf-8"))
    mercado = next((m for m in registro.get("mercados", []) if m.get("claim_id") == claim_id), None)
    if mercado is None:
        raise ReprecificacaoError(f"{claim_id}: claim não existe no registro")

    estado = str(mercado.get("estado", "")).upper()
    if estado == "LIQUIDADO":
        raise ReprecificacaoError(
            f"{claim_id}: já LIQUIDADO — mudar a previsão depois do desfecho é fabricar acerto. "
            "A trajetória de um claim termina quando o mundo responde."
        )

    anterior = float(mercado["probability"])
    novo = float(probabilidade.valor)
    if not 0.0 <= novo <= 1.0:
        raise ReprecificacaoError(f"{claim_id}: probabilidade fora de [0,1], veio {novo!r}")

    movimento = abs(novo - anterior)
    if movimento < MOVIMENTO_MINIMO:
        return {
            "reprecificado": False,
            "motivo": f"movimento {movimento:.4f} abaixo do mínimo {MOVIMENTO_MINIMO} — nada a registrar",
            "probability": anterior,
            "selagem": None,
        }

    proveniencia = probabilidade.as_dict()
    mudanca = {
        "claim_id": claim_id,
        "probabilidade_anterior": anterior,
        "probabilidade_nova": novo,
        "movimento": round(novo - anterior, 6),
        "motivo": motivo.strip(),
        "gerador": proveniencia,
        "reprecificado_em": agora or _agora(),
        "metodo": (
            "reprecificação de mercado ABERTO: o valor anterior permanece na corrente, o novo entra "
            "como evento próprio com a proveniência do sinal. Quem auditar vê quando mudamos de ideia "
            "e por causa de quê — o silêncio é que seria trapaça."
        ),
    }

    # sela ANTES de gravar: falha no meio deixa evento sem efeito (visível e
    # inofensivo), nunca efeito sem evento
    selagem = None
    if sdk is not None:
        from asus_theye.audit.schema import hash_json
        from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

        selagem = selar_registro(
            sdk,
            mudanca,
            tipo_evento="market.repricing",
            recurso="market",
            correlation_id=f"reprecificacao:{hash_json(mudanca)[:32]}",
            occurred_at=str(mudanca["reprecificado_em"]),
            eventos=eventos or EVENTOS_PADRAO,
        )

    mercado["probability"] = novo
    mercado["max_uncertainty"] = abs(novo - 0.5) <= 0.001
    mercado["gerador"] = proveniencia
    mercado.setdefault("reprecificacoes", []).append(
        {k: mudanca[k] for k in ("probabilidade_anterior", "probabilidade_nova", "motivo", "reprecificado_em")}
    )
    store.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"reprecificado": True, "mudanca": mudanca, "selagem": selagem}


# ---------------------------------------------------------------- o laço


# A trilha própria: um gerador só, que serve a QUALQUER área, porque o tom da
# cobertura não é específico do indicador. É de propósito — o que o distingue é
# a ORIGEM (imprensa, não consenso), não o recorte.
# As constantes moram em ``serie_p``, que é quem classifica os pontos na hora
# de pontuar. Duas cópias do mesmo nome divergem no dia em que uma muda.


def _observar_cobertura(
    acoes: list[dict[str, Any]],
    *,
    sdk: Any = None,
    eventos: Path | None = None,
) -> tuple[Any, bool]:
    """Observa e arquiva a cobertura do dia — uma vez para a rodada inteira.

    Devolve ``(observacao, alarme_de_termos)``. Falha de fonte devolve
    ``(None, False)`` e registra a ação: a trilha secundária **nunca** derruba
    a principal, porque o preço publicado é o do Focus e ele não depende disto.

    Importado tarde, para o teste de independência de ``sinais_noticia``
    continuar valendo por inspeção dos imports.
    """
    from asus_theye.markets.arquivo_gdelt import arquivar_cobertura
    from asus_theye.markets.fonte_gdelt import cobertura

    try:
        observacao = cobertura()
    except Exception as erro:  # noqa: BLE001 - trilha secundária nunca derruba a principal
        acoes.append({"claim_id": "", "acao": "cobertura_indisponivel", "motivo": str(erro)[:200]})
        return None, False

    try:
        arquivado = arquivar_cobertura(observacao, sdk=sdk, eventos=eventos)
    except Exception as erro:  # noqa: BLE001 - sem arquivo, o sinal ainda vale; a lacuna é registrada
        acoes.append({"claim_id": "", "acao": "cobertura_nao_arquivada", "motivo": str(erro)[:200]})
        return observacao, False

    acoes.append(
        {
            "claim_id": "",
            "acao": "cobertura_arquivada" if not arquivado["duplicate"] else "cobertura_dedupe",
            "motivo": f"{observacao.eventos} evento(s), tom {observacao.tom_medio:+.4f}, {observacao.arquivo}",
        }
    )
    return observacao, bool(arquivado["alarme_de_termos"])


def _gerador_da_area(area: str) -> Any:
    """O gerador de sinal da área, ou ``None`` se a área ainda não tem um.

    Área sem gerador **não** cai no gerador do IPCA por aproximação: perguntas
    diferentes têm sinais diferentes, e usar o sinal errado é pior do que ficar
    no prior honesto de 0,50.
    """
    from asus_theye.markets.sinais_cambio import probabilidade_para_cambio
    from asus_theye.markets.sinais_ipca import probabilidade_para_ipca
    from asus_theye.markets.sinais_juros import probabilidade_para_juros

    return {
        "macroeconomia": probabilidade_para_ipca,
        "juros": probabilidade_para_juros,
        "cambio": probabilidade_para_cambio,
    }.get(area)


def rodada(
    *,
    store: Path = REGISTRO_PADRAO,
    sdk: Any | None = None,
    eventos: Path | None = None,
    serie: Path | None = None,
    hoje: str | None = None,
) -> dict[str, Any]:
    """Percorre os mercados ABERTOS, consulta o gerador e reprecifica o que mudou.

    É o laço que transforma a série p(t) de reta em trajetória. Sem ele, a
    probabilidade nasce uma vez e ignora o Focus semanal e o IPCA-15 do meio do
    mês — jogando fora exatamente a informação que chega entre a emissão e a
    liquidação.

    Cada claim é independente: falha em um NUNCA aborta os demais nem deixa
    escrita pela metade. Um mercado que não pôde ser precificado hoje volta a
    ser tentado amanhã, e a razão fica registrada na ação.

    Toda passagem grava ponto na série — inclusive quando ``p`` não se move.
    Um dia em que a convicção NÃO mudou é informação: a curva de calibração
    precisa saber que estávamos em 0,75 naquele horizonte, não só nos dias de
    movimento.
    """
    from asus_theye.markets.serie_p import ORIGEM_PROPRIA, ORIGEM_REPRECIFICACAO, registrar_ponto

    if not store.exists():
        raise ReprecificacaoError(f"registro de mercados ausente: {store}")

    dia = hoje or _agora()[:10]
    registro = json.loads(store.read_text(encoding="utf-8"))
    acoes: list[dict[str, Any]] = []

    # A cobertura noticiosa é medida por PAÍS, então uma observação serve à
    # rodada inteira. Buscar aqui, e não dentro do laço, evita baixar o mesmo
    # arquivo uma vez por mercado — e o arquivamento acontece uma vez, com o
    # carimbo dos termos do dia.
    cobertura_do_dia, alarme_de_termos = _observar_cobertura(acoes, sdk=sdk, eventos=eventos)
    if alarme_de_termos:
        acoes.append(
            {
                "claim_id": "",
                "acao": "ALARME_TERMOS_GDELT",
                "motivo": (
                    "a frase que concede o uso sumiu da página de termos do GDELT. "
                    "Isto exige revisão humana HOJE: o direito de usar o dado é o que está em questão."
                ),
            }
        )

    for mercado in registro.get("mercados", []):
        claim_id = str(mercado.get("claim_id", ""))
        estado = str(mercado.get("estado", "ABERTO")).upper()
        if estado == "LIQUIDADO":
            continue  # trajetória encerrada — ponto novo inventaria história

        area = str(mercado.get("market_area_id", ""))
        gerador = _gerador_da_area(area)
        if gerador is None:
            acoes.append({"claim_id": claim_id, "acao": "sem_gerador", "motivo": f"área {area!r} não tem gerador"})
            continue

        try:
            nova = gerador(str(mercado["mes_referencia"]), float(mercado["limiar"]))
        except Exception as erro:  # noqa: BLE001 - falha de fonte não derruba o laço
            acoes.append({"claim_id": claim_id, "acao": "sinal_indisponivel", "motivo": str(erro)[:200]})
            # ainda assim fotografa: o dia existiu, e a convicção vigente é fato
            registrar_ponto(claim_id=claim_id, observado_em=dia, store=store, arquivo=serie, sdk=sdk, eventos=eventos)
            continue

        try:
            resultado = reprecificar(
                claim_id=claim_id,
                probabilidade=nova,
                motivo=f"rodada de {dia}: sinal vigente da área {area}",
                store=store,
                sdk=sdk,
                eventos=eventos,
            )
        except ReprecificacaoError as erro:
            acoes.append({"claim_id": claim_id, "acao": "recusado", "motivo": str(erro)[:200]})
            continue

        # --- a TRILHA PRÓPRIA, ao lado da do Focus -----------------------
        # Ela não altera `probability` do mercado: fica registrada em paralelo,
        # selada antes do desfecho. É isso que torna a comparação verificável em
        # vez de retórica — na liquidação, as duas são pontuadas com a mesma
        # régua, e o resultado é o que os dados disserem, inclusive paridade.
        if cobertura_do_dia is None:
            acoes.append(
                {"claim_id": claim_id, "acao": "trilha_propria_indisponivel", "motivo": "sem cobertura no dia"}
            )
        else:
            from asus_theye.markets.sinais_noticia import probabilidade_da_cobertura

            propria = probabilidade_da_cobertura(cobertura_do_dia)
            anterior_propria = (mercado.get("gerador_proprio") or {}).get("valor")
            mercado["gerador_proprio"] = propria.as_dict()
            registrar_ponto(
                claim_id=claim_id,
                probability=float(propria.valor),
                observado_em=dia,
                causa_id=f"propria:{dia}",
                origem=ORIGEM_PROPRIA,
                store=store,
                arquivo=serie,
                sdk=sdk,
                eventos=eventos,
            )
            acoes.append(
                {
                    "claim_id": claim_id,
                    "acao": "trilha_propria",
                    "de": anterior_propria,
                    "para": round(float(propria.valor), 4),
                }
            )

        if resultado["reprecificado"]:
            selo = resultado.get("selagem") or {}
            causa = f"repricing:{selo.get('event_hash_sha256', '')[:32]}" if selo else ""
            registrar_ponto(
                claim_id=claim_id,
                observado_em=dia,
                causa_id=causa,
                instante=str(resultado["mudanca"]["reprecificado_em"]),
                origem=ORIGEM_REPRECIFICACAO,
                store=store,
                arquivo=serie,
                sdk=sdk,
                eventos=eventos,
            )
            acoes.append(
                {
                    "claim_id": claim_id,
                    "acao": "reprecificado",
                    "de": resultado["mudanca"]["probabilidade_anterior"],
                    "para": resultado["mudanca"]["probabilidade_nova"],
                }
            )
        else:
            registrar_ponto(claim_id=claim_id, observado_em=dia, store=store, arquivo=serie, sdk=sdk, eventos=eventos)
            acoes.append({"claim_id": claim_id, "acao": "estavel", "motivo": resultado["motivo"]})

    # o gerador_proprio foi anexado em memória; persistir junto
    store.write_text(json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    movidos = sum(1 for a in acoes if a["acao"] == "reprecificado")
    return {
        "dia": dia,
        "acoes": acoes,
        "reprecificados": movidos,
        "estaveis": sum(1 for a in acoes if a["acao"] == "estavel"),
        "trilha_propria": sum(1 for a in acoes if a["acao"] == "trilha_propria"),
        "metodo": (
            "laço diário sobre mercados ABERTOS; cada claim é independente e falha em um não "
            "aborta os demais. Ponto de série é gravado SEMPRE — dia sem movimento também é "
            "informação para a calibração por horizonte."
        ),
    }
