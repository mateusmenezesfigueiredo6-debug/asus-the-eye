# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector ANP — preço de combustível na bomba, por UF.

Os riscos específicos desta fonte, e por que cada teste existe:

1. **O nome do arquivo não segue padrão.** No mesmo índice de 2026 convivem
   ``07-dados-abertos-precos-gasolina-etanol.csv`` e
   ``02-cados-abertos-preco-gasolina-etanol.csv`` — com "cados" e "preco" no
   singular. Um conector que montasse o nome por template daria 404 silencioso
   nos meses fora do padrão, e "não publicado" viraria a resposta permanente.

2. **Vazamento de dado identificador.** O CSV traz CNPJ, razão social, rua e CEP
   de cada posto. Nada disso é preciso para liquidar preço mediano, e há teste
   provando que o conector não os devolve.

3. **Mês não publicado ≠ fonte quebrada.** A ANP publica com ~1 mês de atraso.
   Confundir os dois transformaria a espera normal em alarme, todo mês.
"""

from __future__ import annotations

import pytest

from asus_theye.markets.fonte_anp import (
    PRODUTOS,
    FonteAnpError,
    MesNaoPublicado,
    PrecoMediano,
    arquivos_do_ano,
    preco_mediano,
)
from asus_theye.markets.fonte_base import FonteError
from asus_theye.net.http import HttpResponse

CABECALHO = (
    "Regiao - Sigla;Estado - Sigla;Municipio;Revenda;CNPJ da Revenda;Nome da Rua;"
    "Numero Rua;Complemento;Bairro;Cep;Produto;Data da Coleta;Valor de Venda;"
    "Valor de Compra;Unidade de Medida;Bandeira"
)


def posto(uf: str, produto: str, valor: str, *, cnpj: str = " 12.486.809/0004-05") -> str:
    return (
        f"NE;{uf};RIO LARGO;CDA EMPREENDIMENTOS LTDA;{cnpj};RODOVIA BR 104;SN;;"
        f"MATA DO ROLO;57100-000;{produto};01/07/2026;{valor};;R$ / litro;VIBRA"
    )


CSV_PADRAO = "\n".join(
    [
        CABECALHO,
        posto("AL", "GASOLINA", "6,69"),
        posto("AL", "GASOLINA", "6,99"),
        posto("AL", "GASOLINA", "7,19"),
        posto("AL", "ETANOL", "4,50"),
        posto("BA", "GASOLINA", "5,99"),
    ]
).encode("utf-8")

#: Reproduz a inconsistência real do índice, incluindo o mês com "cados".
INDICE = """
<a href="/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsan/2026/07-dados-abertos-precos-gasolina-etanol.csv">julho</a>
<a href="/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsan/2026/02-cados-abertos-preco-gasolina-etanol.csv">fevereiro</a>
<a href="/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsan/2026/07-dados-abertos-precos-diesel-gnv.csv">diesel</a>
<a href="/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsan/2026/07-dados-abertos-precos-glp.csv">glp</a>
""".encode("utf-8")


class TransporteFalso:
    """Devolve o índice para a URL do índice e o CSV para qualquer outra."""

    def __init__(
        self,
        *,
        indice: bytes = INDICE,
        csv_body: bytes = CSV_PADRAO,
        status_csv: int = 200,
        status_indice: int = 200,
    ) -> None:
        self.indice, self.csv_body = indice, csv_body
        self.status_csv, self.status_indice = status_csv, status_indice
        self.urls: list[str] = []

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        self.urls.append(url)
        if url.endswith("serie-historica-de-precos-de-combustiveis"):
            return HttpResponse(url=url, status=self.status_indice, headers={}, body=self.indice)
        return HttpResponse(url=url, status=self.status_csv, headers={}, body=self.csv_body)


def test_calcula_a_mediana_da_uf() -> None:
    r = preco_mediano("2026-07", "AL", "GASOLINA", transport=TransporteFalso())
    assert isinstance(r, PrecoMediano)
    assert r.mediana == pytest.approx(6.99)  # mediana de 6,69 / 6,99 / 7,19
    assert r.coletas == 3
    assert (r.uf, r.produto, r.competencia) == ("AL", "GASOLINA", "2026-07")


def test_a_virgula_e_decimal() -> None:
    r = preco_mediano("2026-07", "BA", "GASOLINA", transport=TransporteFalso())
    assert r is not None and 1.0 < r.mediana < 100.0  # R$/litro, não 599


def test_nao_devolve_cnpj_razao_social_nem_endereco() -> None:
    # O CSV traz tudo isso; o agregado não pode carregar nada disso adiante.
    r = preco_mediano("2026-07", "AL", "GASOLINA", transport=TransporteFalso())
    assert r is not None
    texto = repr(r)
    for proibido in ("12.486.809", "CDA EMPREENDIMENTOS", "RODOVIA BR 104", "57100-000", "RIO LARGO"):
        assert proibido not in texto, f"vazou {proibido!r} no agregado"
    assert set(vars(r)) == {"uf", "produto", "competencia", "mediana", "coletas"}


def test_le_o_indice_em_vez_de_adivinhar_o_nome_do_arquivo() -> None:
    t = TransporteFalso()
    preco_mediano("2026-07", "AL", "GASOLINA", transport=t)
    assert any("serie-historica" in u for u in t.urls), "não consultou o índice"
    assert any("07-dados-abertos-precos-gasolina-etanol.csv" in u for u in t.urls)


def test_acha_o_mes_cujo_nome_foge_do_padrao() -> None:
    # Fevereiro está no índice como "02-cados-abertos-preco-..." (com o erro de
    # digitação da própria ANP). Template fixo daria 404; ler o índice acha.
    t = TransporteFalso()
    preco_mediano("2026-02", "AL", "GASOLINA", transport=t)
    assert any("02-cados-abertos-preco-gasolina-etanol.csv" in u for u in t.urls)


def test_escolhe_a_familia_de_arquivo_pelo_produto() -> None:
    t = TransporteFalso()
    preco_mediano("2026-07", "AL", "GASOLINA", transport=t)
    assert any("gasolina-etanol" in u for u in t.urls)
    t2 = TransporteFalso()
    preco_mediano("2026-07", "AL", "GLP", transport=t2)
    assert any("glp" in u for u in t2.urls)


def test_mes_ausente_do_indice_levanta_MesNaoPublicado_e_nao_erro_generico() -> None:
    with pytest.raises(MesNaoPublicado):
        preco_mediano("2026-08", "AL", "GASOLINA", transport=TransporteFalso())


def test_MesNaoPublicado_e_subclasse_de_FonteAnpError() -> None:
    # Quem quiser tratar tudo junto consegue; quem quiser distinguir também.
    assert issubclass(MesNaoPublicado, FonteAnpError)
    assert issubclass(FonteAnpError, FonteError)


def test_par_uf_produto_sem_coleta_e_None_e_nunca_zero() -> None:
    assert preco_mediano("2026-07", "AC", "GASOLINA", transport=TransporteFalso()) is None


@pytest.mark.parametrize("competencia", ["2026-7", "07/2026", "2026-13", ""])
def test_competencia_malformada_levanta(competencia: str) -> None:
    with pytest.raises(FonteAnpError, match="formato inesperado"):
        preco_mediano(competencia, "AL", "GASOLINA", transport=TransporteFalso())


def test_uf_invalida_levanta() -> None:
    with pytest.raises(FonteAnpError, match="não é unidade da federação"):
        preco_mediano("2026-07", "XX", "GASOLINA", transport=TransporteFalso())


def test_produto_fora_do_escopo_levanta_em_vez_de_devolver_serie_vazia() -> None:
    with pytest.raises(FonteAnpError, match="fora do escopo"):
        preco_mediano("2026-07", "AL", "QUEROSENE", transport=TransporteFalso())


@pytest.mark.parametrize("produto", sorted(PRODUTOS))
def test_todo_produto_do_escopo_e_aceito(produto: str) -> None:
    preco_mediano("2026-07", "AL", produto, transport=TransporteFalso())


def test_layout_mudado_levanta_nomeando_a_coluna() -> None:
    corpo = b"Estado;Produto;Preco\nAL;GASOLINA;6,69\n"
    with pytest.raises(FonteAnpError, match="layout mudou"):
        preco_mediano("2026-07", "AL", "GASOLINA", transport=TransporteFalso(csv_body=corpo))


def test_preco_nao_positivo_levanta() -> None:
    corpo = "\n".join([CABECALHO, posto("AL", "GASOLINA", "0")]).encode()
    with pytest.raises(FonteAnpError, match="não-positivo"):
        preco_mediano("2026-07", "AL", "GASOLINA", transport=TransporteFalso(csv_body=corpo))


def test_preco_nao_numerico_levanta() -> None:
    corpo = "\n".join([CABECALHO, posto("AL", "GASOLINA", "indisponivel")]).encode()
    with pytest.raises(FonteAnpError, match="não numérico"):
        preco_mediano("2026-07", "AL", "GASOLINA", transport=TransporteFalso(csv_body=corpo))


def test_indice_ambiguo_levanta_em_vez_de_escolher_um() -> None:
    indice = INDICE + (
        b'<a href="/x/arquivos/shpc/dsan/2026/07-outro-precos-gasolina-etanol.csv">dup</a>'
    )
    with pytest.raises(FonteAnpError, match="ambíguo"):
        preco_mediano("2026-07", "AL", "GASOLINA", transport=TransporteFalso(indice=indice))


def test_indice_sem_csv_do_ano_levanta_MesNaoPublicado() -> None:
    with pytest.raises(MesNaoPublicado, match="não lista nenhum CSV"):
        arquivos_do_ano(2099, transport=TransporteFalso())


def test_http_404_no_csv_vira_MesNaoPublicado() -> None:
    with pytest.raises(MesNaoPublicado):
        preco_mediano("2026-07", "AL", "GASOLINA", transport=TransporteFalso(status_csv=404))


def test_http_500_no_csv_levanta_erro_de_fonte() -> None:
    with pytest.raises(FonteAnpError, match="HTTP 500"):
        preco_mediano("2026-07", "AL", "GASOLINA", transport=TransporteFalso(status_csv=500))


def test_csv_em_latin1_nao_quebra() -> None:
    # A ANP já publicou arquivo fora de UTF-8; o conector cai para latin-1 em
    # vez de estourar, porque acento em nome de município não pode derrubar
    # a liquidação de um contrato de preço.
    corpo = "\n".join([CABECALHO, posto("AL", "GASOLINA", "6,69")]).encode("latin-1")
    r = preco_mediano("2026-07", "AL", "GASOLINA", transport=TransporteFalso(csv_body=corpo))
    assert r is not None and r.mediana == pytest.approx(6.69)
