# Como contribuir

## Ambiente

```bash
make setup     # cria o ambiente e instala tudo
make check     # o que o CI roda: lint + tipos + testes + cobertura
```

Sem `make`, o equivalente:

```bash
uv venv && uv pip install -e '.[telemetry,dashboard,quantum,dev]'
.venv/bin/ruff check . && .venv/bin/python -m pytest tests/ -q
```

## As regras que este projeto não negocia

Não são preferências de estilo — são as invariantes que fazem o sistema valer
alguma coisa. Um PR que as viole não entra, por melhor que seja o código.

### 1. Número sem denominador não é número

Taxa, percentual e score exigem denominador visível e tamanho de amostra. Uma
conversão de 100% sobre 2 casos **não** é comparável a 40% sobre 200 — e o
código separa fisicamente os dois em vez de deixar a comparação acontecer.

### 2. Ausência é ausência, nunca zero

Componente sem dado é **omitido**, jamais preenchido com 0. Zerar é uma
inferência disfarçada de medição. Quem omite registra o motivo em `limitations`.

### 3. Silêncio vence palpite

Classificador que não reconhece devolve lista vazia. Crosswalk sem fonte oficial
fica com `mappings: []` e `status: pending_*`. `UNKNOWN` é uma resposta legítima
e frequentemente a correta.

### 4. Lista não se preenche até a meta

`qualified_count` é o real. `padded` é `const: false` no schema — não existe
como declarar o contrário. 23 fontes verificadas valem mais que 200 inventadas.

### 5. Evidência é append-only

Correção é evento novo, nunca edição. Os triggers do D1 recusam `UPDATE` e
`DELETE` em `audit_events`. Isso vale para o funil comercial também.

### 6. Dado pessoal não vaza

Nome de cliente vira pseudônimo antes de tocar o disco. Prompt e resposta do LLM
nunca são persistidos — só hashes. Nada de dado pessoal on-chain, nunca.

### 7. Métrica social não ranqueia

Seguidores, curtidas, estrelas e engajamento podem ser registrados como contexto
factual, mas `component_id` é enum fechado: passá-los a um score **levanta
exceção** em vez de ser silenciosamente aceito.

### 8. Toda recusa é registrada com motivo

Cobertura zero tem `blocking_reason` nomeado. Perda no funil exige motivo.
Análise vedada vira registro `PROHIBITED` — contentless, mas auditável.

## Antes de abrir o PR

```bash
make check                                  # tudo verde
python3 scripts/release_check.py L1         # portões da classe
python3 scripts/leak_check.py               # três camadas
```

## Lançamento

Nada sai daqui sem passar pelo [protocolo](docs/governance/RELEASE_PROTOCOL.md).
Classes L0–L2 fluem; L3+ exigem a senha de publicação, que **nenhuma IA possui,
por desenho**.

## Commits

Mensagem que explica **por quê**, não o quê — o diff já mostra o quê. Se a
mudança envolve uma decisão não óbvia, ela vira um ADR em `docs/adr/`.

## Licenciamento da sua contribuicao

O codigo deste projeto esta sob **AGPL-3.0** (ver `LICENSE` e `LICENSE.md`).
Ao enviar contribuicao voce concorda que ela entra sob a mesma licenca.

O diretorio `data/` NAO esta sob AGPL: a taxonomia e os aliases sao trabalho de
curadoria sob licenca restrita (`data/LICENSE`). Contribuicao que toque `data/`
precisa de acordo previo com o titular.

O projeto usou MIT ate 05/08/2026. A troca foi feita enquanto havia autor unico.
