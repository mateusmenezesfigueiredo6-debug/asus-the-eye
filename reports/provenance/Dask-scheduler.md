# Proveniência — coletor paralelo por host (conceito de agendador)

Registro de reuso legítimo, conforme a política de licenças do projeto.

| Campo | Valor |
| --- | --- |
| Componente do projeto | `src/asus_theye/source_graph/paralelo.py` (+ lock em `fetcher.py`) |
| Origem estudada | Dask — `dask/dask` (e a categoria "Saturn Cloud", que é Dask gerenciado) |
| Licença de origem | **BSD-3-Clause** — © Dask core developers |
| Data | 2026-08-18 |

## O que foi absorvido

O **conceito** de agendador que particiona trabalho e o executa por afinidade
(no Dask: por worker/partição; aqui: por **host**, porque o rate limit das
fontes é por host). Do estudo veio a decisão de desenho: paralelismo só entre
partições, série dentro da partição, falha isolada por tarefa.

## O que NÃO foi copiado

Nenhuma linha de código do Dask. A implementação usa a stdlib
(`ThreadPoolExecutor`, padrão que o repo já usava em `apps/comercial/`), tem
~120 linhas e resolve só o caso do projeto. O Dask não entra como dependência —
absorver a ideia sem herdar o runtime é o ponto da política.

## Situação de licença

- Código do projeto: AGPL-3.0-or-later (© 2026 Mateus Menezes Figueiredo).
- Ideia estudada: BSD-3 — permissiva; o aviso de origem é este registro.
