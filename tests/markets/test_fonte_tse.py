# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conector TSE — com foco nas armadilhas que o caminho feliz não pega.

O caminho feliz deste conector é quase trivial: baixar um JSON e ler um campo.
O que merece teste é o conjunto de decisões que separam "liquidou certo" de
"liquidou contra um número inventado" — arredondamento, formato numérico,
apuração parcial e escopo de cargo.

Os números do fixture não são plausíveis: são o boletim presidencial de 2022,
conferido ao vivo. Uma eleição encerrada não muda mais, então o fixture
envelhece bem.
"""

from __future__ import annotations

import json

import pytest

from asus_theye.markets.fonte_base import FonteError
from asus_theye.markets.fonte_tse import (
    FonteTSEError,
    PleitoNaoPublicado,
    abstencao,
    boletim,
    cargo_no_escopo,
    cargos_da_eleicao,
    eleicoes_publicadas,
    houve_segundo_turno,
    percentual_do_candidato,
    situacao_do_candidato,
)
from asus_theye.net.http import HttpResponse

#: Boletim real: ele2022 / 544 / presidente / 1º turno.
BOLETIM_2022 = {
    "pst": "100,00",
    "pa": "20,95",
    "t": "1",
    "vv": "118229719",
    "vb": "1964779",
    "tvn": "3487874",
    "cand": [
        {"n": "13", "nm": "LULA", "pvap": "48,43", "vap": "57259504", "st": "2º turno"},
        {"n": "22", "nm": "JAIR BOLSONARO", "pvap": "43,20", "vap": "51072345", "st": "2º turno"},
        {"n": "15", "nm": "SIMONE TEBET", "pvap": "4,16", "vap": "4915423", "st": "Não eleito"},
    ],
}

INDICE = {
    "c": "ele2024",
    "pl": [
        {
            "cd": "3237",
            "dt": "21/06/2026",
            "e": [
                {
                    "cd": "6278",
                    "cdt2": "6279",
                    "t": "1",
                    "nm": "Eleição Suplementar - Roraima 1&#186; Turno",
                    "abr": [{"cd": "rr", "cp": [{"cd": "3", "ds": "Governador"}]}],
                }
            ],
        },
        {
            "cd": "452",
            "dt": "06/10/2024",
            "e": [
                {
                    "cd": "619",
                    "cdt2": "620",
                    "t": "1",
                    "nm": "Eleição Ordinária Municipal - 2024",
                    "abr": [
                        {
                            "cd": "br",
                            "cp": [{"cd": "11", "ds": "Prefeito"}, {"cd": "13", "ds": "Vereador"}],
                        }
                    ],
                }
            ],
        },
    ],
}


class Transporte:
    """Serve o boletim, a assinatura e o índice por sufixo da URL."""

    def __init__(self, *, corpo: dict | None = None, sig: bytes | None = b"assinatura", status: int = 200) -> None:
        self.corpo = BOLETIM_2022 if corpo is None else corpo
        self.sig = sig
        self.status = status
        self.urls: list[str] = []

    def request(self, url, *, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
        self.urls.append(url)
        if url.endswith("ele-c.json"):
            return HttpResponse(url=url, status=200, headers={}, body=json.dumps(INDICE).encode())
        if url.endswith(".sig"):
            if self.sig is None:
                return HttpResponse(url=url, status=404, headers={}, body=b"")
            return HttpResponse(url=url, status=200, headers={}, body=self.sig)
        return HttpResponse(
            url=url, status=self.status, headers={}, body=json.dumps(self.corpo).encode()
        )


def pega(**mudanca: object):
    corpo = json.loads(json.dumps(BOLETIM_2022))
    corpo.update(mudanca)
    return boletim("ele2022", "544", cargo=1, transport=Transporte(corpo=corpo))


# --------------------------------------------------------------------------
# O que o boletim afirma


def test_le_o_boletim_de_2022_como_o_tse_o_publica():
    b = boletim("ele2022", "544", cargo=1, transport=Transporte())
    assert b.apuracao_encerrada
    assert b.votos_validos == 118_229_719
    assert abstencao(b) == pytest.approx(20.95)
    assert percentual_do_candidato(b, "LULA") == pytest.approx(48.43)
    assert situacao_do_candidato(b, "SIMONE TEBET") == "Não eleito"


def test_url_segue_o_padrao_conferido_ao_vivo():
    t = Transporte()
    boletim("ele2022", "544", cargo=1, transport=t)
    assert t.urls[0].endswith("/ele2022/544/dados-simplificados/br/br-c0001-e000544-r.json")


def test_nome_do_candidato_ignora_acento_e_caixa():
    b = boletim("ele2022", "544", cargo=1, transport=Transporte())
    assert percentual_do_candidato(b, "jair   bolsonaro") == pytest.approx(43.20)


def test_candidato_ausente_levanta_e_mostra_quem_existe():
    b = boletim("ele2022", "544", cargo=1, transport=Transporte())
    with pytest.raises(FonteTSEError, match="não está no boletim"):
        percentual_do_candidato(b, "FULANO DE TAL")


# --------------------------------------------------------------------------
# Apuração parcial: o silêncio é a resposta certa


def test_apuracao_parcial_nao_liquida_nada():
    """96% apurados ainda muda. Devolver o parcial seria decidir no meio do jogo."""
    b = pega(pst="96,31")
    assert not b.apuracao_encerrada
    assert abstencao(b) is None
    assert percentual_do_candidato(b, "LULA") is None
    assert houve_segundo_turno(b) is None
    assert situacao_do_candidato(b, "LULA") is None


# --------------------------------------------------------------------------
# As duas armadilhas numéricas


def test_ponto_sem_virgula_nao_vira_separador_de_milhar():
    """``'48.43'`` é quarenta e oito, não quatro mil e oitocentos.

    Se o TSE mudasse a convenção decimal, a versão ingênua devolveria 4843 sem
    levantar exceção nenhuma — um erro de cem vezes, silencioso, liquidando
    contra um número que ninguém publicou.
    """
    b = pega(pa="48.43")
    assert abstencao(b) == pytest.approx(48.43)


def test_maioria_absoluta_e_apurada_em_inteiros_nao_em_percentual_arredondado():
    """O caso que o ``pvap`` não consegue decidir.

    Candidato com 50,0004% dos válidos: o TSE publica ``'50,00'``. Comparar o
    percentual diria "não passou de 50" e abriria segundo turno numa eleição
    ganha no primeiro. A conta em votos inteiros acerta.
    """
    b = pega(
        vv="100000000",
        cand=[
            {"nm": "GANHOU NO PRIMEIRO", "pvap": "50,00", "vap": "50000400", "st": "Eleito"},
            {"nm": "PERDEU", "pvap": "50,00", "vap": "49999600", "st": "Não eleito"},
        ],
    )
    assert houve_segundo_turno(b) == 0.0


def test_empate_exato_abre_segundo_turno():
    """Metade exata não é maioria absoluta — o art. 77 pede MAIS da metade."""
    b = pega(
        vv="100000000",
        cand=[
            {"nm": "A", "pvap": "50,00", "vap": "50000000", "st": "2º turno"},
            {"nm": "B", "pvap": "50,00", "vap": "50000000", "st": "2º turno"},
        ],
    )
    assert houve_segundo_turno(b) == 1.0


def test_2022_teve_segundo_turno():
    assert houve_segundo_turno(boletim("ele2022", "544", cargo=1, transport=Transporte())) == 1.0


# --------------------------------------------------------------------------
# Assinatura: arquivada ou honestamente ausente


def test_assinatura_e_arquivada_com_o_boletim():
    import hashlib

    b = boletim("ele2022", "544", cargo=1, transport=Transporte(sig=b"assinatura"))
    assert b.assinatura_sha256 == hashlib.sha256(b"assinatura").hexdigest()


def test_sem_assinatura_o_boletim_ainda_liquida_mas_declara_a_ausencia():
    """Trocar uma prova a mais por uma indisponibilidade a mais seria pior."""
    b = boletim("ele2022", "544", cargo=1, transport=Transporte(sig=None))
    assert b.assinatura_sha256 is None
    assert percentual_do_candidato(b, "LULA") == pytest.approx(48.43)


# --------------------------------------------------------------------------
# Escopo de cargos — a decisão do titular, gravada no código


@pytest.mark.parametrize("cargo", ["Presidente", "Governador", "Senador", "Deputado Federal"])
def test_cargos_dentro_do_escopo(cargo):
    assert cargo_no_escopo(cargo)


@pytest.mark.parametrize(
    "cargo", ["Deputado Estadual", "Deputado Distrital", "Prefeito", "Vereador", "Conselheiro Tutelar"]
)
def test_cargos_abaixo_de_deputado_federal_ficam_de_fora(cargo):
    assert not cargo_no_escopo(cargo)


def test_indice_diz_quais_cargos_existem_e_quais_estao_no_escopo():
    cargos = cargos_da_eleicao("619", transport=Transporte())
    assert [(c.descricao, c.no_escopo) for c in cargos] == [
        ("Prefeito", False),
        ("Vereador", False),
    ]


def test_indice_le_o_ciclo_publicado_e_desescapa_o_nome():
    ciclo, eleicoes = eleicoes_publicadas(transport=Transporte())
    assert ciclo == "ele2024"
    assert eleicoes[0].nome == "Eleição Suplementar - Roraima 1º Turno"
    assert eleicoes[0].codigo_segundo_turno == "6279"


def test_eleicao_fora_do_indice_e_pleito_nao_publicado():
    with pytest.raises(PleitoNaoPublicado):
        cargos_da_eleicao("999999", transport=Transporte())


# --------------------------------------------------------------------------
# Falhas de transporte e de forma


def test_404_e_pleito_nao_publicado_nao_erro_de_fonte_quebrada():
    """Até a véspera do pleito, 404 é o estado NORMAL — não um alarme diário."""
    erro = Transporte(status=404)
    with pytest.raises(PleitoNaoPublicado):
        boletim("ele2026", "9999", cargo=1, transport=erro)


def test_pleito_nao_publicado_ainda_e_falha_de_fonte():
    """Quem captura ``FonteError`` no laço de resolução continua cobrindo o TSE."""
    assert issubclass(PleitoNaoPublicado, FonteError)
    assert issubclass(FonteTSEError, FonteError)


def test_boletim_sem_campo_obrigatorio_levanta():
    corpo = {k: v for k, v in BOLETIM_2022.items() if k != "vv"}
    with pytest.raises(FonteTSEError, match="sem o campo"):
        boletim("ele2022", "544", cargo=1, transport=Transporte(corpo=corpo))


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ciclo": "2022", "codigo": "544", "cargo": 1},
        {"ciclo": "ele2022", "codigo": "abc", "cargo": 1},
        {"ciclo": "ele2022", "codigo": "544", "cargo": 0},
    ],
)
def test_parametro_malformado_nao_chega_a_tocar_a_rede(kwargs):
    t = Transporte()
    with pytest.raises(FonteTSEError):
        boletim(kwargs["ciclo"], kwargs["codigo"], cargo=kwargs["cargo"], transport=t)
    assert t.urls == []


def test_linha_nao_dicionario_no_indice_nao_derruba_a_leitura():
    """Robustez de forma: lixo na lista é ignorado, não vira exceção nem valor."""

    class Sujo(Transporte):
        def request(self, url, *, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
            if url.endswith("ele-c.json"):
                sujo = {"c": "ele2024", "pl": [None, {"cd": "1", "dt": "x", "e": ["lixo"]}]}
                return HttpResponse(url=url, status=200, headers={}, body=json.dumps(sujo).encode())
            return super().request(url, headers=headers, timeout=timeout, max_bytes=max_bytes)

    ciclo, eleicoes = eleicoes_publicadas(transport=Sujo())
    assert ciclo == "ele2024"
    assert eleicoes == ()
