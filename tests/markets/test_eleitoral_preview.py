# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""O importador eleitoral cumpre o que o docstring do modelo cobrava.

modelo_2026, atencao_wikimedia e fonte_tse ficaram órfãos por dois dias — o
próprio módulo registrou isso. Estes testes travam o consumidor: TV-only
reproduzível do dado versionado, exclusão honesta da atenção quando um título
não verifica, e a regra de que a família de atenção é tudo-ou-nada.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from asus_theye.markets.eleitoral_preview import (
    evidencia_atencao,
    evidencia_tempo_de_tv,
    gerar_preview,
)
from asus_theye.net.http import HttpResponse

TV = {"A": 0.5, "B": 0.3, "C": 0.2}


def _tv(tmp_path: Path) -> Path:
    caminho = tmp_path / "tv.json"
    caminho.write_text(json.dumps(TV), encoding="utf-8")
    return caminho


def _artigos(tmp_path: Path, mapa: dict[str, str]) -> Path:
    caminho = tmp_path / "artigos.json"
    caminho.write_text(json.dumps(mapa), encoding="utf-8")
    return caminho


def test_preview_tv_only_e_reproduzivel_do_dado_versionado(tmp_path: Path) -> None:
    retrato = gerar_preview(
        com_atencao=False, hoje=date(2026, 9, 1), caminho_tv=_tv(tmp_path)
    )
    assert list(retrato["ordem_sem_apuracao"]) == ["A", "B", "C"]  # ordem da TV
    assert retrato["encolhimento"] == 1.0  # zero observações do ciclo
    # magnitude encolhida ao máximo = uniforme, mas a ORDEM sobrevive
    assert all(v == pytest.approx(1 / 3) for v in retrato["magnitude_encolhida"].values())
    assert retrato["componentes"][0]["fonte_do_peso"].startswith("Speck & Cervi")


def test_candidato_sem_artigo_cadastrado_exclui_a_familia_toda(tmp_path: Path) -> None:
    evidencia, motivos = evidencia_atencao(
        ("A", "B", "C"),
        hoje=date(2026, 9, 1),
        caminho_artigos=_artigos(tmp_path, {"A": "Artigo A", "B": "Artigo B"}),
    )
    assert evidencia is None
    assert any("sem título" in m and "C" in m for m in motivos)


def test_artigo_que_redireciona_exclui_com_motivo_nomeado(tmp_path: Path) -> None:
    """Trava de identidade: medir o artigo errado em silêncio é o defeito
    que verificar_artigo existe para impedir — aqui, quem não verifica sai."""

    class TransporteRedireciona:
        def request(self, url, *, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
            corpo = json.dumps(
                {
                    "query": {
                        "redirects": [{"from": "Artigo A", "to": "Outro"}],
                        "pages": {"1": {"title": "Outro", "pageid": 1}},
                    }
                }
            ).encode()
            return HttpResponse(url=url, status=200, headers={}, body=corpo)

    evidencia, motivos = evidencia_atencao(
        ("A",),
        hoje=date(2026, 9, 1),
        caminho_artigos=_artigos(tmp_path, {"A": "Artigo A"}),
        transport=TransporteRedireciona(),
    )
    assert evidencia is None
    assert any("redireciona" in m for m in motivos)


def test_preview_com_atencao_indisponivel_cai_para_tv_com_motivo(tmp_path: Path) -> None:
    class TransporteQuebrado:
        def request(self, url, *, headers, timeout, max_bytes):  # type: ignore[no-untyped-def]
            return HttpResponse(url=url, status=503, headers={}, body=b"")

    retrato = gerar_preview(
        com_atencao=True,
        hoje=date(2026, 9, 1),
        transport=TransporteQuebrado(),
        caminho_tv=_tv(tmp_path),
        caminho_artigos=_artigos(tmp_path, {"A": "AA", "B": "BB", "C": "CC"}),
    )
    assert len(retrato["componentes"]) == 1  # só TV entrou
    assert retrato["atencao_excluida_por"]  # e o porquê está escrito


def test_evidencia_tv_exige_fonte_do_peso(tmp_path: Path) -> None:
    e = evidencia_tempo_de_tv(_tv(tmp_path))
    assert e.peso == 1.0 and "Speck" in e.fonte_do_peso
