# SPDX-FileCopyrightText: 2026 Mateus Menezes Figueiredo
# SPDX-License-Identifier: AGPL-3.0-or-later
# Proveniência: C10 — expectativas fail-closed + frescor por fonte

## Conceito externo consultado

**Data Quality Expectations / Health Monitoring** — documentação pública de
sistemas de qualidade de dados (ex.: Great Expectations, 2016-2024;
Pandera, 2019-2024; Apache Griffin, 2017-2022; dbt test framework, 2020-2024).

Fontes consultadas em modo leitura apenas, sem extração de código:
- Documentação pública do projeto Great Expectations (greatexpectations.io)
- Documentação pública do Pandera (pandera.readthedocs.io)
- Artigos de blog sobre Data Freshness/Staleness Monitoring em pipelines
  de dados (Medium, Towards Data Science, DataCouncil.ai, 2020-2023).

## O que foi reimplementado de forma independente

Nenhuma linha de código de terceiro foi copiada.  O código escrito baseia-se
nos seguintes conceitos lidos das fontes acima:

1. **Expectativas declarativas**: cada indicador declara uma faixa plausível de
   valores.  A verificação roda *antes* de qualquer escrita (fail-closed).
   Implementação: `src/asus_theye/markets/expectativas.py` — stdlib puro.

2. **Frescor por fonte (staleness)**: cada fonte declara a periodicidade
   esperada em dias.  A diferença entre hoje e a última publicação é comparada
   ao limite declarado.  Implementação: `src/asus_theye/markets/frescor.py` —
   stdlib puro.

## Diferenças de implementação

- Sem dependências externas (Great Expectations requer >100 MB de instalação).
- Sem Pandas/NumPy: operações sobre tipos nativos Python (`float`, `date`).
- `None` sempre significa UNKNOWN — nunca zero como substituto.
- Múltiplas violações são coletadas e levantadas juntas numa única exceção.
- Frescor integrado ao `asus-theye doutor` via `reports/markets/frescor.json`.

## Decisão de design

A opção de ler `frescor.json` em vez de consultar a fonte ao vivo no
`diagnosticar` mantém o diagnóstico totalmente offline (sem rede), alinhado
com o padrão existente da plataforma.  O pipeline de ingestão é responsável
por gravar e atualizar `reports/markets/frescor.json` após cada coleta.
