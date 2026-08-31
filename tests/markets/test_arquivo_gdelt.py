# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do arquivamento da cobertura — e do direito de usá-la.

O teste que importa aqui não confere um número: confere que a plataforma
percebe se a **concessão de uso sumiu** da página de termos. É a mitigação que
faltou no episódio Chaox, e ela só vale se estiver testada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from asus_theye.markets.arquivo_gdelt import (
    CONCESSAO,
    INDICE,
    arquivar_cobertura,
    estado_dos_termos,
)
from asus_theye.markets.fonte_gdelt import CoberturaNoticiosa
from asus_theye.net.http import HttpError

PAGINA_COM_CONCESSAO = f"<html><body><p>all datasets are available for {CONCESSAO} for any purpose</p></body></html>"
PAGINA_SEM_CONCESSAO = "<html><body><p>datasets are available under a new commercial license</p></body></html>"


@dataclass
class RespostaFalsa:
    status: int
    body: bytes


class TermosFalsos:
    def __init__(self, pagina: str, status: int = 200) -> None:
        self.pagina = pagina
        self.status = status

    def request(self, url: str, **_: object) -> object:
        return RespostaFalsa(self.status, self.pagina.encode("utf-8"))


class TermosCaidos:
    def request(self, url: str, **_: object) -> object:
        raise HttpError("timeout")


def _observacao(arquivo: str = "20260821130000.export.CSV.zip", md5: str = "abc123") -> CoberturaNoticiosa:
    return CoberturaNoticiosa(
        pais_fips="BR",
        eventos=12,
        tom_medio=-6.5,
        arquivo=arquivo,
        md5_do_arquivo=md5,
        observado_em="2026-08-21T13:00:00Z",
        licenca="GDELT Terms of Use",
        atribuicao="The GDELT Project (gdeltproject.org)",
    )


# ------------------------------------------------------------ os termos


def test_carimba_o_hash_e_confirma_a_concessao() -> None:
    estado = estado_dos_termos(transport=TermosFalsos(PAGINA_COM_CONCESSAO))
    assert estado["termos_conferidos"] is True
    assert estado["concessao_presente"] is True
    assert len(estado["termos_sha256"]) == 64


def test_concessao_ausente_e_detectada() -> None:
    """O sinal que acorda alguém: não é "mudou", é "o direito sumiu"."""
    estado = estado_dos_termos(transport=TermosFalsos(PAGINA_SEM_CONCESSAO))
    assert estado["termos_conferidos"] is True
    assert estado["concessao_presente"] is False


def test_pagina_fora_do_ar_nao_levanta_e_registra_o_fato() -> None:
    """Recusar o dado porque uma página institucional caiu seria trocar um
    risco real por um problema inventado."""
    estado = estado_dos_termos(transport=TermosCaidos())
    assert estado["termos_conferidos"] is False
    assert "inalcançável" in estado["motivo"]
    assert "termos_sha256" not in estado


def test_http_diferente_de_200_nao_vira_carimbo() -> None:
    estado = estado_dos_termos(transport=TermosFalsos("<html/>", status=503))
    assert estado["termos_conferidos"] is False
    assert "503" in estado["motivo"]


# ------------------------------------------------------- o arquivamento


def test_arquiva_indice_e_recorte_bruto(tmp_path: Path) -> None:
    resultado = arquivar_cobertura(_observacao(), base=tmp_path, transport=TermosFalsos(PAGINA_COM_CONCESSAO))
    assert resultado["duplicate"] is False

    linhas = [json.loads(li) for li in (tmp_path / INDICE).read_text(encoding="utf-8").splitlines()]
    assert len(linhas) == 1
    assert linhas[0]["md5_do_arquivo"] == "abc123"
    assert linhas[0]["concessao_presente"] is True
    assert (tmp_path / "cobertura" / "gdelt-BR-20260821130000.json").exists()


def test_mesmo_arquivo_deduplica(tmp_path: Path) -> None:
    for _ in range(3):
        resultado = arquivar_cobertura(_observacao(), base=tmp_path, transport=TermosFalsos(PAGINA_COM_CONCESSAO))
    assert resultado["duplicate"] is True
    assert len((tmp_path / INDICE).read_text(encoding="utf-8").splitlines()) == 1


def test_arquivo_revisado_pelo_gdelt_vira_registro_novo(tmp_path: Path) -> None:
    """Os dois ficam lado a lado — é o ponto inteiro de arquivar alvo móvel."""
    arquivar_cobertura(_observacao(md5="antes"), base=tmp_path, transport=TermosFalsos(PAGINA_COM_CONCESSAO))
    resultado = arquivar_cobertura(
        _observacao(md5="depois"), base=tmp_path, transport=TermosFalsos(PAGINA_COM_CONCESSAO)
    )
    assert resultado["duplicate"] is False
    assert len((tmp_path / INDICE).read_text(encoding="utf-8").splitlines()) == 2


def test_alarme_dispara_quando_a_concessao_some(tmp_path: Path) -> None:
    """A mitigação que faltou no episódio Chaox, e que só vale testada."""
    resultado = arquivar_cobertura(_observacao(), base=tmp_path, transport=TermosFalsos(PAGINA_SEM_CONCESSAO))
    assert resultado["alarme_de_termos"] is True


def test_termos_indisponiveis_nao_disparam_o_alarme(tmp_path: Path) -> None:
    """Alarme que toca por página fora do ar é alarme que ninguém olha."""
    resultado = arquivar_cobertura(_observacao(), base=tmp_path, transport=TermosCaidos())
    assert resultado["alarme_de_termos"] is False
    assert resultado["registro"]["termos_conferidos"] is False
