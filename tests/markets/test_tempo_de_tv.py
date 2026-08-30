# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tempo de TV — travando os detalhes da lei que mudam a conta.

Este módulo não implementa uma heurística: implementa o art. 47, §2º da Lei
9.504/1997. Um erro aqui não produz previsão ruim — produz previsão que contradiz
a distribuição real do horário eleitoral, que qualquer pessoa pode conferir.

Dois detalhes concentram o risco. O **teto de seis partidos** por coligação, que
existe justamente para neutralizar a manobra de juntar muitas legendas pequenas —
ignorá-lo premiaria exatamente o que a lei quis coibir. E a **fatia igualitária
de 10%**, que garante tempo a quem não tem cadeira nenhuma; suprimi-la zeraria
candidaturas que a lei protege.
"""

from __future__ import annotations

import pytest

from asus_theye.markets.tempo_de_tv import (
    MAX_PARTIDOS_NA_COLIGACAO,
    Candidatura,
    TempoDeTV,
    TempoDeTVError,
)

BANCADA = {"PL": 99, "PT": 68, "UNIAO": 59, "PP": 50, "PSD": 44, "MDB": 42,
           "PCdoB": 6, "PV": 6, "NOVO": 4, "PRTB": 1, "PCB": 0}


def casa(*candidaturas: Candidatura, **kw) -> TempoDeTV:
    return TempoDeTV(bancada=dict(BANCADA), candidaturas=list(candidaturas),
                     cadeiras_esperadas=kw.get("cadeiras", sum(BANCADA.values())))


# --------------------------------------------------------------------------
# A regra dos 90/10


def test_as_fatias_somam_um():
    t = casa(Candidatura("A", ("PL",)), Candidatura("B", ("PT",)), Candidatura("C", ("NOVO",)))
    assert sum(t.fatias().values()) == pytest.approx(1.0)


def test_quem_nao_tem_cadeira_recebe_o_naco_igualitario():
    """A lei garante 10% repartidos igualmente. Zerar seria suprimir direito."""
    t = casa(Candidatura("Grande", ("PL",)), Candidatura("Sem banca", ("PCB",)))
    f = t.fatias()
    assert f["Sem banca"] == pytest.approx(0.10 / 2)
    assert f["Sem banca"] > 0


def test_a_parte_proporcional_segue_a_bancada():
    """Dobro de cadeiras, dobro da parte proporcional — não do total."""
    t = casa(Candidatura("Dobro", ("PL",)), Candidatura("Metade", ("PP",)))
    f = t.fatias()
    igual = 0.10 / 2
    prop_a, prop_b = f["Dobro"] - igual, f["Metade"] - igual
    assert prop_a / prop_b == pytest.approx(99 / 50)


def test_federacao_soma_as_legendas_do_bloco():
    """FE Brasil (PT+PCdoB+PV) conta como bloco único."""
    sozinho = casa(Candidatura("X", ("PT",)), Candidatura("Y", ("PL",)))
    bloco = casa(Candidatura("X", ("PT", "PCdoB", "PV")), Candidatura("Y", ("PL",)))
    assert bloco.fatias()["X"] > sozinho.fatias()["X"]
    assert bloco.cadeiras_do_bloco(bloco.candidaturas[0]) == 68 + 6 + 6


# --------------------------------------------------------------------------
# O teto de seis partidos — art. 47, §2º, I, parte final


def test_coligacao_soma_apenas_os_seis_maiores():
    """O detalhe que existe para neutralizar a manobra dos partidos pequenos.

    Sem o teto, juntar dez legendas nanicas renderia tempo indevido — que é
    exatamente o que o dispositivo veio impedir.
    """
    grande = Candidatura("Coligadão", ("PL", "PT", "UNIAO", "PP", "PSD", "MDB", "NOVO", "PRTB"))
    t = casa(grande, Candidatura("Solo", ("PL",)))
    # Soma os seis maiores: 99+68+59+50+44+42. NOVO e PRTB ficam de fora.
    assert t.cadeiras_do_bloco(grande) == 99 + 68 + 59 + 50 + 44 + 42


def test_o_teto_aparece_no_relatorio_e_nos_avisos():
    grande = Candidatura("Coligadão", ("PL", "PT", "UNIAO", "PP", "PSD", "MDB", "NOVO"))
    t = casa(grande, Candidatura("Solo", ("PCB",)))
    linha = next(r for r in t.relatorio() if r["candidato"] == "Coligadão")
    assert linha["partidos_cortados_pelo_teto"] == ["NOVO"]
    assert any("teto de seis" in a for a in t.avisos())


def test_o_teto_e_seis_e_nao_um_numero_qualquer():
    """Guarda contra alguém 'arredondar' a constante da lei."""
    assert MAX_PARTIDOS_NA_COLIGACAO == 6


def test_partido_desconhecido_entra_com_zero_e_nao_levanta():
    """Legenda sem representação não é erro — é zero cadeira, e isso é correto."""
    c = Candidatura("Novo partido", ("PARTIDO_INEXISTENTE",))
    t = casa(c, Candidatura("Outro", ("PL",)))
    assert t.cadeiras_do_bloco(c) == 0


# --------------------------------------------------------------------------
# Os avisos que o número precisa carregar


def test_bancada_que_nao_fecha_513_e_sinalizada():
    """Contagem inflada por suplente é o defeito real que isto pega.

    A API da Câmara devolve 647 pessoas para 513 cadeiras. Se essa contagem
    passasse, o tempo de quem cedeu mais quadros ao Executivo — o partido do
    governo — sairia inflado.
    """
    t = TempoDeTV(bancada={"PL": 300, "PT": 300}, cadeiras_esperadas=513,
                  candidaturas=[Candidatura("A", ("PL",)), Candidatura("B", ("PT",))])
    assert any("suplentes" in a for a in t.avisos())


def test_a_extrapolacao_municipal_para_presidencial_fica_declarada():
    t = casa(Candidatura("A", ("PL",)), Candidatura("B", ("PT",)))
    assert any("MUNICIPAL" in a and "extrapolação" in a for a in t.avisos())


def test_o_sinal_mais_forte_ausente_fica_declarado():
    """Dinheiro de campanha pesa mais e está atrás do WAF do TSE.

    Omitir isso faria o tempo de TV parecer a melhor evidência disponível,
    quando é a segunda melhor.
    """
    t = casa(Candidatura("A", ("PL",)), Candidatura("B", ("PT",)))
    assert any("DINHEIRO DE CAMPANHA" in a and "403" in a for a in t.avisos())


# --------------------------------------------------------------------------
# As recusas


def test_sem_candidatura_nao_ha_o_que_repartir():
    with pytest.raises(TempoDeTVError, match="nenhuma candidatura"):
        casa().fatias()


def test_candidatura_sem_partido_e_recusada():
    with pytest.raises(TempoDeTVError, match="sem partido"):
        Candidatura("X", ())


def test_partido_repetido_no_bloco_e_recusado():
    """Repetir a sigla dobraria a bancada do bloco em silêncio."""
    with pytest.raises(TempoDeTVError, match="repetido"):
        Candidatura("X", ("PT", "PT"))


def test_candidatura_repetida_na_lista_e_recusada():
    t = casa(Candidatura("A", ("PL",)), Candidatura("A", ("PT",)))
    with pytest.raises(TempoDeTVError, match="repetida"):
        t.fatias()


def test_bancada_vazia_ou_negativa_e_recusada():
    with pytest.raises(TempoDeTVError, match="vazia"):
        TempoDeTV(bancada={})
    with pytest.raises(TempoDeTVError, match="negativa"):
        TempoDeTV(bancada={"PL": -1})


def test_bancada_que_soma_zero_e_ausencia_de_dado_nao_situacao_legitima():
    """Bancada somando zero significa que NÃO TEMOS o dado, e isso é erro.

    É diferente do caso abaixo, e a primeira versão deste teste confundia os
    dois. Sem bancada não há como repartir 90% de nada, e devolver um número
    seria inventá-lo.
    """
    with pytest.raises(TempoDeTVError, match="soma zero"):
        TempoDeTV(bancada={"PCB": 0, "PSTU": 0})


def test_candidatos_todos_sem_cadeira_repartem_igual():
    """Situação legítima: a bancada existe, mas nenhum candidato tem parte dela.

    A lei não prevê o caso porque na prática não ocorre numa eleição
    presidencial. A divisão igual é a leitura menos arbitrária, e o módulo nem
    estoura nem inventa proporção.
    """
    t = TempoDeTV(bancada=dict(BANCADA), cadeiras_esperadas=sum(BANCADA.values()),
                  candidaturas=[Candidatura("A", ("PCB",)), Candidatura("B", ("PSTU",))])
    assert t.fatias() == {"A": pytest.approx(0.5), "B": pytest.approx(0.5)}
    assert any("igualitário" in a for a in t.avisos())
