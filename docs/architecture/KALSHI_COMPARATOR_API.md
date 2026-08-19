# API pública da Kalshi como comparador

Verificação realizada em 19 de agosto de 2026 contra a documentação oficial e
respostas da API de produção, sem conta, chave ou cabeçalhos de autenticação.
Este documento descreve um insumo técnico para o M4; não autoriza sua operação.

## Regra de uso no THE EYE

**Kalshi é comparador, nunca fonte de resolução.** Seu preço registra opinião
agregada e serve para medir divergência em relação à nossa probabilidade. Só é
possível dizer quem acertou depois da liquidação do claim contra a fonte oficial
previamente declarada — por exemplo, o BCB para o IPCA mensal.

## API REST pública, sem autenticação

A URL base de produção recomendada é:

```text
https://external-api.kalshi.com/trade-api/v2
```

A documentação também mantém
`https://api.elections.kalshi.com/trade-api/v2` por compatibilidade, mas recomenda
o host `external-api`. Apesar do nome histórico `elections`, o host alternativo
serve todos os mercados. Os endpoints de dados de mercado abaixo responderam sem
qualquer cabeçalho de autenticação:

| Finalidade | Requisição | Autenticação |
|---|---|---|
| Listar e filtrar mercados | `GET /markets` | não exigida |
| Obter um mercado pelo ticker | `GET /markets/{ticker}` | não exigida |
| Obter negócios executados | `GET /markets/trades` | não exigida |
| Obter livro de ofertas | `GET /markets/{ticker}/orderbook` | não exigida |

Endpoints de portfólio, ordens e conta exigem assinatura e não são alternativa
aceitável para este comparador. O WebSocket também não é necessário para o M4.

### `GET /markets`

Lista paginada. Parâmetros públicos documentados:

| Parâmetro | Significado |
|---|---|
| `limit` | itens por página; padrão 100, máximo 1.000 |
| `cursor` | cursor opaco devolvido pela página anterior |
| `event_ticker` | um ticker de evento |
| `series_ticker` | ticker da série, por exemplo `KXCPI` |
| `tickers` | lista de tickers de mercado separada por vírgulas |
| `status` | filtro: `unopened`, `open`, `paused`, `closed` ou `settled` |
| `min_created_ts`, `max_created_ts` | limites Unix para criação |
| `min_updated_ts` | limite Unix para atualização de metadados |
| `min_close_ts`, `max_close_ts` | limites Unix para fechamento |
| `min_settled_ts`, `max_settled_ts` | limites Unix para liquidação |
| `mve_filter` | `only` ou `exclude` para mercados multivariados |

Há restrições entre filtros temporais e de status; o cliente deve seguir a
matriz da referência oficial, não combinar todos indiscriminadamente. Mercados
anteriores ao corte histórico passam para endpoints `/historical`; portanto,
uma lista vazia não prova que a série nunca existiu.

Exemplo de leitura por série:

```http
GET https://external-api.kalshi.com/trade-api/v2/markets?series_ticker=KXCPI&status=open&limit=1000
```

Forma relevante da resposta atual:

```json
{
  "markets": [
    {
      "ticker": "KXCPI-26AUG-T0.3",
      "title": "Will CPI rise more than 0.3% in August 2026?",
      "yes_bid_dollars": "0.5400",
      "yes_ask_dollars": "0.6900",
      "last_price_dollars": "0.5400",
      "close_time": "2026-09-11T12:25:00Z",
      "status": "active"
    }
  ],
  "cursor": ""
}
```

Os valores acima são uma observação de 19 de agosto de 2026 e não devem ser
tratados como cotação permanente. O `cursor` vazio indica o fim da paginação.
No objeto de resposta, os estados atuais incluem `initialized`, `active`,
`inactive`, `closed`, `determined`, `disputed`, `amended` e `finalized`; os
valores aceitos pelo filtro `status` são aliases mais amplos. Em particular,
`status=settled` seleciona objetos cujo estado devolvido é `finalized`.

### `GET /markets/{ticker}`

Recebe um único ticker no caminho e devolve `{"market": {...}}`. Os campos
relevantes para o comparador são:

- `ticker` e `title`: identidade e enunciado;
- `yes_bid_dollars` e `yes_ask_dollars`: melhor compra e melhor venda de YES;
- `last_price_dollars`: preço do último negócio, que pode estar defasado;
- `close_time`: instante ISO 8601 em que a negociação para, sujeito às regras
  do mercado;
- `status`: estado efetivo no ciclo de vida;
- `price_level_structure` e `price_ranges`: grade e passo válidos do preço.

Exemplo:

```http
GET https://external-api.kalshi.com/trade-api/v2/markets/KXCPI-26AUG-T0.3
```

### `GET /markets/trades`

É a alternativa pública quando se precisa do negócio executado, e não apenas
do campo resumido `last_price_dollars`. Aceita `limit` (padrão 100, máximo
1.000), `cursor`, `ticker`, `min_ts`, `max_ts` e `is_block_trade`. A resposta é
`{"trades": [...], "cursor": "..."}`; cada negócio traz, entre outros,
`ticker`, `yes_price_dollars`, `no_price_dollars`, `count_fp`, `created_time` e
`is_block_trade`.

```http
GET https://external-api.kalshi.com/trade-api/v2/markets/trades?ticker=KXCPI-26AUG-T0.3&limit=1
```

## Do preço à probabilidade implícita

Um contrato YES liquida em US$ 1 se o enunciado ocorrer. Na convenção clássica
de centavos, um preço inteiro `c` entre 1 e 99 centavos corresponde à
probabilidade implícita simples `p = c / 100`: 37 centavos vira `0,37`.

Na API vigente, porém, os campos inteiros `yes_bid`, `yes_ask` e `last_price`
foram removidos em janeiro de 2026. Devem ser lidas as strings decimais
`yes_bid_dollars`, `yes_ask_dollars` e `last_price_dollars`. Assim,
`"0.3700"` vira `Decimal("0.3700")`, numericamente `0,37`. Não se deve usar
`float` nem multiplicar e arredondar prematuramente.

Essa conversão é uma **probabilidade implícita de mercado**, não uma estimativa
estatística neutra nem um desfecho. Ela incorpora liquidez, preferências,
restrições de participantes e custos de negociação.

Armadilhas obrigatórias:

- **spread:** `yes_bid_dollars` é o melhor preço executável para vender YES e
  `yes_ask_dollars`, para comprar YES. O ponto médio pode resumir o intervalo,
  mas não é um negócio executável. O M4 deve guardar bid, ask, último preço,
  política de seleção e instante da observação, em vez de ocultar o spread;
- **último negócio defasado:** `last_price_dollars` pode anteceder bastante o
  livro atual. Consultar `created_time` em `/markets/trades` quando a atualidade
  for material;
- **iliquidez:** bid zero, ask um, spread amplo, baixo volume ou livro vazio
  tornam a probabilidade pouco informativa. Não preencher ausência com 0,50;
- **half-cent e subcent:** os preços são strings com até quatro casas. A grade
  pode ter passos de US$ 0,005 (meio centavo), US$ 0,002, US$ 0,001 ou até
  US$ 0,0001, além de US$ 0,01. Ler dinamicamente `price_ranges[].step`; não
  presumir o intervalo 1–99 nem derivar a grade do nome da estrutura;
- **limites:** valores próximos de US$ 0 ou US$ 1 também são válidos em grades
  atuais. Nunca forçar todo preço ao intervalo 0,01–0,99.

## Mapeamento com os claims do THE EYE

### CPI dos Estados Unidos

A série pública real `KXCPI` existe, é mensal, pertence à categoria Economics e
declara o Bureau of Labor Statistics como fonte de liquidação da própria
Kalshi. Também existem `KXCPIYOY` (inflação CPI em 12 meses) e `KXCPICORE`
(núcleo do CPI). Tickers e títulos reais encontrados em 19 de agosto de 2026:

| Série | Ticker de mercado | Título devolvido pela API |
|---|---|---|
| `KXCPI` | `KXCPI-26AUG-T0.2` | `Will CPI rise more than 0.2% in August 2026?` |
| `KXCPI` | `KXCPI-26AUG-T0.3` | `Will CPI rise more than 0.3% in August 2026?` |
| `KXCPI` | `KXCPI-26AUG-T0.4` | `Will CPI rise more than 0.4% in August 2026?` |
| `KXCPIYOY` | `KXCPIYOY-26AUG-T2.5` | `Will the rate of CPI inflation be above 2.5% for the year ending in August 2026?` |
| `KXCPICORE` | `KXCPICORE-26NOV-T0.3` | `Will CPI Core rise more than 0.3% in November?` |

`KXCPI` mede CPI dos EUA; não mede IPCA brasileiro. Compará-lo ao claim do THE
EYE é **INDIRETO** e exige registrar explicitamente país, índice, população e
cesta coberta, ajuste sazonal, janela de variação, mês de referência, limiar,
operador lógico e fonte oficial. CPI EUA diferente de IPCA BR não pode receber
o rótulo “mesmo mercado”.

### Correção verificada: hoje há mercado de IPCA brasileiro

A afirmação “IPCA brasileiro não existe na Kalshi” está desatualizada e foi
refutada pela API pública em 19 de agosto de 2026. A série real
`KXBRAZILINF`, título `Brazil inflation`, possui mercados como:

| Ticker de mercado | Título devolvido pela API |
|---|---|
| `KXBRAZILINF-26AUG-T4.00` | `Will inflation in Brazil be above 4.00% in Aug 2026?` |
| `KXBRAZILINF-26AUG-T4.50` | `Will inflation in Brazil be above 4.50% in Aug 2026?` |
| `KXBRAZILINF-26AUG-T5.00` | `Will inflation in Brazil be above 5.00% in Aug 2026?` |

Os termos públicos do contrato `BRAZILINF.pdf` definem o subjacente como a
variação em 12 meses do Índice Nacional de Preços ao Consumidor Amplo (IPCA),
publicado pelo IBGE. Há uma inconsistência de metadados que precisa permanecer
visível: a API escreve `IGBE` e aponta uma URL de desemprego, enquanto o PDF
nomeia o IBGE e o IPCA. Isso reduz a confiança operacional nos metadados e
reforça que a Kalshi nunca deve resolver nossos claims.

Esse mercado ainda **não é equivalente ao claim atual do THE EYE**. Nosso
contrato usa a variação **mensal** do IPCA da série SGS 433 e operador `>=`;
`KXBRAZILINF` usa IPCA acumulado em **12 meses** e operador estrito `>`. Logo,
a comparação atual continua INDIRETA. Só seria direta para um futuro claim que
igualasse índice, país, janela de 12 meses, mês, limiar, operador e versão do
dado — e mesmo então a resolução do THE EYE viria da fonte oficial, nunca da
Kalshi.

## Rate limits

A documentação publica limites numéricos por tier apenas para requisições
**autenticadas**. A maioria custa 10 tokens; no tier Basic autenticado, o
orçamento de leitura é 200 tokens por segundo, equivalente a 20 requisições de
custo padrão por segundo em regime sustentado. Esses números não devem ser
atribuídos ao acesso anônimo.

**UNKNOWN:** não foi localizado na documentação oficial consultada um limite
numérico específico para requisições sem autenticação. A ausência de número
publicado não significa ausência de limite. A Kalshi pode alterá-lo sem aviso.
Ao receber HTTP `429`, a documentação informa o corpo
`{"error":"too many requests"}` e que atualmente não há `Retry-After` nem
cabeçalhos `X-RateLimit-*`; usar backoff exponencial, número limitado de
tentativas e cache somente se houver autorização jurídica para armazenar os
dados.

## Termos de uso e bloqueio para o M4

“Endpoint público” descreve acesso técnico sem chave; não concede licença
irrestrita. O uso da API implica aceitação do **Kalshi Developer Agreement
v1.1**. O texto público:

- limita a API à facilitação da negociação própria de um membro;
- proíbe coletar, manter em cache, agregar ou armazenar dados da API fora dessa
  finalidade e proíbe compartilhá-los sem autorização escrita prévia;
- proíbe usar a API para monitoramento de desempenho ou disponibilidade e para
  benchmarking ou finalidade competitiva;
- permite à Kalshi impor ou alterar limites e suspender o acesso;
- exige uso responsável, HTTPS e retries limitados com backoff exponencial.

Os Data Terms of Use ligados pela Kalshi também restringem uso comercial,
extração sistemática, desenvolvimento de software e uso de dados em IA sem
consentimento prévio. A simples disponibilidade pública de bid, ask e negócios
não elimina essas restrições.

**BLOCKED:** a ingestão automatizada, o armazenamento auditável e a publicação
de divergências da Kalshi pelo M4 não devem ser ativados sob os termos públicos
atuais. Antes de implementar ou operar o conector, é necessária autorização
escrita da Kalshi que cubra expressamente coleta, armazenamento, cálculo da
divergência e exibição dos dados no produto, além de revisão jurídica humana.
Sem isso, este documento serve somente como pesquisa técnica local.

## Fontes consultadas

- [API Environments and Endpoints](https://docs.kalshi.com/getting_started/api_environments)
- [Quick Start: Market Data](https://docs.kalshi.com/getting_started/quick_start_market_data)
- [Get Markets](https://docs.kalshi.com/api-reference/market/get-markets)
- [Get Market](https://docs.kalshi.com/api-reference/market/get-market)
- [Get Trades](https://docs.kalshi.com/api-reference/market/get-trades)
- [Fixed-Point Representation](https://docs.kalshi.com/getting_started/fixed_point_migration)
- [Market Lifecycle](https://docs.kalshi.com/getting_started/market_lifecycle)
- [Rate Limits and Tiers](https://docs.kalshi.com/getting_started/rate_limits)
- [API Changelog](https://docs.kalshi.com/changelog)
- [Kalshi Developer Agreement v1.1](https://assets.kalshi.com/Kalshi-Developer-Agreement.pdf)
- [Kalshi Data Terms of Use](https://kalshi-public-docs.s3.amazonaws.com/kalshi-data-terms-of-service.pdf)
- [BRAZILINF Contract Terms](https://assets.kalshi.com/contract_terms/BRAZILINF.pdf)
- [API de produção: série KXCPI](https://external-api.kalshi.com/trade-api/v2/series/KXCPI)
- [API de produção: mercados KXCPI](https://external-api.kalshi.com/trade-api/v2/markets?series_ticker=KXCPI&limit=1000)
- [API de produção: série KXBRAZILINF](https://external-api.kalshi.com/trade-api/v2/series/KXBRAZILINF)
- [API de produção: mercados KXBRAZILINF](https://external-api.kalshi.com/trade-api/v2/markets?series_ticker=KXBRAZILINF&limit=1000)

---

© 2026 Mateus Menezes Figueiredo, AGPL-3.0. Fontes: URLs consultadas acima.
Kalshi é comparador, nunca fonte de resolução.
