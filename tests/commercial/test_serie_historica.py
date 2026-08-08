"""Testes da coleta de serie historica.

O teste central e o das fronteiras de janela: o defeito real encontrado em
revisao foi usar o dia 1 do mes seguinte como fim, o que contava esse dia em
dois meses (published_until da API e inclusivo). Nenhuma consulta de rede aqui.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apps.comercial.serie_historica import contar, meses_ate


def test_janela_termina_no_ultimo_dia_do_proprio_mes():
    """O defeito original: fim no dia 1 do mes seguinte contava o dia duas vezes."""
    janelas = meses_ate(date(2026, 8, 4), 1)
    rotulo, ini, fim = janelas[0]
    assert rotulo == "2026-07"
    assert ini == "2026-07-01"
    assert fim == "2026-07-31", "published_until e inclusivo: nao pode invadir agosto"


def test_janelas_nao_se_sobrepoem():
    janelas = meses_ate(date(2026, 8, 4), 6)
    for anterior, seguinte in zip(janelas, janelas[1:], strict=False):
        assert anterior[2] < seguinte[1], f"{anterior[2]} invade {seguinte[1]}"


def test_janelas_sao_contiguas_sem_buraco():
    janelas = meses_ate(date(2026, 8, 4), 6)
    for anterior, seguinte in zip(janelas, janelas[1:], strict=False):
        fim = date.fromisoformat(anterior[2])
        inicio = date.fromisoformat(seguinte[1])
        assert (inicio - fim).days == 1, "faltou um dia entre as janelas"


def test_virada_de_ano():
    janelas = meses_ate(date(2026, 1, 15), 2)
    assert [j[0] for j in janelas] == ["2025-11", "2025-12"]
    assert janelas[1][1:] == ("2025-12-01", "2025-12-31")


def test_fevereiro_bissexto():
    janelas = meses_ate(date(2024, 3, 10), 1)
    assert janelas[0] == ("2024-02", "2024-02-01", "2024-02-29")


def test_fevereiro_nao_bissexto():
    janelas = meses_ate(date(2026, 3, 10), 1)
    assert janelas[0] == ("2026-02", "2026-02-01", "2026-02-28")


def test_ordem_cronologica_crescente():
    janelas = meses_ate(date(2026, 8, 4), 12)
    assert [j[0] for j in janelas] == sorted(j[0] for j in janelas)
    assert len(janelas) == 12


def test_mes_corrente_nunca_entra():
    """Mes em curso esta incompleto: incluir distorceria a serie."""
    janelas = meses_ate(date(2026, 8, 20), 3)
    assert "2026-08" not in [j[0] for j in janelas]


def test_contar_devolve_none_sem_estourar(monkeypatch):
    """Fonte fora do ar vira None registrado, nunca zero silencioso."""

    def falha(*_args, **_kwargs):
        raise OSError("rede indisponivel")

    monkeypatch.setattr("apps.comercial.serie_historica.urllib.request.urlopen", falha)
    monkeypatch.setattr("apps.comercial.serie_historica.time.sleep", lambda _s: None)
    total, url = contar("execucao fiscal", "2026-07-01", "2026-07-31", tentativas=2)
    assert total is None, "falha de rede nao pode virar 0 — zero e um valor medido"
    assert "published_until=2026-07-31" in url


def test_contar_repete_ate_conseguir(monkeypatch):
    chamadas = {"n": 0}

    class Resposta:
        def read(self):
            return b'{"total_gazettes": 42}'

    def instavel(*_args, **_kwargs):
        chamadas["n"] += 1
        if chamadas["n"] < 3:
            raise OSError("instabilidade")
        return Resposta()

    monkeypatch.setattr("apps.comercial.serie_historica.urllib.request.urlopen", instavel)
    monkeypatch.setattr("apps.comercial.serie_historica.time.sleep", lambda _s: None)
    total, _ = contar("execucao fiscal", "2026-07-01", "2026-07-31", tentativas=4)
    assert total == 42
    assert chamadas["n"] == 3


@pytest.mark.parametrize("quantos", [1, 3, 24, 36])
def test_quantidade_pedida_e_respeitada(quantos):
    assert len(meses_ate(date(2026, 8, 4), quantos)) == quantos
