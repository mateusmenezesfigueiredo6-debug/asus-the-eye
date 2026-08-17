"""Testes da medição contínua: máquina de estados, conector BCB e append-only.

Tudo offline: o fetcher é injetado e o transporte do conector é falso.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from asus_theye.markets.fonte_bcb import FonteBCBError, ipca_mensal
from asus_theye.markets.live import (
    LiveMarketError,
    carregar_registro,
    emitir_macro,
    resolver_pendentes,
    salvar_registro,
)
from asus_theye.markets.scoring import brier_score
from asus_theye.net.http import HttpResponse

HOJE = date(2026, 8, 17)  # depois do fim de 2026-07: o mercado seed está vencido


def novo_store(tmp_path: Path) -> Path:
    store = tmp_path / "registro.json"
    registro = {"versao": 1, "mercados": []}
    emitir_macro(registro, "2026-07", agora="2026-07-25T05:54:18Z")
    salvar_registro(store, registro)
    return store


# --------------------------------------------------------------- máquina de estados


def test_liquida_mercado_vencido_com_valor_publicado(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    acoes = resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE)
    liquidacao = next(a for a in acoes if a["acao"] == "liquidado")
    assert liquidacao["outcome"] == 0  # 0.07 < 0.50
    assert liquidacao["valor_observado"] == pytest.approx(0.07)
    assert liquidacao["brier_do_contrato"] == pytest.approx(0.25)  # (0.5 - 0)^2
    registro = carregar_registro(store)
    mercado = registro["mercados"][0]
    assert mercado["estado"] == "LIQUIDADO"
    # brier gravado é exatamente o do scoring do módulo
    assert mercado["brier_do_contrato"] == brier_score([(0.5, 0)])


def test_desfecho_um_quando_valor_bate_o_limiar(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    acoes = resolver_pendentes(lambda mes: 0.58, store=store, hoje=HOJE)
    liquidacao = next(a for a in acoes if a["acao"] == "liquidado")
    assert liquidacao["outcome"] == 1  # 0.58 >= 0.50


def test_fonte_sem_publicacao_vira_em_resolucao_nao_palpite(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    acoes = resolver_pendentes(lambda mes: None, store=store, hoje=HOJE)
    assert acoes[0]["acao"] == "em_resolucao"
    registro = carregar_registro(store)
    assert registro["mercados"][0]["estado"] == "EM_RESOLUCAO"
    assert len(registro["mercados"][0]["tentativas"]) == 1
    # segunda rodada, agora com valor: liquida
    acoes2 = resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE)
    assert any(a["acao"] == "liquidado" for a in acoes2)


def test_nao_liquida_antes_do_prazo_nem_consulta_a_fonte(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    chamadas: list[str] = []

    def fetcher(mes: str) -> float:
        chamadas.append(mes)
        return 0.07

    acoes = resolver_pendentes(fetcher, store=store, hoje=date(2026, 7, 15))
    assert acoes[0]["acao"] == "aguardando"
    assert chamadas == [], "antes do fim do mês a fonte nem é consultada"


def test_liquidado_e_terminal(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE, emitir_seguinte=False)
    chamadas: list[str] = []

    def fetcher(mes: str) -> float:
        chamadas.append(mes)
        return 0.99

    acoes = resolver_pendentes(fetcher, store=store, hoje=HOJE, emitir_seguinte=False)
    assert chamadas == [], "mercado LIQUIDADO nunca volta à fonte"
    assert all(a["acao"] != "liquidado" for a in acoes)
    # e a resolução gravada não mudou
    linhas = (store.with_name("resolucoes.jsonl")).read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 1


def test_resolucao_e_apendice_com_dados_completos(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE)
    linha = json.loads((store.with_name("resolucoes.jsonl")).read_text(encoding="utf-8").strip())
    assert linha["claim_id"] == "MACRO-01::2026-07"
    assert linha["outcome"] == 0
    assert linha["resolution_source"] == "api.bcb.gov.br (SGS)"  # herdada da área
    assert linha["brier_do_contrato"] == pytest.approx(0.25)


def test_liquidar_emite_o_mes_seguinte_no_limiar(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    acoes = resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE)
    emitido = next(a for a in acoes if a["acao"] == "emitido")
    assert emitido["claim_id"] == "MACRO-01::2026-08"
    registro = carregar_registro(store)
    novo = next(m for m in registro["mercados"] if m["claim_id"] == "MACRO-01::2026-08")
    assert novo["estado"] == "ABERTO"
    assert novo["probability"] == 0.5 and novo["max_uncertainty"] is True
    # idempotente: emitir de novo o mesmo mês devolve None
    assert emitir_macro(registro, "2026-08") is None


def test_virada_de_ano_no_mes_seguinte(tmp_path: Path) -> None:
    registro = {"versao": 1, "mercados": []}
    emitir_macro(registro, "2026-12", agora="2026-12-01T00:00:00Z")
    store = tmp_path / "registro.json"
    salvar_registro(store, registro)
    acoes = resolver_pendentes(lambda mes: 0.4, store=store, hoje=date(2027, 1, 20))
    emitido = next(a for a in acoes if a["acao"] == "emitido")
    assert emitido["claim_id"] == "MACRO-01::2027-01"


def test_registro_com_estado_invalido_levanta(tmp_path: Path) -> None:
    store = tmp_path / "registro.json"
    store.write_text(json.dumps({"versao": 1, "mercados": [{"claim_id": "x", "estado": "QUALQUER"}]}), encoding="utf-8")
    with pytest.raises(LiveMarketError, match="estado inválido"):
        carregar_registro(store)


# ------------------------------------------------- achados da revisão adversarial


def test_rodada_atrasada_pula_meses_ja_decididos_e_nao_explode(tmp_path: Path) -> None:
    """BLOQUEADOR corrigido: liquidar 2026-08 só em outubro emite 2026-10, nunca
    2026-09 (previsão do passado) — e jamais deixa linha órfã no ledger."""
    registro = {"versao": 1, "mercados": []}
    emitir_macro(registro, "2026-08", agora="2026-08-01T00:00:00Z")
    store = tmp_path / "registro.json"
    salvar_registro(store, registro)

    acoes = resolver_pendentes(lambda mes: 0.2, store=store, hoje=date(2026, 10, 5))
    emitido = next(a for a in acoes if a["acao"] == "emitido")
    assert emitido["claim_id"] == "MACRO-01::2026-10"  # setembro (decidido) foi pulado
    linhas = (store.with_name("resolucoes.jsonl")).read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 1
    assert carregar_registro(store)["mercados"][0]["estado"] == "LIQUIDADO"


def test_erro_de_fonte_em_um_mercado_nao_aborta_nem_duplica_os_outros(tmp_path: Path) -> None:
    from asus_theye.markets.fonte_bcb import FonteBCBError

    registro = {"versao": 1, "mercados": []}
    emitir_macro(registro, "2026-06", agora="2026-06-01T00:00:00Z")
    emitir_macro(registro, "2026-07", agora="2026-07-01T00:00:00Z")
    store = tmp_path / "registro.json"
    salvar_registro(store, registro)

    def fetcher(mes: str) -> float:
        if mes == "2026-07":
            raise FonteBCBError("HTTP 500 simulado")
        return 0.16

    acoes = resolver_pendentes(fetcher, store=store, hoje=HOJE, emitir_seguinte=False)
    assert [a["acao"] for a in acoes] == ["liquidado", "erro"]
    # estado persistido: 06 LIQUIDADO no disco, 07 segue ABERTO
    registro2 = carregar_registro(store)
    estados = {m["claim_id"]: m["estado"] for m in registro2["mercados"]}
    assert estados["MACRO-01::2026-06"] == "LIQUIDADO"
    assert estados["MACRO-01::2026-07"] == "ABERTO"
    # retry resolve o 07 e NÃO duplica a linha do 06
    acoes2 = resolver_pendentes(lambda mes: 0.9, store=store, hoje=HOJE, emitir_seguinte=False)
    assert [a["acao"] for a in acoes2] == ["liquidado"]
    linhas = (store.with_name("resolucoes.jsonl")).read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 2


def test_reparo_reconstroi_linha_perdida_do_ledger(tmp_path: Path) -> None:
    """Queda entre salvar o registro e apendar o ledger: o reparo reconstrói."""
    store = novo_store(tmp_path)
    resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE, emitir_seguinte=False)
    jsonl = store.with_name("resolucoes.jsonl")
    jsonl.unlink()  # simula a linha perdida
    acoes = resolver_pendentes(lambda mes: 0.99, store=store, hoje=HOJE, emitir_seguinte=False)
    assert any(a["acao"] == "reparado" for a in acoes)
    linha = json.loads(jsonl.read_text(encoding="utf-8").strip())
    assert linha["claim_id"] == "MACRO-01::2026-07"
    assert linha["valor_observado"] == pytest.approx(0.07)  # dado original, não o 0.99


def test_apendice_e_idempotente_por_claim_id(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE, emitir_seguinte=False)
    from asus_theye.markets.live import _apendar_resolucao, _linha_de_resolucao

    mercado = carregar_registro(store)["mercados"][0]
    assert _apendar_resolucao(store, _linha_de_resolucao(mercado)) is False
    linhas = (store.with_name("resolucoes.jsonl")).read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 1


def test_resolvedor_recusa_area_ou_serie_errada(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    registro = carregar_registro(store)
    registro["mercados"][0]["serie_sgs"] = 999
    salvar_registro(store, registro)
    with pytest.raises(LiveMarketError, match="só liquida"):
        resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE)


def test_criterio_divergente_do_limiar_levanta(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    registro = json.loads(store.read_text(encoding="utf-8"))
    registro["mercados"][0]["limiar"] = 0.7  # texto continua dizendo 0.50%
    store.write_text(json.dumps(registro), encoding="utf-8")
    with pytest.raises(LiveMarketError, match="não bate com o limiar"):
        carregar_registro(store)


def test_mes_sem_zero_a_esquerda_levanta(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    registro = json.loads(store.read_text(encoding="utf-8"))
    registro["mercados"][0]["mes_referencia"] = "2026-7"
    store.write_text(json.dumps(registro), encoding="utf-8")
    with pytest.raises(LiveMarketError, match="aaaa-mm"):
        carregar_registro(store)


def test_linha_do_ledger_e_auditavel_sozinha(tmp_path: Path) -> None:
    store = novo_store(tmp_path)
    resolver_pendentes(lambda mes: 0.07, store=store, hoje=HOJE, emitir_seguinte=False)
    linha = json.loads((store.with_name("resolucoes.jsonl")).read_text(encoding="utf-8").strip())
    # dá para recomputar tudo só com a linha:
    assert int(linha["valor_observado"] >= linha["limiar"]) == linha["outcome"]
    assert (linha["probability"] - linha["outcome"]) ** 2 == pytest.approx(linha["brier_do_contrato"])
    assert linha["mes_referencia"] == "2026-07"
    assert linha["max_uncertainty"] is True


# --------------------------------------------------------------- conector BCB


class TransporteFalso:
    def __init__(self, status: int = 200, body: bytes = b"[]") -> None:
        self.status, self.body = status, body

    def request(self, url: str, *, headers, timeout, max_bytes) -> HttpResponse:  # type: ignore[no-untyped-def]
        return HttpResponse(url=url, status=self.status, headers={}, body=self.body)


CORPO = b'[{"data":"01/06/2026","valor":"0.16"},{"data":"01/07/2026","valor":"0.07"}]'


def test_ipca_mensal_acha_o_mes() -> None:
    assert ipca_mensal("2026-07", transport=TransporteFalso(body=CORPO)) == pytest.approx(0.07)
    assert ipca_mensal("2026-06", transport=TransporteFalso(body=CORPO)) == pytest.approx(0.16)


def test_ipca_mensal_mes_nao_publicado_e_none() -> None:
    assert ipca_mensal("2026-08", transport=TransporteFalso(body=CORPO)) is None


def test_ipca_mensal_virgula_decimal() -> None:
    corpo = b'[{"data":"01/07/2026","valor":"0,07"}]'
    assert ipca_mensal("2026-07", transport=TransporteFalso(body=corpo)) == pytest.approx(0.07)


@pytest.mark.parametrize(
    "status,body",
    [(500, b"erro"), (200, b"nao-json"), (200, b'{"nao":"lista"}'), (200, b'[{"sem":"campos"}]')],
)
def test_ipca_mensal_resposta_invalida_levanta(status: int, body: bytes) -> None:
    with pytest.raises(FonteBCBError):
        ipca_mensal("2026-07", transport=TransporteFalso(status=status, body=body))


@pytest.mark.parametrize("janela", [0, 21, 100])
def test_ipca_mensal_janela_fora_do_limite_da_api_levanta(janela: int) -> None:
    """O BCB rejeita janelas > 20 ('A quantidade máxima de valores deve ser 20')."""
    with pytest.raises(FonteBCBError, match="janela"):
        ipca_mensal("2026-07", janela=janela, transport=TransporteFalso(body=CORPO))


def test_ipca_mensal_mes_anterior_a_janela_levanta_nao_e_unknown() -> None:
    """Mês fora da janela é 'inconsultável', não 'não publicado' — senão o
    mercado antigo ficaria EM_RESOLUCAO para sempre."""
    with pytest.raises(FonteBCBError, match="não alcança"):
        ipca_mensal("2025-01", transport=TransporteFalso(body=CORPO))


def test_ipca_mensal_mes_duplicado_divergente_levanta() -> None:
    corpo = b'[{"data":"01/07/2026","valor":"0.07"},{"data":"15/07/2026","valor":"0.99"}]'
    with pytest.raises(FonteBCBError, match="divergentes"):
        ipca_mensal("2026-07", transport=TransporteFalso(body=corpo))


def test_ipca_mensal_mes_duplicado_concordante_devolve_o_valor() -> None:
    corpo = b'[{"data":"01/07/2026","valor":"0.07"},{"data":"15/07/2026","valor":"0.07"}]'
    assert ipca_mensal("2026-07", transport=TransporteFalso(body=corpo)) == pytest.approx(0.07)


def test_ipca_mensal_serie_vazia_levanta() -> None:
    with pytest.raises(FonteBCBError, match="vazia"):
        ipca_mensal("2026-07", transport=TransporteFalso(body=b"[]"))
