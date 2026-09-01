#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Backfill da série vintage do Focus — destrava o baseline do nowcast.

O nowcast exige VINTAGES_MINIMOS (24) meses arquivados para sair do BLOCKED;
existiam 2. Este script reconstrói, mês a mês, o consenso Focus COMO ELE ERA
no último dia de cada mês, lendo o arquivo datado do Olinda (pesquisas
imutáveis, com data de origem). Cada registro é rotulado como reconstrução
(campo ``metodo``) e selado na corrente auditável como ``market.vintage``.

Uso: .venv/bin/python scripts/backfill_vintage_focus.py [--meses N] [--ate aaaa-mm]
"""

from __future__ import annotations

import argparse
from calendar import monthrange
from datetime import date

from asus_theye.markets.auditoria import abrir_auditoria
from asus_theye.markets.vintage_focus import VintageError, reconstruir_vintage


def _meses_ate(fim: str, quantidade: int) -> list[str]:
    ano, mes = (int(p) for p in fim.split("-"))
    saida: list[str] = []
    for _ in range(quantidade):
        saida.append(f"{ano}-{mes:02d}")
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return list(reversed(saida))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meses", type=int, default=26, help="quantos meses reconstruir (padrão: 26)")
    parser.add_argument("--ate", default="2026-08", help="último mês fechado a reconstruir (aaaa-mm)")
    parser.add_argument("--no-audit", action="store_true", help="reconstrói sem selar na cadeia")
    args = parser.parse_args()

    sdk = None if args.no_audit else abrir_auditoria()
    novos = duplicados = ausentes = erros = 0
    for mes in _meses_ate(args.ate, args.meses):
        ano, numero = (int(p) for p in mes.split("-"))
        corte = date(ano, numero, monthrange(ano, numero)[1]).isoformat()
        try:
            resultado = reconstruir_vintage(mes, corte, sdk=sdk)
        except VintageError as erro:
            erros += 1
            print(f"{mes}  ERRO: {erro}")
            continue
        registro = resultado["registro"]
        if registro is None:
            ausentes += 1
            print(f"{mes}  sem pesquisa até {corte} — ausência registrada, não inventada")
        elif resultado["duplicate"]:
            duplicados += 1
            print(f"{mes}  já arquivado (boletim {registro['data_do_boletim']}, mediana {registro['mediana']})")
        else:
            novos += 1
            selo = " · selado" if resultado["selagem"] else ""
            print(f"{mes}  mediana {registro['mediana']} no corte {corte} (boletim {registro['data_do_boletim']}){selo}")
    print(f"\nnovos={novos} duplicados={duplicados} ausentes={ausentes} erros={erros}")
    return 1 if erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
