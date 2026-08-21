# Proveniência — GDELT Project (cobertura noticiosa)

Registro de uso de **dado de terceiro sob termos permissivos**, escrito **antes**
do código entrar, conforme a política do projeto.

## Por que esta fonte existe aqui

Este é o registro mais importante da pasta, e vale dizer o motivo.

Até aqui a probabilidade publicada pela plataforma **derivava do consenso
Focus** — o gerador WPAM usa o boletim do Banco Central como sinal dominante.
Isso criava um limite intransponível: era **impossível afirmar desempenho
próprio**, porque qualquer auditor honesto apontaria que somos o consenso com
pesos diferentes.

O GDELT é a única fonte encontrada que produz um número de **origem diferente**:
contagem e tom sobre texto de notícia, não pesquisa com economistas. Não é um
sinal melhor — é um sinal **independente**, e é disso que o produto precisava.

## A fonte, e os termos conferidos na origem

| campo | valor |
|---|---|
| Projeto | The GDELT Project — `gdeltproject.org` |
| Caminho usado | arquivos brutos por HTTPS em `data.gdeltproject.org/gdeltv2/` |
| Termos | `gdeltproject.org/about.html`, seção *Terms of Use* |
| Conferido em | 21/08/2026 |
| `sha256` da página de termos na data | `384754b514042255c4542d51dc1e631d…` |

Os termos, citados na íntegra do trecho que decide o caso:

> "all datasets released by the GDELT Project are available for unlimited and
> unrestricted use for any academic, commercial, or governmental use of any kind
> without fee"

> "You may redistribute, rehost, republish, and mirror any of the GDELT datasets
> in any form"

Única obrigação: **citar o GDELT Project**, com link para o site. Cumprida no
`NOTICE`, neste registro, e — como fizemos com o World Bank — **no próprio
dado**, para que o crédito viaje junto e não dependa de alguém lembrar.

## A diferença em relação ao caso Kalshi

Os termos do GDELT são de **site**, editáveis a qualquer momento, e **não têm**
cláusula de irrevogabilidade como a CC-BY. Isso poderia parecer o mesmo risco
que obrigou o expurgo da Kalshi. **Não é**, e a diferença é específica:

- os termos **vigentes autorizam expressamente redistribuir e espelhar**, e
  **não há cláusula de retomada**. Dado obtido sob a concessão vigente não vira
  passivo retroativo;
- os termos da Kalshi, ao contrário, **já proibiam** armazenar, exibir e derivar
  no momento em que usávamos.

**Mitigação adotada, e é por isso que ela existe:** a página de termos é
arquivada com `sha256` **na data de cada ingestão**, encadeada na corrente. Se
os termos mudarem amanhã, a proveniência prova quais vigiam quando baixamos.

## O que é absorvido

Apenas **campos numéricos e codificados** do arquivo de eventos (GDELT 2.0):
contagem de registros e média do tom (`AvgTone`, coluna 34), filtrados por
código de país (coluna 53). O arquivo tem 61 colunas; usamos duas.

## O que foi deliberadamente NÃO absorvido

Esta seção é a que protege o titular, e cada item tem motivo próprio:

- **Texto de artigo, manchete e URL de origem.** Os termos do GDELT permitem,
  mas o conteúdo apontado pertence a **veículos de imprensa**, cujos termos são
  outros e não foram lidos. Guardar contagem e tom não toca a obra de ninguém;
  guardar manchete, sim. A fronteira é do projeto, não da licença.
- **BigQuery.** É serviço pago do Google com faturamento por consulta — viola a
  regra de custo zero. Os arquivos brutos por HTTPS dão o mesmo dado.
- **A API de consulta** (`api.gdeltproject.org`). Testada em 21/08/2026: devolve
  aviso de limite mesmo com 8 segundos entre requisições. Não é confiável, e
  insistir seria abusar de um serviço gratuito.
- **O arquivo GKG.** 5,6 MB a cada 15 minutos — 540 MB por dia. O arquivo de
  eventos, com 73 KB, entrega o que precisamos.

## O que é do titular

O **conector** (`src/asus_theye/markets/fonte_gdelt.py`) e o **gerador de
sinal** (`src/asus_theye/markets/sinais_noticia.py`) são obra própria de Mateus
Menezes Figueiredo, escritos do zero contra a documentação pública do formato,
licenciados AGPL-3.0-or-later. Nenhuma linha de código de terceiro foi copiada
ou adaptada.

Os **dados** permanecem do GDELT Project sob os termos acima. Usar dado
licenciado não o torna nosso — e não precisa: os termos já permitem o uso que o
produto faz, inclusive comercial.

## A honestidade que o produto exige

O sinal de tom noticioso é **fraco e ruidoso** para inflação e juros. É esperado
que ele **não supere** o consenso Focus.

Isso está registrado aqui de propósito, antes de qualquer resultado: a razão de
adotá-lo não é vencer, é **poder medir**. Hoje a plataforma não pode afirmar
nada sobre desempenho próprio. Com as duas trilhas seladas antes do desfecho,
ela passa a poder afirmar o que os dados mostrarem — inclusive paridade, que é
resultado publicável e defensável.

---

© 2026 Mateus Menezes Figueiredo — projeto ASUS THE EYE, AGPL-3.0-or-later.
Os dados permanecem do GDELT Project, sob os termos citados.
