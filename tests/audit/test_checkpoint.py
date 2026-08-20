# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes dos checkpoints — a trava que recusa ação sensível sem motivo."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from asus_theye.audit.checkpoint import ACOES_SENSIVEIS, CheckpointError, exigir, protegido, registrar

MOTIVO = "publicação autorizada pelo titular após revisão dos termos aplicáveis"


# ------------------------------------------------------------ a trava


def test_acao_fora_do_registro_levanta() -> None:
    """Acrescentar ação sensível é commit revisável, não parâmetro solto."""
    with pytest.raises(CheckpointError, match="não está no registro"):
        registrar(acao="fazer_qualquer_coisa", justificativa=MOTIVO, ator="titular")


def test_justificativa_vazia_levanta() -> None:
    with pytest.raises(CheckpointError, match="ao menos"):
        registrar(acao="publicar", justificativa="   ", ator="titular")


def test_justificativa_curta_levanta() -> None:
    """A trava é contra o reflexo: 'ok' não é motivo."""
    with pytest.raises(CheckpointError, match="ao menos 20"):
        registrar(acao="publicar", justificativa="ok", ator="titular")


def test_ator_vazio_levanta() -> None:
    """Justificativa sem autor não responsabiliza ninguém."""
    with pytest.raises(CheckpointError, match="ator"):
        registrar(acao="publicar", justificativa=MOTIVO, ator="  ")


def test_expurgo_exige_justificativa_mais_longa() -> None:
    """Remover dado é mais grave que publicar — a exigência acompanha."""
    assert ACOES_SENSIVEIS["expurgar"]["minimo_de_caracteres"] > ACOES_SENSIVEIS["publicar"]["minimo_de_caracteres"]
    with pytest.raises(CheckpointError, match="ao menos 30"):
        registrar(acao="expurgar", justificativa="motivo de vinte e cinco", ator="titular")


def test_recibo_carrega_quem_o_que_e_por_que() -> None:
    recibo = registrar(acao="ancorar", justificativa=MOTIVO, ator="titular", alvo="lote-42")["recibo"]
    assert recibo["acao"] == "ancorar"
    assert recibo["ator"] == "titular"
    assert recibo["alvo"] == "lote-42"
    assert recibo["justificativa"] == MOTIVO
    assert "irreversível" in recibo["descricao"]


# ------------------------------------------------------------ o portão


def test_corpo_nao_roda_quando_a_validacao_falha() -> None:
    """É isto que torna a trava fechada em vez de decorativa."""
    rodou = []
    with pytest.raises(CheckpointError):
        with exigir(acao="publicar", justificativa="curto", ator="titular"):
            rodou.append(True)
    assert rodou == []


def test_corpo_roda_com_justificativa_valida() -> None:
    rodou = []
    with exigir(acao="publicar", justificativa=MOTIVO, ator="titular") as recibo:
        rodou.append(recibo["recibo"]["acao"])
    assert rodou == ["publicar"]


def test_decorador_recusa_chamada_sem_justificativa() -> None:
    efeitos = []

    @protegido("espelhar")
    def enviar() -> str:
        efeitos.append("enviado")
        return "ok"

    with pytest.raises(CheckpointError):
        enviar()
    assert efeitos == []  # nenhum efeito aconteceu
    assert enviar(justificativa=MOTIVO, ator="titular") == "ok"
    assert efeitos == ["enviado"]


# ------------------------------------------------------------ selagem


def test_checkpoint_e_selado_na_corrente(tmp_path: Path) -> None:
    from asus_theye.audit.schema import verify_chain
    from asus_theye.markets.auditoria import abrir_auditoria

    corrente = tmp_path / "corrente.jsonl"
    sdk = abrir_auditoria(
        tmp_path / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=corrente,
        fingerprint=tmp_path / "chave.fingerprint",
    )
    resultado = registrar(
        acao="ancorar", justificativa=MOTIVO, ator="titular", alvo="lote-42", sdk=sdk, eventos=corrente
    )
    assert resultado["selagem"] is not None
    eventos = [json.loads(li) for li in corrente.read_text(encoding="utf-8").splitlines() if li.strip()]
    assert verify_chain(eventos) is True
    assert eventos[-1]["event_type"] == "governance.checkpoint"


def test_justificativas_diferentes_geram_eventos_diferentes(tmp_path: Path) -> None:
    """Cada decisão é um evento próprio — dois 'ancorar' não colapsam em um."""
    from asus_theye.markets.auditoria import abrir_auditoria, cabeca_da_corrente

    corrente = tmp_path / "corrente.jsonl"
    sdk = abrir_auditoria(
        tmp_path / "ledger.db",
        chave=b"chave-de-teste-32-bytes-ok!!",
        eventos=corrente,
        fingerprint=tmp_path / "chave.fingerprint",
    )
    registrar(acao="ancorar", justificativa=MOTIVO, ator="titular", sdk=sdk, eventos=corrente)
    registrar(
        acao="ancorar", justificativa=MOTIVO + " (segunda rodada do mês)", ator="titular", sdk=sdk, eventos=corrente
    )
    assert cabeca_da_corrente(sdk) == 2
