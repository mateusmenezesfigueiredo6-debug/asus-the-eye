# Perguntas de pesquisa

Toda conclusão material registra: pergunta, classificação da alegação, evidência
primária, melhor evidência contrária, justificativa, confiança, limitações, e o
que mudaria a conclusão (`AGENTS.md:11-20`).

Classes: `FACT` · `DERIVED` · `INFERENCE` · `RECOMMENDATION` · `UNKNOWN` ·
`CONFLICTED` · `BLOCKED`.

---

## Q001 — Existe fonte gratuita e legítima para volume de vendas de livros por nicho?

- **Classe:** `FACT` (negativa)
- **Evidência primária:** documentação da Open Library declara explicitamente não
  ser infraestrutura comercial e não fornecer dado de vendas nem ranking;
  Circana BookScan e Nielsen BookData são produtos licenciados e pagos.
- **Melhor evidência contrária:** listas públicas de mais vendidos (NYT, jornais)
  existem — mas são rankings editoriais sem volume absoluto, e derivar volume
  delas seria inferência.
- **Justificativa:** volume de vendas é o produto comercial dessas empresas; não
  há incentivo nem obrigação de publicá-lo gratuitamente.
- **Confiança:** alta
- **Limitações:** não verificamos todo provedor regional existente.
- **O que mudaria:** assinatura licenciada, ou divulgação oficial de editora com
  proveniência hasheada.
- **Consequência:** `data/source-graph/sales_data_crosswalk.json` fica em
  `pending_licensed_source` com `mappings: []`, travado por teste.

## Q002 — Os algoritmos de recomendação de Instagram/Meta/X/TikTok são obteníveis?

- **Classe:** `FACT` (negativa)
- **Evidência primária:** nenhuma dessas empresas publica o algoritmo de
  ranqueamento em produção.
- **Melhor evidência contrária:** existem (a) papers de engenharia dessas
  empresas e (b) divulgações obrigatórias do art. 40 do DSA europeu.
- **Justificativa:** o algoritmo é ativo competitivo e vetor de manipulação;
  publicá-lo seria contra o interesse da plataforma e contra a integridade dela.
- **Confiança:** alta
- **Limitações:** vazamentos e engenharia reversa parcial existem, mas seriam
  INFERENCE vestida de FACT — e a coleta violaria ToS.
- **O que mudaria:** obrigação regulatória de publicação integral.
- **Consequência:** redefinido como "indexar as publicações e divulgações".

## Q003 — OpenAlex ainda é gratuito para uso programático?

- **Classe:** `FACT`
- **Evidência primária:** desde fev/2026 a API exige chave e cobra por uso, com
  franquia de US$1/dia; o dump CC0 completo continua gratuito via S3, sem chave.
- **Melhor evidência contrária:** a franquia diária cobre uso pequeno.
- **Justificativa:** custo por chamada, ainda que baixo, é custo — e o
  `AGENTS.md` lista "create costs" entre as proibições.
- **Confiança:** alta
- **Limitações:** preços podem mudar; a verificação tem data.
- **O que mudaria:** retorno ao modelo gratuito, ou decisão explícita do dono
  sobre orçamento.
- **Consequência:** conector `openalex` com `requires_key: true` e `enabled:
  false`; teste trava. Caminho correto é o dump, no Estágio 2.

## Q004 — Análise de microexpressões faciais e tom de voz é permitida neste projeto?

- **Classe:** `FACT` (negativa)
- **Evidência primária:** `MISSION:464-466` bloqueia explicitamente perfilamento
  biométrico e psicológico; `AGENTS.md:136-140` repete a lista. LGPD art. 5º, II
  classifica dado biométrico como sensível.
- **Melhor evidência contrária:** as proibições da missão estão textualmente no
  escopo de *adjudicadores*, não da plataforma inteira.
- **Justificativa:** a leitura restritiva seria formalista — o espírito da regra
  e a LGPD alcançam qualquer pessoa, não só juízes. E a base legal para
  biometria exige consentimento específico que este projeto não tem.
- **Confiança:** alta
- **Limitações:** a lacuna textual é real e merece emenda explícita na missão.
- **O que mudaria:** consentimento específico documentado + DPIA + base legal
  mapeada, por profissional humano.
- **Consequência:** fora de escopo. `PROHIBITED_FRAGMENTS` bloqueia os nomes de
  campo correspondentes em todo schema.

## Q005 — Qual o intervalo mínimo educado entre requisições?

- **Classe:** `DERIVED`
- **Evidência primária:** arXiv exige 1 requisição a cada 3 s com 1 conexão — o
  mais estrito do conjunto verificado; Crossref público permite 5 req/s por DOI
  e 1 req/s para listas (limites revisados em 01/12/2025); Open Library, 1 req/s
  anônimo.
- **Melhor evidência contrária:** usar 3 s para todos desperdiça capacidade onde
  o host permite mais.
- **Justificativa:** o custo de ser lento demais é tempo; o de ser rápido demais
  é bloqueio e má cidadania. Errar para o lado educado.
- **Confiança:** média (limites mudam)
- **Limitações:** verificado em 2026-08-02; vários mudaram recentemente.
- **O que mudaria:** publicação de novos limites pelos provedores.
- **Consequência:** `default_min_interval_seconds: 3.0`, sobrescritível por
  conector com o valor que os termos daquele host permitem.

## Q006 — [ABERTA] Como conciliar identificação educada com não-rastreabilidade?

- **Classe:** `CONFLICTED`
- **Tensão:** Crossref polite pool pede `mailto`; SEC EDGAR **exige** User-Agent
  com contato; Open Library exige contato. O `AGENTS.md` manda respeitar
  "source attribution" e não burlar controle de acesso. Ao mesmo tempo, o dono
  do projeto levantou preocupação com rastreamento das interações.
- **Terceiro caminho identificado:** **dumps em massa** — uma requisição em vez
  de milhares. Mais privado *e* mais educado ao mesmo tempo.
- **Confiança:** —
- **O que resolveria:** decisão do dono sobre modelo de ameaça (§ ver
  `UNKNOWNS.md`), e escolha entre e-mail genérico de projeto, só fontes que não
  exigem contato, ou só dumps.
- **Status:** **não bloqueia o Estágio 1**, que é inteiramente offline. Decidir
  antes do primeiro fetch real.
