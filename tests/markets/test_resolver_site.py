# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Resolvedor dos contratos emitidos pelos seeds do site.

O risco aqui não é errar uma conta: é **liquidar quando não devia**. Um
contrato liquidado contra estimativa, ou contra fonte que ainda não publicou,
envenena a série de acerto — que é o único ativo que o produto vende. Por isso
a maior parte destes testes verifica o que o resolvedor **se recusa** a fazer.
"""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

import pytest

from asus_theye.markets.fonte_base import FonteError
from asus_theye.markets.resolver_site import (
    AreaSemResolvedor,
    ResolucaoError,
    liquidar_vencidos,
)

COLUNAS = (
    "claim_id TEXT PRIMARY KEY, area TEXT, pergunta TEXT, criterio TEXT, limiar REAL, "
    "deadline TEXT, estado TEXT, fonte_liquidacao TEXT, serie_sgs INTEGER, criado_em TEXT, "
    "prob_atual REAL, valor_observado REAL, outcome INTEGER, brier REAL, resolvido_em TEXT"
)


def banco_com(tmp_path: Path, *linhas: tuple) -> Path:
    p = tmp_path / "h.db"
    con = sqlite3.connect(p)
    con.execute(f"CREATE TABLE mercados ({COLUNAS})")
    for claim_id, area, limiar, deadline, estado, prob in linhas:
        con.execute(
            "INSERT INTO mercados (claim_id,area,pergunta,criterio,limiar,deadline,estado,"
            "fonte_liquidacao,criado_em,prob_atual) VALUES (?,?,'p','c',?,?,?,'f','2026-01-01',?)",
            (claim_id, area, limiar, deadline, estado, prob),
        )
    con.commit()
    con.close()
    return p


class TransporteCarga:
    """CSV do ONS com um dia publicado."""

    def __init__(self, corpo: bytes | None = None) -> None:
        self.corpo = corpo if corpo is not None else (
            b"id_subsistema;nom_subsistema;din_instante;val_cargaenergiamwmed\n"
            b"SE;Sudeste;2026-09-01;50000.0\n"
        )

    def request(self, url, *, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
        from asus_theye.net.http import HttpResponse

        return HttpResponse(url=url, status=200, headers={}, body=self.corpo)


def test_liquida_SIM_quando_o_valor_passa_do_limiar(tmp_path: Path) -> None:
    b = banco_com(tmp_path, ("energia-carga-se-2026-09-01::p50", "energia-carga", 43000.0, "2026-09-05", "ABERTO", 0.6))
    liq, pend = liquidar_vencidos(b, hoje=date(2026, 9, 6), transport=TransporteCarga())
    assert len(liq) == 1 and not pend
    assert liq[0].outcome == 1
    assert liq[0].valor_observado == pytest.approx(50000.0)
    assert liq[0].brier == pytest.approx((0.6 - 1) ** 2)


def test_liquida_NAO_quando_nao_passa(tmp_path: Path) -> None:
    b = banco_com(tmp_path, ("energia-carga-se-2026-09-01::p90", "energia-carga", 60000.0, "2026-09-05", "ABERTO", 0.1))
    liq, _ = liquidar_vencidos(b, hoje=date(2026, 9, 6), transport=TransporteCarga())
    assert liq[0].outcome == 0
    assert liq[0].brier == pytest.approx(0.01)


def test_contrato_NAO_vencido_nao_e_tocado(tmp_path: Path) -> None:
    # Liquidar antes do prazo é decidir o contrato com o jogo em andamento.
    b = banco_com(tmp_path, ("energia-carga-se-2026-09-01::p50", "energia-carga", 43000.0, "2026-12-31", "ABERTO", 0.5))
    liq, pend = liquidar_vencidos(b, hoje=date(2026, 9, 6), transport=TransporteCarga())
    assert not liq and not pend


def test_fonte_que_ainda_nao_publicou_deixa_o_contrato_ABERTO(tmp_path: Path) -> None:
    # O caso mais importante: a ausência do dia no CSV NÃO é desfecho zero.
    vazio = b"id_subsistema;nom_subsistema;din_instante;val_cargaenergiamwmed\nSE;Sudeste;2026-08-01;1.0\n"
    b = banco_com(tmp_path, ("energia-carga-se-2026-09-01::p50", "energia-carga", 43000.0, "2026-09-05", "ABERTO", 0.5))
    liq, pend = liquidar_vencidos(b, hoje=date(2026, 9, 6), transport=TransporteCarga(vazio))
    assert not liq
    assert len(pend) == 1 and "não publicou" in pend[0].motivo
    con = sqlite3.connect(b)
    assert con.execute("SELECT estado FROM mercados").fetchone()[0] == "ABERTO"


def test_fonte_fora_do_ar_nao_liquida_e_nao_derruba_a_rodada(tmp_path: Path) -> None:
    class Quebrado:
        def request(self, url, *, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
            from asus_theye.net.http import HttpResponse

            return HttpResponse(url=url, status=503, headers={}, body=b"")

    b = banco_com(tmp_path, ("energia-carga-se-2026-09-01::p50", "energia-carga", 1.0, "2026-09-05", "ABERTO", 0.5))
    liq, pend = liquidar_vencidos(b, hoje=date(2026, 9, 6), transport=Quebrado())
    assert not liq and len(pend) == 1
    assert "indisponível" in pend[0].motivo


def test_area_sem_resolvedor_vira_PENDENTE_e_nao_derruba_a_rodada(tmp_path: Path) -> None:
    """O defeito que a primeira execução contra o banco real expôs.

    Dois contratos de `cambio-diario` venceram em 31/08 e a exceção subiu,
    impedindo TODOS os contratos de energia e combustível de liquidar. Área sem
    resolvedor é dívida conhecida, não falha — e dívida conhecida não pode
    derrubar a rodada dos outros.

    (Em 01/09 o câmbio GANHOU resolvedor — o exemplo aqui virou uma área
    fictícia exatamente para este teste continuar cobrindo o caso "sem
    resolvedor" para sempre, independente de qual área é a próxima da fila.)
    """
    b = banco_com(
        tmp_path,
        ("clima-chuva-sp-2026-09-01", "clima-sem-resolvedor-ainda", 5.2, "2026-09-05", "ABERTO", 0.5),
        ("energia-carga-se-2026-09-01::p50", "energia-carga", 43000.0, "2026-09-05", "ABERTO", 0.6),
    )
    liq, pend = liquidar_vencidos(b, hoje=date(2026, 9, 6), transport=TransporteCarga())
    assert len(liq) == 1, "o contrato de energia tinha de liquidar mesmo assim"
    assert len(pend) == 1 and "não tem resolvedor" in pend[0].motivo


def test_cambio_diario_liquida_contra_a_ptax_do_dia(tmp_path: Path) -> None:
    """O câmbio foi a PRIMEIRA área a vencer sem resolvedor (31/08) — agora tem.

    O fato do claim está no sufixo (`CAMBIO-D::aaaa-mm-dd`), diferente das
    outras áreas; o teste trava esse parsing e a decisão contra o limiar.
    """

    class TransportePTAX:
        def request(self, url, *, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
            from asus_theye.net.http import HttpResponse

            corpo = b'[{"data":"01/09/2026","valor":"5.1570"}]'
            return HttpResponse(url=url, status=200, headers={}, body=corpo)

    b = banco_com(tmp_path, ("CAMBIO-D::2026-09-01", "cambio-diario", 5.2005, "2026-09-01", "ABERTO", 0.5))
    liq, pend = liquidar_vencidos(b, hoje=date(2026, 9, 2), transport=TransportePTAX())
    assert not pend and len(liq) == 1
    assert liq[0].valor_observado == pytest.approx(5.157)
    assert liq[0].outcome == 0  # 5,157 não é MAIOR que 5,2005
    assert liq[0].brier == pytest.approx(0.25)


def test_cambio_diario_com_claim_fora_do_padrao_levanta(tmp_path: Path) -> None:
    b = banco_com(tmp_path, ("CAMBIO-D-sem-sufixo", "cambio-diario", 5.2, "2026-09-01", "ABERTO", 0.5))
    with pytest.raises(ResolucaoError, match="fora do padrão"):
        liquidar_vencidos(b, hoje=date(2026, 9, 2), transport=TransporteCarga())


def test_AreaSemResolvedor_e_subclasse_de_ResolucaoError(tmp_path: Path) -> None:
    # Quem quiser tratar tudo junto consegue; quem quiser distinguir também.
    assert issubclass(AreaSemResolvedor, ResolucaoError)


def test_claim_id_fora_do_padrao_levanta_em_vez_de_adivinhar(tmp_path: Path) -> None:
    b = banco_com(tmp_path, ("energia-carga-lixo", "energia-carga", 1.0, "2026-09-05", "ABERTO", 0.5))
    with pytest.raises(ResolucaoError, match="fora do padrão"):
        liquidar_vencidos(b, hoje=date(2026, 9, 6), transport=TransporteCarga())


def test_o_resolvedor_NAO_reescreve_criterio_nem_limiar(tmp_path: Path) -> None:
    # A promessa central do produto. Se um dia o resolvedor tocar nisto, o
    # banco recusa — mas o teste garante que ele nem tenta.
    b = banco_com(tmp_path, ("energia-carga-se-2026-09-01::p50", "energia-carga", 43000.0, "2026-09-05", "ABERTO", 0.6))
    con = sqlite3.connect(b)
    antes = con.execute("SELECT criterio, limiar, deadline, criado_em FROM mercados").fetchone()
    con.close()
    liquidar_vencidos(b, hoje=date(2026, 9, 6), transport=TransporteCarga())
    con = sqlite3.connect(b)
    depois = con.execute("SELECT criterio, limiar, deadline, criado_em FROM mercados").fetchone()
    assert antes == depois


def test_contrato_ja_liquidado_nao_e_reliquidado(tmp_path: Path) -> None:
    b = banco_com(tmp_path, ("energia-carga-se-2026-09-01::p50", "energia-carga", 1.0, "2026-09-05", "LIQUIDADO", 0.5))
    liq, pend = liquidar_vencidos(b, hoje=date(2026, 9, 6), transport=TransporteCarga())
    assert not liq and not pend


def test_o_sufixo_do_degrau_nao_atrapalha_a_leitura_da_fonte(tmp_path: Path) -> None:
    # A escada põe `::p10`, `::p90` etc. no claim_id; o fato é o mesmo.
    b = banco_com(
        tmp_path,
        ("energia-carga-se-2026-09-01::p10", "energia-carga", 40000.0, "2026-09-05", "ABERTO", 0.9),
        ("energia-carga-se-2026-09-01::p90", "energia-carga", 60000.0, "2026-09-05", "ABERTO", 0.1),
    )
    liq, _ = liquidar_vencidos(b, hoje=date(2026, 9, 6), transport=TransporteCarga())
    assert len(liq) == 2
    assert {x.outcome for x in liq} == {0, 1}  # o mesmo fato decide os dois lados
