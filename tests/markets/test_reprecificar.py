# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da reprecificação e do laço que move p entre emissão e liquidação."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from asus_theye.markets.reprecificar import MOVIMENTO_MINIMO, ReprecificacaoError, reprecificar


@dataclass
class ProbabilidadeFalsa:
    valor: float

    def as_dict(self) -> dict:
        return {"valor": self.valor, "metodo": "fonte de teste", "sinais": []}


def _store(tmp: Path, *, p: float = 0.5, estado: str = "ABERTO") -> Path:
    caminho = tmp / "registro.json"
    caminho.write_text(
        json.dumps(
            {
                "versao": 1,
                "mercados": [
                    {
                        "claim_id": "MACRO-01::2026-09",
                        "market_area_id": "macroeconomia",
                        "mes_referencia": "2026-09",
                        "limiar": 0.5,
                        "probability": p,
                        "estado": estado,
                        "deadline": "2026-09-30",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return caminho


class _GDELTFalso:
    """Transporte que responde como o GDELT — para o arquivamento ACONTECER.

    Um transporte que só recusa provaria ausência de rede, mas não provaria
    isolamento: a cobertura falharia antes de chegar ao arquivamento, e um teste
    de "não escreve fora do store" passaria sem nunca exercitar a escrita. Este
    responde de verdade, então o arquivamento roda e o teste mede onde ele caiu.
    """

    def __init__(self) -> None:
        import hashlib
        import io
        import zipfile

        colunas = [""] * 61
        colunas[53] = "BR"  # ActionGeo_CountryCode
        colunas[34] = "-8.0"  # AvgTone
        linhas = "\n".join(["\t".join(colunas)] * 8)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as pacote:
            pacote.writestr("20260820.export.CSV", linhas)
        self.pacote = buffer.getvalue()
        self.md5 = hashlib.md5(self.pacote, usedforsecurity=False).hexdigest()

    def request(self, url: str, **_: object) -> object:
        if url.endswith("lastupdate.txt"):
            corpo = f"72948 {self.md5} http://data.gdeltproject.org/gdeltv2/20260820.export.CSV.zip\n"
            return _RespostaFalsa(200, corpo.encode("utf-8"))
        if "about.html" in url:  # a página de termos
            return _RespostaFalsa(200, b"<html>unlimited and unrestricted use</html>")
        return _RespostaFalsa(200, self.pacote)


@dataclass
class _RespostaFalsa:
    status: int
    body: bytes


class _SemRede:
    """Transporte que recusa qualquer requisição.

    Existe para PROVAR a ausência de rede, não para simulá-la: se a rodada
    tentar sair para a internet, o teste quebra com uma mensagem que diz
    exatamente o que aconteceu, em vez de passar mais devagar e gravar dados de
    verdade no repositório.
    """

    def request(self, url: str, **_: object) -> object:
        raise AssertionError(f"a rodada tentou acessar a rede: {url}")


def test_move_p_e_guarda_o_valor_anterior(tmp_path: Path) -> None:
    store = _store(tmp_path)
    r = reprecificar(
        claim_id="MACRO-01::2026-09", probabilidade=ProbabilidadeFalsa(0.8), motivo="sinal novo", store=store
    )
    assert r["reprecificado"] is True
    assert r["mudanca"]["probabilidade_anterior"] == 0.5
    assert r["mudanca"]["probabilidade_nova"] == 0.8
    mercado = json.loads(store.read_text(encoding="utf-8"))["mercados"][0]
    assert mercado["probability"] == 0.8
    assert mercado["reprecificacoes"][0]["probabilidade_anterior"] == 0.5


def test_recusa_reprecificar_claim_liquidado(tmp_path: Path) -> None:
    """A única fraude que este módulo poderia viabilizar, barrada na porta.

    Mudar a previsão depois que o mundo respondeu é fabricar acerto — e num
    ledger imutável isso seria fabricar acerto de forma permanente.
    """
    store = _store(tmp_path, estado="LIQUIDADO")
    with pytest.raises(ReprecificacaoError, match="fabricar acerto"):
        reprecificar(claim_id="MACRO-01::2026-09", probabilidade=ProbabilidadeFalsa(0.99), motivo="x" * 40, store=store)
    assert json.loads(store.read_text(encoding="utf-8"))["mercados"][0]["probability"] == 0.5


def test_movimento_minusculo_nao_vira_evento(tmp_path: Path) -> None:
    """Ruído do gerador encheria a corrente e tornaria a trajetória ilegível."""
    store = _store(tmp_path, p=0.5)
    r = reprecificar(
        claim_id="MACRO-01::2026-09",
        probabilidade=ProbabilidadeFalsa(0.5 + MOVIMENTO_MINIMO / 2),
        motivo="ruído",
        store=store,
    )
    assert r["reprecificado"] is False
    assert json.loads(store.read_text(encoding="utf-8"))["mercados"][0]["probability"] == 0.5


def test_motivo_vazio_levanta(tmp_path: Path) -> None:
    with pytest.raises(ReprecificacaoError, match="motivo"):
        reprecificar(
            claim_id="MACRO-01::2026-09", probabilidade=ProbabilidadeFalsa(0.8), motivo="  ", store=_store(tmp_path)
        )


def test_probabilidade_fora_da_faixa_levanta(tmp_path: Path) -> None:
    with pytest.raises(ReprecificacaoError, match="fora de"):
        reprecificar(
            claim_id="MACRO-01::2026-09", probabilidade=ProbabilidadeFalsa(1.4), motivo="x" * 40, store=_store(tmp_path)
        )


def test_claim_inexistente_levanta(tmp_path: Path) -> None:
    with pytest.raises(ReprecificacaoError, match="não existe"):
        reprecificar(
            claim_id="FANTASMA::2026-09", probabilidade=ProbabilidadeFalsa(0.8), motivo="x" * 40, store=_store(tmp_path)
        )


# ------------------------------------------------------------ o laço


def test_laco_ignora_liquidado_e_area_sem_gerador(tmp_path: Path) -> None:
    """Área sem gerador NÃO cai no gerador do IPCA por aproximação.

    Perguntas diferentes têm sinais diferentes; usar o sinal errado é pior do
    que ficar no prior honesto.
    """
    from asus_theye.markets.reprecificar import rodada

    store = tmp_path / "r.json"
    store.write_text(
        json.dumps(
            {
                "versao": 1,
                "mercados": [
                    {
                        "claim_id": "X::2026-07",
                        "market_area_id": "macroeconomia",
                        "mes_referencia": "2026-07",
                        "limiar": 0.5,
                        "probability": 0.5,
                        "estado": "LIQUIDADO",
                        "deadline": "2026-07-31",
                    },
                    {
                        "claim_id": "Y::2026-09",
                        "market_area_id": "area_inventada",
                        "mes_referencia": "2026-09",
                        "limiar": 1.0,
                        "probability": 0.5,
                        "estado": "ABERTO",
                        "deadline": "2026-09-30",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    r = rodada(store=store, serie=tmp_path / "s.jsonl", hoje="2026-08-20", transport=_SemRede())
    acoes = {a["claim_id"]: a["acao"] for a in r["acoes"]}
    assert "X::2026-07" not in acoes  # liquidado nem é consultado
    assert acoes["Y::2026-09"] == "sem_gerador"
    assert r["reprecificados"] == 0


def test_a_rodada_nao_escreve_fora_do_store_que_recebeu(tmp_path: Path) -> None:
    """O invariante que faltava, e que custou dados de verdade no repositório.

    Antes, `rodada()` aceitava `store` e `serie` isolados mas arquivava a
    cobertura em `reports/markets` fixo — então rodar a SUÍTE baixava do GDELT
    de verdade e gravava na evidência versionada do repositório. Um parâmetro
    que não se pode injetar é um parâmetro fixo, por mais que a assinatura
    sugira o contrário.

    Este teste fotografa o repositório antes e depois, e não uma lista de
    caminhos que alguém precise lembrar de atualizar: a única forma de ele
    continuar valendo quando a rodada ganhar um artefato novo.
    """
    import json as _json

    from asus_theye.markets.reprecificar import rodada

    raiz = Path(__file__).resolve().parents[2]
    antes = {p: p.stat().st_mtime_ns for p in (raiz / "reports").rglob("*") if p.is_file()}

    store = tmp_path / "registro.json"
    store.write_text(
        _json.dumps(
            {
                "mercados": [
                    {
                        "claim_id": "Z::2026-09",
                        "market_area_id": "macroeconomia",
                        "mes_referencia": "2026-09",
                        "limiar": 0.5,
                        "probability": 0.5,
                        "estado": "ABERTO",
                        "deadline": "2026-09-30",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    resultado = rodada(store=store, serie=tmp_path / "s.jsonl", hoje="2026-08-20", transport=_GDELTFalso())

    # o arquivamento TEM de ter acontecido — senão este teste não prova nada
    acoes = {a["acao"] for a in resultado["acoes"]}
    assert "cobertura_arquivada" in acoes or "cobertura_dedupe" in acoes, acoes
    assert (tmp_path / "cobertura_gdelt.jsonl").exists(), "o arquivo caiu fora do store recebido"

    depois = {p: p.stat().st_mtime_ns for p in (raiz / "reports").rglob("*") if p.is_file()}
    novos = sorted(str(p.relative_to(raiz)) for p in set(depois) - set(antes))
    tocados = sorted(str(p.relative_to(raiz)) for p in set(antes) & set(depois) if antes[p] != depois[p])
    assert not novos, f"a rodada criou arquivos na evidência versionada: {novos}"
    assert not tocados, f"a rodada alterou a evidência versionada: {tocados}"
