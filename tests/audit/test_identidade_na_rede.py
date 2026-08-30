# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Nenhum dado pessoal do titular sai desta casa dentro de uma chamada de rede.

Este teste nasceu de um incidente real, em 30/08/2026, e existe para que ele não
se repita.

O QUE ACONTECEU. Duas coisas, de tamanhos diferentes:

  1. O conector acadêmico mandava o **e-mail pessoal do titular** no cabeçalho
     ``User-Agent`` de toda chamada — Crossref, arXiv, ROR. Estava assim havia
     tempo. A intenção era legítima (Crossref dá fila prioritária a quem se
     identifica), mas o efeito era o endereço pessoal registrado no log de cada
     serviço, e versionado no repositório.

  2. Num teste de conector novo, o assistente montou à mão um ``User-Agent``
     com o nome do produto e o usuário de GitHub do titular, e fez cerca de 8
     chamadas à Wikimedia com ele — enquanto a ordem vigente era sigilo até a
     publicação. O que vazou não foi dado: foi **intenção**, a associação entre
     o projeto e pesquisa eleitoral, num terceiro.

POR QUE UM TESTE E NÃO UMA REGRA ESCRITA. O Compromisso de Sigilo e Custódia
(elo 52) já dizia que nada do titular sai daqui. A regra existia e foi violada
duas vezes assim mesmo, porque regra escrita depende de alguém lembrar dela na
hora de escrever um cabeçalho. Cláusula sem teste é promessa; teste que quebra o
build é garantia. É a diferença entre prometer sigilo e ter sigilo.

O QUE PASSA E O QUE NÃO PASSA. O nome do titular em cabeçalho **SPDX** é
autoria declarada — é justamente o que ele mandou existir em todo arquivo, e
autoria é pública por definição. O que não passa é identificador pessoal em
qualquer lugar de onde possa embarcar numa requisição: e-mail, usuário de conta,
ou o nome fora do contexto de copyright.
"""

from __future__ import annotations

import pathlib
import re

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[2] / "src"

#: E-mails do titular. Nunca devem aparecer no código, em lugar nenhum — nem em
#: comentário, porque comentário de hoje é constante de amanhã.
EMAILS = (
    "mateusmenezesfigueiredo6@gmail.com",
    "mateusmenezesfigueiredo7@gmail.com",
)

#: Usuário de conta. Identifica a pessoa tanto quanto o e-mail.
CONTAS = ("mateusmenezesfigueiredo6-debug", "mateusmenezesfigueiredo6")

#: Cabeçalhos e chaves por onde um identificador embarca numa requisição.
CAMPOS_DE_REDE = re.compile(
    r"(user[-_]?agent|from|x-contact|mailto|contact|referer)", re.IGNORECASE
)


def _fontes() -> list[pathlib.Path]:
    return [
        p
        for p in RAIZ.rglob("*.py")
        if "__pycache__" not in p.parts and ".egg-info" not in str(p)
    ]


def _linhas_relevantes(caminho: pathlib.Path):
    """Linhas do arquivo, exceto o cabeçalho SPDX de autoria."""
    for numero, linha in enumerate(caminho.read_text(encoding="utf-8").splitlines(), 1):
        if linha.lstrip().startswith("# SPDX-"):
            continue
        yield numero, linha


def test_nenhum_email_do_titular_no_codigo():
    """E-mail pessoal não aparece em lugar nenhum de ``src/``.

    Não há exceção legítima: se um serviço exigir contato, ele vem do ambiente
    em tempo de execução, nunca do arquivo versionado.
    """
    achados = [
        f"{caminho.relative_to(RAIZ)}:{numero}"
        for caminho in _fontes()
        for numero, linha in _linhas_relevantes(caminho)
        if any(email in linha for email in EMAILS)
    ]
    assert not achados, (
        "e-mail do titular encontrado no código — ele embarcaria em chamada de "
        f"rede ou ficaria versionado: {achados}"
    )


def test_nenhuma_conta_pessoal_em_campo_de_rede():
    """Usuário de conta não vai em cabeçalho que sai pela rede.

    O incidente de 30/08 foi exatamente este: ``User-Agent`` montado com o
    usuário de GitHub do titular, enviado à Wikimedia junto com a lista de
    candidatos consultados.
    """
    achados = [
        f"{caminho.relative_to(RAIZ)}:{numero}: {linha.strip()[:90]}"
        for caminho in _fontes()
        for numero, linha in _linhas_relevantes(caminho)
        if CAMPOS_DE_REDE.search(linha) and any(conta in linha for conta in CONTAS)
    ]
    assert not achados, f"conta pessoal em campo de rede: {achados}"


def test_user_agent_do_conector_academico_nao_carrega_pessoa():
    """A constante que causou o incentivo original continua limpa."""
    from asus_theye.source_graph.connectors import academico

    ua = academico.USER_AGENT
    assert "(" in ua, "a política do fetcher exige contato entre parênteses"
    for identificador in EMAILS + CONTAS:
        assert identificador not in ua, f"{identificador!r} de volta no User-Agent"


def test_contato_opcional_vem_do_ambiente_e_nao_do_arquivo(monkeypatch):
    """Quem quiser fila prioritária opta explicitamente, ciente do que envia.

    O caminho continua existindo — o Crossref realmente prioriza quem se
    identifica. O que mudou é que a escolha é feita por quem roda, na hora, e
    não fica gravada no repositório.
    """
    import importlib

    from asus_theye.source_graph.connectors import academico

    monkeypatch.setenv("ASUS_THE_EYE_CONTATO", "contato@exemplo.invalido")
    recarregado = importlib.reload(academico)
    try:
        assert "contato@exemplo.invalido" in recarregado.USER_AGENT
    finally:
        monkeypatch.delenv("ASUS_THE_EYE_CONTATO", raising=False)
        importlib.reload(academico)


@pytest.mark.parametrize("identificador", EMAILS + CONTAS)
def test_o_proprio_teste_pega_o_que_deveria(identificador):
    """Guarda contra o pior defeito possível aqui: um teste que nunca falha.

    Um teste de vazamento que não detecta nada dá a mesma saída verde de um
    sistema limpo. Este caso prova que a busca funciona antes de confiar no
    silêncio dela.
    """
    linha = f'USER_AGENT = "cliente/1.0 (+{identificador})"'
    assert CAMPOS_DE_REDE.search(linha)
    assert identificador in linha
