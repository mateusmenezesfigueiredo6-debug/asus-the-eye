# Proveniência — rastreio de corridas de ML (conceito de run tracking)

Registro de reuso legítimo, conforme a política de licenças do projeto.

| Campo | Valor |
| --- | --- |
| Componente do projeto | `src/asus_theye/mlops/` (rastreio + produtor do benchmark) |
| Origem estudada | MLflow — `mlflow/mlflow` (e a categoria "Databricks", que é a mantenedora) |
| Licença de origem | **Apache-2.0** — © MLflow Project / Databricks |
| Data | 2026-08-19 |

## O que foi absorvido

Os **conceitos** do MLflow Tracking e do Model Registry: uma *corrida* carrega
params, métricas e artefatos; um *registry* liga modelo → versões; a decisão de
produção é *campeão/desafiante* (stages). Do estudo veio a decisão de desenho:
rastrear execuções como registros imutáveis, nunca como estado mutável.

## O que NÃO foi copiado

Nenhuma linha de código do MLflow. A implementação usa a stdlib + o núcleo de
auditoria do próprio projeto, tem ~300 linhas e resolve só o caso do projeto.
O MLflow não entra como dependência — absorver a ideia sem herdar o runtime é
o ponto da política.

## O que o nosso faz que a origem não faz

Cada registro (modelo, versão, corrida, promoção) é **selado na cadeia
auditável** (evento de 40 campos, RFC 8785 + SHA-256, corrente por tenant) —
run tracking com prova criptográfica. A identidade da corrida é o hash
canônico do conteúdo (dedupe honesto, divergência levanta), e o store é
versionado no repo (`reports/mlops/*.jsonl`): qualquer clone confere o
histórico sem servidor. É também a materialização do esquema `ml_*` legado
(registry → versions → runs → champion/challenger), desenhado e nunca operado.

## Situação de licença

- Código do projeto: AGPL-3.0-or-later (© 2026 Mateus Menezes Figueiredo).
- Ideia estudada: Apache-2.0 — permissiva; o aviso de origem é este registro.
