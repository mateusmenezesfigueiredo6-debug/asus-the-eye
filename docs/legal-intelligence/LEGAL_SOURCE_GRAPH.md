# Grafo de fontes de conhecimento

O que é, o que contém, e como navegar sem se perder.

## O núcleo comum

Quatro pedidos aparentemente distintos — indexar livros de marketing, mapear
algoritmos preditivos, listar universidades em IA, analisar setores como O&G e
saneamento — compartilham **um único objeto**: um grafo de entidades-fonte com

1. **proveniência hasheada** (URL oficial + `retrieved_at` + `content_hash_sha256`);
2. **classificação por nicho** (reusando `suggest_legal_areas` sobre os 145);
3. **ranking com evidência** (componentes rastreáveis, nunca imputados);
4. **cobertura honesta** (o real, nunca preenchido até 100/200/500).

Construir esse núcleo uma vez serve aos quatro. Construir quatro pipelines
separados produziria quatro verdades sobre a mesma pergunta.

## As quatro trilhas

O painel (`asus-theye chart`) agrupa as 19 categorias da Phase C em trilhas de
navegação:

| Trilha | Categorias | Estado |
| --- | --- | --- |
| **fundação** | periódicos e repositórios, datasets oficiais, associações, conferências | 0/400 — `not_yet_attempted` |
| **acadêmico** | universidades, escolas, centros de pesquisa, clínicas, observatórios | 0/500 — `not_yet_attempted` |
| **setorial** | reguladores, tribunais, instituições arbitrais, federações, escritórios, veículos | 0/600 — `not_yet_attempted` |
| **gated_dpia** | acadêmicos, praticantes, árbitros, autoridades | 0/400 — `requires_dpia` |

A quarta trilha é a diferença entre "ainda não fizemos" e "não vamos fazer sem
um humano": as quatro categorias que descrevem **pessoas** ficam bloqueadas por
DPIA, não por falta de tempo.

## O que já existe no grafo

- **13 conectores** declarados com licença, termos, intervalo mínimo, limite de
  tamanho e `does_not_provide` obrigatório. **Nenhum habilitado** — o Estágio 1
  não toca a rede.
- **23 artefatos de software** com PoC: das bibliotecas tabulares dominantes
  (XGBoost, LightGBM) aos modelos de fundação para previsão (Chronos, TimesFM,
  Moirai), passando por derivativos (QuantLib) e quântica (Qiskit, PennyLane).
  Todos `declared_unverified` até o hash da licença ser buscado.
- **22 comunidades** registradas como *fontes*: Hugging Face, r/LocalLLaMA,
  Quantitative Finance StackExchange, Wilmott, ABRAJI, Data Hackers, SICSS...
  Registra-se o fórum, **nunca as pessoas nele**.

## O que está fora, e por quê

| Fora | Motivo |
| --- | --- |
| Volume de vendas de livros, cap market por nicho | Nenhuma API gratuita entrega. Circana/Nielsen são licenciadas; Amazon BSR é vedado por ToS. Slot vazio honesto em `sales_data_crosswalk.json` |
| Algoritmos de recomendação de Instagram/Meta/X/TikTok | Não são públicos. O indexável são as publicações dessas empresas e as divulgações do art. 40 do DSA |
| OpenAlex via API | Desde fev/2026 cobra por uso; `AGENTS.md` proíbe criar custos. O caminho é o dump CC0 no S3 |
| Ranking de pessoas | L4: exige DPIA humana |
| Grupos fechados de WhatsApp/Telegram | Conteúdo privado; indexar exigiria coletar mensagens de pessoas |
| Previsão musical, de apostas, valoração de contas sociais | `PROHIBITED_FRAGMENTS` bloqueia `prediction`; "do not rank by followers" é regra da missão. A **literatura** sobre esses temas entra; o produto preditivo não |

Cada uma dessas aparece no painel como uma lacuna com `blocking_reason` e
`what_would_unblock` — nomeada, não escondida.

## Fluxo

```
descoberta (discovery-query, hasheada)
  → fetch educado (robots + rate limit + max_bytes + licença declarada)
    → normalização (knowledge-source com source_manifest)
      → classificação por nicho (suggest_legal_areas — vazio é válido)
        → score com evidência (componentes presentes, ausentes omitidos)
          → ranking-list (nunca preenchida, entity_type único)
            → cobertura (todo zero com motivo)
              → evento no ledger (só hashes)
```

Cada seta é uma fronteira onde algo pode ser recusado, e toda recusa é
registrada com o motivo.

## Diagramas

O painel HTML (`reports/chart/mistress-chart.html`) renderiza o grafo em Mermaid:
trilhas → estado, com o motivo do bloqueio visível em cada aresta parada.
