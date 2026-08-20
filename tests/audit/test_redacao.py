# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes do expurgo com recibo — apagar sem apagar a prova de que se apagou."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.audit.redacao import MOTIVO_TERCEIRO, RedacaoError, redigir

# O checkpoint exige justificativa de verdade (>= 30 caracteres para expurgo):
# "ok" não é motivo, e a trava existe contra o reflexo, não como exame.
JUSTIFICATIVA = "termos de terceiro restringem armazenar, exibir publicamente e criar obras derivadas"

LINHAS = [
    {"observacao_id": "aaa", "preco": 0.61, "ticker": "SEGREDO-1"},
    {"observacao_id": "bbb", "preco": 0.42, "ticker": "FICA-2"},
]


@pytest.fixture
def store(tmp_path: Path) -> Path:
    caminho = tmp_path / "obs.jsonl"
    caminho.write_text("".join(json.dumps(li) + "\n" for li in LINHAS), encoding="utf-8")
    return caminho


def test_remove_so_a_linha_alvo(store: Path) -> None:
    r = redigir(
        store=store, campo_id="observacao_id", valor_id="aaa", motivo=MOTIVO_TERCEIRO, justificativa=JUSTIFICATIVA
    )
    restante = store.read_text(encoding="utf-8")
    assert "SEGREDO-1" not in restante  # o dado sumiu de verdade
    assert "FICA-2" in restante  # o vizinho não foi arrastado junto
    assert r["recibo"]["linhas_removidas"] == 1


def test_recibo_guarda_o_hash_e_nao_o_conteudo(store: Path) -> None:
    """A propriedade central: provar O QUE saiu sem manter cópia do que saiu."""
    r = redigir(
        store=store, campo_id="observacao_id", valor_id="aaa", motivo=MOTIVO_TERCEIRO, justificativa=JUSTIFICATIVA
    )
    recibo_serializado = json.dumps(r["recibo"])
    assert "SEGREDO-1" not in recibo_serializado
    assert "0.61" not in recibo_serializado
    assert len(r["recibo"]["hash_do_removido"][0]) == 64  # sha256


def test_motivo_nao_declarado_levanta(store: Path) -> None:
    with pytest.raises(RedacaoError, match="motivo"):
        redigir(store=store, campo_id="observacao_id", valor_id="aaa", motivo="sei_la", justificativa=JUSTIFICATIVA)


def test_justificativa_vazia_levanta(store: Path) -> None:
    """Expurgo sem 'por quê' é indistinguível de encobrimento."""
    with pytest.raises(RedacaoError, match="justificativa"):
        redigir(store=store, campo_id="observacao_id", valor_id="aaa", motivo=MOTIVO_TERCEIRO, justificativa="  ")


def test_justificativa_curta_demais_levanta(store: Path) -> None:
    """A trava é contra o reflexo: "ok" passa pelo teste de vazio, não pelo de conteúdo."""
    with pytest.raises(RedacaoError, match="ao menos"):
        redigir(store=store, campo_id="observacao_id", valor_id="aaa", motivo=MOTIVO_TERCEIRO, justificativa="ok")


def test_alvo_inexistente_levanta(store: Path) -> None:
    """Expurgar coisa que não existe costuma significar que se está apagando errado."""
    with pytest.raises(RedacaoError, match="nada a expurgar"):
        redigir(
            store=store, campo_id="observacao_id", valor_id="zzz", motivo=MOTIVO_TERCEIRO, justificativa=JUSTIFICATIVA
        )


def test_expurgo_sela_recibo_e_NAO_quebra_a_corrente(store: Path, tmp_path: Path) -> None:
    """O ponto de todo o desenho: o dado sai, a prova fica, o encadeamento aguenta.

    Remover o EVENTO e re-selar quebraria a âncora on-chain e faria a prova
    temporal acusar adulteração. Removendo só o conteúdo do store, os hashes
    seguem intactos e a plataforma não passa a testemunhar contra si mesma.
    """
    from asus_theye.audit.schema import verify_chain
    from asus_theye.markets.auditoria import abrir_auditoria, selar_registro

    corrente = tmp_path / "corrente.jsonl"
    sdk = abrir_auditoria(
        tmp_path / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=corrente,
        fingerprint=tmp_path / "chave.fingerprint",
    )
    # um evento anterior, para haver encadeamento de verdade a preservar
    selar_registro(
        sdk, LINHAS[0], tipo_evento="market.comparator", recurso="comparator", correlation_id="x", eventos=corrente
    )
    antes = [json.loads(li) for li in corrente.read_text(encoding="utf-8").splitlines() if li.strip()]

    r = redigir(
        store=store,
        campo_id="observacao_id",
        valor_id="aaa",
        motivo=MOTIVO_TERCEIRO,
        justificativa=JUSTIFICATIVA,
        sdk=sdk,
        eventos=corrente,
    )
    depois = [json.loads(li) for li in corrente.read_text(encoding="utf-8").splitlines() if li.strip()]

    assert r["selagem"] is not None
    assert verify_chain(depois) is True
    # DOIS eventos novos, nesta ordem: o checkpoint ANTES do efeito, o expurgo
    # depois. Falha no meio deixaria checkpoint sem efeito (inofensivo e
    # visível), nunca efeito sem checkpoint.
    assert len(depois) == len(antes) + 2  # o expurgo ADICIONA, nunca subtrai
    assert depois[0]["event_hash_sha256"] == antes[0]["event_hash_sha256"]  # evento antigo intocado
    assert depois[-2]["event_type"] == "governance.checkpoint"
    assert depois[-1]["event_type"] == "data.redaction"
    assert "SEGREDO-1" not in corrente.read_text(encoding="utf-8")  # nem na corrente


def test_o_hash_do_recibo_identifica_o_conteudo_expurgado(store: Path) -> None:
    """O recibo casa com o content_hash que o evento original selou."""
    from asus_theye.audit.schema import hash_json

    r = redigir(
        store=store, campo_id="observacao_id", valor_id="aaa", motivo=MOTIVO_TERCEIRO, justificativa=JUSTIFICATIVA
    )
    assert r["recibo"]["hash_do_removido"] == [hash_json(LINHAS[0])]
