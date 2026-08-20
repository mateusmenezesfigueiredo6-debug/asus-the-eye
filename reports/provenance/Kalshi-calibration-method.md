# Proveniência — método de calibração (leitura de publicação da Kalshi)

Registro de absorção de **conceito**, conforme a política do projeto. Não houve
cópia de código nem de texto: a publicação foi **lida**, o método foi
**interpretado**, e a implementação neste repositório é **independente**.

## O que foi lido

| campo | valor |
|---|---|
| Publicação | *Calibration In Prediction Markets – Theory and Evidence* |
| Autor | Kalshi Research |
| Data | agosto de 2026 |
| Onde | `https://kalshi.com/research/publications/calibration` |
| Natureza | artigo público de pesquisa, com PDF; **material proprietário de terceiro** |
| Lido em | 20/08/2026 |

Também consultada, do mesmo grupo: *Beyond Consensus: Prediction Markets and the
Forecasting of Inflation Shocks* (jan/2025), registrada em
`Kalshi-consensus-benchmark.md`.

## O que foi absorvido — e o que não foi

**Absorvido (conceito, não implementação):**

1. **Brier estratificado por horizonte.** Um Brier agregado esconde quase tudo: o
   mesmo 0,50 significa coisas diferentes a três meses e na véspera. A métrica só
   é interpretável quando cortada por tempo-até-resolução.
2. **Diagrama de confiabilidade contra a diagonal.** A curva que compara
   probabilidade declarada com frequência realizada é a forma canônica de
   apresentar calibração — e é geometria estatística de domínio público
   (Brier 1950; Murphy 1973), não invenção deles.
3. **Estratificação por categoria.** Eles mostram que categorias com longa janela
   de descoberta de informação calibram melhor que categorias de janela curta.
   Aplicado aqui como calibração **por área** (macroeconomia / juros / câmbio).
4. **Re-ancoragem temporal no evento real.** O achado que eles declaram como
   inédito: medir o horizonte contra o **momento real de ocorrência do evento**,
   em vez do timestamp bruto de fechamento do contrato, melhora a calibração e
   remove viés. É o que motiva, aqui, separar `determination_date` (quando a
   fonte oficial publicou) do `deadline` do contrato.

**Deliberadamente NÃO absorvido:**

- Nenhuma linha de código — a publicação não distribui código, e não buscamos.
- Nenhum número deles é reproduzido como se fosse nosso. Os resultados que eles
  relatam descrevem **a plataforma deles**, medida em 2,2 milhões de mercados; a
  nossa tem uma liquidação. Comparar as duas magnitudes sem dizer isso seria
  desonesto, e é por isso que o painel de calibração daqui é obrigado a declarar
  n insuficiente enquanto for o caso.
- Orderbook, volume e contagem de traders como covariáveis de calibração: eles
  mostram que calibração melhora com profundidade de mercado, mas **não temos
  mercado com traders** — a probabilidade aqui vem de modelo com sinal nomeado,
  não de fluxo de ordens. Importar essa parte seria fingir uma estrutura que não
  existe.

## Onde isso vive neste repositório

| conceito | implementação própria |
|---|---|
| série de `p(t)` com horizonte | `src/asus_theye/markets/serie_p.py` |
| separação deadline × publicação da fonte | `determination_date` na liquidação |
| Brier por horizonte e por área | painel `/calibracao` |
| honestidade com n pequeno | aviso obrigatório no painel |

A decisão de projeto que **diverge** deles e do resto da casa: numa série
temporal o relógio **entra** na identidade do registro (`(claim_id, observado_em)`),
porque o ponto é o par (valor, momento). Deduplicar por valor apagaria "p ficou
parado em 0,50 por trinta dias", que é justamente um dos fatos que a calibração
precisa enxergar. Nos demais stores do projeto a regra continua a inversa.

## Fronteira de titularidade

A publicação é **obra de terceiro** e permanece de quem a escreveu. Este arquivo
registra a leitura, não incorpora a obra. Todo o código citado acima é obra
própria, licenciada AGPL-3.0-or-later, com cabeçalho SPDX em cada arquivo.

---

© 2026 Mateus Menezes Figueiredo — projeto ASUS THE EYE, AGPL-3.0-or-later.
A publicação lida permanece de titularidade da Kalshi.
