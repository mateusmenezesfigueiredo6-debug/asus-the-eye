# Benchmark Engine 0.2

## Objetivo e escopo

O Benchmark Engine fornece um protocolo reproduzível para comparar três representações
do mesmo problema: busca clássica exata, construção/resolução QUBO local e amostragem
QAOA local. Ele mede resultados; não presume que tecnologias diferentes sejam
equivalentes nem transforma uma execução isolada em alegação científica.

O dataset demo (`demo_portfolio_v1`) é um problema binário de mochila versionado no
código. A semente padrão é 42, o QAOA usa 1.024 shots e duas camadas, e a estabilidade
usa dez sementes consecutivas. Esses parâmetros ficam registrados no primeiro evento
de cada execução.

## Métricas

| Métrica | Definição | Leitura segura |
| --- | --- | --- |
| QAR | `score_qaoa / score_classical` | Sinal comparativo; não prova vantagem quântica |
| Speed ratio | `tempo_classico / tempo_qaoa` | Acima de 1 indica menor tempo medido do QAOA naquele ambiente |
| Quality gap | `score_classico - score_qaoa` | Positivo favorece o baseline clássico |
| Stability | média, desvio padrão populacional e variância em 10 rodadas | Menor dispersão indica maior repetibilidade |
| Fidelity | Probabilidade total dos estados ótimos no vetor de estado | Concentração da distribuição no ótimo conhecido |

O tempo QUBO separa construção e resolução. Densidade é a fração dos pares distintos
com termo quadrático não nulo. A memória clássica usa RSS do processo via `psutil` quando
disponível e recorre ao pico RSS reportado pelo sistema operacional.

## Segurança de backend

`run_qaoa_benchmark` mantém uma allowlist fechada: `local_simulator` e `fake_backend`.
Qualquer outro backend falha antes da execução. O módulo não contém cliente IBM,
credenciais, submissão de job ou fallback para hardware. Uma futura integração IBM deve
ser um adaptador separado, exigir autorização explícita existente e registrar custo e
identificador do job.

## Auditoria e telemetria

Cada execução registra configuração, resultados dos três solvers, métricas agregadas,
CPU/RAM/tempo, custo estimado e hash do relatório. Cada linha do ledger contém o hash da
linha anterior, formando uma cadeia verificável por `verify_ledger(path)`.

`latest.json` é substituído atomicamente; uma interrupção durante a escrita não deixa um
relatório parcial. `history.jsonl` preserva um resumo por execução para o gráfico histórico.

## Execução e validação

```bash
asus-theye benchmark --seed 42 --shots 1024 --layers 2 --stability-runs 10
pytest
ruff check .
```

Para isolar relatórios de experimentos, use `--output-dir`. Registre hardware, sistema
operacional, carga concorrente e versões ao comparar tempos entre máquinas.

## Critérios antes de alegações científicas

São necessários problemas representativos em múltiplas escalas, repetição suficiente,
intervalos de confiança, controle de custo total, comparação com baselines competitivos,
hardware real autorizado e revisão independente. Mesmo nessas condições, a conclusão
deve distinguir qualidade de solução, tempo total e custo operacional.
