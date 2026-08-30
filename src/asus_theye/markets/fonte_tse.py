# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector de resolução: TSE — resultado oficial de eleição.

Lê o servidor de divulgação do Tribunal Superior Eleitoral, que publica os
boletins em JSON. É a fonte que decide o desfecho de qualquer contrato
eleitoral: o número que o próprio Estado apura.

O QUE ESTE MÓDULO **NÃO** É. Ele não coleta opinião, não entrevista ninguém,
não tem amostra nem questionário. Lê resultado consumado — mesma natureza de
dado da PTAX. A distinção é jurídica, não retórica: a Res. TSE 23.600/2019
disciplina "pesquisa de opinião pública", caracterizada por população-alvo,
plano amostral, modo de coleta e questionário. Nada disso existe aqui, porque
aqui não se pergunta nada a ninguém.

TUDO ABAIXO FOI CONFERIDO AO VIVO EM 30/08/2026, não deduzido de documentação.

  Boletim presidencial de 2022 (imutável, serve de padrão-ouro):
    /oficial/ele2022/544/dados-simplificados/br/br-c0001-e000544-r.json -> 200
    pst='100,00'  pa='20,95'  t='1'  vv='118229719'  vb='1964779'  tvn='3487874'
    cand[0] = {n:'13', nm:'LULA',           pvap:'48,43', vap:'57259504', st:'2º turno'}
    cand[1] = {n:'22', nm:'JAIR BOLSONARO', pvap:'43,20', vap:'51072345', st:'2º turno'}

  Índice oficial de eleições:
    /oficial/comum/config/ele-c.json -> 200
    Diz qual ciclo está publicado e, para cada eleição, QUAIS CARGOS existem
    (``pl[].e[].abr[].cp[]`` traz ``cd`` e ``ds``). É daí que saem os códigos
    de cargo — nenhum número é chutado neste arquivo.

  O QUE AINDA NÃO EXISTE, e é bom que o código diga isso em voz alta:
    em 30/08/2026 o índice aponta o ciclo ``ele2024`` e o pleito mais recente é
    de 21/06/2026. **A eleição geral de 2026 não está publicada.** Por isso
    "ainda não publicado" é um estado de primeira classe aqui, não um erro.

  Bloqueios desta rede, declarados em vez de escondidos:
    resultados.tse.jus.br        -> 200 (é o que usamos)
    dadosabertos.tse.jus.br      -> 403, inclusive o robots.txt
    www.tse.jus.br               -> 403
    .../config/cert-*.cer        -> 403  (o certificado do TSE)

ASSINATURA: ARQUIVAR AGORA, VERIFICAR DEPOIS. Ao lado de cada boletim o TSE
publica um ``.sig`` — 128 bytes de assinatura RSA em base64. O certificado que
a verificaria está bloqueado nesta rede, então **não verificamos, e não
dizemos que verificamos**. O que fazemos é baixar o ``.sig`` junto com o
boletim e selar o sha256 dos dois no mesmo elo. Assinatura só tem valor se
alguém a guardou no instante da liquidação; guardada, a verificação continua
possível amanhã, quando o certificado estiver alcançável. Não guardada,
nenhuma perícia futura a recupera.

RESULTADO NÃO É ETERNO. Cassação e recontagem judicial já mudaram resultado
anos depois do pleito. Por isso todo contrato liquidado aqui declara: **liquida
pelo boletim oficial da data declarada; reversão judicial posterior não
reabre**. Sem essa cláusula um contrato ficaria aberto por todo o mandato.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass

from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpError, Transport, get_bytes

BASE = "https://resultados.tse.jus.br/oficial"
URL_INDICE = f"{BASE}/comum/config/ele-c.json"
URL_BOLETIM = "{base}/{ciclo}/{codigo}/dados-simplificados/{abr}/{arquivo}"

MAX_BYTES = 4_000_000
TIMEOUT = 45

#: Apuração encerrada. Abaixo disto o número ainda muda, e liquidar com
#: apuração parcial é decidir o contrato com um placar de meio-tempo.
PST_MINIMO = 100.0

#: ESCOPO DE CARGOS — decisão do titular, gravada no código.
#:
#: "desde presidência até deputado federal, não mais abaixo que isso."
#:
#: A trava é expressa sobre o RÓTULO que o próprio TSE publica (``ds``), não
#: sobre números de cargo decorados. Assim o escopo não depende de eu ter
#: adivinhado certo o código de senador: se o TSE chama de "Deputado
#: Estadual", fica de fora, seja qual for o número. Um mercado de vereador não
#: é rejeitado por convenção — ele não consegue nascer.
ESCOPO_PERMITIDO = frozenset(
    {"presidente", "governador", "senador", "deputado federal"}
)

#: Só Presidente (CF art. 77) e Governador (CF art. 28, que remete ao art. 77)
#: têm segundo turno por maioria absoluta. Senador é eleito por pluralidade
#: (CF art. 46) e Deputado Federal por sistema proporcional — nenhum dos dois
#: tem "segundo turno" como conceito. Aplicar a aritmética de maioria absoluta
#: a um boletim desses cargos devolveria 0.0/1.0 com aparência de resposta
#: confiável, mas semanticamente sem sentido — achado da revisão do Copilot em
#: 30/08/2026, verificado e confirmado antes de corrigir.
CARGOS_COM_SEGUNDO_TURNO = frozenset({"presidente", "governador"})


class FonteTSEError(FonteError):
    """Resposta inesperada do TSE. Sempre levanta — nunca degrada em valor."""


class PleitoNaoPublicado(FonteTSEError):
    """O pleito ainda não está no servidor.

    Subclasse própria porque este caso é NORMAL até a véspera da apuração, e
    quem chama precisa distinguir "o TSE ainda não publicou" de "o TSE
    respondeu algo que eu não entendo". Confundir os dois transformaria a
    espera pelo pleito em alarme de fonte quebrada, todo dia, por meses.
    """


def _texto_normalizado(texto: str) -> str:
    """Compara sem tropeçar em acento, caixa ou espaço repetido."""
    sem_acento = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    return re.sub(r"\s+", " ", sem_acento).casefold().strip()


def cargo_no_escopo(descricao: str) -> bool:
    """O titular autoriza contrato sobre este cargo?"""
    return _texto_normalizado(descricao) in ESCOPO_PERMITIDO


def _numero(bruto: object, campo: str) -> float:
    """Percentual como o TSE escreve: vírgula decimal (``'48,43'``).

    O ponto só é tratado como separador de milhar QUANDO HÁ VÍRGULA. Sem essa
    condição, o dia em que o TSE publicasse ``'48.43'`` viraria ``4843`` em
    silêncio — um erro de cem vezes que nenhuma exceção denunciaria, e que
    liquidaria o contrato contra um número inventado.
    """
    texto = str(bruto).strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        valor = float(texto)
    except ValueError as exc:
        raise FonteTSEError(f"campo {campo!r} não numérico no TSE: {bruto!r}") from exc
    if valor != valor or valor in (float("inf"), float("-inf")):
        raise FonteTSEError(f"campo {campo!r} veio NaN/Infinito do TSE: {bruto!r}")
    return valor


def _inteiro(bruto: object, campo: str) -> int:
    """Contagem de votos. Inteiro de verdade — nunca passa por ``float``.

    ``vv`` de 2022 é 118.229.719. Ainda cabe em float64 sem perda, mas contagem
    de voto é a última coisa que deve andar em ponto flutuante: a comparação de
    maioria absoluta lá embaixo depende de ser exata.
    """
    texto = str(bruto).strip().replace(".", "")
    if not re.fullmatch(r"\d+", texto):
        raise FonteTSEError(f"campo {campo!r} não é contagem de votos: {bruto!r}")
    return int(texto)


@dataclass(frozen=True)
class Boletim:
    """Um boletim do TSE e a prova de que foi ele que lemos."""

    ciclo: str
    codigo: str
    abrangencia: str
    #: Código do cargo (ex.: 1 = presidente). Guardado porque
    #: :func:`houve_segundo_turno` precisa saber que cargo é este para não
    #: aplicar maioria absoluta a senador ou deputado federal.
    cargo: int
    url: str
    sha256: str
    #: sha256 do ``.sig`` publicado ao lado. ``None`` quando o TSE não publicou
    #: assinatura para este arquivo, ou quando ela não pôde ser baixada — e
    #: ``None`` significa exatamente isso, nunca "verificada".
    assinatura_sha256: str | None
    dados: dict

    @property
    def apuracao_encerrada(self) -> bool:
        return _numero(self.dados["pst"], "pst") >= PST_MINIMO

    @property
    def votos_validos(self) -> int:
        return _inteiro(self.dados["vv"], "vv")


def _baixar(url: str, transport: Transport | None) -> bytes:
    try:
        resposta = get_bytes(
            url,
            headers={"Accept": "application/json"},
            timeout=TIMEOUT,
            max_bytes=MAX_BYTES,
            transport=transport,
        )
    except HttpError as exc:
        raise FonteTSEError(f"TSE inalcançável: {exc}") from exc
    if resposta.status == 404:
        raise PleitoNaoPublicado(f"o TSE ainda não publicou: {url}")
    if resposta.status != 200:
        raise FonteTSEError(f"TSE respondeu HTTP {resposta.status} em {url}")
    return resposta.body


def boletim(
    ciclo: str,
    codigo: str,
    *,
    cargo: int,
    abrangencia: str = "br",
    transport: Transport | None = None,
) -> Boletim:
    """Baixa o boletim de um cargo num pleito, com a prova do que foi lido.

    ``cargo`` é o código que o TSE publica no índice — obtenha-o com
    :func:`cargos_da_eleicao`, não de memória.
    """
    if not re.fullmatch(r"ele\d{4}", ciclo):
        raise FonteTSEError(f"ciclo em formato inesperado: {ciclo!r}")
    if not re.fullmatch(r"\d{1,10}", str(codigo)):
        raise FonteTSEError(f"código de eleição em formato inesperado: {codigo!r}")
    if not re.fullmatch(r"[a-z]{2}", abrangencia):
        raise FonteTSEError(f"abrangência em formato inesperado: {abrangencia!r}")
    if not 1 <= int(cargo) <= 99:
        raise FonteTSEError(f"código de cargo fora da faixa: {cargo!r}")

    arquivo = f"{abrangencia}-c{int(cargo):04d}-e{int(codigo):06d}-r.json"
    url = URL_BOLETIM.format(base=BASE, ciclo=ciclo, codigo=codigo, abr=abrangencia, arquivo=arquivo)
    corpo = _baixar(url, transport)

    try:
        dados = json.loads(corpo.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FonteTSEError(f"resposta do TSE não é JSON válido ({exc})") from exc
    if not isinstance(dados, dict):
        raise FonteTSEError(f"boletim em formato inesperado: {type(dados).__name__}")
    for campo in ("pst", "pa", "vv", "cand"):
        if campo not in dados:
            raise FonteTSEError(f"boletim sem o campo {campo!r}: {sorted(dados)[:12]}")

    # A assinatura é acessório: se ela falhar, o boletim ainda liquida — mas
    # fica registrado que liquidou SEM assinatura arquivada. O contrário
    # (derrubar a liquidação porque um .sig não veio) trocaria uma prova a mais
    # por uma indisponibilidade a mais.
    assinatura: str | None = None
    try:
        assinatura = hashlib.sha256(
            _baixar(url.removesuffix(".json") + ".sig", transport)
        ).hexdigest()
    except FonteTSEError:
        assinatura = None

    return Boletim(
        ciclo=ciclo,
        codigo=str(codigo),
        abrangencia=abrangencia,
        cargo=int(cargo),
        url=url,
        sha256=hashlib.sha256(corpo).hexdigest(),
        assinatura_sha256=assinatura,
        dados=dados,
    )


def abstencao(b: Boletim) -> float | None:
    """Percentual de abstenção, ou ``None`` se a apuração não encerrou.

    Abstenção é estatística administrativa — quantos eleitores não
    compareceram. Não é opinião de ninguém sobre nada.
    """
    return _numero(b.dados["pa"], "pa") if b.apuracao_encerrada else None


def _candidato(b: Boletim, nome_urna: str) -> dict:
    candidatos = b.dados.get("cand")
    if not isinstance(candidatos, list) or not candidatos:
        raise FonteTSEError(f"boletim sem lista de candidatos: {candidatos!r}")
    alvo = _texto_normalizado(nome_urna)
    achados = [
        c
        for c in candidatos
        if isinstance(c, dict) and _texto_normalizado(str(c.get("nm", ""))) == alvo
    ]
    if not achados:
        publicados = [str(c.get("nm", "")) for c in candidatos if isinstance(c, dict)][:12]
        raise FonteTSEError(
            f"candidato {nome_urna!r} não está no boletim — publicados: {publicados}"
        )
    if len(achados) > 1:
        raise FonteTSEError(f"mais de um candidato chamado {nome_urna!r} no boletim")
    return achados[0]


def percentual_do_candidato(b: Boletim, nome_urna: str) -> float | None:
    """Percentual dos VOTOS VÁLIDOS do candidato, ou ``None`` se não encerrou.

    "Válidos" é dito de propósito: é a base do art. 77 da Constituição, já
    líquida de branco e nulo. Confundir com votos totais mudaria o desfecho de
    qualquer contrato de percentual — em 2022 seriam 48,43% contra 46,29%.
    """
    if not b.apuracao_encerrada:
        return None
    return _numero(_candidato(b, nome_urna).get("pvap"), "pvap")


def houve_segundo_turno(b: Boletim, *, descricao_cargo: str) -> float | None:
    """1.0 se ninguém teve maioria absoluta dos válidos; 0.0 se teve.

    A conta é feita em INTEIROS (``vap * 2 > vv``), não sobre ``pvap``. O
    percentual publicado vem arredondado em duas casas: um candidato com
    50,004% dos válidos aparece como ``'50,00'``, e a comparação em float diria
    "houve segundo turno" numa eleição decidida no primeiro. Voto se conta, não
    se arredonda.

    ``descricao_cargo`` é OBRIGATÓRIO e é o rótulo publicado pelo TSE, obtido
    de :func:`cargos_da_eleicao` — nunca decorado. Sem isso a função aplicaria
    maioria absoluta a QUALQUER boletim: senador (CF art. 46, pluralidade) e
    deputado federal (sistema proporcional) não têm segundo turno como
    conceito, e a conta devolveria 0.0/1.0 com aparência de resposta confiável
    sem sentido nenhum. Mesma disciplina de declarar-não-derivar do escopo de
    cargos e do título de artigo na Wikipédia.
    """
    if _texto_normalizado(descricao_cargo) not in CARGOS_COM_SEGUNDO_TURNO:
        raise FonteTSEError(
            f"{descricao_cargo!r} não tem segundo turno por maioria absoluta — "
            f"só {sorted(CARGOS_COM_SEGUNDO_TURNO)} têm. Aplicar esta conta a "
            "outro cargo produziria um número sem sentido jurídico."
        )
    if not b.apuracao_encerrada:
        return None
    candidatos = [c for c in b.dados.get("cand", []) if isinstance(c, dict)]
    if not candidatos:
        raise FonteTSEError("boletim sem candidatos para apurar segundo turno")
    validos = b.votos_validos
    if validos <= 0:
        raise FonteTSEError(f"boletim com votos válidos não positivos: {validos}")
    maior = max(_inteiro(c.get("vap"), "vap") for c in candidatos)
    return 0.0 if maior * 2 > validos else 1.0


def situacao_do_candidato(b: Boletim, nome_urna: str) -> str | None:
    """O veredito do próprio TSE: ``'Eleito'``, ``'2º turno'``, ``'Não eleito'``…

    Para o mercado "quem ganha", este campo é melhor do que qualquer conta que
    eu fizesse sobre percentuais: quem declara eleito é o Tribunal, e o
    contrato deve liquidar pelo que o Tribunal declarou — não pela aritmética
    que a casa achou correta.
    """
    if not b.apuracao_encerrada:
        return None
    situacao = _candidato(b, nome_urna).get("st")
    if not isinstance(situacao, str) or not situacao.strip():
        raise FonteTSEError(f"candidato {nome_urna!r} sem situação declarada no boletim")
    return situacao.strip()


@dataclass(frozen=True)
class CargoPublicado:
    """Um cargo que existe de fato num pleito, segundo o índice do TSE."""

    codigo: int
    descricao: str
    abrangencia: str

    @property
    def no_escopo(self) -> bool:
        return cargo_no_escopo(self.descricao)


@dataclass(frozen=True)
class EleicaoPublicada:
    codigo: str
    nome: str
    data: str
    turno: str
    codigo_segundo_turno: str | None
    cargos: tuple[CargoPublicado, ...]


def eleicoes_publicadas(
    *, transport: Transport | None = None
) -> tuple[str, tuple[EleicaoPublicada, ...]]:
    """Lê o índice oficial: ``(ciclo_publicado, eleições)``.

    Existe para que ninguém precise adivinhar código de eleição nem de cargo —
    e para que a resposta a "o TSE já publicou 2026?" seja uma leitura, não uma
    suposição. Em 30/08/2026 a resposta honesta é: ainda não.
    """
    corpo = _baixar(URL_INDICE, transport)
    try:
        indice = json.loads(corpo.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise FonteTSEError(f"índice do TSE não é JSON válido ({exc})") from exc
    if not isinstance(indice, dict) or "pl" not in indice:
        raise FonteTSEError(f"índice do TSE em formato inesperado: {sorted(indice)[:12]}")

    def _lista(pai: dict, chave: str, contexto: str) -> list:
        """``pai[chave]`` como lista, ou levanta — nunca itera o que não é lista.

        Achado da revisão do Copilot em 30/08/2026: se o TSE devolvesse uma
        STRING aqui em vez de lista, ``for x in "abc"`` iteraria caractere por
        caractere, cada um falharia no ``isinstance(x, dict)`` seguinte, e a
        função devolveria eleições vazias — indistinguível de "TSE ainda não
        publicou". É o pior defeito possível neste projeto: formato quebrado
        mentindo como ausência de dado.
        """
        valor = pai.get(chave, [])
        if not isinstance(valor, list):
            raise FonteTSEError(
                f"{contexto}: campo {chave!r} deveria ser lista, veio "
                f"{type(valor).__name__}"
            )
        return valor

    eleicoes: list[EleicaoPublicada] = []
    for pleito in _lista(indice, "pl", "índice do TSE"):
        if not isinstance(pleito, dict):
            continue
        for eleicao in _lista(pleito, "e", f"pleito {pleito.get('cd')!r}"):
            if not isinstance(eleicao, dict):
                continue
            cargos: list[CargoPublicado] = []
            for abr in _lista(eleicao, "abr", f"eleição {eleicao.get('cd')!r}"):
                if not isinstance(abr, dict):
                    continue
                uf = str(abr.get("cd", "")).lower()
                for cargo in _lista(abr, "cp", f"abrangência {uf!r}"):
                    if not isinstance(cargo, dict):
                        continue
                    codigo_cargo = str(cargo.get("cd", "")).strip()
                    if not codigo_cargo.isdigit():
                        continue
                    cargos.append(
                        CargoPublicado(
                            codigo=int(codigo_cargo),
                            descricao=str(cargo.get("ds", "")),
                            abrangencia=uf,
                        )
                    )
            eleicoes.append(
                EleicaoPublicada(
                    codigo=str(eleicao.get("cd", "")),
                    # O TSE publica entidade HTML crua no nome ("1&#186; Turno").
                    nome=_sem_entidade(str(eleicao.get("nm", ""))),
                    data=str(pleito.get("dt", "")),
                    turno=str(eleicao.get("t", "")),
                    codigo_segundo_turno=str(eleicao.get("cdt2") or "") or None,
                    cargos=tuple(cargos),
                )
            )
    return str(indice.get("c", "")), tuple(eleicoes)


def _sem_entidade(texto: str) -> str:
    import html

    return html.unescape(texto)


def cargos_da_eleicao(
    codigo: str, *, transport: Transport | None = None
) -> tuple[CargoPublicado, ...]:
    """Cargos que existem numa eleição, lidos do índice — nunca chutados."""
    _, eleicoes = eleicoes_publicadas(transport=transport)
    for eleicao in eleicoes:
        if eleicao.codigo == str(codigo):
            return eleicao.cargos
    raise PleitoNaoPublicado(f"eleição {codigo!r} não está no índice do TSE")
