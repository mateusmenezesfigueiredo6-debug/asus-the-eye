# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Preview eleitoral 2026 — o importador que faltava para modelo_2026.

Uma varredura estrutural de 30/08/2026 registrou, no próprio docstring do
modelo, que NENHUM import chamava as peças eleitorais: modelo_2026,
atencao_wikimedia e fonte_tse existiam testadas e órfãs. Este módulo é o
consumidor declarado: monta as evidências a partir de dado versionado (tempo
de TV) e de medição ao vivo (atenção Wikipédia), roda o Modelo2026 e devolve
o retrato datado que ``dados/modelo_2026_preview.json`` guarda.

Regras que este módulo IMPÕE (não só promete):
- Título de artigo é conferido por ``verificar_artigo`` antes de qualquer
  medição — título que não verifica EXCLUI a família de atenção da rodada
  inteira (a evidência tem de cobrir todos os candidatos; medir só alguns
  distorceria a composição), com o motivo listado no resultado.
- Candidato sem dado de TV medido fica FORA da ordem, listado em
  ``excluidos`` — UNKNOWN não vira piso inventado.
- Pesos com citação (exigência de ``Evidencia``); a razão 1:1 entre as duas
  famílias é ESCOLHA DECLARADA de neutralidade na ausência de medição
  conjunta publicada — está escrita no campo ``fonte_do_peso``, onde o
  auditor vai ler.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from asus_theye.markets.atencao_wikimedia import (
    AtencaoError,
    excedente_sobre_base,
    verificar_artigo,
    visualizacoes,
)
from asus_theye.markets.modelo_2026 import Evidencia, Modelo2026

DADOS = Path("dados")
ARQ_TEMPO_TV = DADOS / "tempo_de_tv_2026.json"
ARQ_ARTIGOS = DADOS / "artigos_wikipedia_2026.json"
ARQ_PREVIEW = DADOS / "modelo_2026_preview.json"

#: Janelas da medição de atenção, declaradas — mudar é decisão, não acidente.
JANELA_ATUAL_DIAS = 14
BASE_INICIO_DIAS = 60
BASE_FIM_DIAS = 30

#: Pausa entre candidatos na medição ao vivo. A primeira rodada real levou
#: HTTP 429 da Wikimedia no 4º candidato (3 chamadas por candidato, em
#: rajada); robô educado espera, não martela.
PAUSA_ENTRE_CANDIDATOS_S = 1.0

FONTE_PESO_TV = (
    "Speck & Cervi (2016), Dados — tempo de HGPE, beta padronizado 0,106 "
    "(N=13.038, R²=0,54)"
)
FONTE_PESO_ATENCAO = (
    "Yasseri & Bright (2016), EPJ Data Science — a VARIAÇÃO de visualização "
    "informa, o absoluto não; razão 1:1 com a família de TV é escolha "
    "declarada de neutralidade entre famílias, na ausência de medição "
    "conjunta publicada"
)
VIES_ATENCAO = "leitor da Wikipédia: ~72% homem, urbano, instruído — não é o eleitorado"


def evidencia_tempo_de_tv(caminho: Path = ARQ_TEMPO_TV) -> Evidencia:
    valores = json.loads(caminho.read_text(encoding="utf-8"))
    return Evidencia(
        nome="tempo de TV (HGPE, art. 47 §2º Lei 9.504/1997)",
        valores={str(k): float(v) for k, v in valores.items()},
        peso=1.0,
        fonte_do_peso=FONTE_PESO_TV,
    )


def evidencia_atencao(
    candidatos: tuple[str, ...],
    *,
    hoje: date | None = None,
    caminho_artigos: Path = ARQ_ARTIGOS,
    transport: Any = None,
) -> tuple[Evidencia | None, list[str]]:
    """Família de atenção ao vivo — ou ``(None, motivos)`` quando não sustenta.

    Tudo-ou-nada por desenho: a evidência precisa cobrir todos os candidatos.
    """
    hoje = hoje or date.today()
    mapa = {
        k: v
        for k, v in json.loads(caminho_artigos.read_text(encoding="utf-8")).items()
        if not k.startswith("_")
    }
    motivos: list[str] = []
    faltando = [c for c in candidatos if c not in mapa]
    if faltando:
        return None, [f"sem título de artigo cadastrado: {faltando}"]

    atual: dict[str, list[int]] = {}
    base: dict[str, list[int]] = {}
    for indice, candidato in enumerate(candidatos):
        if indice and transport is None:  # pausa só na medição real, nunca no fake
            import time

            time.sleep(PAUSA_ENTRE_CANDIDATOS_S)
        titulo = mapa[candidato]
        try:
            artigo = verificar_artigo(titulo, transport=transport)
            if not artigo.confiavel:
                detalhe = (
                    f"redireciona para {artigo.titulo_real!r}" if artigo.redireciona else "não existe"
                )
                motivos.append(f"{candidato}: artigo {titulo!r} não confiável ({detalhe})")
                continue
            a = visualizacoes(
                titulo, hoje - timedelta(days=JANELA_ATUAL_DIAS), hoje - timedelta(days=1), transport=transport
            )
            b = visualizacoes(
                titulo,
                hoje - timedelta(days=BASE_INICIO_DIAS),
                hoje - timedelta(days=BASE_FIM_DIAS),
                transport=transport,
            )
        except AtencaoError as erro:
            motivos.append(f"{candidato}: {erro}")
            continue
        if not a or not b:
            motivos.append(f"{candidato}: Wikimedia sem dias publicados na janela")
            continue
        atual[candidato] = list(a.values())
        base[candidato] = list(b.values())

    if motivos:
        return None, motivos
    excedente = excedente_sobre_base(atual, base)
    if all(v == 0.0 for v in excedente.values()):
        return None, ["excedente zero para todos — nenhuma atenção de campanha medida na janela"]
    return (
        Evidencia(
            nome=f"atenção Wikipédia (excedente sobre base, janelas {JANELA_ATUAL_DIAS}d vs {BASE_INICIO_DIAS}–{BASE_FIM_DIAS}d)",
            valores=excedente,
            peso=1.0,
            fonte_do_peso=FONTE_PESO_ATENCAO,
            vies_declarado=VIES_ATENCAO,
        ),
        [],
    )


def gerar_preview(
    *,
    com_atencao: bool = True,
    hoje: date | None = None,
    transport: Any = None,
    caminho_tv: Path = ARQ_TEMPO_TV,
    caminho_artigos: Path = ARQ_ARTIGOS,
) -> dict[str, Any]:
    """Roda o modelo e devolve o retrato datado (sem gravar nada)."""
    hoje = hoje or date.today()
    tv = evidencia_tempo_de_tv(caminho_tv)
    candidatos = tuple(tv.valores.keys())
    evidencias = [tv]
    atencao_motivos: list[str] = []
    if com_atencao:
        atencao, atencao_motivos = evidencia_atencao(
            candidatos, hoje=hoje, caminho_artigos=caminho_artigos, transport=transport
        )
        if atencao is not None:
            evidencias.append(atencao)

    modelo = Modelo2026(candidatos=candidatos, evidencias=evidencias)
    return {
        "gerado_em": hoje.isoformat(),
        "componentes": [
            {"nome": e.nome, "peso": e.peso, "fonte_do_peso": e.fonte_do_peso, "vies_declarado": e.vies_declarado}
            for e in evidencias
        ],
        "atencao_excluida_por": atencao_motivos,
        "ordem_sem_apuracao": dict(modelo.ordem()),
        "magnitude_encolhida": modelo.fatias(magnitude=True),
        "encolhimento": modelo.encolhimento,
        "avisos": modelo.avisos(hoje),
    }
