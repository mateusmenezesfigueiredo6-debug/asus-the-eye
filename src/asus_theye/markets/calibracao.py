# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Calibração — a probabilidade declarada vale alguma coisa?

Um Brier agregado esconde quase tudo. O mesmo 0,50 significa coisas muito
diferentes a três meses e na véspera, e um previsor pode ter Brier bom sendo
sistematicamente mal calibrado. Este módulo mede as três coisas que respondem
de verdade:

1. **Curva de confiabilidade** — quando dissemos 70%, aconteceu ~70% das vezes?
   A curva ideal é a diagonal; o desvio dela é o viés.
2. **Brier estratificado por horizonte** — o número só é interpretável cortado
   por tempo-até-o-desfecho.
3. **Decomposição de Murphy** — ``BS = confiabilidade − resolução + incerteza``.
   Separa "erra o nível" (confiabilidade) de "não distingue os casos"
   (resolução). Um previsor que sempre diz a taxa-base é perfeitamente
   confiável e completamente inútil; só a decomposição mostra isso.

**O horizonte é re-ancorado.** O ponto da série guarda o horizonte contra o
``deadline`` do contrato, que é um proxy. O horizonte que vale é o medido contra
``determination_date`` — quando a fonte oficial publicou. Pontos cuja base é
``desconhecida`` (import legado) são **excluídos**: sem saber quando a fonte
publicou, o horizonte é ficção com aparência de número.

**Recusa antes de enfeitar.** Abaixo da amostra mínima nada é agregado. Curva de
confiabilidade com poucos pontos é ruído desenhado com régua, e gráfico convence
mais do que merece.

A matemática aqui é de domínio público (Brier 1950; Murphy 1973) e está
reimplementada em ~40 linhas de stdlib — nenhuma dependência nova entra para
calcular média e diferença ao quadrado.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

SERIE_PADRAO = Path("reports/markets/serie_p.jsonl")
RESOLUCOES_PADRAO = Path("reports/markets/resolucoes.jsonl")

# Curva de confiabilidade com poucos pares é ruído desenhado com régua. O corte
# é alto de propósito: estimar frequência observada por faixa exige pontos EM
# CADA faixa, não no total. Declarado, não escondido.
AMOSTRA_MINIMA = 30

# O portão que importa mais, e por que ele existe separado do de cima.
#
# A série grava um ponto POR DIA para cada mercado aberto. Três mercados vivos
# por quarenta dias produzem cento e vinte pares — e apenas TRÊS desfechos. O
# Brier sobre esses pares, a curva de confiabilidade e o skill score sairiam
# todos com aparência de amostra grande, apoiados em três caras-ou-coroas.
#
# O tamanho amostral efetivo de uma medição de calibração é o número de
# DESFECHOS distintos, não o de observações: os pontos de um mesmo claim são
# quase perfeitamente correlacionados, porque o desfecho deles é o mesmo. Contar
# pontos seria a forma mais eficiente de esta plataforma publicar um número que
# não vale o que aparenta — exatamente o que o cabeçalho deste arquivo diz
# recusar.
#
# O valor 30 não é escolhido aqui: é o mesmo que o projeto já declara como
# gargalo real ("trinta contratos precisam terminar"). O portão passa a
# EXIGIR o que o plano já dizia.
CLAIMS_MINIMOS = 30

# Mínimo por faixa para a faixa ser reportada — abaixo disso ela sai como None.
# Também em CLAIMS distintos, pelo mesmo argumento: cinco pontos de um único
# contrato dão frequência observada de 0 ou 1, que é ruído, não frequência.
MINIMO_POR_FAIXA = 5

# Faixas de probabilidade da curva. Cortes nossos, escolhidos para que 0,50
# (o prior de máxima incerteza deste projeto) caia no MEIO de uma faixa e não
# na fronteira entre duas.
FAIXAS_P = ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0))

# Faixas de horizonte, em dias até a determinação. Cortes nossos: refletem o
# calendário de divulgação brasileiro (mensal), não o de outra economia.
FAIXAS_HORIZONTE = (
    ("ate_7d", 0, 7),
    ("8_a_30d", 8, 30),
    ("31_a_90d", 31, 90),
    ("mais_de_90d", 91, 10_000),
)


class CalibracaoError(RuntimeError):
    """Insumo corrompido. Sempre levanta — calibração não se inventa."""


def _jsonl(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def pares(
    *,
    serie: Path = SERIE_PADRAO,
    resolucoes: Path = RESOLUCOES_PADRAO,
) -> dict[str, Any]:
    """Cruza cada ponto de p(t) com o desfecho do seu claim, re-ancorando o horizonte.

    Devolve os pares utilizáveis e, separadamente, o motivo de cada exclusão —
    porque "por que sobrou tão pouco" é a pergunta que um auditor faz primeiro.
    """
    from asus_theye.markets.resolution import BASES_CONFIAVEIS
    from asus_theye.markets.serie_p import trilha_de

    por_claim = {str(li["claim_id"]): li for li in _jsonl(resolucoes) if li.get("outcome") is not None}

    utilizaveis: list[dict[str, Any]] = []
    excluidos = {
        "claim_sem_desfecho": 0,
        "sem_determination_date": 0,
        "base_nao_confiavel": 0,
        "origem_nao_classificada": 0,
    }

    for ponto in _jsonl(serie):
        desfecho = por_claim.get(str(ponto.get("claim_id")))
        if desfecho is None:
            excluidos["claim_sem_desfecho"] += 1
            continue
        determinada = desfecho.get("determination_date")
        if not determinada:
            excluidos["sem_determination_date"] += 1
            continue
        if str(desfecho.get("determination_basis", "")) not in BASES_CONFIAVEIS:
            excluidos["base_nao_confiavel"] += 1
            continue
        trilha = trilha_de(ponto.get("origem"))
        if trilha is None:
            # Não sabemos de que trilha veio: excluir é a única saída honesta.
            # Chutar contamina a régua das DUAS de uma vez.
            excluidos["origem_nao_classificada"] += 1
            continue
        try:
            horizonte = (date.fromisoformat(str(determinada)) - date.fromisoformat(str(ponto["observado_em"]))).days
        except (ValueError, TypeError) as exc:
            raise CalibracaoError(f"{ponto.get('claim_id')}: datas inválidas no par ({exc})") from exc

        utilizaveis.append(
            {
                "claim_id": str(ponto["claim_id"]),
                "trilha": trilha,
                "market_area_id": str(ponto.get("market_area_id", "")),
                "probability": float(ponto["probability"]),
                "outcome": int(desfecho["outcome"]),
                "observado_em": str(ponto["observado_em"]),
                "determination_date": str(determinada),
                # o horizonte que VALE: contra a publicação da fonte, não contra
                # o fechamento do contrato
                "horizonte_dias": horizonte,
                "horizonte_ate_deadline": ponto.get("horizonte_dias"),
            }
        )
    return {"pares": utilizaveis, "excluidos": excluidos}


def _claims(itens: list[dict[str, Any]]) -> int:
    """Quantos DESFECHOS distintos há por trás destes pares.

    É este o tamanho amostral efetivo de qualquer medição de calibração: os
    pontos de um mesmo claim compartilham o desfecho, então contá-los como
    observações independentes infla a amostra sem acrescentar evidência.

    Item **sem** identidade cai num balde só. É a escolha fechada: sem saber de
    que contrato o ponto veio, não há como provar que ele é independente dos
    outros, e presumir que é seria inflar a amostra exatamente onde a prova
    falta. ``pares()`` sempre preenche ``claim_id``; o balde existe para quem
    chame estes auxiliares com dado avulso.
    """
    return len({str(i.get("claim_id") or "\u2014sem-identidade\u2014") for i in itens})


def _brier(itens: list[dict[str, Any]]) -> float | None:
    if not itens:
        return None
    return round(sum((float(i["probability"]) - int(i["outcome"])) ** 2 for i in itens) / len(itens), 4)


def comparar_trilhas(itens: list[dict[str, Any]]) -> dict[str, Any]:
    """Pontua as duas trilhas com a mesma régua — e só onde a régua é a mesma.

    **Por que a comparação exige pares casados.** Comparar o Brier de dois
    preditores só é honesto sobre o **mesmo conjunto de eventos**. Se a trilha
    própria ficou sem ponto justamente nos dias em que a fonte de notícia
    estava fora do ar, o Brier dela sai artificialmente bom — não porque
    acertou mais, mas porque **não estava lá** nos dias difíceis. Isso é viés
    de sobrevivência com aparência de mérito, e é o modo mais fácil de esta
    plataforma alegar um desempenho que não tem.

    Por isso o skill score só olha ``(claim_id, observado_em)`` onde **as duas**
    trilhas publicaram. Os pontos sem par continuam contando nas métricas
    individuais de cada trilha, mas nunca na comparação.

    **O benchmark é declarado, não escolhido depois.** O denominador é sempre o
    Focus. Skill positivo significa que a trilha própria bateu o consenso;
    negativo, que perdeu — e perder é o resultado esperado, registrado antes de
    qualquer liquidação em ``reports/provenance/GDELT-cobertura-noticiosa.md``.
    """
    from asus_theye.markets.serie_p import TRILHA_FOCUS, TRILHA_PROPRIA

    por_trilha: dict[str, list[dict[str, Any]]] = {TRILHA_FOCUS: [], TRILHA_PROPRIA: []}
    for item in itens:
        por_trilha.setdefault(str(item.get("trilha", TRILHA_FOCUS)), []).append(item)

    focus = {(i["claim_id"], i["observado_em"]): i for i in por_trilha[TRILHA_FOCUS]}
    propria = {(i["claim_id"], i["observado_em"]): i for i in por_trilha[TRILHA_PROPRIA]}
    casados = sorted(set(focus) & set(propria))
    claims_casados = len({c[0] for c in casados})

    resultado: dict[str, Any] = {
        "por_trilha": [
            {"trilha": nome, "n": len(por_trilha[nome]), "brier": _brier(por_trilha[nome])}
            for nome in (TRILHA_FOCUS, TRILHA_PROPRIA)
        ],
        "benchmark": TRILHA_FOCUS,
        "n_casados": len(casados),
        "claims_casados": claims_casados,
        "amostra_minima": AMOSTRA_MINIMA,
        "claims_minimos": CLAIMS_MINIMOS,
        "metodo": (
            "skill score = 1 − Brier(própria)/Brier(Focus), calculado SÓ sobre pontos em que as "
            "duas trilhas publicaram no mesmo claim e no mesmo dia. Pontos sem par contam nas "
            "métricas de cada trilha, nunca na comparação: uma trilha que falta nos dias difíceis "
            "teria Brier melhor sem ter acertado mais. O portão conta DESFECHOS distintos, não "
            "pares: pontos do mesmo claim compartilham o desfecho e não são evidência independente."
        ),
    }

    if claims_casados < CLAIMS_MINIMOS or len(casados) < AMOSTRA_MINIMA:
        resultado["suficiente"] = False
        resultado["skill_score"] = None
        resultado["brier_casado"] = None
        resultado["leitura"] = (
            f"{claims_casados} desfecho(s) distinto(s) casado(s) contra mínimo de {CLAIMS_MINIMOS} "
            f"({len(casados)} par(es) contra {AMOSTRA_MINIMA}). Nada é comparado: declarar vantagem "
            "sobre um punhado de desfechos é o erro que esta casa não comete — e cem pares vindos de "
            "três contratos são três desfechos, por mais que pareçam cem."
        )
        return resultado

    brier_focus = _brier([focus[c] for c in casados])
    brier_propria = _brier([propria[c] for c in casados])
    resultado["suficiente"] = True
    resultado["brier_casado"] = {TRILHA_FOCUS: brier_focus, TRILHA_PROPRIA: brier_propria}

    if not brier_focus:
        # Focus perfeito no conjunto casado: a razão não existe, e inventar um
        # número aqui seria pior que dizer que não dá para dividir.
        resultado["skill_score"] = None
        resultado["leitura"] = (
            "Brier do Focus é zero no conjunto casado — o skill score é uma razão que não existe. "
            "Sem número: a trilha própria não tem como superar um acerto perfeito."
        )
        return resultado

    skill = round(1.0 - (float(brier_propria or 0.0) / float(brier_focus)), 4)
    resultado["skill_score"] = skill
    if skill > 0:
        veredito = "a trilha própria SUPEROU o consenso no conjunto casado"
    elif skill < 0:
        veredito = "a trilha própria perdeu para o consenso — que era o resultado esperado"
    else:
        veredito = "paridade com o consenso"
    resultado["leitura"] = f"{veredito} (skill {skill:+.4f} sobre {len(casados)} pares casados)."
    return resultado


def curva_de_confiabilidade(itens: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Frequência observada por faixa de probabilidade declarada.

    Faixa com menos de :data:`MINIMO_POR_FAIXA` **desfechos distintos** reporta
    ``None`` — uma frequência estimada com 2 casos não é uma frequência, é uma
    anedota. E cinco pontos do mesmo contrato são um caso, não cinco: a
    frequência observada deles só pode valer 0 ou 1.
    """
    curva = []
    for inicio, fim in FAIXAS_P:
        # a última faixa inclui 1.0; as demais são semiabertas
        na_faixa = [
            i
            for i in itens
            if inicio <= float(i["probability"]) < fim or (fim == 1.0 and float(i["probability"]) == 1.0)
        ]
        claims_na_faixa = _claims(na_faixa)
        suficiente = claims_na_faixa >= MINIMO_POR_FAIXA
        curva.append(
            {
                "faixa": f"{inicio:.1f}–{fim:.1f}",
                "n": len(na_faixa),
                "claims": claims_na_faixa,
                "p_media_declarada": round(sum(float(i["probability"]) for i in na_faixa) / len(na_faixa), 4)
                if na_faixa
                else None,
                "frequencia_observada": round(sum(int(i["outcome"]) for i in na_faixa) / len(na_faixa), 4)
                if suficiente
                else None,
                "suficiente": suficiente,
            }
        )
    return curva


def decomposicao_de_murphy(itens: list[dict[str, Any]]) -> dict[str, Any] | None:
    """``BS = confiabilidade − resolução + incerteza`` (Murphy, 1973).

    Sem isto o Brier é opaco. Um previsor que sempre diz a taxa-base tem
    confiabilidade perfeita e resolução zero: acerta o nível e não distingue
    caso nenhum. Só a decomposição separa as duas coisas.
    """
    if not itens:
        return None
    n = len(itens)
    taxa_base = sum(int(i["outcome"]) for i in itens) / n
    confiabilidade = 0.0
    resolucao = 0.0
    for inicio, fim in FAIXAS_P:
        na_faixa = [
            i
            for i in itens
            if inicio <= float(i["probability"]) < fim or (fim == 1.0 and float(i["probability"]) == 1.0)
        ]
        if not na_faixa:
            continue
        peso = len(na_faixa) / n
        p_media = sum(float(i["probability"]) for i in na_faixa) / len(na_faixa)
        o_media = sum(int(i["outcome"]) for i in na_faixa) / len(na_faixa)
        confiabilidade += peso * (p_media - o_media) ** 2
        resolucao += peso * (o_media - taxa_base) ** 2
    return {
        "confiabilidade": round(confiabilidade, 4),
        "resolucao": round(resolucao, 4),
        "incerteza": round(taxa_base * (1 - taxa_base), 4),
        "taxa_base": round(taxa_base, 4),
        "nota": "BS = confiabilidade − resolução + incerteza; confiabilidade menor é melhor, resolução maior é melhor",
    }


def medir(*, serie: Path = SERIE_PADRAO, resolucoes: Path = RESOLUCOES_PADRAO) -> dict[str, Any]:
    """Snapshot da calibração. Abaixo da amostra mínima, RECUSA agregar."""
    from asus_theye.markets.serie_p import TRILHA_FOCUS

    cruzamento = pares(serie=serie, resolucoes=resolucoes)
    todos = cruzamento["pares"]

    # As métricas de manchete são da trilha do Focus, e por um motivo: é o `p`
    # que a plataforma PUBLICA como preço do contrato. A trilha própria é
    # medida em pé de igualdade logo abaixo, mas não se mistura aqui — somar as
    # duas num Brier só produziria um número que não mede nenhuma das duas.
    itens = [i for i in todos if str(i.get("trilha", TRILHA_FOCUS)) == TRILHA_FOCUS]
    n = len(itens)
    claims = _claims(itens)

    snapshot: dict[str, Any] = {
        "versao": 3,
        "n": n,
        "claims": claims,
        "claims_minimos": CLAIMS_MINIMOS,
        "trilha_das_metricas": TRILHA_FOCUS,
        "trilhas": comparar_trilhas(todos),
        "amostra_minima": AMOSTRA_MINIMA,
        "excluidos": cruzamento["excluidos"],
        "metodo_do_horizonte": (
            "horizonte medido contra determination_date (quando a fonte publicou), não contra o "
            "deadline do contrato. Pontos com base 'desconhecida' (import legado) são EXCLUÍDOS: "
            "sem saber quando a fonte publicou, o horizonte é ficção com aparência de número."
        ),
    }

    if claims < CLAIMS_MINIMOS or n < AMOSTRA_MINIMA:
        snapshot["suficiente"] = False
        snapshot["brier"] = None
        snapshot["curva"] = None
        snapshot["por_horizonte"] = None
        snapshot["por_area"] = None
        snapshot["murphy"] = None
        snapshot["metodo"] = (
            f"amostra insuficiente: {claims} desfecho(s) distinto(s) contra mínimo de "
            f"{CLAIMS_MINIMOS} (e {n} par(es) contra {AMOSTRA_MINIMA}). Nada é agregado. "
            "O que conta é DESFECHO distinto, não ponto: a série grava um ponto por dia, então "
            "três mercados vivos por quarenta dias dariam cento e vinte pares apoiados em três "
            "caras-ou-coroas. Curva de confiabilidade com poucos desfechos é ruído desenhado com "
            "régua, e gráfico convence mais do que merece — por isso ele não é desenhado."
        )
        return snapshot

    snapshot["suficiente"] = True
    snapshot["brier"] = _brier(itens)
    snapshot["curva"] = curva_de_confiabilidade(itens)
    snapshot["murphy"] = decomposicao_de_murphy(itens)
    snapshot["por_horizonte"] = [
        {
            "faixa": nome,
            "n": len([i for i in itens if inicio <= int(i["horizonte_dias"]) <= fim]),
            "brier": _brier([i for i in itens if inicio <= int(i["horizonte_dias"]) <= fim]),
        }
        for nome, inicio, fim in FAIXAS_HORIZONTE
    ]
    areas = sorted({str(i["market_area_id"]) for i in itens})
    snapshot["por_area"] = [
        {
            "area": area,
            "n": len([i for i in itens if i["market_area_id"] == area]),
            "brier": _brier([i for i in itens if i["market_area_id"] == area]),
        }
        for area in areas
    ]
    snapshot["metodo"] = (
        "Brier por par (p − desfecho)²; curva de confiabilidade por faixa de p; decomposição de "
        "Murphy (1973); estratificação por horizonte re-ancorado e por área de mercado. As "
        "métricas acima são da trilha do Focus, que é o p publicado; a comparação com a trilha "
        "própria está em 'trilhas', pontuada com a mesma régua e só sobre pontos casados."
    )
    return snapshot


def selar(sdk: Any, snapshot: dict[str, Any] | None = None, *, eventos: Path | None = None) -> dict[str, Any]:
    """Sela a medição de calibração. Snapshot idêntico = dedupe; estado novo = evento novo.

    A identidade é o hash do CONTEÚDO COMPLETO, e o motivo é uma cicatriz real:
    a versão antiga usava só {n, brier} — constante {0, None} enquanto a amostra
    é insuficiente — mas o conteúdo carrega contagens que mudam a cada rodada
    (excluidos cresce com a série). Identidade constante + conteúdo variável =
    divergência de selagem TODO dia, para sempre. Com o hash completo, cada
    estado distinto vira o seu próprio evento — a trilha de estados é história
    auditável, não colisão.
    """
    from asus_theye.markets.auditoria import EVENTOS_PADRAO, hash_de_conteudo, selar_registro

    snap = snapshot or medir()
    identidade = hash_de_conteudo(snap)
    return selar_registro(
        sdk,
        snap,
        tipo_evento="market.calibration",
        recurso="calibration",
        correlation_id=f"calibracao:{identidade[:32]}",
        eventos=eventos or EVENTOS_PADRAO,
    )
