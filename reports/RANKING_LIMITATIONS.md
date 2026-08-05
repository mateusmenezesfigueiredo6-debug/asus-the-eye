# Limitações do ranking

Gerado em 2026-08-05 · metodologia 1.0.0 · snapshot `3c7da12fdcb10c60…`

O que os números desta plataforma **não** significam.

## Estruturais

- **Componente ausente é omitido, nunca zerado.** Um score de 3-de-7
  componentes não é comparável a um de 7-de-7; `components_present` e
  `components_declared` viajam junto de todo score exatamente por isso.
- **Listas não são preenchidas.** `qualified_count` é o real e `padded` é
  sempre `false` — o schema não tem como representar o contrário.
- **Pessoas não são ranqueadas.** É L4 e exige DPIA humana; o pipeline
  levanta se alguém tentar.
- **Nenhuma métrica social entra no score.** `component_id` é enum
  fechado: `follower_count` levanta em vez de ser ignorado.

## De cobertura

- Nenhuma busca foi executada ainda: todos os 19
  contadores de categoria estão em zero por `not_yet_attempted`, não por
  ausência de entidades no mundo.
- As licenças dos artefatos de software são as **declaradas** pelos
  projetos, não verificadas com hash — todos em `declared_unverified`.

## De fonte

- Volume de vendas de livros e tamanho de mercado por nicho exigem fonte
  licenciada. Derivar de nota, resenha ou interesse de busca seria proxy
  vendido como medição.
- Algoritmos proprietários de recomendação não são públicos. O que se
  indexa são as publicações das empresas e as divulgações obrigatórias.
- Contagem de citações do Crossref é parcial; do OpenAlex, hoje paga.
