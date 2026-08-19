# M5 — especificação de importação do DuckDB legado

## Resultado

**Classificação: DERIVED.** O banco foi aberto por `.venv/bin/python` com
`duckdb.connect(..., read_only=True)`. A junção por identificador produz 40
contratos de `voto_legislativo`, todos com exatamente uma cotação e uma
resolução. Não houve escrita no banco.

O conteúdo mecânico do import está especificado abaixo, mas a promoção dos
eventos como liquidações verificadas depende de decisões registradas em
“Divergências e decisões pendentes”. Em particular, o banco não contém o host
`dadosabertos.camara.leg.br` nem uma URL oficial: contém somente descrições
textuais atribuídas à Câmara. Não se deve completar a fonte por suposição.

### Snapshot analisado

| Campo | Valor |
| --- | --- |
| Caminho | variável `ASUS_MARKETS_DB` |
| Tamanho | 53.227.520 bytes |
| SHA-256 | `61ab92d4529071663d9c3715c634408d879fe9de829833355acf652d4bc0b5b5` |
| Modificação do arquivo | `2026-08-02 07:31:29.786921520-03:00` |
| Modo de abertura | `duckdb.connect(path, read_only=True)` |
| Recorte | `mercados.produto = 'voto_legislativo'` e presença em `resolucoes` |

Contagens observadas: 50 mercados, 50 cotações, 41 resoluções; 41 junções
1:1:1, das quais 40 são de voto legislativo e uma de macroeconomia. Não há
identificadores duplicados nas três tabelas.

## Esquema legado relevante

### `mercados` — 50 linhas

| Coluna | Tipo | Restrição observada | Uso no M5 |
| --- | --- | --- | --- |
| `id` | `VARCHAR` | chave primária, não nulo | `claim_id` |
| `produto` | `VARCHAR` | não nulo | seleção e mapa de área |
| `etiqueta` | `VARCHAR` | não nulo | metadado legado opcional |
| `pergunta_leiga` | `VARCHAR` | não nulo | `question` |
| `data_abertura` | `VARCHAR` | não nulo | `created_at` |
| `data_limite` | `VARCHAR` | não nulo | `deadline` |
| `fonte_resolucao` | `VARCHAR` | não nulo | fonte declarada, não a confirmação |
| `criterio_resolucao` | `VARCHAR` | não nulo | `resolution_criterion` |
| `limiar` | `DOUBLE` | anulável | não importar sem decisão |
| `status` | `VARCHAR` | não nulo | guarda: deve ser `LIQUIDADO` |

### `cotacoes` — 50 linhas

| Coluna | Tipo | Restrição observada | Uso no M5 |
| --- | --- | --- | --- |
| `mercado_id` | `VARCHAR` | chave primária composta, não nulo | junção com `mercados.id` |
| `timestamp` | `VARCHAR` | chave primária composta, não nulo | `quoted_at` |
| `probabilidade` | `DOUBLE` | não nulo | `probability`, diretamente |
| `faixa_95` | `VARCHAR` | anulável | fora do recorte solicitado |
| `faixa_99` | `VARCHAR` | anulável | fora do recorte solicitado |
| `metodo` | `VARCHAR` | anulável | `probability_method` |
| `brier_index` | `DOUBLE` | anulável | não importar sem definição/método |

### `resolucoes` — 41 linhas

| Coluna | Tipo | Restrição observada | Uso no M5 |
| --- | --- | --- | --- |
| `mercado_id` | `VARCHAR` | chave primária, não nulo | junção e conferência do `claim_id` |
| `timestamp` | `VARCHAR` | não nulo | `resolved_at` e `occurred_at` |
| `resultado_real` | `INTEGER` | não nulo | `outcome` |
| `valor_observado` | `DOUBLE` | anulável | não importar sem definição/método |
| `brier_do_contrato` | `DOUBLE` | anulável | `brier_do_contrato`, após conferência |
| `acerto` | `INTEGER` | anulável | não importar sem definição/método |
| `fonte_confirmacao` | `VARCHAR` | não nulo | `resolution_source` textual |

Junção normativa:

```sql
FROM mercados AS m
JOIN cotacoes AS c ON c.mercado_id = m.id
JOIN resolucoes AS r ON r.mercado_id = m.id
WHERE m.produto = 'voto_legislativo'
  AND m.status = 'LIQUIDADO'
```

## Mapeamento para `market.settlement`

O envelope segue `src/asus_theye/markets/auditoria.py`: o evento é
`market.settlement`, a ação é `settle`, e a idempotência é por `claim_id`.

### Envelope auditável

| Campo do evento | Origem/regra |
| --- | --- |
| `event_type` | constante `market.settlement` |
| `action` | constante `settle` |
| `correlation_id` | `m.id`, sem transformação; é exatamente o `claim_id` |
| `occurred_at` | `r.timestamp`; nunca `m.data_abertura`, `c.timestamp` ou a data do import |
| `resource_type` | constante `market` |
| `resource_id` antes da pseudonimização | `m.id` |
| `content_hash_sha256` | calculado pelo SDK sobre o conteúdo normalizado abaixo |
| demais campos de corrente | produzidos pelo SDK, não pelo DuckDB legado |

Todos os 40 valores propostos para `occurred_at` são
`2026-07-25T06:24:48Z`. O sufixo `Z` fornece timezone UTC e satisfaz o contrato
ISO 8601 do validador. O import deve recusar qualquer linha cujo
`resolved_at` não tenha timezone; não deve substituí-lo pelo horário corrente.

### Conteúdo hasheado

| Campo normalizado | Coluna/regra |
| --- | --- |
| `claim_id` | `m.id` |
| `market_area_id` | mapa versionado `voto_legislativo` → `voto-legislativo` |
| `legacy_product` | `m.produto` |
| `question` | `m.pergunta_leiga` |
| `created_at` | `m.data_abertura`, preservado mesmo quando retrospectivo |
| `quoted_at` | `c.timestamp`; não confundir com criação |
| `deadline` | `m.data_limite` |
| `probability` | `c.probabilidade`; não reconstruir a partir do Brier |
| `probability_method` | `c.metodo`; nos 40 casos, `taxa_seguimento_partidario` |
| `declared_resolution_source` | `m.fonte_resolucao` |
| `resolution_criterion` | `m.criterio_resolucao` |
| `outcome` | `r.resultado_real` |
| `resolution_source` | `r.fonte_confirmacao`, como texto legado não verificado |
| `resolved_at` | `r.timestamp`, igual ao `occurred_at` do envelope |
| `brier_do_contrato` | `r.brier_do_contrato`, somente se igual a `(probability - outcome)²` |
| `historical_reconstruction` | constante `true`; decisão de governança, não fato extraído do banco |
| `forecast_eligible` | constante `false`, enquanto a cronologia retrospectiva não for resolvida |

`etiqueta` e `status` podem viajar como `legacy_label` e `legacy_status` se o
importador preservar todos os textos de origem. `limiar`, `brier_index`,
`valor_observado` e `acerto` ficam de fora: a presença de um número no banco não
é método nem definição.

Como as perguntas nomeiam pessoas naturais, este lote não autoriza extração de
entidades nem criação de cadastro de indivíduos. O texto solicitado pode ser
preservado como conteúdo histórico do próprio contrato.

## Consistência medida

| Verificação | Resultado |
| --- | --- |
| Brier por contrato | 40/40 iguais **exatamente**, em `DOUBLE`, a `(p - outcome)²`; diferença máxima `0.0` |
| Brier médio | `0.00329250675`, arredondado a seis casas: `0.003293` |
| Probabilidade | 40/40 em `[0, 1]`; média `0.9584325`; método presente em 40/40 |
| Desfecho | 40/40 iguais a `1` |
| Datas de criação | 40/40 ISO 8601 com timezone `Z` |
| Datas de cotação | 40/40 ISO 8601 com timezone `Z` |
| Datas de resolução | 40/40 ISO 8601 com timezone `Z` |
| Fonte declarada | 40/40: `Câmara dos Deputados — dados abertos (votações nominais)` |
| Host oficial no banco inteiro | zero ocorrência de `dadosabertos.camara.leg.br` em qualquer coluna `VARCHAR` |
| Nulos nos campos listados para import | zero |

Como controle estatístico separado do import, `voto_seguimento` contém 68.234
pares, dos quais 65.445 têm `seguiu = 1`: taxa histórica
`0.9591259489404109`. O palpite constante nessa taxa teria Brier
`0.001670688050021895` contra estes 40 desfechos, menor que o Brier médio dos
contratos. Portanto, este lote não demonstra habilidade preditiva.

## Valores dos 40 contratos

Campos comuns a todas as linhas: `market_area_id = "voto-legislativo"`,
`legacy_product = "voto_legislativo"`, `deadline = "2026-07-14"`,
`probability_method = "taxa_seguimento_partidario"`,
`declared_resolution_source = "Câmara dos Deputados — dados abertos (votações nominais)"`,
`historical_reconstruction = true` e `forecast_eligible = false`. A coluna
“fonte de resolução” é o texto exato de `resolucoes.fonte_confirmacao`, não uma
URL acrescentada posteriormente.

| `claim_id` | Pergunta | `probability` | `outcome` | Fonte de resolução | `created_at` | `quoted_at` | `resolved_at` / `occurred_at` | Brier armazenado |
| --- | --- | ---: | ---: | --- | --- | --- | --- | ---: |
| `VOTO-01::2637721-10::141398` | O deputado Carlos Zarattini (PT-SP) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9952 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00002304 |
| `VOTO-01::2637721-10::160538` | O deputado Bohn Gass (PT-RS) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9951 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00002401 |
| `VOTO-01::2637721-10::178829` | O deputado Capitão Augusto (PL-SP) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9410 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00348100 |
| `VOTO-01::2637721-10::178927` | O deputado Aliel Machado (PV-PR) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9211 | 1 | Câmara · votação 2637721-10: PV orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00622521 |
| `VOTO-01::2637721-10::178937` | O deputado Altineu Côrtes (PL-RJ) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9744 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00065536 |
| `VOTO-01::2637721-10::204369` | O deputado Caroline de Toni (PL-SC) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.8503 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.02241009 |
| `VOTO-01::2637721-10::204374` | O deputado Bia Kicis (PL-DF) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9120 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00774400 |
| `VOTO-01::2637721-10::204378` | O deputado Coronel Chrisóstomo (PL-RO) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9427 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00328329 |
| `VOTO-01::2637721-10::204388` | O deputado Bibo Nunes (PL-RS) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9593 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00165649 |
| `VOTO-01::2637721-10::204426` | O deputado Carlos Veras (PT-PE) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9875 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00015625 |
| `VOTO-01::2637721-10::204460` | O deputado Carlos Jordy (PL-RJ) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.8897 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.01216609 |
| `VOTO-01::2637721-10::204462` | O deputado Chris Tonietto (PL-RJ) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9173 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00683929 |
| `VOTO-01::2637721-10::204495` | O deputado Airton Faleiro (PT-PA) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9921 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:58Z` | `2026-07-25T06:22:58Z` | `2026-07-25T06:24:48Z` | 0.00006241 |
| `VOTO-01::2637721-10::204501` | O deputado Alencar Santana (PT-SP) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9795 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:58Z` | `2026-07-25T06:22:58Z` | `2026-07-25T06:24:48Z` | 0.00042025 |
| `VOTO-01::2637721-10::204504` | O deputado Cezinha de Madureira (PL-SP) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9000 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.01000000 |
| `VOTO-01::2637721-10::204515` | O deputado André Janones (REDE-MG) vai votar conforme a orientação do seu partido na proposição em pauta? | 1.0000 | 1 | Câmara · votação 2637721-10: REDE orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00000000 |
| `VOTO-01::2637721-10::204528` | O deputado Adriana Ventura (NOVO-SP) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9907 | 1 | Câmara · votação 2637721-10: NOVO orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:58Z` | `2026-07-25T06:22:58Z` | `2026-07-25T06:24:48Z` | 0.00008649 |
| `VOTO-01::2637721-10::204572` | O deputado Capitão Alberto Neto (PL-AM) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9407 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00351649 |
| `VOTO-01::2637721-10::206018` | O deputado Célia Xakriabá (PSOL-MG) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9933 | 1 | Câmara · votação 2637721-10: PSOL orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00004489 |
| `VOTO-01::2637721-10::213762` | O deputado Carla Dickson (PL-RN) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9000 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.01000000 |
| `VOTO-01::2637721-10::220548` | O deputado Camila Jara (PT-MS) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9853 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00021609 |
| `VOTO-01::2637721-10::220556` | O deputado Ana Paula Lima (PT-SC) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9951 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00002401 |
| `VOTO-01::2637721-10::220576` | O deputado Alfredo Gaspar (PL-AL) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.8636 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:58Z` | `2026-07-25T06:22:58Z` | `2026-07-25T06:24:48Z` | 0.01860496 |
| `VOTO-01::2637721-10::220594` | O deputado Coronel Assis (PL-MT) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9583 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00173889 |
| `VOTO-01::2637721-10::220595` | O deputado Coronel Fernanda (PL-MT) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9757 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00059049 |
| `VOTO-01::2637721-10::220605` | O deputado Bandeira de Mello (PV-RJ) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9809 | 1 | Câmara · votação 2637721-10: PV orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00036481 |
| `VOTO-01::2637721-10::220632` | O deputado Ana Pimentel (PT-MG) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9923 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00005929 |
| `VOTO-01::2637721-10::220657` | O deputado André Fernandes (PL-CE) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9545 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00207025 |
| `VOTO-01::2637721-10::220666` | O deputado Coronel Meira (PL-PE) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9430 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00324900 |
| `VOTO-01::2637721-10::220690` | O deputado Capitão Alden (PL-BA) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.8973 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.01054729 |
| `VOTO-01::2637721-10::220704` | O deputado Carol Dartora (PT-PR) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9927 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00005329 |
| `VOTO-01::2637721-10::221148` | O deputado Alfredinho (PT-SP) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9806 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:58Z` | `2026-07-25T06:22:58Z` | `2026-07-25T06:24:48Z` | 0.00037636 |
| `VOTO-01::2637721-10::221328` | O deputado Adilson Barroso (PL-SP) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9637 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:58Z` | `2026-07-25T06:22:58Z` | `2026-07-25T06:24:48Z` | 0.00131769 |
| `VOTO-01::2637721-10::69871` | O deputado Bacelar (PV-BA) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9726 | 1 | Câmara · votação 2637721-10: PV orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00075076 |
| `VOTO-01::2637721-10::73433` | O deputado Arlindo Chinaglia (PT-SP) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9975 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00000625 |
| `VOTO-01::2637721-10::73579` | O deputado Alberto Fraga (PL-DF) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9533 | 1 | Câmara · votação 2637721-10: PL orientou 'Sim', deputado votou 'Sim' -> seguiu | `2026-07-25T06:22:58Z` | `2026-07-25T06:22:58Z` | `2026-07-25T06:24:48Z` | 0.00218089 |
| `VOTO-01::2637721-10::73701` | O deputado Benedita da Silva (PT-RJ) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9901 | 1 | Câmara · votação 2637721-10: PT orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00009801 |
| `VOTO-01::2637721-10::74057` | O deputado Alice Portugal (PCdoB-BA) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9784 | 1 | Câmara · votação 2637721-10: PCdoB orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:58Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00046656 |
| `VOTO-01::2637721-10::74171` | O deputado Chico Alencar (PSOL-RJ) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9908 | 1 | Câmara · votação 2637721-10: PSOL orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00008464 |
| `VOTO-01::2637721-10::88256` | O deputado Clodoaldo Magalhães (PV-PE) vai votar conforme a orientação do seu partido na proposição em pauta? | 0.9897 | 1 | Câmara · votação 2637721-10: PV orientou 'Não', deputado votou 'Não' -> seguiu | `2026-07-25T06:22:59Z` | `2026-07-25T06:22:59Z` | `2026-07-25T06:24:48Z` | 0.00010609 |

## Divergências e decisões pendentes

1. **Fonte oficial não demonstrada no banco — UNKNOWN.** Nenhum dos 40 campos
   `fonte_resolucao` ou `fonte_confirmacao` contém
   `dadosabertos.camara.leg.br`; a busca em todas as colunas textuais do banco
   também encontrou zero ocorrências. Os textos são semanticamente compatíveis
   com dados abertos da Câmara, mas isso não prova host, endpoint, resposta ou
   snapshot. Decisão: obter e registrar a URL oficial e sua evidência primária,
   ou importar declarando explicitamente `source_verification = "unknown"`.
   Não inventar uma URL a partir do identificador `2637721-10`.

2. **Todos os contratos são retrospectivos — FACT.** O prazo é
   `2026-07-14`, enquanto as criações ocorreram em `2026-07-25`, onze dias
   depois. A resolução foi gravada apenas 109 ou 110 segundos após a criação.
   Decisão proposta: selar como reconstrução histórica, com
   `historical_reconstruction = true` e `forecast_eligible = false`; não usar os
   40 registros como evidência de previsão anterior ao evento.

3. **Criação e cotação divergem em uma linha — FACT.** Em
   `VOTO-01::2637721-10::74057`, `data_abertura` é
   `2026-07-25T06:22:58Z`, mas a cotação é
   `2026-07-25T06:22:59Z`. A diferença de um segundo deve ser preservada; não
   sobrescrever um campo com o outro.

4. **A probabilidade existe diretamente — FACT.** A documentação atual da
   ponte em `src/asus_theye/markets/duckdb_source.py` afirma que ela não está
   gravada e a recupera de Brier + desfecho. Isso diverge do banco: há 40
   valores em `cotacoes.probabilidade`, todos com método. Decisão: o M5 deve ler
   a coluna direta e usar a igualdade do Brier apenas como validação. A
   reconstrução algébrica perde independência e pode mascarar corrupção.

5. **Números sem semântica/método suficiente — BLOCKED para esses campos.** O
   valor `brier_index = 81.03` aparece nas 40 cotações, mas o esquema não define
   unidade, fórmula ou janela. `valor_observado = 1.0` e `acerto = 1` repetem-se
   nas 40 resoluções sem definição do cálculo; `limiar = 1.0` também não traz
   método operacional no banco. Eles não entram no conteúdo selado até existir
   documentação reprodutível. Isso não bloqueia `probability`, cujo método é
   `taxa_seguimento_partidario`, nem `brier_do_contrato`, cuja fórmula foi
   reproduzida exatamente.

6. **Recorte sem variação de desfecho — FACT.** Os 40 outcomes são `1`, vêm de
   uma única votação e cobrem sete partidos. O Brier médio baixo não demonstra
   skill: o baseline histórico nomeado acima é melhor. Essa limitação deve
   acompanhar qualquer agregado derivado depois do import.

## Evidência e limites da conclusão

| Pergunta | Classe | Evidência primária | Evidência contrária | Confiança | Limite / o que mudaria |
| --- | --- | --- | --- | --- | --- |
| Há 40 liquidações de voto prontas para tradução mecânica? | FACT | catálogo e junção 1:1:1 do snapshot identificado | nenhuma duplicata ou nulo encontrado | alta | outro hash do banco exige nova análise |
| O Brier armazenado está consistente? | DERIVED | recomputação por linha com a probabilidade direta e o outcome | nenhuma das 40 linhas divergiu | alta | diferença em novo snapshot |
| A fonte é `dadosabertos.camara.leg.br`? | UNKNOWN | descrições textuais da Câmara | host ausente no banco inteiro | alta para a ausência; baixa para a origem efetiva | URL/snapshot oficial verificável |
| As datas podem alimentar a cadeia? | FACT | parsing ISO 8601 com timezone em 40/40 | cronologia é retrospectiva, não inválida sintaticamente | alta | nenhuma para formato; decisão humana para interpretação |
| O lote demonstra skill preditiva? | FACT/DERIVED | 40 outcomes iguais a 1; Brier do baseline histórico menor | nenhuma janela alternativa medida neste lote | alta neste recorte | amostra prospectiva, variada e pré-registrada |

