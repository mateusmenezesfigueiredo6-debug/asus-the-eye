# Proveniência — World Bank Open Data (CC-BY 4.0)

Registro de uso de **dado de terceiro sob licença permissiva**. Diferente dos
demais arquivos desta pasta, que registram absorção de *conceito*, este registra
o uso do **dado em si** — permitido, e com a obrigação que a licença cria.

## A fonte

| campo | valor |
|---|---|
| Origem | World Bank Open Data — `data.worldbank.org` |
| API | `api.worldbank.org/v2` — pública, **sem chave e sem custo** |
| Licença | **CC-BY 4.0** (Creative Commons Attribution 4.0 International) |
| Verificado em | 20/08/2026 |

## Por que esta fonte, e não um comparador proprietário

A licença é o critério. A CC-BY 4.0 permite **copiar, modificar e distribuir os
dados para qualquer fim, inclusive comercial** — exigindo apenas atribuição e
indicação de alterações. É exatamente o oposto do que encontramos nos termos de
comparadores proprietários, que proíbem armazenar, exibir publicamente e criar
obras derivadas (ver `Kalshi-dados-expurgo.md`).

Uma plataforma de prova precisa fazer as três coisas proibidas lá: armazenar,
exibir e derivar. Logo, a única fonte compatível com o produto é uma de licença
permissiva — e esta cobre **dezenas de economias**, o que é mais alcance global
do que o comparador expurgado nos daria.

## Como a atribuição é cumprida

A CC-BY exige crédito. Cumprimos em três lugares, sendo o primeiro o que importa:

1. **No próprio dado** — cada `ObservacaoGlobal` carrega `licenca` e
   `atribuicao`, de modo que o crédito viaja junto em qualquer lugar que o valor
   apareça: painel, export estático, evento selado, API. Não depende de alguém
   lembrar de escrever num rodapé.
2. **No `NOTICE`** da raiz.
3. **Neste registro.**

Se houver transformação do dado, ela é declarada no evento selado — a exigência
de "indicar alterações" é atendida pela própria corrente auditável.

## O que é do titular

O **conector** (`src/asus_theye/markets/fonte_worldbank.py`) é obra própria de
Mateus Menezes Figueiredo, escrita do zero contra a documentação pública da API,
licenciada AGPL-3.0-or-later. Nenhum código de terceiro foi copiado ou adaptado.

Os **dados** permanecem do World Bank sob CC-BY 4.0. Usar dado licenciado não o
torna nosso — e não precisa: a licença já permite o uso que o produto faz.

## Fronteira declarada

O conector admite apenas indicadores **registrados em código**, cada um com
unidade e periodicidade declaradas. Indicador não registrado levanta. Isso
impede que um número entre sem que se saiba o que ele significa — 3,1 em "% ao
ano" e 3,1 em "% do PIB" são coisas diferentes.

---

© 2026 Mateus Menezes Figueiredo — projeto ASUS THE EYE, AGPL-3.0-or-later.
Os dados do World Bank permanecem sob CC-BY 4.0, de titularidade do World Bank Group.
