# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Arquivamento da cobertura noticiosa — e do direito de usá-la.

O GDELT é **alvo móvel**: a lista de fontes cresce, os arquivos de 15 minutos
são revisados, e a página de termos é editável a qualquer momento. Sem arquivo
próprio, o histórico não é reproduzível e a proveniência não é demonstrável.

Duas coisas são carimbadas a cada ingestão, e elas servem a propósitos
diferentes:

**O MD5 do arquivo original**, que o GDELT publica junto. É o que prova qual
recorte foi lido. Já é conferido no conector; aqui ele é guardado.

**O estado dos termos na data.** É o que separa este caso do episódio Chaox:
se os termos mudarem amanhã, o arquivo prova o que vigia quando baixamos.

Sobre os termos, uma decisão que vale explicar. O caminho óbvio seria alarmar
quando o ``sha256`` da página muda — e seria ruim. Página muda a cada correção
de vírgula; um alarme que toca toda semana é um alarme desligado, e o dia em
que importasse ninguém estaria olhando.

Então são **dois sinais com pesos diferentes**:

- ``termos_sha256`` é o **carimbo de prova**. Muda quando muda, e ninguém é
  acordado por isso;
- ``concessao_presente`` é o **alarme**: a frase literal que autoriza o uso
  ainda está na página? Se sumir, o direito de usar o dado é o que está em
  questão, e aí sim alguém tem de olhar hoje.

Falha ao buscar os termos **não** aborta o arquivamento. O dado continua válido
sob os termos vigentes; o que se perde é o carimbo daquele dia, e isso é
registrado como fato (``termos_conferidos: false``). Recusar o dado porque uma
página institucional caiu seria trocar um risco real por um problema inventado.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from asus_theye.markets.fonte_gdelt import CoberturaDia, CoberturaNoticiosa
from asus_theye.net.http import HttpError, Transport, get_bytes

BASE_PADRAO = Path("reports/markets")
PASTA_COBERTURA = "cobertura"
INDICE = "cobertura_gdelt.jsonl"

URL_TERMOS = "https://www.gdeltproject.org/about.html"

# A frase que CONCEDE o uso, citada literalmente da página de termos. É o
# alarme: enquanto ela estiver lá, o direito está lá. Trecho curto e verificável
# de propósito — quanto maior a citação, mais fácil quebrar por reformatação.
CONCESSAO = "unlimited and unrestricted use"


class ArquivoGDELTError(RuntimeError):
    """Arquivamento impossível. Sempre levanta — histórico não se remenda."""


@contextmanager
def _trava(base: Path) -> Iterator[None]:
    """Mesma disciplina do vintage: escrita concorrente não intercala linha."""
    import fcntl

    base.mkdir(parents=True, exist_ok=True)
    trava = base / f".{INDICE}.lock"
    with trava.open("w", encoding="utf-8") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _linhas(caminho: Path) -> list[dict[str, Any]]:
    if not caminho.exists():
        return []
    return [json.loads(li) for li in caminho.read_text(encoding="utf-8").splitlines() if li.strip()]


def estado_dos_termos(*, transport: Transport | None = None) -> dict[str, Any]:
    """O carimbo dos termos na data — e se a concessão ainda está de pé.

    Nunca levanta: indisponibilidade vira ``termos_conferidos: False`` com o
    motivo. O dado não deixa de ser válido porque uma página caiu.
    """
    conferido_em = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        resposta = get_bytes(
            URL_TERMOS, headers={"Accept": "text/html"}, timeout=60, max_bytes=4_000_000, transport=transport
        )
    except HttpError as erro:
        return {
            "termos_conferidos": False,
            "termos_url": URL_TERMOS,
            "termos_conferidos_em": conferido_em,
            "motivo": f"página de termos inalcançável: {erro}"[:200],
        }
    if resposta.status != 200:
        return {
            "termos_conferidos": False,
            "termos_url": URL_TERMOS,
            "termos_conferidos_em": conferido_em,
            "motivo": f"página de termos respondeu HTTP {resposta.status}",
        }

    texto = resposta.body.decode("utf-8", "replace")
    return {
        "termos_conferidos": True,
        "termos_url": URL_TERMOS,
        "termos_sha256": hashlib.sha256(resposta.body).hexdigest(),
        "termos_conferidos_em": conferido_em,
        "concessao_citada": CONCESSAO,
        "concessao_presente": CONCESSAO in texto,
    }


def arquivar_cobertura(
    observacao: CoberturaNoticiosa,
    *,
    base: Path = BASE_PADRAO,
    transport: Transport | None = None,
    sdk: Any = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Arquiva o recorte próprio da cobertura, com MD5 e o estado dos termos.

    Identidade = ``(arquivo, md5, país)``: o mesmo arquivo de 15 minutos para o
    mesmo país arquivado duas vezes **deduplica**. Arquivo revisado pelo GDELT
    tem MD5 novo, logo é registro novo — e os dois ficam, lado a lado, que é o
    ponto inteiro de arquivar um alvo móvel.

    Devolve também ``alarme_de_termos``: verdadeiro quando a concessão sumiu da
    página. Quem chama **precisa** propagar isso — é a única coisa aqui que
    exige olho humano no mesmo dia.
    """
    termos = estado_dos_termos(transport=transport)

    conteudo: dict[str, Any] = dict(observacao.as_dict())
    conteudo.update(termos)
    identidade = json.dumps(
        {"arquivo": observacao.arquivo, "md5": observacao.md5_do_arquivo, "pais": observacao.pais_fips},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    conteudo["cobertura_id"] = hashlib.sha256(identidade).hexdigest()

    # A concessão sumiu da página: não é "os termos mudaram", é o direito de
    # usar o dado que está em questão. Só isto acorda alguém.
    alarme = termos.get("termos_conferidos") is True and termos.get("concessao_presente") is False

    nome = f"gdelt-{observacao.pais_fips}-{observacao.arquivo.split('.')[0]}.json"
    vigente, duplicado, selagem = _gravar_registro(
        conteudo, base=base, nome_do_recorte=nome, correlation_prefixo="cobertura", sdk=sdk, eventos=eventos
    )

    return {
        "registro": vigente,
        "duplicate": duplicado,
        "selagem": selagem,
        "alarme_de_termos": alarme,
    }


def _gravar_registro(
    conteudo: dict[str, Any],
    *,
    base: Path,
    nome_do_recorte: str,
    correlation_prefixo: str,
    sdk: Any,
    eventos: Path | None,
) -> tuple[dict[str, Any], bool, Any]:
    """Dedup, selagem e escrita sob trava — comum à janela única e ao dia.

    Devolve ``(vigente, duplicado, selagem)``. Só grava quando a identidade
    ainda não existe no índice; registro existente nunca é reescrito.
    """
    with _trava(base):
        indice = base / INDICE
        existente = next((li for li in _linhas(indice) if li.get("cobertura_id") == conteudo["cobertura_id"]), None)
        vigente: dict[str, Any] = existente if existente is not None else conteudo

        selagem = None
        if sdk is not None:
            from asus_theye.markets.auditoria import EVENTOS_PADRAO, selar_registro

            selagem = selar_registro(
                sdk,
                vigente,
                tipo_evento="market.news_coverage",
                recurso="cobertura",
                correlation_id=f"{correlation_prefixo}:{vigente['cobertura_id'][:32]}",
                occurred_at=str(vigente.get("observado_em") or ""),
                eventos=eventos or EVENTOS_PADRAO,
            )

        if existente is None:
            pasta = base / PASTA_COBERTURA
            pasta.mkdir(parents=True, exist_ok=True)
            (pasta / nome_do_recorte).write_text(
                json.dumps(conteudo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            with indice.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(conteudo, ensure_ascii=False) + "\n")

    return vigente, existente is not None, selagem


def arquivar_cobertura_do_dia(
    observacao: CoberturaDia,
    *,
    base: Path = BASE_PADRAO,
    transport: Transport | None = None,
    sdk: Any = None,
    eventos: Path | None = None,
) -> dict[str, Any]:
    """Arquiva o agregado DIÁRIO da cobertura — o conserto de 2026-09-02.

    Identidade = ``(dia, país, regime "dia-utc")``: o mesmo dia UTC para o
    mesmo país arquivado duas vezes **deduplica**. Não há MD5 aqui porque não
    há UM arquivo: o registro é a soma de até 96 janelas, e é o ``metodo``
    que declara de quantas.

    **Imutabilidade — e como os regimes convivem no mesmo índice.** As linhas
    antigas de janela única (uma por arquivo de 15 minutos) **não** são
    reescritas nem apagadas: histórico não se remenda. Elas ficam rotuladas
    pelo que já carregam — o ``metodo`` de janela única e a AUSÊNCIA do
    ``metodo`` novo ("agregado de N janelas de 15min do dia UTC...") e do
    campo ``dia``. Quem lê o índice separa os regimes por esses campos; nada
    é migrado retroativamente.

    Devolve também ``alarme_de_termos`` — mesma regra da janela única: quem
    chama **precisa** propagar.
    """
    termos = estado_dos_termos(transport=transport)

    conteudo: dict[str, Any] = dict(observacao.as_dict())
    conteudo.update(termos)
    identidade = json.dumps(
        {"dia": observacao.dia, "pais": observacao.pais_fips, "regime": "dia-utc"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    conteudo["cobertura_id"] = hashlib.sha256(identidade).hexdigest()

    alarme = termos.get("termos_conferidos") is True and termos.get("concessao_presente") is False

    nome = f"gdelt-dia-{observacao.pais_fips}-{observacao.dia}.json"
    vigente, duplicado, selagem = _gravar_registro(
        conteudo, base=base, nome_do_recorte=nome, correlation_prefixo="cobertura-dia", sdk=sdk, eventos=eventos
    )

    return {
        "registro": vigente,
        "duplicate": duplicado,
        "selagem": selagem,
        "alarme_de_termos": alarme,
    }
