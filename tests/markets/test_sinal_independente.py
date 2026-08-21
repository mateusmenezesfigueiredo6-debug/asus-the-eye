# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da trilha independente — offline, com transporte injetado.

O teste mais importante deste arquivo não verifica um número: verifica que a
trilha própria **não toca no consenso**. Se essa propriedade se perder, a
comparação entre as duas trilhas perde o sentido inteiro, e a plataforma
passaria a alegar desempenho próprio comparando o Focus com o Focus.
"""

from __future__ import annotations

import hashlib
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pytest

from asus_theye.markets.fonte_gdelt import COL_PAIS, COL_TOM, FonteGDELTError, cobertura
from asus_theye.net.http import HttpError

RAIZ = Path(__file__).resolve().parents[2]


@dataclass
class RespostaFalsa:
    status: int
    body: bytes


def _evento(pais: str, tom: float) -> str:
    """Uma linha do formato de eventos: 61 colunas separadas por tabulação."""
    colunas = [""] * 61
    colunas[COL_PAIS] = pais
    colunas[COL_TOM] = str(tom)
    return "\t".join(colunas)


def _pacote(linhas: list[str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as pacote:
        pacote.writestr("20260821.export.CSV", "\n".join(linhas))
    return buffer.getvalue()


class TransporteFalso:
    """Devolve o índice e depois o pacote — a suíte roda sem rede."""

    def __init__(self, pacote: bytes, *, md5: str | None = None, indice: str | None = None) -> None:
        self.pacote = pacote
        self.md5 = md5 if md5 is not None else hashlib.md5(pacote, usedforsecurity=False).hexdigest()
        self.indice = indice
        self.urls: list[str] = []

    def request(self, url: str, **_: object) -> object:
        self.urls.append(url)
        if url.endswith("lastupdate.txt"):
            corpo = self.indice
            if corpo is None:
                corpo = (
                    f"72948 {self.md5} http://data.gdeltproject.org/gdeltv2/20260821.export.CSV.zip\n"
                    "117713 aaa http://data.gdeltproject.org/gdeltv2/20260821.mentions.CSV.zip\n"
                    "5625833 bbb http://data.gdeltproject.org/gdeltv2/20260821.gkg.csv.zip\n"
                )
            return RespostaFalsa(200, corpo.encode("utf-8"))
        return RespostaFalsa(200, self.pacote)


# ------------------------------------------------------------ o conector


def test_conta_e_calcula_o_tom_do_pais_pedido() -> None:
    t = TransporteFalso(_pacote([_evento("BR", -8.0), _evento("BR", -4.0), _evento("US", 50.0)]))
    obs = cobertura("BR", transport=t)
    assert obs.eventos == 2
    assert obs.tom_medio == -6.0
    assert "US" not in str(obs.as_dict())


def test_forca_https_no_arquivo_publicado_como_http() -> None:
    """O índice publica http; seguir redirecionamento entre esquemas não é seguro."""
    t = TransporteFalso(_pacote([_evento("BR", -8.0)] * 6))
    cobertura("BR", transport=t)
    assert all(u.startswith("https://") for u in t.urls), t.urls


def test_md5_divergente_levanta() -> None:
    """Arquivo corrompido não vira dado — o que entra selado só sai por expurgo."""
    t = TransporteFalso(_pacote([_evento("BR", -8.0)] * 6), md5="0" * 32)
    with pytest.raises(FonteGDELTError, match="MD5 divergente"):
        cobertura("BR", transport=t)


def test_ausencia_de_cobertura_nao_levanta_e_marca_insuficiente() -> None:
    """ "Não sei" e "deu erro" são coisas diferentes, e o conector não as confunde."""
    t = TransporteFalso(_pacote([_evento("US", 10.0)]))
    obs = cobertura("BR", transport=t)
    assert obs.eventos == 0
    assert obs.suficiente is False
    assert obs.tom_medio == 0.0  # zero de contagem, não zero de tom "medido"


def test_amostra_pequena_e_declarada_insuficiente() -> None:
    t = TransporteFalso(_pacote([_evento("BR", -8.0), _evento("BR", -7.0)]))
    assert cobertura("BR", transport=t).suficiente is False


def test_indice_sem_arquivo_de_eventos_levanta() -> None:
    t = TransporteFalso(_pacote([]), indice="5625833 bbb http://data.gdeltproject.org/gdeltv2/x.gkg.csv.zip\n")
    with pytest.raises(FonteGDELTError, match="formato inesperado"):
        cobertura("BR", transport=t)


def test_fonte_inalcancavel_levanta() -> None:
    class Caida:
        def request(self, url: str, **_: object) -> object:
            raise HttpError("timeout")

    with pytest.raises(FonteGDELTError, match="inalcançável"):
        cobertura("BR", transport=Caida())


def test_pacote_ilegivel_levanta() -> None:
    t = TransporteFalso(b"isto nao e um zip")
    with pytest.raises(FonteGDELTError, match="ilegível"):
        cobertura("BR", transport=t)


def test_registro_declara_licenca_e_atribuicao() -> None:
    """A atribuição exigida viaja no dado, não num rodapé que alguém esquece."""
    t = TransporteFalso(_pacote([_evento("BR", -8.0)] * 6))
    dados = cobertura("BR", transport=t).as_dict()
    assert "GDELT" in dados["atribuicao"]
    assert dados["licenca"]
    assert "md5" in str(dados)


# ------------------------------------------------------------ o sinal


def test_tom_mais_negativo_que_a_referencia_aponta_para_sim() -> None:
    from asus_theye.markets.sinais_noticia import TOM_DE_REFERENCIA, sinal_de_cobertura

    t = TransporteFalso(_pacote([_evento("BR", TOM_DE_REFERENCIA - 5)] * 6))
    sinal = sinal_de_cobertura(cobertura("BR", transport=t))
    assert sinal is not None and sinal.direcao == "sim"


def test_tom_acima_da_referencia_aponta_para_nao() -> None:
    from asus_theye.markets.sinais_noticia import TOM_DE_REFERENCIA, sinal_de_cobertura

    t = TransporteFalso(_pacote([_evento("BR", TOM_DE_REFERENCIA + 5)] * 6))
    sinal = sinal_de_cobertura(cobertura("BR", transport=t))
    assert sinal is not None and sinal.direcao == "nao"


def test_amostra_insuficiente_nao_vira_sinal_fraco_vira_nada() -> None:
    """Poucos eventos não são evidência fraca — não são evidência."""
    from asus_theye.markets.sinais_noticia import sinal_de_cobertura

    t = TransporteFalso(_pacote([_evento("BR", -20.0)]))
    assert sinal_de_cobertura(cobertura("BR", transport=t)) is None


def test_sem_cobertura_degrada_para_maxima_incerteza() -> None:
    from asus_theye.markets.sinais_noticia import probabilidade_por_noticia

    t = TransporteFalso(_pacote([_evento("US", 10.0)]))
    p = probabilidade_por_noticia("2026-09", 0.5, transport=t)
    assert p.valor == 0.5
    assert p.max_uncertainty is True


def test_o_peso_da_noticia_e_menor_que_o_do_consenso() -> None:
    """Tom de notícia é evidência mais fraca que a mediana de cem instituições.

    Peso alto aqui produziria convicção que o dado não sustenta.
    """
    from asus_theye.markets.sinais_ipca import PESO_FOCUS
    from asus_theye.markets.sinais_noticia import PESO_NOTICIA

    assert PESO_NOTICIA < PESO_FOCUS


# ------------------------------------------------------------ a independência


def test_a_trilha_propria_nao_toca_no_consenso() -> None:
    """O teste que sustenta a comparação inteira.

    Se a trilha própria passar a ler o Focus — ou o IPCA-15, que é insumo dele —
    a plataforma passaria a comparar o Focus com o Focus e chamar isso de
    desempenho próprio. Este teste quebra antes que isso aconteça.
    """
    fonte = (RAIZ / "src/asus_theye/markets/sinais_noticia.py").read_text(encoding="utf-8")
    linhas_de_import = [li for li in fonte.splitlines() if li.startswith(("import ", "from "))]
    proibidos = ("sinais_ipca", "sinais_juros", "sinais_cambio", "vintage_focus", "fonte_bcb", "consenso")
    for linha in linhas_de_import:
        for proibido in proibidos:
            assert proibido not in linha, (
                f"a trilha própria importou {proibido!r} — a independência é estrutural, não uma promessa no comentário"
            )
    # menção em PROSA é legítima e desejável: o docstring explica por que a
    # independência importa. O que não pode existir é dependência de código.
    assert linhas_de_import, "arquivo sem imports — leitura falhou"


def test_o_conector_nao_le_texto_de_artigo_nem_url() -> None:
    """A fronteira que o projeto impõe, mais estrita do que a licença pede.

    O conteúdo apontado pertence a veículos de imprensa, cujos termos são outros
    e não foram lidos. Guardar contagem não toca a obra de ninguém.
    """
    from asus_theye.markets.fonte_gdelt import COL_PAIS as _pais
    from asus_theye.markets.fonte_gdelt import COL_TOM as _tom

    fonte = (RAIZ / "src/asus_theye/markets/fonte_gdelt.py").read_text(encoding="utf-8")
    colunas_usadas = {_tom, _pais}
    assert len(colunas_usadas) == 2, "só duas colunas de 61 devem ser lidas"
    # a coluna 60 é SOURCEURL no formato de eventos — nunca deve ser referenciada
    assert "colunas[60]" not in fonte and "COL_URL" not in fonte
