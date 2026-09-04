# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Liquida os contratos emitidos pelos seeds do site, contra a fonte oficial.

POR QUE ISTE MÓDULO PRECISOU EXISTIR. Em 31/08/2026 o catálogo tinha 366
contratos e **um** liquidado. A causa não era falta de fonte: ``fonte_ons.py`` e
``fonte_anp.py`` existiam, com 62 testes entre os dois, e **nenhum importador
fora dos próprios arquivos de teste**. Sabiam liquidar; não liquidavam.

E o relógio já estava correndo: em 31/08 nenhum contrato estava vencido, mas
**em 05/09 vencem 40 de uma vez**, e nos dois dias seguintes mais 80. Sem este
módulo, eles ficariam ``ABERTO`` para sempre, em silêncio, sem alarme nenhum —
que é o pior modo de falha possível para um produto cujo ativo é a série de
acerto.

POR QUE EM PYTHON, e não no Node do site. Os conectores testados vivem aqui. Um
resolvedor em Node teria de reimplementar o parsing do CSV do ONS e o índice
caótico da ANP — e duas implementações da mesma leitura divergem, sempre. Já
aconteceu nesta casa: a "mediana da casa" chegou a ter duas definições, uma em
cada linguagem. O resolvedor abre o SQLite do site diretamente e usa o conector
que já passou por teste.

O QUE ELE PODE E O QUE NÃO PODE ESCREVER. Os triggers instalados em 31/08
(``scripts/travar-criterio.mjs``) recusam alteração de ``criterio``, ``limiar``,
``deadline``, ``pergunta``, ``fonte_liquidacao`` e ``criado_em`` em contrato já
emitido. Este módulo não tenta: escreve apenas ``valor_observado``, ``outcome``,
``brier``, ``resolvido_em`` e ``estado``, que são os campos que a liquidação
existe para preencher. Se um dia ele tentar tocar o resto, o banco recusa — e é
assim que tem de ser.

BRIER, E POR QUE ELE NUNCA É ZERO ANTES DA HORA. ``brier = (p - desfecho)²``,
com ``p`` sendo o preço publicado ANTES do fato. Contrato aberto tem ``brier``
nulo, não zero: zero é a nota perfeita, e exibi-la em contrato não liquidado
inflaria a série de acerto com pontos que ninguém ganhou.

UNKNOWN OVER GUESS. Se a fonte ainda não publicou o dia, o contrato **fica
aberto** e o módulo diz isso. Não existe liquidar por estimativa: quem decide o
desfecho é o órgão, e órgão que não publicou não decidiu nada.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from asus_theye.markets.fonte_base import FonteError

#: Campos que a liquidação escreve. Tudo o que define o CONTRATO fica de fora —
#: e o banco recusa, caso alguém tente.
CAMPOS_MUTAVEIS = ("valor_observado", "outcome", "brier", "resolvido_em", "estado")


#: As áreas que este módulo sabe liquidar hoje. As demais aparecem como
#: pendentes com motivo explícito — nunca como falha silenciosa nem como
#: exceção que derruba a rodada dos outros.
AREAS_COM_RESOLVEDOR = frozenset(
    {
        "energia-carga",
        "energia-reservatorio",
        "combustivel-uf",
        "commodities",
        "cultura-streaming",
        "cambio-diario",
        "cyber",
        "commodities-fao",
        "clima-ear",
        "biotec-trials",
    }
)

#: IC-Br por segmento — as séries SGS que os PRÓPRIOS contratos declaram no
#: critério ("conforme a série NNNNN"). Conferido contra o banco do site em
#: 01/09/2026: geral 27574, agro 27575, metal 27576, energia 27577.
SERIES_ICBR = {"geral": 27574, "agro": 27575, "metal": 27576, "energia": 27577}


class ResolucaoError(RuntimeError):
    """Falha ao liquidar. Sempre levanta — nunca liquida por estimativa."""


class AreaSemResolvedor(ResolucaoError):
    """A área existe no catálogo, mas ninguém escreveu o resolvedor dela ainda.

    Subclasse própria porque este caso é NORMAL enquanto o catálogo cresce mais
    rápido que os resolvedores, e quem chama precisa distinguir "falta código"
    de "a fonte quebrou". Confundir os dois transformaria dívida conhecida em
    alarme de fonte — todo dia, em toda rodada.
    """


@dataclass(frozen=True)
class Liquidacao:
    claim_id: str
    valor_observado: float
    outcome: int
    brier: float


@dataclass(frozen=True)
class Pendente:
    """Contrato vencido que a fonte ainda não permite decidir."""

    claim_id: str
    motivo: str


def _observado(claim_id: str, area: str, transport=None) -> float | None:
    """O número que decide o contrato, lido da fonte oficial.

    Devolve ``None`` quando a fonte ainda não publicou — que é diferente de
    falhar. Levanta quando a fonte responde algo que não se entende.
    """
    # O sufixo `::pNN` é o degrau da escada; a chave do fato está no prefixo.
    base = claim_id.split("::")[0]

    if area in {"energia-carga", "energia-reservatorio"}:
        from asus_theye.markets.fonte_ons import (
            SUBSISTEMAS,
            carga_do_dia,
            ear_percentual_do_dia,
        )

        # energia-carga-se-2026-09-01  ->  sub="se", dia="2026-09-01"
        partes = base.rsplit("-", 3)
        if len(partes) != 4:
            raise ResolucaoError(f"claim_id fora do padrão esperado: {base!r}")
        sub = partes[0].rsplit("-", 1)[-1].upper()
        dia = "-".join(partes[1:])
        if sub not in SUBSISTEMAS:
            raise ResolucaoError(f"subsistema {sub!r} não é do SIN, em {base!r}")
        ler = carga_do_dia if area == "energia-carga" else ear_percentual_do_dia
        return ler(dia, sub, transport=transport)

    if area == "combustivel-uf":
        from asus_theye.markets.fonte_anp import MesNaoPublicado, preco_mediano

        # combustivel-gasolina-ac-2026-09  ->  uf="AC", competencia="2026-09"
        partes = base.rsplit("-", 3)
        if len(partes) != 4:
            raise ResolucaoError(f"claim_id fora do padrão esperado: {base!r}")
        uf = partes[1].upper()
        competencia = f"{partes[2]}-{partes[3]}"
        try:
            r = preco_mediano(competencia, uf, "GASOLINA", transport=transport)
        except MesNaoPublicado:
            return None  # normal até a ANP publicar; não é falha
        return None if r is None else r.mediana

    if area == "commodities":
        # commodities-icbr-geral-2026-09  ->  segmento="geral", competencia="2026-09"
        from asus_theye.markets.fonte_bcb import ipca_mensal

        partes = base.split("-")
        if len(partes) != 5 or partes[:2] != ["commodities", "icbr"]:
            raise ResolucaoError(f"claim_id fora do padrão esperado: {base!r}")
        serie = SERIES_ICBR.get(partes[2])
        if serie is None:
            raise ResolucaoError(
                f"segmento IC-Br {partes[2]!r} desconhecido em {base!r}; conhecidos: {sorted(SERIES_ICBR)}"
            )
        competencia = f"{partes[3]}-{partes[4]}"
        # ipca_mensal é o leitor genérico de série SGS mensal (nome histórico):
        # devolve o VALOR publicado da competência — para o IC-Br, o nível em
        # pontos, que é exatamente o que o critério dos contratos compara.
        return ipca_mensal(competencia, serie=serie, transport=transport)

    if area == "cyber":
        from asus_theye.markets.fonte_cisa import contagem_kev_no_mes

        # cyber-kev-2026-09 → competência no fim; o deadline do contrato dá a
        # folga pós-fechamento (o dateAdded da CISA é imediato, mas o mês só
        # se conta fechado).
        partes = base.split("-")
        if len(partes) != 4 or partes[:2] != ["cyber", "kev"]:
            raise ResolucaoError(f"claim_id fora do padrão esperado: {base!r}")
        return float(contagem_kev_no_mes(f"{partes[2]}-{partes[3]}", transport=transport))

    if area == "commodities-fao":
        from asus_theye.markets.fonte_fao import indice_no_mes

        # commodities-fao-ffpi-2026-08 → a FAO publica com ~1 mês de atraso;
        # None até publicar é PENDENTE, nunca zero.
        partes = base.split("-")
        if len(partes) != 5 or partes[:3] != ["commodities", "fao", "ffpi"]:
            raise ResolucaoError(f"claim_id fora do padrão esperado: {base!r}")
        return indice_no_mes(f"{partes[3]}-{partes[4]}", transport=transport)

    if area == "biotec-trials":
        from asus_theye.markets.fonte_clinicaltrials import contagem_estudos_no_mes

        # biotec-trials-br-2026-09 → país no meio, competência no fim. O
        # desenho manda o deadline dar folga (StartDate antecipável, registro
        # atrasado): o resolvedor lê a fonte NA DATA em que roda, como o
        # critério do contrato declara.
        partes = base.split("-")
        if len(partes) != 5 or partes[:2] != ["biotec", "trials"]:
            raise ResolucaoError(f"claim_id fora do padrão esperado: {base!r}")
        pais = {"br": "Brazil"}.get(partes[2])
        if pais is None:
            raise ResolucaoError(f"país {partes[2]!r} sem mapeamento em {base!r}")
        return float(
            contagem_estudos_no_mes(f"{partes[3]}-{partes[4]}", pais=pais, transport=transport)
        )

    if area == "clima-ear":
        from calendar import monthrange
        from datetime import timedelta

        from asus_theye.markets.fonte_ons import SUBSISTEMAS, ear_percentual_do_dia

        # clima-ear-se-2026-09 → EAR do ÚLTIMO registro do mês (critério IQF
        # 85/100 de 01/09/2026): tenta o último dia e volta até 7 dias, porque
        # o dataset diário pode não ter o dia-calendário exato ainda.
        partes = base.split("-")
        if len(partes) != 5 or partes[:2] != ["clima", "ear"]:
            raise ResolucaoError(f"claim_id fora do padrão esperado: {base!r}")
        sub = partes[2].upper()
        if sub not in SUBSISTEMAS:
            raise ResolucaoError(f"subsistema {sub!r} não é do SIN, em {base!r}")
        ano, mes = int(partes[3]), int(partes[4])
        fim = date(ano, mes, monthrange(ano, mes)[1])
        for volta in range(7):
            valor = ear_percentual_do_dia((fim - timedelta(days=volta)).isoformat(), sub, transport=transport)
            if valor is not None:
                return valor
        return None  # mês sem registro nenhum na janela: fonte ainda não publicou

    if area == "cambio-diario":
        from asus_theye.markets.fonte_ptax import ptax_venda_do_dia

        # CAMBIO-D::2026-09-01 — diferente das demais áreas, o fato aqui está
        # no SUFIXO: o dia do contrato vem depois do `::`. Dois contratos de
        # câmbio vencidos foram exatamente o que derrubou a primeira rodada
        # real (ver comentário no fim desta função) — este ramo fecha a dívida.
        partes = claim_id.split("::")
        if len(partes) != 2 or len(partes[1]) != 10:
            raise ResolucaoError(f"claim_id fora do padrão esperado: {claim_id!r}")
        return ptax_venda_do_dia(partes[1], transport=transport)

    if area == "cultura-streaming":
        # cultura-netflix-br-films-2026-08-30  ->  pais="BR", lista="Films", semana
        from asus_theye.markets.fonte_netflix import semanas_no_topo

        partes = base.split("-")
        if len(partes) != 7 or partes[:2] != ["cultura", "netflix"]:
            raise ResolucaoError(f"claim_id fora do padrão esperado: {base!r}")
        pais = partes[2].upper()
        categoria = {"films": "Films", "tv": "TV"}.get(partes[3])
        if categoria is None:
            raise ResolucaoError(f"lista {partes[3]!r} desconhecida em {base!r} (films|tv)")
        semana = "-".join(partes[4:])
        valor = semanas_no_topo(semana, pais=pais, categoria=categoria, transport=transport)
        return None if valor is None else float(valor)

    # Área sem resolvedor é estado CONHECIDO, não erro — e a diferença é a
    # rodada inteira. Levantar aqui faria um `cambio-diario` vencido derrubar a
    # liquidação de todos os contratos de energia e combustível do mesmo dia.
    #
    # Foi o que aconteceu na primeira execução contra o banco real: dois
    # contratos de câmbio venceram em 31/08, a exceção subiu, e nada liquidou.
    # É o mesmo modo de falha que `fonte_base.py` registra como bug já vivido —
    # a PTAX escapando do laço e derrubando a rodada.
    #
    # `AreaSemResolvedor` é subclasse para quem chama poder distinguir "ainda
    # não construí o resolvedor desta área" de "a fonte quebrou".
    raise AreaSemResolvedor(
        f"área {area!r} não tem resolvedor. Áreas com resolvedor: "
        + ", ".join(sorted(AREAS_COM_RESOLVEDOR))
    )


def liquidar_vencidos(
    banco: Path,
    *,
    hoje: date | None = None,
    transport=None,
    limite: int | None = None,
) -> tuple[list[Liquidacao], list[Pendente]]:
    """Liquida todo contrato vencido cuja fonte já publicou o desfecho.

    Devolve ``(liquidados, pendentes)``. Pendente **não é erro**: é a fonte
    ainda não ter publicado, e o contrato continua aberto esperando — como
    deve.
    """
    hoje = hoje or datetime.now(timezone.utc).date()
    con = sqlite3.connect(banco)
    con.row_factory = sqlite3.Row
    # Sem isto o trigger de imutabilidade não dispara em REPLACE. Ver a nota em
    # scripts/travar-criterio.mjs — é PRAGMA por conexão, não persistente.
    con.execute("PRAGMA recursive_triggers = ON")

    linhas = con.execute(
        "SELECT claim_id, area, limiar, prob_atual, deadline FROM mercados "
        "WHERE estado = 'ABERTO' AND deadline <= ? ORDER BY deadline, claim_id",
        (hoje.isoformat(),),
    ).fetchall()
    if limite is not None:
        linhas = linhas[:limite]

    liquidados: list[Liquidacao] = []
    pendentes: list[Pendente] = []

    for linha in linhas:
        try:
            valor = _observado(linha["claim_id"], linha["area"], transport=transport)
        except AreaSemResolvedor as exc:
            # Dívida conhecida, não falha: registra e segue para os outros.
            pendentes.append(Pendente(linha["claim_id"], str(exc)))
            continue
        except FonteError as exc:
            pendentes.append(Pendente(linha["claim_id"], f"fonte indisponível: {exc}"))
            continue
        if valor is None:
            pendentes.append(Pendente(linha["claim_id"], "fonte ainda não publicou"))
            continue

        # O critério de todo contrato desta casa é "MAIOR que o limiar".
        outcome = 1 if valor > float(linha["limiar"]) else 0
        p = float(linha["prob_atual"])
        brier = (p - outcome) ** 2

        con.execute(
            "UPDATE mercados SET valor_observado = ?, outcome = ?, brier = ?, "
            "resolvido_em = ?, estado = 'LIQUIDADO' WHERE claim_id = ?",
            (
                valor,
                outcome,
                brier,
                datetime.now(timezone.utc).isoformat(),
                linha["claim_id"],
            ),
        )
        liquidados.append(Liquidacao(linha["claim_id"], valor, outcome, brier))

    con.commit()
    con.close()
    return liquidados, pendentes
