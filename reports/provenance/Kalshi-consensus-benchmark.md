# Proveniência — método de comparação contra consenso (leitura de publicação)

Registro de absorção de **conceito**. A publicação foi **lida**, o método foi
**interpretado**, e a implementação neste repositório é **independente**. Nenhum
código, nenhum texto e **nenhum dado** de terceiro foi copiado — a distinção
entre ler publicação e usar dado está registrada em `Kalshi-dados-expurgo.md`.

## O que foi lido

| campo | valor |
|---|---|
| Publicação | *Beyond Consensus: Prediction Markets and the Forecasting of Inflation Shocks* |
| Autor | Kalshi Research |
| Data | janeiro de 2025 |
| Onde | `https://kalshi.com/research/publications/crisis-alpha` |
| Natureza | artigo público de pesquisa; **material proprietário de terceiro** |
| Lido em | 20/08/2026 |

## O conceito absorvido

O desenho experimental — e apenas ele:

1. **Comparar previsão contra o consenso de analistas**, no mesmo horizonte, e
   medir erro absoluto médio (MAE) em vez de só acerto binário.
2. **Estratificar por regime de surpresa.** O ganho de um previsor não é
   uniforme: importa separar meses tranquilos de meses de choque, porque é no
   choque que previsão boa vale dinheiro e modelo histórico costuma falhar.
3. **Taxa de acerto na discordância.** Quando as duas previsões divergem, qual
   ficou mais perto? É a pergunta que isola contribuição de coincidência.
4. **Múltiplos horizontes.** Medir a uma semana, a um dia e no dia da
   divulgação mostra se a informação está sendo incorporada ao longo do tempo.
5. **Divergência como meta-sinal.** A distância entre as duas previsões pode,
   por si só, indicar probabilidade de surpresa.

## O que foi deliberadamente NÃO absorvido

- **Os limiares numéricos deles.** A classificação de choque de referência foi
  calibrada sobre o CPI norte-americano. Copiar o corte para o IPCA brasileiro
  seria importar a variância de outra economia — nossos limiares têm de ser
  calibrados nos nossos dados, e ficam declarados como provisórios até haver
  amostra que os justifique.
- **Os resultados deles.** Nenhum número da publicação é reproduzido aqui como
  se descrevesse esta plataforma. Aqueles resultados descrevem a plataforma
  deles, sobre a série deles, no período deles.
- **A premissa de independência.** Ver abaixo — é o ponto mais importante deste
  registro.

## A ressalva que muda a conclusão (achado próprio)

O desenho da publicação funciona porque a previsão de mercado deles se forma de
maneira **heterogênea** em relação ao consenso: são traders com informação e
incentivos próprios.

**Aqui não é assim, e reconhecer isso é obrigatório.** O gerador WPAM
(`markets/sinais_ipca.py`) usa o **Focus como sinal dominante** — peso 20,
contra 10 do IPCA-15. Nossa probabilidade **deriva** do consenso.

Portanto **é impossível, hoje, afirmar que superamos o consenso**: medir "nosso
p contra o Focus" mediria sobretudo o nosso próprio esquema de pesos aplicado ao
insumo dele. Chamar isso de desempenho superior seria fabricar mérito.

O que **é** honesto medir, e é o que esta implementação faz:

- **o MAE do próprio Focus** contra o realizado — a linha de base que qualquer
  calibração precisa ter, e que ninguém pode calcular por nós;
- **o efeito de acrescentar o IPCA-15** ao Focus, que é a nossa contribuição
  real e mensurável;
- a **dependência declarada em todo resultado**, para que nenhum leitor
  interprete o número como vantagem independente.

Uma comparação verdadeiramente independente só passa a ser possível quando
existirem sinais que não derivem do consenso. Isso é trabalho futuro, e está
dito como tal em vez de ser contornado.

## Honestidade estatística obrigatória

No momento deste registro existem **1 vintage do Focus** (mês 2026-09) e **1
liquidação** (mês 2026-07) — que **não se cruzam**. Não há um único par
(previsão, realizado) disponível. A implementação **recusa** emitir métrica
agregada abaixo de uma amostra mínima declarada, em vez de imprimir um número
que pareceria significativo.

## Onde isso vive

| conceito | implementação própria |
|---|---|
| pareamento vintage × realizado | `src/asus_theye/markets/consenso.py` |
| arquivamento do consenso vigente | `src/asus_theye/markets/vintage_focus.py` (anterior) |
| trava de amostra mínima | `AMOSTRA_MINIMA` em `consenso.py` |

## Fronteira de titularidade

A publicação é **obra de terceiro** e permanece de titularidade de quem a
escreveu. Este arquivo registra a leitura; não incorpora a obra. Todo o código
citado é **obra própria de Mateus Menezes Figueiredo**, licenciada
AGPL-3.0-or-later, com cabeçalho SPDX em cada arquivo.

---

© 2026 Mateus Menezes Figueiredo — projeto ASUS THE EYE, AGPL-3.0-or-later.
A publicação lida permanece de titularidade da Kalshi.
