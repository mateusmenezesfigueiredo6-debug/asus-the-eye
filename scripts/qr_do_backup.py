#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""QR de custódia do backup cifrado das chaves — reprodutível, versionado, verificado.

DECISÃO DE PROJETO — hash em vez de conteúdo bruto
===================================================
O arquivo de backup (.tar.gz.gpg) pode ter vários megabytes, muito além da
capacidade máxima de um QR code (≈ 3 KB para dados binários). Por isso o QR
não embute o conteúdo: embute o **SHA-256 do arquivo cifrado** (64 caracteres
hexadecimais). O QR prova a custódia ao tornar o hash do pacote cifrado legível
por qualquer leitor de QR de prateleira, sem revelar nenhum dado privado.

Quando o dono escanear o QR e digitar o SHA-256 que vê, basta rodar:
    sha256sum <arquivo.gpg>
e comparar. Se divergir, o backup foi adulterado ou o QR é de outro arquivo.

BIBLIOTECAS
===========
- segno 1.6+   MIT   https://github.com/heuer/segno
- zxing-cpp    Apache-2.0   https://github.com/zxing-cpp/zxing-cpp
- Pillow       HPND (permissive)   https://github.com/python-pillow/Pillow

Registradas em reports/provenance/segno-zxingcpp.md.

USO
===
    python scripts/qr_do_backup.py <arquivo.gpg> [--saida QR.png]

SAÍDA
=====
    sha256_backup : <hex>   # hash do arquivo cifrado
    sha256_qr     : <hex>   # hash do PNG do QR gerado
    qr_salvo_em   : <path>

SEGURANÇA
=========
A chave privada NUNCA aparece neste script, nos seus logs nem nas suas
mensagens de erro. O único dado que trafega é o hash do pacote cifrado.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import sys
from pathlib import Path


def _sha256_arquivo(caminho: Path) -> str:
    """Retorna o SHA-256 hexadecimal de um arquivo, sem carregar tudo na RAM."""
    h = hashlib.sha256()
    with caminho.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _sha256_bytes(dados: bytes) -> str:
    return hashlib.sha256(dados).hexdigest()


def gerar_e_verificar(arquivo_backup: Path, saida: Path) -> dict[str, str]:
    """Gera o QR do backup, verifica byte a byte e retorna os hashes.

    Comportamento fail-closed: se a decodificação do QR gerado não reproduzir
    exatamente o SHA-256 que foi codificado, o arquivo de saída NÃO é escrito
    e o processo termina com código de saída 1.

    Parameters
    ----------
    arquivo_backup:
        Caminho do arquivo .gpg (ou qualquer pacote cifrado) cujo hash será
        codificado no QR.
    saida:
        Caminho do PNG de saída.  Só é escrito após a verificação passar.

    Returns
    -------
    dict com chaves ``sha256_backup``, ``sha256_qr`` e ``qr_salvo_em``.
    """
    try:
        import segno  # noqa: PLC0415
        import zxingcpp  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415
    except ImportError as exc:
        print(
            f"ERRO: biblioteca de QR ausente — instale o extra [qr]: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not arquivo_backup.exists():
        print(f"ERRO: arquivo não encontrado: {arquivo_backup}", file=sys.stderr)
        sys.exit(1)

    hash_backup = _sha256_arquivo(arquivo_backup)

    # Gera QR em memória (PNG bruto em bytes)
    qr = segno.make(hash_backup, error="H")
    png_bytes_io = io.BytesIO()
    qr.save(png_bytes_io, kind="png", scale=8)
    png_bytes = png_bytes_io.getvalue()

    # Verificação byte a byte — fail-closed
    img = Image.open(io.BytesIO(png_bytes))
    resultados = zxingcpp.read_barcodes(img)
    if not resultados:
        print(
            "ERRO: decodificação falhou — nenhum QR encontrado na imagem gerada.",
            file=sys.stderr,
        )
        sys.exit(1)

    texto_decodificado = resultados[0].text
    if texto_decodificado != hash_backup:
        print(
            "ERRO: divergência byte a byte — o QR gerado não reproduz o hash original.\n"
            "O arquivo de saída NÃO foi escrito.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Só chega aqui se a verificação passou
    saida.write_bytes(png_bytes)
    hash_qr = _sha256_bytes(png_bytes)

    return {
        "sha256_backup": hash_backup,
        "sha256_qr": hash_qr,
        "qr_salvo_em": str(saida),
    }


def _cli() -> None:
    parser = argparse.ArgumentParser(description="Gera e verifica o QR de custódia do backup cifrado das chaves.")
    parser.add_argument("backup", type=Path, help="Arquivo .gpg do backup das chaves")
    parser.add_argument(
        "--saida",
        type=Path,
        default=None,
        help="Caminho do PNG de saída (padrão: <backup>.qr.png no mesmo diretório)",
    )
    args = parser.parse_args()

    saida: Path = args.saida or args.backup.parent / (args.backup.name + ".qr.png")
    resultado = gerar_e_verificar(args.backup, saida)

    for chave, valor in resultado.items():
        print(f"{chave} : {valor}")


if __name__ == "__main__":
    _cli()
