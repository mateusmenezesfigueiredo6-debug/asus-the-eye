# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Detector de CPF — a precisão importa tanto quanto a sensibilidade.

Um detector que grita demais é desligado por quem trabalha com ele; um que
grita de menos deixa o dado sair. Estes testes fixam os dois lados.

Nenhum CPF real aparece aqui: os números usados são construídos com checksum
válido só para o teste, e o próprio arquivo é a prova de que dá para testar a
trava sem escrever o dado que ela protege.
"""

from __future__ import annotations

import hashlib
import re

import pytest

from asus_theye.audit.dados_pessoais import CPF_CRU, achar_cpf, cpf_valido


def _com_checksum(base9: str) -> str:
    """Fecha um CPF sintético a partir de 9 dígitos, para gerar caso de teste."""
    digitos = base9
    for posicao in (9, 10):
        soma = sum(int(digitos[i]) * ((posicao + 1) - i) for i in range(posicao))
        dv = (soma * 10) % 11
        digitos += "0" if dv == 10 else str(dv)
    return digitos


SINTETICO = _com_checksum("123456789")


def test_cpf_sintetico_e_reconhecido() -> None:
    assert cpf_valido(SINTETICO), f"{SINTETICO} deveria ser válido por construção"
    assert achar_cpf(f"id={SINTETICO} fim") == [SINTETICO]


def test_o_numero_que_disparou_o_falso_positivo_no_elo_68() -> None:
    """45654796264 é trecho de sha256, não CPF — o checksum não fecha.

    Este é o caso concreto que motivou o módulo: a frase que explicava a regex
    continha um exemplo que a própria regex capturava.
    """
    assert not cpf_valido("45654796264")
    assert achar_cpf("sha256 produz 11 dígitos seguidos (pegou 45654796264 no HTML)") == []


def test_cpf_formatado_e_pego_sem_precisar_de_checksum() -> None:
    """Com pontuação não há ambiguidade: nada mais no mundo tem essa forma."""
    assert achar_cpf("Titular 000.111.222-33 fim") == ["000.111.222-33"]


@pytest.mark.parametrize("repetido", ["00000000000", "11111111111", "99999999999"])
def test_digito_repetido_nao_conta_como_cpf(repetido: str) -> None:
    """Passam na aritmética, mas são inválidos por convenção e comuns em teste."""
    assert not cpf_valido(repetido)


def test_hash_nao_dispara_o_detector() -> None:
    """A prova de precisão: 2000 sha256 reais, nenhum falso positivo."""
    falsos = []
    for i in range(2000):
        h = hashlib.sha256(str(i).encode()).hexdigest()
        falsos += achar_cpf(h)
    assert falsos == [], f"falso positivo em hash: {falsos[:3]}"


def test_a_regex_crua_sozinha_seria_insuficiente() -> None:
    """Documenta POR QUE o checksum é necessário, não só que ele existe.

    A regex captura o candidato; sem validar, ele viraria veredito.
    """
    texto = "pegou 45654796264 no HTML"
    assert CPF_CRU.search(texto), "a regex acha o candidato"
    assert achar_cpf(texto) == [], "mas o checksum o descarta"


def test_texto_limpo_nao_gera_achado() -> None:
    assert achar_cpf("") == []
    assert achar_cpf("nenhum dado pessoal por aqui, só prosa") == []
    assert achar_cpf("2026-08-30T12:00:00Z e 1234567890123456") == []


def test_casa_decimal_de_planilha_nao_e_cpf() -> None:
    """Achado de varredura em 698 documentos, 30/08.

    Planilha financeira guarda float como ``1234.56789012345``. A corrida de
    dígitos depois da vírgula tem o comprimento exato de um CPF, e ~1% passa no
    checksum por acaso — foram 26 falsos positivos em 6 planilhas. Detector que
    barra entrega legítima é desligado por quem trabalha com ele.
    """
    assert achar_cpf(f"valor 1234.{SINTETICO} na planilha") == []
    assert achar_cpf(f"total 0,{SINTETICO} apurado") == []


def test_mas_cpf_de_verdade_continua_sendo_pego() -> None:
    """O contrapeso do teste acima: afrouxar não pode cegar."""
    assert achar_cpf(f"CPF {SINTETICO}") == [SINTETICO]
    assert achar_cpf(f"id={SINTETICO};") == [SINTETICO]
    assert achar_cpf(f"({SINTETICO})") == [SINTETICO]
