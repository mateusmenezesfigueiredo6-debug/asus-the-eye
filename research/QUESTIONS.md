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

## Q007 — Quantos artefatos existem nos 12 recortes de medição do chart?

- **Classe:** `FACT`
- **Evidência primária:** `data/mistress-chart/projects.json` e teste T101.
- **Melhor evidência contrária:** presença no disco não prova conteúdo correto,
  cobertura de teste ou operação.
- **Justificativa:** a pergunta mede existência literal, conforme definido pelo
  próprio chart; 103 de 106 caminhos existem.
- **Confiança:** alta.
- **Limitações:** snapshot local de 2026-08-05.
- **O que mudaria:** criação, remoção ou renomeação de um artefato declarado.

## Q008 — Qual projeto não recebe trabalho há mais tempo?

- **Classe:** `DERIVED`.
- **Evidência primária:** `git log --since=2026-07-30 --name-only`, último
  commit por escopo e `mtime` dos artefatos (T102).
- **Melhor evidência contrária:** o corte antecede o primeiro commit disponível e
  o commit estrutural de 03/08 tocou vários projetos sem avanço de domínio.
- **Justificativa:** `public-verifier` não tem arquivo nem commit; entre projetos
  existentes, `benchmark-engine` tem a mudança substantiva mais antiga (01/08).
- **Confiança:** alta para ausência; média para a leitura de estagnação.
- **Limitações:** `mtime` não demonstra autoria e não há baseline em 30/07.
- **O que mudaria:** histórico anterior, snapshot externo ou novo commit de
  domínio.

## Q009 — Qual seria o custo mensurável de segmentar de 15 para 145 nichos?

- **Classe:** `DERIVED` para cardinalidades; `UNKNOWN` para regex, pessoas e
  fontes.
- **Evidência primária:** taxonomia com 145 áreas/22 grupos; configuração com 15
  nichos referenciando 39 áreas; ontologia com 8 regex, 3 bloqueios físicos e 4
  modos genéricos (T103). A coleta salva do Querido Diário contém sinal em
  138/145 áreas, 7 sem contagem e 6 termos suspeitos (T105).
- **Melhor evidência contrária:** THE EYE é uma plataforma única e não tem meta
  atual de 145 produtos; a taxonomia pode ser exposta por menos nichos
  agregadores. Nomes das áreas não classificam a parte nem a fonte.
- **Justificativa:** se essa segmentação for escolhida, configuração um-a-um pede
  +130 linhas e cobertura agregada pede relações para 106 áreas ainda não
  ligadas ao recorte. As outras contagens dependem de matriz inexistente.
- **Confiança:** alta nas cardinalidades; alta em classificar os demais totais
  como `UNKNOWN`.
- **Limitações:** não houve pesquisa de fontes alternativas por área nem corpus
  rotulado; o snapshot 138/145 foi lido, não reexecutado, por esta análise.
- **O que mudaria:** decisão do dono de segmentar, seguida de matriz
  área→produto→tipo de parte→fonte→padrão revisada e testada.

## Q010 — Como Palantir e Chaox devem orientar o roadmap?

- **Classe:** `RECOMMENDATION`.
- **Evidência primária:** `AGENTS.md` distingue Palantir como arquitetura e
  Chaox como produto; a branch preservada `chaox-20260725` existe e contém
  ciclo de mercado/resolução em modo somente-leitura e dinheiro desligado.
- **Melhor evidência contrária:** transpor código legado diretamente criaria um
  subsistema paralelo; qualquer liquidez real traz requisitos regulatórios e
  externos.
- **Justificativa:** manter uma ontologia e uma cadeia de eventos. Palantir exige
  a linhagem transversal dessa plataforma única; Chaox orienta atributos e
  comportamento de produto nas mesmas claims: preço, resolução e liquidez
  mensurada.
- **Confiança:** média-alta.
- **Limitações:** recomendação arquitetural; nenhum código foi transplantado nem
  houve operação externa.
- **O que mudaria:** decisão do dono, revisão legal, teste ponta a ponta ou nova
  evidência de produto.

## Q011 — A QKP da taxonomia está correta e justifica uma execução quântica?

- **Classe:** `FACT` para o ótimo da formulação; `RECOMMENDATION` para não usar
  QPU; `UNKNOWN` para utilidade comercial.
- **Evidência primária:** snapshot de 145 áreas, formulação salva com 138
  variáveis e referência por recozimento; verificador exato independente por
  programação dinâmica entre grupos (C107–C110, T107).
- **Melhor evidência contrária:** 138 variáveis parecem formar uma instância
  combinatória grande e 12 partidas independentes convergiram no mesmo valor.
- **Justificativa:** pesos unitários, capacidade efetiva 13, sinergias positivas
  apenas dentro dos 22 grupos e ausência de arestas entre grupos permitem ótimo
  exato por DP. O valor é 39.087, mas quatro termos suspeitos concentram 77,8%
  da demanda-base selecionada.
- **Confiança:** alta para a matemática e os dados salvos; baixa para valor de
  negócio.
- **Limitações:** a fonte é apenas um proxy, peso e sinergia não foram medidos e
  sete áreas não têm contagem.
- **O que mudaria:** custos observados, sinergias validadas, fontes adequadas por
  área e uma formulação cuja estrutura não admita solução clássica barata.

## Q012 — Os percentuais de QAOA relatados pelo Claude são verificáveis?

- **Classe:** `UNKNOWN` para os percentuais; `FACT` para o estado dos artefatos.
- **Evidência primária:** resposta no quadro de coordenação e inspeção do JSON de
  escalada e do código que o gera (C111, T108).
- **Melhor evidência contrária:** o commit `1f9a19c` e o quadro relatam 74,0%,
  66,3% e 60,9% para N=10, 14 e 16.
- **Justificativa:** o artefato oficial ainda registra `null` para score, tempo e
  qualidade QAOA nessas linhas. Não há comando, stdout ou novo JSON persistido
  que permita reproduzir os percentuais. O código declara simulador local.
- **Confiança:** alta sobre o estado atual dos arquivos; baixa sobre a execução
  apenas relatada.
- **Limitações:** uma execução em terminal sem log pode ter ocorrido.
- **O que mudaria:** comando exato, ambiente, saída completa e artefato com hash.

## Q013 — A superfície pública verifica provas sem revelar dados registrados?

- **Classe:** `FACT` para o código local; `UNKNOWN` para operação publicada.
- **Evidência primária:** Worker e teste de resposta sem tenant ou conteúdo
  (C112–C115, T109–T110 e T113).
- **Melhor evidência contrária:** o binding D1 é uma capacidade técnica de banco,
  não uma credencial SQL limitada a `SELECT`; a garantia de leitura está no
  código revisado e no contrato de rota.
- **Justificativa:** nenhuma rota autentica, persiste ou devolve documentos. A
  única consulta seleciona quatro hashes de âncoras confirmadas, sem campos de
  evento, lote identificador ou tenant.
- **Confiança:** alta para a implementação local.
- **Limitações:** não houve deploy, teste remoto, revisão independente ou dado
  confirmado real no D1.
- **O que mudaria:** deploy autorizado seguido de teste de integração e revisão
  das permissões/bindings no ambiente Cloudflare.

## Q014 — A implementação TypeScript preserva a semântica criptográfica local?

- **Classe:** `FACT` para os vetores e casos testados.
- **Evidência primária:** contratos Python de canonicalização, cadeia e Merkle;
  evento selado fixo e vetores Keccak/Merkle cruzados (C113–C115, T109–T111).
- **Melhor evidência contrária:** o verificador Python aceita uma lista cujo
  primeiro número seja maior que 1, enquanto a tarefa exige continuidade até a
  gênese.
- **Justificativa:** SHA-256 canônico, Keccak-256 com separação de domínio,
  ordenação de nós e ruptura de cadeia coincidiram com vetores Python. O Worker
  deliberadamente exige sequência 1 e os 64 zeros para cumprir o contrato mais
  estrito da etapa 7.
- **Confiança:** alta para os vetores cobertos.
- **Limitações:** não houve auditoria criptográfica externa nem fuzzing entre
  runtimes para todo o domínio I-JSON.
- **O que mudaria:** vetor divergente, fuzzing diferencial ou revisão externa
  que identifique incompatibilidade.
