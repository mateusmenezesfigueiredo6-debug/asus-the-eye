# Modelo de autoridade de fonte

Como o projeto decide **quanto peso** dar a uma fonte — e por quê.

## A hierarquia (AGENTS.md:37-46)

`data/source-graph/authority_tiers.json` espelha, literal e na ordem, a
hierarquia de evidências do `AGENTS.md`. Tier 1 é o mais autoritativo.

| Tier | Classe |
| --- | --- |
| 1 | constituições, leis, regulamentos, diários oficiais |
| 2 | tribunais, decisões oficiais, tabelas processuais, datasets oficiais |
| 3 | reguladores, legislaturas, ministérios, autoridades públicas |
| 4 | universidades, pesquisa revisada por pares, centros de pesquisa reconhecidos |
| 5 | instituições profissionais e diretórios jurídicos transparentes |
| 6 | imprensa especializada |
| 7 | imprensa geral |
| 8 | comentário profissional identificado |

Para trabalho **técnico**, o `AGENTS.md` define uma hierarquia própria de quatro
níveis (código do repositório e logs reproduzíveis > documentação oficial e
especificações primárias > repositórios oficiais > material secundário). O
mapeamento entre as duas está no mesmo arquivo JSON.

## O que a autoridade NÃO é

- **Não é popularidade.** Uma fonte muito citada em rede social não sobe de tier.
- **Não é tamanho.** Uma universidade grande e uma pequena estão no mesmo tier 4;
  o que as separa no score é `subarea_specialization` e `documented_impact`,
  ambos com denominador visível.
- **Não é reputação percebida.** Tier é uma classificação estrutural do *tipo* de
  fonte, não um juízo sobre a qualidade daquela fonte específica.

O `authority_tier` vale 25% do score — é o maior peso, mas é minoria. Uma fonte
tier 4 bem especializada e com impacto documentado supera uma tier 3 genérica.

## Licença: declarada, nunca deduzida

Toda entidade carrega `license` com `license_id` e `license_url`, e esses valores
vêm **exclusivamente** de `connectors.json`. Nenhuma licença é inferida de página
web. Se um conector não declara `license_id`, o `PoliteFetcher` **recusa nascer**
— não existe caminho de código que produza uma entidade com licença adivinhada.

## Proveniência: hash ou nada

Toda entidade exige `source_manifest` com pelo menos uma entrada contendo
`official_url`, `retrieved_at` e `content_hash_sha256` (64 hex, travado por
pattern no schema). Uma afirmação sem manifesto não entra no grafo.

E o corolário do fetcher: corpo acima de `max_bytes` produz `FetchRefusal` e
**nenhum hash**. Truncar em silêncio geraria o hash de um documento parcial — uma
mentira criptografada, pior que a ausência do dado.

## Base de acesso: sempre nomeada

Cada busca grava `robots_decision`, que é um de:

- `robots_allowed` — o robots.txt do host permite;
- `no_robots_file` — o host não publica robots.txt (permitido pelo padrão, e o
  motivo fica registrado em vez de virar um "sim" anônimo);
- `api_terms:<url>` — o host é uma API cujos **termos publicados autorizam** uso
  programático, mesmo que o robots.txt proíba `/` para crawlers genéricos;
- `robots_disallowed` — recusa; nunca reintentada.

Não existe `respect_robots=False` em lugar nenhum do código. O caso legítimo das
APIs é tratado por declaração explícita da base, gravada em cada resultado **e em
cada evento do ledger** — nunca por um silêncio.

## Classes de alegação

Toda entidade e toda entrada ranqueada carrega `claim_class`:

`FACT` (publicação oficial) · `DERIVED_METRIC` (computado com denominador) ·
`INFERENCE` (marcado, com evidência contrária) · `UNKNOWN` (evidência
insuficiente) · `PROHIBITED` (recusa registrada, sem conteúdo).

Uma licença declarada mas não hasheada é `UNKNOWN`, não `FACT` — é por isso que
os 23 artefatos de software da semente estão em `verification_status:
declared_unverified` até o Estágio 2 buscar e hashear cada `LICENSE`.
