# Metodologia de ranking (Phase C)

`methodology_version: 1.0.0` — versionada junto com `data/source-graph/ranking_weights.json`.
Qualquer mudança de peso, de componente ou de corte exige bump de versão, e o
número aparece em toda entrada ranqueada.

## O que é ranqueado — e o que não é

Ranqueamos **instituições, periódicos, repositórios, datasets, APIs, observatórios,
associações, conferências, veículos, obras, artefatos de software e comunidades**.

**Não ranqueamos pessoas.** Acadêmicos, praticantes, árbitros e autoridades são
dado pessoal: pelo `RELEASE_PROTOCOL.md` isso é L4 e exige DPIA concluída por
profissional humano. O schema prevê `entity_type: "person"` para o futuro; o
pipeline (`scoring.build_ranking`) **levanta** se alguém tentar.

E a regra da própria missão: *"do not rank people primarily by social-media
followers"*. Aqui ela é mais forte que uma recomendação — nenhum componente de
score aceita métrica social, e `component_id` é enum fechado: passar
`follower_count` levanta na validação em vez de ser silenciosamente ignorado.

## Componentes do score

| `component_id` | Peso | Como se calcula | Fonte |
| --- | --- | --- | --- |
| `authority_tier` | 0,25 | `(9 - tier) / 8`, tier de `authority_tiers.json` | classe institucional declarada (FACT) |
| `subarea_specialization` | 0,20 | registros que casam o nicho ÷ total recuperado — **denominador sempre gravado** | Crossref |
| `documented_impact` | 0,20 | citações normalizadas por percentil do conjunto recuperado | Crossref. **Nunca seguidores, curtidas ou alcance** |
| `recency_continuity` | 0,10 | função decrescente de anos desde a produção datada mais recente | datas dos registros |
| `methodology_transparency` | 0,10 | publica metodologia própria / é revisada por pares / é OA verificável | DOAJ |
| `structured_data_accessibility` | 0,10 | oferece API ou dump com licença declarada | `connectors.json` |
| `jurisdictional_relevance` | 0,05 | país/ROR casa a jurisdição pedida | ROR |

Soma dos pesos: **1,0** (travado por teste).

## As três regras que impedem o score de mentir

### 1. Sem imputação

Componente sem dado é **omitido**, nunca zerado. Zerar é uma inferência
disfarçada de medição: dizer "impacto documentado = 0" afirma que não há impacto,
quando o que houve foi ausência de dado. O componente omitido vira uma linha em
`limitations`, nomeando qual e com que peso.

### 2. Denominador visível

O score é média ponderada **só sobre os componentes presentes**, e
`components_present` / `components_declared` viajam junto. Um score de 3-de-7
nunca pode ser lido como comparável a um de 7-de-7 — e a `confidence` degrada
junto: cobertura total = `high`, ≥70% = `medium`, ≥40% = `low`, abaixo disso =
`insufficient`.

### 3. Sem preenchimento

`build_ranking` devolve o que existe. Se há 7 candidatos qualificados e o alvo
era 100, a lista tem 7 entradas, `qualified_count: 7` e `padded: false` — e o
schema **não tem como representar** uma lista preenchida artificialmente.

> Uma lista de 23 periódicos verificados vale mais que 200 linhas preenchidas.

## A rubrica A+++ … A

As letras só existem como **tabela de corte versionada**. Sem isso, "rating A+++"
é numerologia com aparência de rigor.

| Rótulo | Score | Cobertura mínima de componentes | Confiança mínima |
| --- | --- | --- | --- |
| **A+++** | ≥ 0,90 | 7 de 7 | high |
| **A++** | ≥ 0,80 | ≥ 6 de 7 | high |
| **A+** | ≥ 0,70 | ≥ 5 de 7 | medium |
| **A** | ≥ 0,60 | ≥ 4 de 7 | medium |
| *sem rótulo* | qualquer | < 4 de 7 | — |

Repare na segunda coluna: **um score alto com cobertura baixa não recebe letra**.
Uma entidade com 0,95 medido sobre 2 componentes não é A+++ — é uma entidade
pouco medida. A letra atesta score *e* completude da medição, nunca só o número.

Toda entrada rotulada carrega `methodology_version`, `cut_off_date`,
`validation_date`, `limitations`, `conflicts_of_interest` e
`human_review.status` — os campos que a Phase C exige sem exceção.

## Separação de listas

A Phase C exige separar `global`, `brazil`, `jurisdictional`, `academic`,
`professional`, `institutional`, `emerging` e `period_specific`. Isso é
`list_scope` no schema. E `entity_type` é **único por lista**: não se mistura
periódico com universidade, nem instituição com conferência.

## O que muda esta metodologia

Um componente novo, um peso diferente, um corte de letra alterado, ou uma fonte
de dado trocada. Qualquer um deles exige bump de `methodology_version` — e
scores de versões diferentes não são comparáveis entre si.
