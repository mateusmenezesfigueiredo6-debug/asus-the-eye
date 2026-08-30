# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Detecção de dado pessoal no que sai desta casa.

Existe para uma trava específica: o CPF do titular nunca pode aparecer em
export público, página estática ou qualquer artefato distribuível. A trava é
antiga; o que mudou foi a forma de detectar.

A PRIMEIRA VERSÃO comparava com o número literal — e por isso escrevia o CPF
dentro de um arquivo versionado, num repositório com remoto. O teste que
protegia o dado era o que o expunha.

A SEGUNDA passou a casar o FORMATO: onze dígitos. Ficou mais forte (pega
qualquer CPF, não só o do titular) mas ganhou falsos positivos, porque
sequências de onze dígitos aparecem naturalmente dentro de hashes. Um
lookbehind hexadecimal resolveu o caso de estar *dentro* de um sha256 — e não
resolveu o caso de o número estar em texto comum, que foi o que aconteceu no
elo 68 da corrente: a frase que explica a regex contém o exemplo que a regex
dispara.

ESTA VERSÃO valida o dígito verificador. CPF não é uma sequência qualquer de
onze dígitos: os dois últimos são checksum dos nove primeiros. Um trecho de
hash tem 1 chance em ~100 de passar por acaso; um CPF real passa sempre. Isso
mantém a força da versão anterior (pega qualquer CPF, inclusive um que ainda
não exista no código) e devolve a precisão que a contagem de dígitos não tinha.
"""

from __future__ import annotations

import re

#: CPF formatado, com pontuação. Ambíguo com nada — não precisa de checksum.
CPF_FORMATADO = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")

#: Onze dígitos crus, fora de contexto hexadecimal. Candidato, não veredito:
#: quem decide é :func:`cpf_valido`.
CPF_CRU = re.compile(r"(?<![0-9a-fA-F])\d{11}(?![0-9a-fA-F])")


def cpf_valido(digitos: str) -> bool:
    """Confere os dois dígitos verificadores do CPF (algoritmo da Receita).

    Sequências de dígito repetido (``00000000000``, ``11111111111``…) passam
    na aritmética do checksum mas são inválidas por convenção, e aparecem em
    dado de teste com frequência — ficam de fora.
    """
    if len(digitos) != 11 or not digitos.isdigit() or digitos == digitos[0] * 11:
        return False
    for posicao in (9, 10):
        soma = sum(int(digitos[i]) * ((posicao + 1) - i) for i in range(posicao))
        verificador = (soma * 10) % 11
        if verificador == 10:
            verificador = 0
        if verificador != int(digitos[posicao]):
            return False
    return True


def achar_cpf(texto: str) -> list[str]:
    """CPFs encontrados em ``texto`` — formatados sempre, crus só se válidos.

    Devolve a lista para quem chama poder dizer o que achou. Vazia significa
    que o texto pode sair daqui.
    """
    achados = [m.group(0) for m in CPF_FORMATADO.finditer(texto)]
    achados += [m.group(0) for m in CPF_CRU.finditer(texto) if cpf_valido(m.group(0))]
    return achados
