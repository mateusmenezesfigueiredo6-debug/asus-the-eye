# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Testes de qr_do_backup — geração, verificação byte a byte e fail-closed.

Todos os testes rodam offline: nenhuma chamada de rede é realizada.

As bibliotecas de QR são um extra OPCIONAL (``[qr]``), então o módulo é pulado
inteiro quando elas não estão presentes — o mesmo padrão que a suíte já usa em
25 lugares para duckdb, web3, qiskit e fastapi. Sem isso, um extra opcional
viraria dependência de fato e deixaria a suíte vermelha em toda máquina que não
o instalou.

O pulo é de MÓDULO, não por teste, e isso é deliberado: com o pulo por teste, o
caso de "arquivo inexistente" continuaria rodando sem o extra e passaria
observando o ImportError em vez do erro que diz cobrir.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("segno")
pytest.importorskip("zxingcpp")
pytest.importorskip("PIL")

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

from qr_do_backup import _sha256_arquivo, _sha256_bytes, gerar_e_verificar  # noqa: E402


@pytest.fixture()
def backup_falso(tmp_path: Path) -> Path:
    """Cria um arquivo binário falso que simula um .gpg."""
    arq = tmp_path / "backup.tar.gz.gpg"
    arq.write_bytes(b"\x00\xff" * 512 + b"dados-de-teste-the-eye-2026")
    return arq


def test_sha256_arquivo_correto(backup_falso: Path) -> None:
    esperado = hashlib.sha256(backup_falso.read_bytes()).hexdigest()
    assert _sha256_arquivo(backup_falso) == esperado


def test_sha256_bytes_correto() -> None:
    dados = b"prova-de-custodia"
    assert _sha256_bytes(dados) == hashlib.sha256(dados).hexdigest()


def test_gerar_e_verificar_byte_a_byte(backup_falso: Path, tmp_path: Path) -> None:
    """Gera o QR, decodifica e verifica igualdade byte a byte — offline."""
    saida = tmp_path / "backup.qr.png"
    resultado = gerar_e_verificar(backup_falso, saida)

    # O arquivo foi escrito
    assert saida.exists()

    # Os hashes estão presentes e corretos
    hash_backup_esperado = hashlib.sha256(backup_falso.read_bytes()).hexdigest()
    assert resultado["sha256_backup"] == hash_backup_esperado
    assert resultado["sha256_qr"] == hashlib.sha256(saida.read_bytes()).hexdigest()
    assert resultado["qr_salvo_em"] == str(saida)

    # A imagem decodifica exatamente o hash do backup
    import zxingcpp  # noqa: PLC0415
    from PIL import Image  # noqa: PLC0415

    img = Image.open(saida)
    resultados = zxingcpp.read_barcodes(img)
    assert len(resultados) == 1
    assert resultados[0].text == hash_backup_esperado


def test_fail_closed_arquivo_inexistente(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Se o arquivo não existe, sai com SystemExit(1) sem escrever saída.

    A asserção da MENSAGEM não é preciosismo. O guard de import sai com o mesmo
    código 1, então conferir só o código deixava este teste verde mesmo quando
    a checagem de existência era apagada — ele estaria observando o erro errado.
    Com a mensagem, ele passa a pegar a mutação em qualquer máquina.
    """
    saida = tmp_path / "saida.png"
    with pytest.raises(SystemExit) as exc_info:
        gerar_e_verificar(tmp_path / "nao_existe.gpg", saida)
    assert exc_info.value.code == 1
    assert "arquivo não encontrado" in capsys.readouterr().err
    assert not saida.exists()


def test_saida_nao_escrita_em_divergencia(backup_falso: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Se a decodificação divergir, o arquivo NÃO é escrito e sai com código 1."""
    saida = tmp_path / "qr.png"

    # Forja uma decodificação errada via patch de zxingcpp
    import types

    import qr_do_backup  # noqa: PLC0415, F401
    import zxingcpp  # noqa: PLC0415

    resultado_falso = types.SimpleNamespace(text="b" * 64)
    monkeypatch.setattr(zxingcpp, "read_barcodes", lambda _img: [resultado_falso])

    # O hash que o script calculará é o real, mas o decodificado é "bbb...bbb"
    with pytest.raises(SystemExit) as exc_info:
        gerar_e_verificar(backup_falso, saida)
    assert exc_info.value.code == 1
    assert not saida.exists(), "QR corrompido não deve ser gravado"
