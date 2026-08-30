# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sinal de atenção pública: visualizações de artigo na Wikipédia.

Conta quantas vezes uma página foi aberta por dia. Não é opinião, não é intenção
de voto, não é declaração de ninguém — é dado observacional, no mesmo sentido em
que volume negociado é dado observacional. Ninguém foi perguntado.

Fonte pública, gratuita, sem cadastro, série diária desde 2015, API documentada.
Não é API de concorrente nem de agregador: é o operador do site publicando o
próprio tráfego. E cobre outubro de 2022 inteiro, o que permite medir o modelo
contra uma eleição já ocorrida em vez de esperar outubro para descobrir se presta.

────────────────────────────────────────────────────────────────────────────
DUAS COISAS QUE A LITERATURA DIZ, E QUE ESTE ARQUIVO OBEDECE

**1. Visualização absoluta não prevê nada.** Yasseri & Bright (EPJ Data Science
5:22, 2016) — pageviews dão "pouco insight sobre o resultado absoluto", mas
informam sobre *mudança*. Medido aqui em 30/08/2026 com os candidatos de 2026: a
fatia bruta dava 38% a um autor de best-sellers e 7% ao presidente em exercício.
Por isso :func:`fatia_de_atencao` existe mas é a função errada para o modelo; a
certa é :func:`excedente_sobre_base`, que subtrai a fama pré-existente.

**2. Nenhuma normalização é consenso.** Excedente, log-razão, z-score,
detrending — a literatura não convergiu. O subtítulo do próprio trabalho de
continuidade de Yasseri & Bright ("towards theoretically informed models") é a
admissão de que esse é o problema aberto. Este módulo entrega a série crua e as
normalizações candidatas; **quem escolhe é o backtest, não o autor do módulo.**

E O VIÉS QUE NÃO DÁ PARA CONSERTAR AQUI, só declarar: pela pesquisa da própria
Wikimedia, o leitorado tem escolaridade superior, é majoritariamente jovem e
urbano, e homens geram cerca de 72% das visualizações. Para prever eleição
brasileira — onde as classes C, D e E decidem e 87% da classe DE acessa só por
celular — isso é viés de seleção grave. Não existe número publicado medindo o
tamanho dele. O sinal daqui entra no modelo como **um** regressor entre outros,
com peso aprendido, nunca como estimador isolado.
────────────────────────────────────────────────────────────────────────────

A ARMADILHA DO TÍTULO, que justifica a verificação obrigatória. O TSE publica o
nome de urna ``'LULA'``. Na Wikipédia em português o verbete ``Lula``
**redireciona para ``Teuthida``** — o molusco. Conferido ao vivo, mesma janela de
01–10/10/2022: o candidato teve 267.873 visualizações; o molusco, 1.474. Derivar
o artigo do nome de urna erraria por um fator de 180, sem exceção nenhuma e sem
nada parecer quebrado. Daí a regra: **título é declarado e verificado por
pessoa; título que redireciona é recusado, não seguido.**

IDENTIDADE NA REDE. O ``User-Agent`` identifica o cliente e nada mais. Em
30/08/2026 este projeto vazou nome de produto e conta de GitHub em cerca de 8
chamadas à Wikimedia, violando o Compromisso de Sigilo e Custódia. A política da
Wikimedia exige identificação com contato — não exige nome de produto nem conta
pessoal. O teste ``tests/audit/test_identidade_na_rede.py`` quebra o build se
isso voltar.

ATRASO: cerca de um dia. Conferido em 30/08/2026 — 29/08 tinha dado, 30/08 não.
Dia ausente é ausência, **nunca zero**: zero afirmaria que ninguém abriu a
página, coisa bem diferente de "ainda não publicaram".
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
import urllib.parse
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import median

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

PROJETO_PADRAO = "pt.wikipedia"
URL_VISUALIZACOES = (
    "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article"
    "/{projeto}/all-access/user/{artigo}/daily/{inicio}/{fim}"
)
URL_API = "https://{projeto}.org/w/api.php"

#: Identifica o CLIENTE, não a pessoa. Contato é opcional e vem do ambiente —
#: nunca do arquivo versionado. Ver o incidente no cabeçalho do módulo.
_CONTATO = os.environ.get("ASUS_THE_EYE_CONTATO", "").strip()
USER_AGENT = f"asus-the-eye/0.2 (+{_CONTATO})" if _CONTATO else "asus-the-eye/0.2 (+bot)"

MAX_BYTES = 4_000_000
TIMEOUT = 45
ATRASO_DIAS = 1


class AtencaoError(FonteError):
    """Falha ao ler o sinal de atenção. Nunca degrada em zero."""


class ArtigoAmbiguoError(AtencaoError):
    """O título redireciona ou não existe — quem resolve é uma pessoa."""


def _pedir(url: str, transport: Transport | None) -> bytes:
    try:
        r = get_bytes(
            url,
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise AtencaoError(f"Wikimedia inalcançável: {exc}") from exc
    if r.status == 404:
        raise AtencaoError(
            f"a Wikimedia não tem dado para este artigo/período: {url} — ambíguo "
            "por natureza (artigo inexistente OU período sem dado); confira o "
            "título com verificar_artigo() antes de concluir qualquer coisa"
        )
    if r.status == 429:
        raise AtencaoError("Wikimedia limitou a taxa (HTTP 429) — reduza a frequência")
    if r.status != 200:
        raise AtencaoError(f"Wikimedia respondeu HTTP {r.status} em {url}")
    return r.body


@dataclass(frozen=True)
class Artigo:
    titulo_pedido: str
    titulo_real: str
    redireciona: bool
    existe: bool

    @property
    def confiavel(self) -> bool:
        return self.existe and not self.redireciona


def verificar_artigo(
    titulo: str, *, projeto: str = PROJETO_PADRAO, transport: Transport | None = None
) -> Artigo:
    """Confere um título ANTES de medi-lo. Use uma vez, ao cadastrar."""
    if not titulo.strip():
        raise AtencaoError("título vazio")
    url = URL_API.format(projeto=projeto) + "?" + urllib.parse.urlencode(
        {"action": "query", "titles": titulo, "redirects": "1", "format": "json"}
    )
    try:
        consulta = json.loads(_pedir(url, transport).decode("utf-8"))["query"]
        paginas = list(consulta["pages"].values())
    except (ValueError, KeyError, AttributeError, UnicodeDecodeError) as exc:
        raise AtencaoError(f"resposta inesperada da API da Wikipédia ({exc})") from exc
    if not paginas:
        raise AtencaoError(f"a Wikipédia não devolveu página para {titulo!r}")
    p = paginas[0]
    return Artigo(
        titulo_pedido=titulo,
        titulo_real=str(p.get("title", titulo)),
        redireciona=bool(consulta.get("redirects")),
        existe="missing" not in p,
    )


def exigir_artigo_confiavel(
    titulo: str, *, projeto: str = PROJETO_PADRAO, transport: Transport | None = None
) -> str:
    """Devolve o título se for seguro; levanta explicando o destino se não for."""
    a = verificar_artigo(titulo, projeto=projeto, transport=transport)
    if not a.existe:
        raise ArtigoAmbiguoError(f"o artigo {titulo!r} não existe em {projeto}")
    if a.redireciona:
        raise ArtigoAmbiguoError(
            f"o título {titulo!r} redireciona para {a.titulo_real!r} em {projeto}. "
            "Declare o destino explicitamente, depois de conferir que é a pessoa "
            "certa — 'Lula' redireciona para 'Teuthida', o molusco."
        )
    return a.titulo_real


def visualizacoes(
    artigo: str,
    inicio: date,
    fim: date,
    *,
    projeto: str = PROJETO_PADRAO,
    transport: Transport | None = None,
) -> dict[date, int]:
    """Visualizações diárias, só nos dias que a Wikimedia publicou."""
    if inicio > fim:
        raise AtencaoError(f"período invertido: {inicio} > {fim}")
    if not re.fullmatch(r"[a-z]{2,3}\.wikipedia", projeto):
        raise AtencaoError(f"projeto em formato inesperado: {projeto!r}")
    url = URL_VISUALIZACOES.format(
        projeto=projeto,
        # safe="" é essencial: títulos têm "/" e "(" que precisam escapar.
        artigo=urllib.parse.quote(artigo.replace(" ", "_"), safe=""),
        inicio=inicio.strftime("%Y%m%d"),
        fim=fim.strftime("%Y%m%d"),
    )
    try:
        itens = json.loads(_pedir(url, transport).decode("utf-8"))["items"]
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        raise AtencaoError(f"resposta inesperada da Wikimedia ({exc})") from exc
    if not isinstance(itens, list):
        raise AtencaoError(f"items em formato inesperado: {type(itens).__name__}")
    serie: dict[date, int] = {}
    for item in itens:
        if not isinstance(item, dict):
            continue
        carimbo, vistas = str(item.get("timestamp", "")), item.get("views")
        if not re.fullmatch(r"\d{10}", carimbo) or not isinstance(vistas, int):
            raise AtencaoError(f"item malformado na série da Wikimedia: {item!r}")
        if vistas < 0:
            raise AtencaoError(f"contagem negativa de visualizações: {item!r}")
        serie[date(int(carimbo[:4]), int(carimbo[4:6]), int(carimbo[6:8]))] = vistas
    return serie


def fatia_de_atencao(totais: dict[str, float]) -> dict[str, float]:
    """Fatia bruta. **Não use como preditor** — está aqui para comparação.

    Yasseri & Bright (2016): visualização absoluta dá pouco insight sobre
    resultado. Medido com os candidatos de 2026: dá 38% a um autor de
    best-sellers e 7% ao presidente em exercício.
    """
    soma = sum(totais.values())
    if soma <= 0:
        raise AtencaoError("atenção total zero — série indisponível, não empate")
    return {k: v / soma for k, v in totais.items()}


def excedente_sobre_base(
    atual: dict[str, list[int]], base: dict[str, list[int]]
) -> dict[str, float]:
    """Atenção de campanha = mediana atual − mediana da linha de base.

    Subtrair (em vez de dividir) remove a fama pré-existente **mantendo a
    escala absoluta**. A razão pura infla quem parte de base pequena: medido
    aqui, um candidato saindo de 44 visualizações/dia aparecia com "5,6× de
    alta" e vencia o presidente em exercício.

    A mediana, e não a média, porque um único dia de pico distorce a média e um
    escândalo produz exatamente esse pico.
    """
    if set(atual) != set(base):
        raise AtencaoError(f"conjuntos diferentes: {sorted(set(atual) ^ set(base))}")
    fora: dict[str, float] = {}
    for nome in atual:
        if not atual[nome] or not base[nome]:
            raise AtencaoError(f"série vazia para {nome!r} — ausência não vira zero")
        fora[nome] = max(0.0, median(atual[nome]) - median(base[nome]))
    return fora


def log_razao(fatias: dict[str, float], *, piso: float = 1e-6) -> dict[str, float]:
    """Transformação log-razão centrada (CLR) de uma composição.

    Recomendação da literatura de dados composicionais (Aitchison; Stoetzer et
    al., *Political Analysis* 2019) para o problema que temos: mapear um sinal
    de ranking para proporções. Trabalhar em log-razão é o que permite ajustar
    concentração como uma **inclinação** — grandeza interpretável e regularizável
    — em vez do expoente de potência que, ajustado direto em 2022, disparou para
    o limite da busca (k = 6,0) e denunciou sobreajuste.

    ``piso`` evita log(0). Fatia zerada é ausência de sinal, não impossibilidade.
    """
    if not fatias:
        raise AtencaoError("composição vazia")
    seguras = {k: max(v, piso) for k, v in fatias.items()}
    media_log = sum(math.log(v) for v in seguras.values()) / len(seguras)
    return {k: math.log(v) - media_log for k, v in seguras.items()}


def de_log_razao(clr: dict[str, float]) -> dict[str, float]:
    """Volta de log-razão para composição que soma 1."""
    exp = {k: math.exp(v) for k, v in clr.items()}
    soma = sum(exp.values())
    if soma <= 0:
        raise AtencaoError("composição degenerada ao voltar do log-razão")
    return {k: v / soma for k, v in exp.items()}


def ultimo_dia_disponivel(hoje: date | None = None) -> date:
    """O dia mais recente que provavelmente já fechou na Wikimedia."""
    return (hoje or date.today()) - timedelta(days=ATRASO_DIAS)


def normalizar(texto: str) -> str:
    """Compara nome sem tropeçar em acento, caixa ou espaço repetido."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", sem_acento).casefold().strip()
