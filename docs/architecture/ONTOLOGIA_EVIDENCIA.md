# Ontologia de Evidência — THE EYE

> Projeto da ontologia de objetos e linhagem da plataforma **THE EYE — Evidência**
> (benchmark de arquitetura: Palantir). Documento de DESENHO; a implementação
> vive em `src/asus_theye/` e é feita a partir daqui.
>
> Referências estudadas (licença que permite reuso — política de reuso do dono):
> **OpenMetadata** (Apache-2.0, `open-metadata/OpenMetadata`) e **DataHub**
> (Apache-2.0, `datahub-project/datahub`). Nenhum código é copiado; absorve-se a
> ESTRUTURA (entidade tipada + relações explícitas + linhagem upstream/downstream
> + versionamento). A proveniência de qualquer implementação vai para
> `reports/provenance/`.

## 1. Por que uma ontologia, e o que ela supera na Palantir

A Palantir vende ontologia de objetos com linhagem até a fonte — **a portas
fechadas** ("confie na Palantir"). A nossa proposta faz o mesmo modelo, mas com
uma diferença estrutural: **cada objeto carrega a própria prova criptográfica** e
a linhagem é **verificável por terceiros** sem acesso ao nosso banco. Não é
"confie", é "verifique". O que se absorve dos projetos Apache é a disciplina de
modelagem; o que se acrescenta é a camada de evidência (hash, corrente, âncora)
que já existe em `src/asus_theye/audit/` e `src/asus_theye/markets/`.

## 2. Princípios de modelagem (o que vem de OpenMetadata/DataHub)

| Princípio | Origem (Apache-2.0) | Como aplicamos |
| --- | --- | --- |
| Entidade **tipada** com identidade estável | OpenMetadata (schema-first, JSON Schema por entidade) | cada objeto tem `tipo` + `id` canônico e imutável |
| **Relações explícitas** (não implícitas em joins) | DataHub (modelo de metadados em grafo) | arestas nomeadas e direcionais entre objetos |
| **Linhagem** upstream/downstream | ambos (lineage graph) | quem derivou de quem, até a fonte primária |
| **Versionamento/aspectos** | DataHub (aspects) / OpenMetadata (versions) | mudança é evento novo, nunca edição no lugar |
| **Proveniência** obrigatória | doutrina do projeto + ambos | toda entidade aponta a fonte; sem fonte, não entra |

## 3. As entidades (mapeadas aos objetos que JÁ existem)

Ordem canônica da corrente (é a linhagem):

```
Fonte → Artefato → EventoSelado → LoteMerkle → Âncora → Recibo
                        ▲
             Mercado → Resolução
```

### 3.1 `Fonte`
Origem oficial nomeada de um desfecho ou dado. (Ex.: `api.bcb.gov.br (SGS 433)`,
`dadosabertos.camara.leg.br`.)
- Campos: `id`, `nome`, `tipo` (`api|arquivo|feed`), `jurisdicao`, `url_publica`.
- Relações: `FORNECE →` `Artefato`/`Resolução`.
- Invariante: Kalshi **nunca** é `Fonte` (é `Comparador`, entidade à parte).

### 3.2 `Artefato`
Dado bruto obtido de uma `Fonte`, com hash e `retrieved_at`.
- Campos: `id`, `fonte_id`, `sha256`, `retrieved_at`, `descricao`.
- Relações: `DERIVA_DE →` `Fonte`.

### 3.3 `Mercado` / `Resolução` (de `src/asus_theye/markets/`)
- `Mercado`: pergunta binária com prazo, `probability`, `resolution_source`,
  `max_uncertainty`. (`claim.py`)
- `Resolução`: desfecho medido contra a `Fonte`, com `outcome`,
  `brier_do_contrato`. (`resolution.py`, `live.py`)
- Relações: `Resolução —RESOLVE→ Mercado`; `Resolução —CONTRA→ Fonte`.

### 3.4 `EventoSelado` (de `src/asus_theye/audit/schema.py`)
O evento canônico de 40 campos (RFC 8785 + SHA-256), corrente por tenant.
- Campos-chave: `event_id`, `sequence`, `event_hash_sha256`,
  `previous_event_hash_sha256`, `content_hash_sha256`.
- Relações: `SELA →` `Resolução` (hoje) / futuramente qualquer mutação;
  `SUCEDE →` `EventoSelado` anterior (a corrente).

### 3.5 `LoteMerkle` (de `audit/merkle.py`, `audit/manifest.py`)
Árvore Keccak-256 de um intervalo de eventos + manifesto.
- Campos: `batch_id`, `merkle_root`, `first_sequence`, `last_sequence`,
  `manifest_hash_sha256`.
- Relações: `AGREGA →` N `EventoSelado`; `SUCEDE →` `LoteMerkle` anterior
  (`previous_batch_root`).

### 3.6 `Âncora` (de `src/asus_theye/audit/anchor.py`)
Registro on-chain (Base Sepolia) de um `LoteMerkle`.
- Campos: `chain_id`, `contract_address`, `tx_hash`, `block_number`, `status`.
- Relações: `ANCORA →` `LoteMerkle`.

### 3.7 `Recibo`
O resultado de uma verificação (o que o worker público devolve).
- Campos: `estado` (`valid|not_anchored|anchor_unconfirmed|tampered|invalid`),
  `verificacoes`.
- Relações: `ATESTA →` `EventoSelado`/`LoteMerkle`/`Âncora`.

### 3.8 `Comparador` (Kalshi)
Entidade separada, deliberadamente **fora** da linhagem de resolução.
- Relações: `DIVERGE_DE →` `Mercado` (registro de divergência), nunca `RESOLVE`.

## 4. Linhagem — a consulta que a plataforma precisa responder

> "Dado este `Recibo`, prove a cadeia até a `Fonte` primária."

`Recibo → Âncora → LoteMerkle → EventoSelado → Resolução → Fonte`. Cada aresta é
verificável: hash do evento, inclusão Merkle, âncora on-chain, `content_hash` da
resolução contra a linha publicada em `resolucoes.jsonl`. É a linhagem da
Palantir, com prova em cada salto.

## 5. Proposta de implementação (território `src/`, do Claude)

Módulo novo `src/asus_theye/evidence/` (não conflita com nada existente):

- `entidades.py` — as 8 entidades como dataclasses frozen, cada uma com
  `tipo`/`id`/`as_dict()`, no estilo de `markets/claim.py`.
- `grafo.py` — arestas nomeadas e a consulta de linhagem (`caminho_ate_a_fonte`),
  lendo o que já existe (`reports/markets/eventos.jsonl`, `ancoras.jsonl`) — sem
  duplicar dado, só relacionando.
- `render.py` — reaproveita o painel `/markets` do dashboard para uma view de
  ontologia navegável (o app Evidência).
- Testes em `tests/evidence/`.

Sem novo banco: a ontologia é uma **camada de relações** sobre os artefatos
versionados que já são a fonte da verdade. Cada entidade absorvida de padrão
Apache ganha registro em `reports/provenance/` citando origem, arquivo e commit.

## 6. O que fica de fora (honestidade)

- Não se importa nenhum dado dos projetos Apache — só a disciplina de modelagem.
- Não se cria dependência de runtime de OpenMetadata/DataHub (são pesados e
  criariam custo/operação); absorve-se a ideia, roda-se leve.
- Entidades de pessoas (ranking) permanecem L4/DPIA e **fora** desta ontologia
  até haver base legal, como já recusa `source_graph/scoring.py`.
