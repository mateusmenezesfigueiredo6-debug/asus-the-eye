# Medição real da plataforma única pelos 12 registros do chart

Data de corte: 5 de agosto de 2026, 16:27, fuso `America/Sao_Paulo`.

Commit observado no corte: `26ebc79`.

Unidade medida: artefato listado em `data/mistress-chart/projects.json`.

Critério: um artefato conta somente quando `Path(artefato).exists()` é verdadeiro

THE EYE é **uma plataforma, um pipeline, um modelo de dados e uma cadeia de
evidência**. Os 12 “projetos” são divisões do registro para medir intenção contra
artefatos; não são fronteiras arquiteturais, módulos independentes, produtos ou
serviços. O recorte comercial de 15 nichos é configuração sobre a plataforma e
não define seu escopo. A mesma plataforma pode receber filtros de mercado quando
o dono decidir, sem ser desmontada ou duplicada.

## Resumo técnico

- **FACT:** existem **103 dos 106 artefatos declarados (97,2%)**. Onze projetos
  têm 100% dos caminhos declarados; a superfície pública de verificação tem
  **0 de 3 (0,0%)**. Existência não comprova correção, teste, uso em produção ou
  promoção de fase.
- **FACT:** o repositório não possui commit em ou antes de 30 de julho de 2026;
  o primeiro commit é de 1º de agosto. Portanto, **regressão desde 30/07 é
  UNKNOWN**: não existe baseline Git naquele dia para comparar.
- **DERIVED:** pelo critério estrito de “nenhum commit em artefato declarado
  desde 30/07”, somente `public-verifier` está estagnado. Ele não tem artefato,
  commit de implementação ou `mtime`. Entre projetos com artefatos, o
  `benchmark-engine` tem a alteração substantiva mais antiga, em 1º de agosto;
  o toque posterior de 3 de agosto foi uma reorganização estrutural.
- **FACT:** no cenário hipotético de segmentar comercialmente a plataforma de
  15 para 145 nichos, a passagem não seria uma simples multiplicação de linhas.
  Os 15 nichos atuais referenciam 39 áreas distintas; **106 das 145 áreas não
  estão ligadas ao recorte comercial atual**. Criar 145 nichos um-a-um exigiria
  mais 130 configurações. Nenhuma dessas opções é o escopo padrão da plataforma:
  ambas dependem de decisão futura do dono.
- **UNKNOWN:** o repositório não permite contar honestamente quantos dos 130
  nichos novos exigiriam regex própria, cairiam na regra de pessoa física ou
  não teriam fonte pública adequada. Uma coleta concorrente tentou o mesmo
  Querido Diário para 145 áreas e guardou sinal para 138, com 7 sem contagem e 6
  termos suspeitos; isso não classifica adequação nem prova que as demais tenham
  ou não fonte equivalente. A taxonomia não contém `tipo_parte`, `fonte_id` ou
  `padrao_extracao`.

Uma tabela, e não um gráfico, é usada para a medição principal: a finalidade é
conferir valores exatos e caminhos binários; uma visualização agregada esconderia
os três artefatos ausentes.

## 103 de 106 artefatos existem

| Projeto | Etapa | Declarados | Existem | Percentual real |
|---|---:|---:|---:|---:|
| Grafo de fontes de conhecimento (`source-graph`) | 1-ingestao | 35 | 35 | 100,0% |
| Contexto decisório (`decision-context`) | 2-classificacao | 14 | 14 | 100,0% |
| Taxonomia legal (`legal-taxonomy`) | 2-classificacao | 8 | 8 | 100,0% |
| Engine de benchmark (`benchmark-engine`) | 3-processamento | 5 | 5 | 100,0% |
| LLM local auditado (`local-llm`) | 3-processamento | 3 | 3 | 100,0% |
| Adaptador IBM Quantum (`quantum-adapter`) | 3-processamento | 2 | 2 | 100,0% |
| Plataforma comercial (`comercial`) | 4-operacao | 9 | 9 | 100,0% |
| Núcleo de auditoria (`audit-core`) | 5-evidencia | 10 | 10 | 100,0% |
| Ledger em produção (`ledger-staging`) | 5-evidencia | 5 | 5 | 100,0% |
| Contrato de ancoragem (`anchor-contract`) | 6-verificacao | 4 | 4 | 100,0% |
| Governança (`governance`) | 6-verificacao | 8 | 8 | 100,0% |
| Superfície pública (`public-verifier`) | 7-publicacao | 3 | 0 | 0,0% |
| **Total** | **pipeline completo** | **106** | **103** | **97,2%** |

O percentual é `artefatos existentes / artefatos declarados`, sem peso por
tamanho ou importância. Diretórios, arquivos não declarados, status escrito em
documentação, serviços e recursos externos não entram no numerador.

## A publicação é a única etapa com ausência declarada

Os três caminhos ausentes são:

- `apps/public-verifier/worker.ts`;
- `apps/public-verifier/wrangler.toml`;
- `apps/public-verifier/README.md`.

Isso comprova ausência no disco, não autorização para criá-los ou publicar. O
território de infraestrutura/publicação pertence ao Claude e qualquer saída da
máquina continua sujeita à trava de publicação e à aprovação humana.

## Estagnação: resultado depende do critério declarado

### Critério estrito e reproduzível

“Estagnado desde 30/07” significa zero commit que toque qualquer artefato ou
caminho declarado do projeto no intervalo iniciado em 30 de julho. Nesse
critério, somente `public-verifier` está estagnado: zero commit e zero arquivo.

### Último toque e última mudança substantiva

| Projeto | Commits desde 30/07 no escopo | Último toque Git observado | `mtime` mais recente de artefato | Leitura |
|---|---:|---|---|---|
| `source-graph` | 4 | 03/08 18:46, refatoração; domínio em 03/08 03:24 | 03/08 18:46 | atividade substantiva em 03/08 |
| `decision-context` | 2 | 03/08 18:46, refatoração; domínio em 02/08 05:45 | 03/08 18:46 | sem domínio após 02/08 |
| `legal-taxonomy` | 2 | 02/08 10:54, aliases 145/145 | 02/08 08:50 | sem toque após 02/08 |
| `benchmark-engine` | 2 | 03/08 18:46, refatoração; domínio em 01/08 16:11 | 03/08 18:46 | mudança substantiva mais antiga entre os projetos existentes |
| `local-llm` | 2 | 03/08 18:46, refatoração; domínio em 02/08 06:00 | 03/08 18:46 | sem domínio após 02/08 |
| `quantum-adapter` | 2 | 03/08 18:46, refatoração; domínio em 02/08 06:13 | 03/08 18:46 | sem domínio após 02/08; nenhuma execução feita nesta medição |
| `comercial` | 21 no escopo amplo observado | 05/08, mudanças de domínio | 05/08 em arquivos fora da lista de 9 | único recorte com atividade substantiva após 03/08 |
| `audit-core` | 2 | 03/08 18:46, refatoração; domínio em 02/08 05:26 | 03/08 18:46 | sem domínio após 02/08 |
| `ledger-staging` | 7 | 03/08 18:46, refatoração; domínio em 02/08 07:00 | 03/08 18:46 | sem domínio após 02/08 |
| `anchor-contract` | 1 | 02/08 05:26, criação | 02/08 06:20 | sem toque após 02/08 |
| `governance` | 5 | 03/08 18:46, refatoração; domínio em 02/08 07:26 | 03/08 18:46 | sem domínio após 02/08 |
| `public-verifier` | 0 | nenhum | nenhum | nunca implementado no histórico observado |

O número 21 do recorte comercial usa o escopo amplo (`paths` mais
`artifacts`), porque os trabalhos de 4 e 5 de agosto estão principalmente em
arquivos novos de `apps/comercial/`, não nos nove artefatos originalmente
declarados. Os demais números também usam o escopo declarado. O commit
`1666450` tem assunto de reorganização estrutural; ele conta como toque, mas não
como evidência de avanço funcional de cada domínio.

Não é possível declarar regressão desde 30/07. `git rev-list -1
--before='2026-07-30 23:59:59 -0300' HEAD` não devolve commit; logo não há árvore
histórica de referência. O primeiro commit observado é `1cddc9a`, em 01/08 às
16:11. O que mudaria a conclusão seria um snapshot externo, tag ou histórico
anterior não presente neste repositório.

## Cenário opcional: segmentar comercialmente de 15 para 145

### A taxonomia da plataforma não é um catálogo de produtos

O estado atual é:

| Medida | Valor | Como foi obtida |
|---|---:|---|
| Áreas na taxonomia | 145 | comprimento de `areas` e `area_count` |
| Grupos | 22 | comprimento e valores distintos de `groups` |
| Nichos comerciais | 15 | comprimento de `niches` e `niche_count` |
| Áreas distintas referenciadas pelos 15 nichos | 39 | união de `legal_area_ids` |
| Áreas sem mapeamento comercial | 106 | `145 - 39` |
| Linhas de configuração adicionais para 145 nichos um-a-um | 130 | `145 - 15` |

Se o dono optar por ampliar a segmentação comercial, há dois desenhos possíveis:

1. **Segmentação agregada:** manter uma única configuração canônica de mercado e
   adicionar relações até que 145 de 145 áreas estejam mapeadas. O mínimo
   mensurável é 106 relações de área; o número de filtros comerciais é decisão
   de mercado.
2. **Segmentação um-a-um:** criar uma linha de configuração para cada área na
   mesma plataforma. Isso exige 130 linhas adicionais e uma regra canônica de
   identidade, porque as 15 atuais agrupam 39 áreas.

Esses números são uma estimativa condicional de custo, não uma recomendação para
reduzir a plataforma a nichos. Tratar “+130 nichos” e “+106 áreas ligadas” como
o mesmo custo produziria dupla contagem e perderia a relação muitos-para-muitos
já existente.

### O custo que está medido e o que permanece desconhecido

| Dimensão | Base atual medida | Gap para o alvo | Classificação |
|---|---|---|---|
| Configuração comercial | 15 linhas | +130 se o alvo for 145 filtros um-a-um | `DERIVED` |
| Relação nicho→área | 39/145 áreas ligadas ao recorte | 106 sem relação comercial, se cobertura total for desejada | `DERIVED` |
| Termo de sinal por área | aliases existem para 145; coleta salva mediu 138/145 | 7 sem contagem e 6 termos suspeitos no snapshot | `FACT` |
| Padrão customizado de entidade | 8/15 atuais | 130 linhas novas não têm padrão; quantas precisam dele é `UNKNOWN` | `UNKNOWN` |
| Modo genérico atual | 4/15 atuais | qualidade para os novos não foi avaliada | `FACT`/`UNKNOWN` |
| Bloqueio explícito por pessoa física | 3/15 atuais | 130 novos não foram classificados | `FACT`/`UNKNOWN` |
| Fonte de sinal | Querido Diário foi tentado para 145 áreas | adequação não classificada; 7 sem medida, 6 termos suspeitos | `FACT`/`UNKNOWN` |

Os oito padrões existentes são específicos ao texto e ao papel procurado; não
há evidência de que possam ser reutilizados automaticamente. Os três bloqueios
explícitos são `previdenciario`, `familia` e `sucessoes`. **Quatro** configurações
(`trabalhista`, `consumidor`, `civel-contencioso` e
`protecao-dados`) não têm regex nem bloqueio explícito e operam no modo genérico.
A partição validada é **8 com padrão + 3 bloqueados + 4 genéricos = 15**.

Assim, as respostas honestas às três contagens pedidas são:

- **Padrão de extração novo:** 130 novas configurações não possuem definição;
  **quantas exigem regex customizada é UNKNOWN**. O baseline validado é 8 de 15
  atuais com regex e 4 em modo genérico.
- **Regra de pessoa física:** 3 de 15 atuais são explicitamente bloqueadas;
  **o total entre 145 é UNKNOWN**. A taxonomia de 145 áreas só traz id, número,
  nome, grupo, status e fonte, e não autoriza inferir o tipo da parte.
- **Sem fonte pública equivalente:** **UNKNOWN**. O mesmo Querido Diário foi
  tentado para 145 áreas; o snapshot local registrou `138/145`, 7 áreas sem
  contagem e 6 termos marcados como possivelmente genéricos. Isso mede retorno
  de consulta, não equivalência ou adequação da fonte. O snapshot foi gerado às
  16:20, antes da revisão de código das 16:26, e não foi reexecutado nesta
  análise.

Nota de robustez: a contagem é por presença simultânea de `busca_lead` e
`regex_entidade`; o teste de reprodutibilidade ao final confirma os oito objetos.

### Como tornar as três contagens mensuráveis

Antes de qualquer segmentação, cada configuração candidata precisa de um registro
no mesmo modelo canônico com:

- `legal_area_ids` e cardinalidade explícita;
- `tipo_parte: juridica | fisica | nenhuma | mista | desconhecida`;
- `politica_extracao: entidade | agregado | recusado`;
- `termo_sinal`, `fonte_id`, jurisdição, cobertura temporal e licença;
- `padrao_extracao_id`, corpus de teste, precisão, revocação e taxa de ruído;
- fonte de resolução objetiva, quando o objeto gerar um mercado;
- status `UNKNOWN` enquanto qualquer campo obrigatório não tiver evidência.

Somente depois dessa matriz é legítimo somar regex novas, bloqueios pessoais e
fontes ausentes. Até lá, “145” mede o universo taxonômico da plataforma, não uma
obrigação de criar 145 nichos nem prontidão comercial.

## Palantir volta como contrato de arquitetura

Palantir deve orientar o “como” de **uma arquitetura coerente**, não justificar
12 subsistemas. A plataforma precisa de uma ontologia canônica e de uma espinha
única de eventos versionados:

`Fonte -> Documento/Observação -> Evento -> Classificação -> Decisão/Previsão -> Evidência -> Verificação -> Publicação`

O mesmo registro canônico recebe identidade, fonte, observação, área legal,
política de privacidade, claim, probabilidade, decisão, resolução e recibo à
medida que atravessa o pipeline. Cada estágio **enriquece o mesmo fato**; não
cria uma cópia, banco, ontologia ou verdade paralela. Toda relação material
carrega origem, versão de schema, hash canônico, instante e classe da afirmação.
Nicho, mercado e chart são projeções dessa ontologia única.

Prioridades:

1. **P0 — identidade e envelope únicos:** um id canônico, um schema de evento e
   uma taxonomia relacionam fonte, classificação, operação e prova.
2. **P0 — uma só trilha de mutação:** toda mutação crítica passa pelo mesmo
   SDK/outbox; se a evidência falhar, a operação inteira falha.
3. **P0 — uma só semântica:** área jurídica é classificação universal; nicho é
   filtro comercial opcional; mercado é uma claim com preço e resolução. Nenhum
   deles cria outra plataforma.
4. **P1 — fechar fatias ponta a ponta:** evoluir casos reais do início à
   verificação pelo pipeline completo, em vez de “completar” cada linha do chart
   isoladamente.
5. **P1 — chart como visão medida:** calcular os 12 recortes sobre a mesma árvore
   de artefatos e guardar o snapshot como evento, nunca como status manual.
6. **P2 — verificação como última visão:** a superfície pública lê a mesma cadeia
   de evidência; só nasce após recibos locais e aprovação humana.

Regra anti-Frankenstein: nenhuma linha do chart ganha identidade, taxonomia,
banco de verdade, cadeia de auditoria ou roadmap próprios. Um novo nicho é dado;
um mercado é um estado de uma claim; o verificador é uma visão da mesma prova.
Se uma implementação exigir sincronizar “verdades” entre essas partes, o desenho
está errado.

## Kalshi volta como contrato de produto

A branch preservada `kalshi-20260725` foi confirmada, sem alteração, em
`/home/sexexes/asus`. Seu commit de ponta observado é `fe5d93e` (28/07), cujo
assunto declara conector a mercados abertos com dinheiro desligado. Ela é
referência histórica de produto, não um pacote a ser enxertado. Nada deve ser
copiado ou integrado como um subsistema Kalshi. Os princípios observados em
somente-leitura — pergunta imutável, cotações append-only, `EM_RESOLUCAO`, fonte
oficial, Brier realizado e trava financeira — devem ser expressos no mesmo
modelo e na mesma cadeia de eventos da THE EYE.

Kalshi deve orientar o “o quê”:

1. **P0 — claim que pode virar mercado:** uma claim já existente na plataforma
   recebe pergunta binária inequívoca, data-limite, probabilidade, critério e
   fonte oficial de resolução; não nasce outro produto técnico.
2. **P0 — resolução objetiva:** estados `ABERTO -> EM_RESOLUCAO -> LIQUIDADO`;
   ausência da publicação oficial mantém o estado intermediário em vez de
   inventar resultado.
3. **P1 — preço e qualidade na mesma evidência:** probabilidade e suas revisões
   são novos eventos ligados à claim; baseline, Brier e cobertura usam a mesma
   resolução. Sem evento resolvido, desempenho é `UNKNOWN`.
4. **P1 — liquidez mensurável:** começar em modo papel/leitura com spread,
   profundidade, atualização e cobertura somente quando esses dados existirem.
   Não chamar atividade, volume de menções ou número de previsões de liquidez.
5. **P2 — comparação externa como fonte:** se usada, Kalshi entra no registro de
   fontes da plataforma e no mesmo placar de eventos resolvidos; nenhuma camada
   paralela e nenhuma alegação de superar sem amostra e denominador.
6. **Bloqueado sem nova autoridade:** ordens, dinheiro, custos, transmissão ou
   qualquer escrita externa. Preservar a branch não autoriza operar nem publicar.

O benchmark técnico clássico/QUBO/QAOA permanece subordinado: pode selecionar
ou medir um método para produzir probabilidades, mas não define a ontologia
(Palantir) nem o produto de mercado (Kalshi). Nenhuma rotina quântica foi
executada nesta medição.

## Limitações e verificações contrárias

- Existência é a métrica solicitada e pode premiar um arquivo vazio ou obsoleto.
  Testes e conteúdo não foram usados para aumentar o percentual.
- `mtime` é metadado do filesystem e pode mudar por cópia ou checkout. O Git é a
  fonte preferida para autoria; os dois foram mostrados porque a tarefa exige
  ambos.
- O commit estrutural de 03/08 tocou muitos projetos. Contá-lo como avanço
  funcional favoreceria artificialmente os projetos sem trabalho de domínio.
- A plataforma comercial recebeu commits concorrentes durante esta medição.
  Por isso a data e o escopo estão fixados e arquivos do Claude não integram a
  entrega.
- O arquivo local `reports/commercial/sinal_taxonomia.json` é evidência de uma
  corrida anterior à versão `26ebc79`: 138 áreas com contagem, 7 sem contagem e
  6 termos suspeitos. A versão nova não foi executada, e o resultado antigo não
  prova cobertura semântica nem qualidade da fonte.
- O corte de 30/07 antecede o primeiro commit disponível; regressão requer um
  baseline externo.
- Nenhuma pesquisa externa por 145 fontes foi realizada. O número de áreas sem
  fonte equivalente permanece `UNKNOWN`, como exige a política de evidência.

## Próximos passos recomendados

1. Manter um único roadmap ponta a ponta, regido pelo fluxo
   fonte→classificação→processamento→operação→evidência→verificação→publicação.
   As 12 linhas do chart medem lacunas; não viram 12 roadmaps.
2. Fechar primeiro uma capacidade inteira sobre a ontologia, o id e a cadeia de
   eventos canônicos, evitando soluções locais por linha do chart.
3. Se o dono optar por ampliar a segmentação comercial, escolher entre relações
   agregadas e 145 nichos um-a-um e então criar a matriz de prontidão com revisão
   humana de privacidade.
4. Nesse cenário opcional, pedir ao Claude, em seu território, um corpus rotulado
   e testes por padrão de extração; medir precisão, revocação e ruído antes de
   promover um nicho.
5. Expressar preço e resolução como campos/eventos da claim canônica, usando a
   branch Kalshi apenas como referência preservada, sem migrar um módulo.
6. Tratar `public-verifier` como a visão final da mesma plataforma e da mesma
   cadeia, sem confundir criação local com autorização para publicar.

## Questões que permanecem abertas

- Se e quando a plataforma for segmentada para novos mercados, quantos produtos
  agregadores são comercialmente úteis? Não há meta atual de 145 produtos.
- Qual definição operacional de “fonte pública equivalente” será usada:
  corpus pesquisável, API sem chave, cobertura nacional, dado primário ou
  capacidade de resolução objetiva?
- Quem aprova `tipo_parte` e a base legal de cada área mista?
- Qual amostra mínima e limiar de qualidade promovem um padrão de extração?
- Qual conjunto inicial de claims deve receber preço e resolução objetiva para
  validar a experiência inspirada em Kalshi dentro do pipeline único?

## Registro das conclusões materiais

| Questão | Classe | Evidência primária | Melhor evidência contrária | Justificativa | Confiança | Limitações | O que mudaria |
|---|---|---|---|---|---|---|---|
| Quantos artefatos existem? | `FACT` | chart + `Path.exists`: 103/106 | existência não prova qualidade | métrica literal pedida | alta | snapshot local | arquivo criado/removido |
| Qual projeto está mais estagnado? | `DERIVED` | Git, `mtime`, zero arquivos do `public-verifier` | cutoff anterior ao primeiro commit | zero evidência supera simples data antiga | alta para ausência; média para “estagnado” | sem baseline 30/07 | histórico ou artefato anterior |
| Houve regressão desde 30/07? | `UNKNOWN` | nenhum commit antes do cutoff | pode existir snapshot fora do repo | comparação exige dois estados | alta | só este repositório | snapshot anterior |
| Qual o custo do cenário comercial? | `DERIVED` | 145 áreas, 15 nichos, união de 39 ids | a plataforma não exige 145 produtos | reporta dois denominadores condicionais | alta | não mede esforço humano | decisão futura de segmentação |
| Quantas regex/pessoas/fontes faltam? | `UNKNOWN` | campos ausentes na taxonomia | nomes das áreas permitem palpites | nome não substitui classificação e fonte validada | alta | matriz não existe | matriz revisada e testada |
| Como Palantir orienta? | `RECOMMENDATION` | regra de arquitetura e ontologia atual | custo de uma semântica transversal | unifica linhagem e claims no pipeline | média-alta | arquitetura proposta, não implementada | teste ponta a ponta mostrar desenho inadequado |
| Como Kalshi orienta? | `RECOMMENDATION` | regra de produto + branch preservada inspecionada | liquidez real implica regulação e dados | incorpora preço e resolução à claim canônica sem subsistema paralelo | média-alta | nenhuma operação executada | decisão do dono, revisão legal e evidência de produto |

## Método reproduzível

Comandos executados, todos somente-leitura salvo a criação deste relatório e dos
registros de pesquisa:

```bash
python3 -c "import json; d=json.load(open('data/mistress-chart/projects.json'))"
git log --since=2026-07-30 --name-only --format='COMMIT %H %cI'
git rev-list -1 --before='2026-07-30 23:59:59 -0300' HEAD
git log --reverse --format='%cI|%H|%s'
git -C /home/sexexes/asus branch --list kalshi-20260725
git -C /home/sexexes/asus log -1 --format='%H|%cI|%s' kalshi-20260725
```

Para repetir a existência e os denominadores:

```bash
python3 - <<'PY'
import json
from pathlib import Path

chart = json.load(open("data/mistress-chart/projects.json"))
for project in sorted(chart["projects"], key=lambda p: p["pipeline_order"]):
    existing = sum(Path(path).exists() for path in project["artifacts"])
    declared = len(project["artifacts"])
    print(project["project_id"], project["pipeline_stage"], declared,
          existing, round(100 * existing / declared, 1))

taxonomy = json.load(open("data/legal-taxonomy/legal_areas.master.json"))
niches = json.load(open("data/commercial/niches.json"))["niches"]
ontology = json.load(open("apps/comercial/ontologia.json"))["nichos"]
covered = {area for niche in niches for area in niche["legal_area_ids"]}
print(len(taxonomy["areas"]), len(taxonomy["groups"]), len(niches),
      len(covered), len({a["legal_area_id"] for a in taxonomy["areas"]} - covered))
custom = [n for n in ontology if n.get("busca_lead") and n.get("regex_entidade")]
physical = [n for n in ontology if n.get("tipo_parte") == "fisica"]
generic = [n for n in ontology
           if not n.get("regex_entidade") and n.get("tipo_parte") != "fisica"]
print(len(custom), len(physical), len(generic))
PY
```

## Inventário individual dos 106 artefatos

### `source-graph` — 35/35

- [x] `data/source-graph/knowledge-source.schema.json`
- [x] `data/source-graph/ranking-entry.schema.json`
- [x] `data/source-graph/ranking-list.schema.json`
- [x] `data/source-graph/discovery-query.schema.json`
- [x] `data/source-graph/coverage-report.schema.json`
- [x] `data/source-graph/source_categories.json`
- [x] `data/source-graph/authority_tiers.json`
- [x] `data/source-graph/connectors.json`
- [x] `data/source-graph/ranking_weights.json`
- [x] `data/source-graph/sales_data_crosswalk.json`
- [x] `data/source-graph/software_artifacts.json`
- [x] `data/source-graph/communities.json`
- [x] `src/asus_theye/net/http.py`
- [x] `src/asus_theye/source_graph/fetcher.py`
- [x] `src/asus_theye/source_graph/robots.py`
- [x] `src/asus_theye/source_graph/scoring.py`
- [x] `src/asus_theye/source_graph/events.py`
- [x] `src/asus_theye/source_graph/coverage.py`
- [x] `src/asus_theye/source_graph/report.py`
- [x] `docs/legal-intelligence/RANKING_METHODOLOGY.md`
- [x] `docs/legal-intelligence/SOURCE_AUTHORITY_MODEL.md`
- [x] `docs/legal-intelligence/LEGAL_SOURCE_GRAPH.md`
- [x] `docs/adr/ADR-011-SOURCE-GRAPH-FETCH.md`
- [x] `reports/LEGAL_SOURCE_COVERAGE.md`
- [x] `reports/SOURCE_GAPS.md`
- [x] `reports/RANKING_LIMITATIONS.md`
- [x] `research/QUESTIONS.md`
- [x] `research/SOURCES.jsonl`
- [x] `research/DECISIONS.md`
- [x] `research/UNKNOWNS.md`
- [x] `tests/source_graph/test_source_graph_schemas.py`
- [x] `tests/source_graph/test_registries.py`
- [x] `tests/source_graph/test_fetcher.py`
- [x] `tests/source_graph/test_scoring.py`
- [x] `tests/source_graph/test_events.py`

### `decision-context` — 14/14

- [x] `data/decision-context/decision-makers.schema.json`
- [x] `data/decision-context/decision-bodies.schema.json`
- [x] `data/decision-context/assignment-rules.schema.json`
- [x] `data/decision-context/public-decisions.schema.json`
- [x] `data/decision-context/jurisprudential-patterns.schema.json`
- [x] `data/decision-context/panel-dynamics.schema.json`
- [x] `data/decision-context/conflict-alerts.schema.json`
- [x] `data/decision-context/institutional-context.schema.json`
- [x] `data/decision-context/metrics.schema.json`
- [x] `data/decision-context/data-protection.schema.json`
- [x] `src/asus_theye/decision_context/extractor.py`
- [x] `src/asus_theye/decision_context/legal_areas.py`
- [x] `docs/security/DECISION_CONTEXT_LGPD.md`
- [x] `tests/decision_context/test_schemas.py`

### `legal-taxonomy` — 8/8

- [x] `data/legal-taxonomy/legal_areas.master.json`
- [x] `data/legal-taxonomy/legal_areas.master.yaml`
- [x] `data/legal-taxonomy/legal_area_aliases.json`
- [x] `data/legal-taxonomy/legal_area_relationships.json`
- [x] `data/legal-taxonomy/cnj_crosswalk.json`
- [x] `data/legal-taxonomy/international_crosswalk.json`
- [x] `docs/legal-intelligence/LEGAL_TAXONOMY.md`
- [x] `docs/legal-intelligence/TAXONOMY_METHODOLOGY.md`

### `benchmark-engine` — 5/5

- [x] `src/asus_theye/benchmark/runner.py`
- [x] `src/asus_theye/benchmark/qaoa_benchmark.py`
- [x] `src/asus_theye/problem.py`
- [x] `tests/test_benchmark.py`
- [x] `docs/BENCHMARK_ENGINE.md`

### `local-llm` — 3/3

- [x] `src/asus_theye/llm/ollama_client.py`
- [x] `src/asus_theye/llm/audited.py`
- [x] `tests/llm/test_audited_llm.py`

### `quantum-adapter` — 2/2

- [x] `src/asus_theye/benchmark/ibm_backend.py`
- [x] `tests/benchmark/test_ibm_backend_gate.py`

### `comercial` — 9/9

- [x] `data/commercial/niches.json`
- [x] `data/commercial/opportunity.schema.json`
- [x] `data/commercial/niche-metrics.schema.json`
- [x] `src/asus_theye/commercial/niches.py`
- [x] `src/asus_theye/commercial/pipeline.py`
- [x] `src/asus_theye/commercial/metrics.py`
- [x] `apps/comercial/api.py`
- [x] `apps/comercial/static/index.html`
- [x] `tests/commercial/test_commercial.py`

### `audit-core` — 10/10

- [x] `src/asus_theye/audit/canonical.py`
- [x] `src/asus_theye/audit/keccak.py`
- [x] `src/asus_theye/audit/merkle.py`
- [x] `src/asus_theye/audit/manifest.py`
- [x] `src/asus_theye/audit/schema.py`
- [x] `src/asus_theye/audit/sdk.py`
- [x] `src/asus_theye/audit/verifier.py`
- [x] `src/asus_theye/audit/batching.py`
- [x] `migrations/0001_audit_ledger.sql`
- [x] `tests/audit/test_audit_core.py`

### `ledger-staging` — 5/5

- [x] `infra/cloudflare/staging/worker.ts`
- [x] `infra/cloudflare/staging/wrangler.toml`
- [x] `infra/cloudflare/STAGING_PROVISIONING.md`
- [x] `apps/verifier/app.py`
- [x] `tests/apps/test_verifier_app.py`

### `anchor-contract` — 4/4

- [x] `contracts/audit-anchor/src/TheEyeAuditAnchor.sol`
- [x] `contracts/audit-anchor/test/TheEyeAuditAnchor.t.sol`
- [x] `contracts/audit-anchor/foundry.toml`
- [x] `contracts/audit-anchor/README.md`

### `governance` — 8/8

- [x] `docs/governance/RELEASE_PROTOCOL.md`
- [x] `scripts/publish_lock.py`
- [x] `scripts/publish_guard.py`
- [x] `scripts/release_check.py`
- [x] `scripts/leak_check.py`
- [x] `scripts/policy_gate.py`
- [x] `docs/security/LEAK_CHECK.md`
- [x] `tests/scripts/test_publish_guard.py`

### `public-verifier` — 0/3

- [ ] `apps/public-verifier/worker.ts` — não existe
- [ ] `apps/public-verifier/wrangler.toml` — não existe
- [ ] `apps/public-verifier/README.md` — não existe
