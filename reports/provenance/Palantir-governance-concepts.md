# Proveniência — conceitos de governança (leitura de whitepapers)

Registro de absorção de **conceito**. Os documentos foram **lidos**, os conceitos
**interpretados**, e as implementações neste repositório são **independentes**.
Nenhuma linha de código, nenhum trecho de texto e nenhum dado foi copiado.

## O que foi lido

| id | documento | ano | onde |
|---|---|---|---|
| P-A | *Palantir Privacy and Governance Whitepaper* (25 páginas) | 2024 | `palantir.com/assets/...Palantir_Privacy_and_Governance_Whitepaper.pdf` |
| P-B | *Foundry Technical Overview* (7 páginas) | 2022 | `palantir.com/assets/...Whitepaper_-_Foundry_2022.pdf` |
| P-Doc | Documentação pública de integração de dados | vivo | `palantir.com/docs/foundry/data-integration/overview/` |

Lidos em 20/08/2026. Material **proprietário de terceiro**.

Consultados e **descartados por estarem fora do escopo**: *Foundry Streaming*
(2023), *Foundry for Industry 4.0* (2022), *Accelerating R&D in the
Semiconductor Industry* — todos tratam de domínios ou arquiteturas que este
projeto não tem.

## Os seis princípios de P-A, e onde estamos em cada um

| princípio | estado aqui |
|---|---|
| Segurança e Integridade | **coberto** — corrente encadeada por hash + âncora on-chain |
| Transparência | **coberto** — verificador público responde sem token |
| Limitação de Propósito | **parcial** — `classification` existe por evento, não por campo |
| Minimização de Dados | **parcial** |
| **Retenção e Deleção** | **coberto** — `audit/redacao.py`, expurgo com recibo selado |
| **Prestação de Contas e Supervisão** | **coberto** — `audit/checkpoint.py`, este registro |

## O conceito absorvido — Checkpoints

De P-A: ação sensível exige que quem a executa **declare uma justificativa**, e
essa justificativa gera **entrada correspondente no log de auditoria**. O
mecanismo é configurável por tipo de ação e pode barrar exportação,
transformação ou acesso a campos.

**A implementação daqui, e onde ela diverge por decisão própria:**

- A justificativa é **selada na corrente ANTES do efeito**, não registrada
  depois. Selar depois deixaria uma janela em que o efeito existe sem
  justificativa — e é exatamente essa janela que alguém usaria. Selando antes,
  uma falha no meio deixa checkpoint sem efeito (inofensivo e visível), nunca
  efeito sem checkpoint.
- O registro de ações sensíveis é **código**, não configuração: acrescentar uma
  ação exige um commit revisável.
- Há **mínimo de caracteres por ação**, e ele é maior para expurgar do que para
  publicar. A trava é contra o vazio e o reflexo — "ok" não é justificativa.
- O campo `human_review_status` do esquema, que existia desde o começo e nunca
  fora lido por nada, passa a ter função. Era a mesma doença que `estado` tinha
  antes de a medição validá-lo: campo que parece governança e não governa.

## O conceito absorvido — Retenção e Deleção com registro

De P-A: políticas de retenção precisam permitir **purgar com confiança e
fornecer registros da deleção**, e a deleção granular depende de entender a
linhagem para encontrar todas as cópias.

**A implementação daqui** (`audit/redacao.py`) resolve o problema de um jeito
que o documento lido não descreve, porque a arquitetura é outra: como a corrente
guarda apenas o `content_hash`, remover a linha do store apaga o dado **sem
tocar em nenhum hash**. O encadeamento permanece íntegro e a âncora on-chain
continua válida. O recibo guarda o **hash do que saiu**, provando a identidade
do material sem manter cópia dele.

## O conceito lido e AINDA NÃO absorvido

- **Job Spec / provenância total do build** (P-B): cada derivação sabe qual
  código e quais parâmetros a produziram. Temos `build_version`; falta amarrar
  commit e parâmetros ao evento selado. É o item C9 do plano.
- **Data Expectations / Health Monitoring** (P-Doc): validação que aborta a
  ingestão antes de qualquer escrita, e frescor por fonte. É o item C10.
- **Marcações de segurança granulares por campo** (P-A): temos por evento.

## O que foi deliberadamente NÃO absorvido

- **A arquitetura de plataforma**: Ontology como camada semântica sobre um
  data lake, branching de datasets, Virtual Tables, compute pushdown. São
  respostas a um problema de escala empresarial que este projeto não tem, e
  importá-las traria complexidade sem necessidade.
- **Streaming, CDC e Iceberg**: mesma razão.
- **Qualquer número, exemplo ou formulação textual** dos documentos.

## Fronteira de titularidade

Os documentos são **obra de terceiro** e permanecem de titularidade de quem os
escreveu. Este arquivo registra a leitura; não incorpora a obra. Todo o código
citado — `src/asus_theye/audit/checkpoint.py`, `src/asus_theye/audit/redacao.py`
— é **obra própria de Mateus Menezes Figueiredo**, licenciada
AGPL-3.0-or-later, com cabeçalho SPDX em cada arquivo.

---

© 2026 Mateus Menezes Figueiredo — projeto ASUS THE EYE, AGPL-3.0-or-later.
Os documentos lidos permanecem de titularidade da Palantir Technologies Inc.
