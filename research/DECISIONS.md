# Decisões de pesquisa

Cada decisão com a razão e o que a reverteria.

---

## D001 — Um grafo de fontes, não quatro pipelines

**Decisão:** os pedidos de livros, algoritmos, universidades e setores viram um
único módulo `source_graph`.

**Razão:** os quatro compartilham o mesmo objeto — entidade-fonte com
proveniência hasheada, classificação por nicho e ranking com evidência. Quatro
pipelines produziriam quatro verdades sobre a mesma pergunta.

**Reverteria:** se um dos domínios exigisse um modelo de entidade
incompatível — não é o caso hoje.

## D002 — Estágio 1 inteiramente offline

**Decisão:** nenhum conector habilitado, nenhum teste toca a rede.

**Razão:** o esqueleto verificável tem valor independente, e as decisões sobre
identificação em requisições (U001, U002) ainda não foram tomadas. Construir o
esqueleto primeiro evita que a pressa de ver dado real force uma decisão de
privacidade mal pensada.

**Reverteria:** decisão do dono sobre modelo de ameaça, mais habilitação
explícita de conector.

## D003 — `net/http.py` novo em vez de refatorar `batching.py`

**Decisão:** cria-se um cliente HTTP novo; as quatro cópias existentes de
`urllib` permanecem.

**Razão:** `batching.py` não tem nenhum teste. Refatorar um caminho do núcleo de
auditoria sem rede de proteção, para viabilizar uma feature nova, é a troca de
risco errada.

**Reverteria:** escrever testes para `batching.py` primeiro. Registrado em
ADR-011 com a ordem correta.

## D004 — Componente ausente é omitido, nunca zerado

**Decisão:** o score é média ponderada só dos componentes presentes.

**Razão:** zerar afirma "não há impacto" quando o que houve foi "não há dado".
É inferência disfarçada de medição.

**Reverteria:** nada. É a regra central da honestidade do score.

## D005 — Ranking de pessoas recusado no código, não só desencorajado

**Decisão:** `build_ranking` levanta se `entity_type == "person"`.

**Razão:** dado pessoal é L4 pelo `RELEASE_PROTOCOL.md` — exige DPIA humana.
Uma regra que depende de disciplina será violada; uma que levanta, não.

**Reverteria:** DPIA concluída, base legal mapeada, aprovação de DPO/jurídico —
e mesmo assim o gate continuaria, só mudaria de lugar.

## D006 — Letras A+++…A exigem cobertura, não só score

**Decisão:** a rubrica corta por score **e** por número de componentes medidos.

**Razão:** uma entidade com 0,95 medido sobre 2 de 7 componentes não é excelente
— é pouco medida. Rotular só pelo número transformaria a rubrica em numerologia.

**Reverteria:** nada; se a rubrica mudar, muda `methodology_version` junto.

## D007 — Crosswalk de vendas nasce vazio em vez de estimado

**Decisão:** `sales_data_crosswalk.json` em `pending_licensed_source` com
`mappings: []`, travado por teste.

**Razão:** derivar volume de vendas de nota do Goodreads, número de resenhas ou
interesse de busca é proxy vendido como medição. O slot vazio e honesto é mais
útil que um número inventado — e diz exatamente o que o destravaria.

**Reverteria:** fonte licenciada (Circana/Nielsen) ou divulgação oficial.

## D008 — Comunidades entram como fontes, pessoas nunca

**Decisão:** `communities.json` registra fóruns com URL oficial e escopo; grupos
fechados de WhatsApp/Telegram ficam de fora, com o motivo escrito.

**Razão:** indexar um fórum público é registrar uma fonte; coletar mensagens de
membros é perfilar pessoas. A linha é clara e o teste a trava (nenhuma chave com
`follower`, `engagement` ou `sentiment` pode existir no registro).

**Reverteria:** nada.
