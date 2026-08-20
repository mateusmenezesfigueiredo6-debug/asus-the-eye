# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes da série p(t) — a trajetória, não só o valor de agora."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.markets.serie_p import SerieError, registrar_ponto, registrar_vivos, serie_do_claim

MERCADOS = {
    "mercados": [
        {
            "claim_id": "MACRO-01::2026-09",
            "market_area_id": "macroeconomia",
            "question": "IPCA de 2026-09 fica em 0,50% ou mais?",
            "deadline": "2026-09-30",
            "probability": 0.5,
            "resolution_source": "api.bcb.gov.br (SGS)",
            "created_at": "2026-08-20T00:00:00Z",
        },
        {
            "claim_id": "JUROS-01::2026-09",
            "market_area_id": "juros",
            "question": "Selic ao fim de 2026-09 em 14,00% ou mais?",
            "deadline": "2026-09-30",
            "probability": 0.62,
            "resolution_source": "api.bcb.gov.br (Selic)",
            "created_at": "2026-08-20T00:00:00Z",
        },
        {
            "claim_id": "MACRO-01::2026-07",
            "market_area_id": "macroeconomia",
            "question": "IPCA de julho?",
            "deadline": "2026-07-31",
            "probability": 0.5,
            "estado": "LIQUIDADO",
            "resolution_source": "api.bcb.gov.br (SGS)",
            "created_at": "2026-07-01T00:00:00Z",
        },
    ]
}


@pytest.fixture
def base(tmp_path: Path) -> tuple[Path, Path]:
    store = tmp_path / "registro.json"
    store.write_text(json.dumps(MERCADOS), encoding="utf-8")
    return store, tmp_path / "serie_p.jsonl"


# ------------------------------------------------------------ ponto


def test_ponto_guarda_horizonte_contra_o_deadline(base: tuple[Path, Path]) -> None:
    store, arquivo = base
    r = registrar_ponto(claim_id="MACRO-01::2026-09", observado_em="2026-08-31", store=store, arquivo=arquivo)
    assert r["registro"]["horizonte_dias"] == 30  # 31/08 → 30/09
    assert r["registro"]["probability"] == 0.5
    assert r["duplicate"] is False


def test_ponto_usa_o_p_vigente_do_registro_quando_omitido(base: tuple[Path, Path]) -> None:
    """O caso do cron: fotografar o que a plataforma acredita hoje."""
    store, arquivo = base
    r = registrar_ponto(claim_id="JUROS-01::2026-09", observado_em="2026-09-01", store=store, arquivo=arquivo)
    assert r["registro"]["probability"] == 0.62


def test_horizonte_negativo_quando_o_prazo_ja_passou(base: tuple[Path, Path]) -> None:
    """Claim vencido sem liquidar é um fato — a série registra, não esconde."""
    store, arquivo = base
    r = registrar_ponto(claim_id="MACRO-01::2026-09", observado_em="2026-10-05", store=store, arquivo=arquivo)
    assert r["registro"]["horizonte_dias"] == -5


def test_um_ponto_por_claim_por_dia(base: tuple[Path, Path]) -> None:
    """Idempotência do cron: rodar de novo no mesmo dia não duplica."""
    store, arquivo = base
    registrar_ponto(claim_id="MACRO-01::2026-09", observado_em="2026-08-31", store=store, arquivo=arquivo)
    r2 = registrar_ponto(claim_id="MACRO-01::2026-09", observado_em="2026-08-31", store=store, arquivo=arquivo)
    assert r2["duplicate"] is True
    assert len(serie_do_claim("MACRO-01::2026-09", arquivo=arquivo)) == 1


def test_p_parado_em_dias_diferentes_gera_pontos_diferentes(base: tuple[Path, Path]) -> None:
    """A regra invertida: numa série o relógio ENTRA na identidade.

    Se deduplicássemos por valor (o padrão dos outros stores), 'p ficou em 0,50
    por trinta dias' viraria um único ponto — e essa é exatamente a informação
    que a calibração por horizonte precisa enxergar.
    """
    store, arquivo = base
    registrar_ponto(claim_id="MACRO-01::2026-09", observado_em="2026-08-30", store=store, arquivo=arquivo)
    r2 = registrar_ponto(claim_id="MACRO-01::2026-09", observado_em="2026-08-31", store=store, arquivo=arquivo)
    assert r2["duplicate"] is False
    serie = serie_do_claim("MACRO-01::2026-09", arquivo=arquivo)
    assert [p["probability"] for p in serie] == [0.5, 0.5]  # mesmo valor
    assert [p["horizonte_dias"] for p in serie] == [31, 30]  # horizontes distintos


def test_claim_fantasma_levanta(base: tuple[Path, Path]) -> None:
    store, arquivo = base
    with pytest.raises(SerieError, match="não existe no registro"):
        registrar_ponto(claim_id="NAO-EXISTE::2026-09", store=store, arquivo=arquivo)


def test_probability_fora_da_faixa_levanta(base: tuple[Path, Path]) -> None:
    store, arquivo = base
    with pytest.raises(SerieError, match="fora de"):
        registrar_ponto(claim_id="MACRO-01::2026-09", probability=1.4, store=store, arquivo=arquivo)


def test_registro_ausente_levanta(tmp_path: Path) -> None:
    with pytest.raises(SerieError, match="ausente"):
        registrar_ponto(claim_id="X", store=tmp_path / "nao-existe.json", arquivo=tmp_path / "s.jsonl")


# ------------------------------------------------------------ varredura


def test_vivos_ignora_liquidado(base: tuple[Path, Path]) -> None:
    """Claim liquidado teve sua trajetória encerrada — ponto novo inventaria história."""
    store, arquivo = base
    r = registrar_vivos(observado_em="2026-08-31", store=store, arquivo=arquivo)
    ids = {p["registro"]["claim_id"] for p in r["pontos"]}
    assert ids == {"MACRO-01::2026-09", "JUROS-01::2026-09"}
    assert "MACRO-01::2026-07" not in ids
    assert r["novos"] == 2


def test_vivos_e_idempotente(base: tuple[Path, Path]) -> None:
    store, arquivo = base
    registrar_vivos(observado_em="2026-08-31", store=store, arquivo=arquivo)
    segunda = registrar_vivos(observado_em="2026-08-31", store=store, arquivo=arquivo)
    assert segunda["novos"] == 0
    assert segunda["duplicados"] == 2


def test_serie_volta_em_ordem_cronologica(base: tuple[Path, Path]) -> None:
    store, arquivo = base
    for dia in ("2026-09-02", "2026-08-30", "2026-09-01"):
        registrar_ponto(claim_id="MACRO-01::2026-09", observado_em=dia, store=store, arquivo=arquivo)
    dias = [p["observado_em"] for p in serie_do_claim("MACRO-01::2026-09", arquivo=arquivo)]
    assert dias == ["2026-08-30", "2026-09-01", "2026-09-02"]


# ------------------------------------------------------------ selagem


def test_ponto_sela_na_corrente_e_deduplica(base: tuple[Path, Path], tmp_path: Path) -> None:
    from asus_theye.markets.auditoria import abrir_auditoria, cabeca_da_corrente

    store, arquivo = base
    corrente = tmp_path / "corrente.jsonl"
    sdk = abrir_auditoria(
        tmp_path / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=corrente,
        fingerprint=tmp_path / "chave.fingerprint",
    )
    r1 = registrar_ponto(
        claim_id="MACRO-01::2026-09", observado_em="2026-08-31", store=store, arquivo=arquivo, sdk=sdk, eventos=corrente
    )
    assert r1["selagem"]["duplicate"] is False
    assert cabeca_da_corrente(sdk) == 1
    selado = json.loads(corrente.read_text(encoding="utf-8").strip())
    assert selado["event_type"] == "market.probability_point"

    # mesmo dia = dedupe também na cadeia
    r2 = registrar_ponto(
        claim_id="MACRO-01::2026-09", observado_em="2026-08-31", store=store, arquivo=arquivo, sdk=sdk, eventos=corrente
    )
    assert r2["selagem"]["duplicate"] is True
    assert cabeca_da_corrente(sdk) == 1

    # dia novo = evento novo
    r3 = registrar_ponto(
        claim_id="MACRO-01::2026-09", observado_em="2026-09-01", store=store, arquivo=arquivo, sdk=sdk, eventos=corrente
    )
    assert r3["selagem"]["duplicate"] is False
    assert cabeca_da_corrente(sdk) == 2


# ------------------------------------------------------------ re-ancoragem


def test_reancorar_mede_contra_a_determinacao_nao_contra_o_deadline(base: tuple[Path, Path]) -> None:
    """O achado central: o relógio do contrato não é o relógio do mundo.

    O deadline é 30/09. Se a fonte só publicou em 10/10, um ponto de 31/08 está
    a 40 dias do desfecho — não a 30. Calibrar contra o deadline embute viés.
    """
    from asus_theye.markets.resolution import BASE_PRIMEIRA_OBSERVACAO
    from asus_theye.markets.serie_p import reancorar

    store, arquivo = base
    registrar_ponto(claim_id="JUROS-01::2026-09", observado_em="2026-08-31", store=store, arquivo=arquivo)
    r = reancorar(
        "JUROS-01::2026-09",
        determination_date="2026-10-10",
        determination_basis=BASE_PRIMEIRA_OBSERVACAO,
        arquivo=arquivo,
    )
    ponto = r["pontos"][0]
    assert ponto["horizonte_dias"] == 30  # contra o deadline 30/09
    assert ponto["horizonte_reancorado_dias"] == 40  # contra a determinação 10/10
    assert r["confiavel"] is True


def test_reancorar_com_base_desconhecida_nao_e_confiavel(base: tuple[Path, Path]) -> None:
    """Legado: sem saber quando a fonte publicou, o horizonte é ficção."""
    from asus_theye.markets.resolution import BASE_DESCONHECIDA
    from asus_theye.markets.serie_p import reancorar

    store, arquivo = base
    registrar_ponto(claim_id="JUROS-01::2026-09", observado_em="2026-08-31", store=store, arquivo=arquivo)
    r = reancorar(
        "JUROS-01::2026-09", determination_date="2026-10-10", determination_basis=BASE_DESCONHECIDA, arquivo=arquivo
    )
    assert r["confiavel"] is False
    assert "não use" in r["metodo"]


def test_reancorar_nao_reescreve_a_serie_selada(base: tuple[Path, Path]) -> None:
    """História selada não se corrige à mão — o horizonte novo é derivado na leitura."""
    from asus_theye.markets.resolution import BASE_PRIMEIRA_OBSERVACAO
    from asus_theye.markets.serie_p import reancorar

    store, arquivo = base
    registrar_ponto(claim_id="JUROS-01::2026-09", observado_em="2026-08-31", store=store, arquivo=arquivo)
    antes = arquivo.read_text(encoding="utf-8")
    reancorar(
        "JUROS-01::2026-09",
        determination_date="2026-10-10",
        determination_basis=BASE_PRIMEIRA_OBSERVACAO,
        arquivo=arquivo,
    )
    assert arquivo.read_text(encoding="utf-8") == antes
