# THE EYE Markets

## Mercados preditivos evidence-first

Uma probabilidade só é útil quando também é possível responder: **de onde ela veio, como será liquidada e quem pode conferir o resultado?** O THE EYE Markets foi construído para responder às três perguntas no próprio registro do mercado.

### Real em 19/08/2026

Há três mercados vivos, cada um com regra prévia e fonte oficial própria:

- `MACRO-01::2026-08`: IPCA mensal de agosto maior ou igual a 0,50%, resolvido pela série 433 do BCB;
- `JUROS-01::2026-09`: meta Selic ao fim de setembro maior ou igual a 14,00% a.a., limiar igual à meta vigente na emissão, resolvido pela série 432 do BCB;
- `CAMBIO-01::2026-09`: PTAX de venda ao fim de setembro maior ou igual a R$ 5,17, limiar vigente na emissão, resolvido pela fonte PTAX do BCB.

O workflow de operação contínua no GitHub Actions já executa o resolvedor, emite o contrato seguinte e espelha a corrente no D1; o ensaio manual foi concluído. Os segredos operacionais estão plantados e uma rodada real do workflow já resolveu, selou, espelhou e commitou sem intervenção humana. **Ainda em roteiro operacional:** a primeira liquidação de calendário pelo cron mensal (setembro/2026). Contrato aberto não tem Brier: o erro só nasce depois da liquidação contra a fonte oficial.

### Probabilidade com proveniência, sem antecipar o próximo contrato

O gerador WPAM transforma sinais nomeados em probabilidade. Para o mercado mensal de IPCA, a implementação consulta fontes do Banco Central do Brasil:

- mediana das expectativas do IPCA no Focus, via API Olinda;
- IPCA-15, prévia oficial disponível na série SGS 7478.

Cada sinal conserva direção, peso e descrição da fonte. Quando uma emissão usa o gerador, o registro recebe o bloco `gerador`, com probabilidade, prior, pesos e fontes. Se não houver sinal disponível, o sistema não inventa convicção: retorna 0,50 e marca incerteza máxima.

Os três contratos vivos foram emitidos antes dessa integração e **não têm** o bloco `gerador`. A implementação já produziu sinal real para setembro — Focus de 0,52% ante limiar de 0,50%, resultando em 0,8333 —, mas a **próxima emissão de IPCA** é a primeira prevista para nascer do WPAM e gravar o bloco no registro. WPAM para Selic e câmbio continua em roteiro.

### Liquidação contra o mundo, não contra outra opinião

Cada pergunta declara antes do resultado o critério, o prazo e a fonte oficial de resolução. Comparadores externos servem para registrar onde discordamos do consenso; **nunca são fonte de resolução**.

A máquina de divergência foi provada de ponta a ponta: a observação vira evento `market.comparator` selado, com nota de mapeamento obrigatória declarando o que está sendo comparado. O comparador oficial é o **consenso Focus do Banco Central** — dado público, e comparação direta com o IPCA. Um teste anterior usou um mercado externo de CPI norte-americano e foi **expurgado** (evento `data.redaction`), tanto por restrição de termos de terceiro quanto por ser comparação indireta: índices e países distintos não respondem à mesma pergunta.

O Brier permanece nulo enquanto o contrato está aberto. Só passa a existir após a publicação do dado oficial e a liquidação. No caso real já registrado, “IPCA de julho de 2026 em 0,50% ou mais?”, a probabilidade era 0,50, o IPCA observado foi 0,07%, o resultado foi “não” e o Brier foi **0,25**. O número mede esse contrato; não é apresentado como desempenho geral.

### Nowcast: ponto de partida medido, não skill vendável

Duas corridas reais do desafiante linear foram seladas em walk-forward de 18 meses: R2 com Brier 0,0575 e R4 com 0,0611, ambas com cobertura de 42,86%. O modelo permanece **sem peso** no WPAM. O Brier comparativo do Focus está `BLOCKED`, porque não há vintage reproduzível no mesmo corte; usar dados revisados criaria vantagem informacional.

Esse resultado não demonstra uma skill. É somente um ponto de partida medido. Qualquer influência futura exige a porta prospectiva de 24 meses com Brier menor ou igual ao Focus.

### Da pergunta à prova verificável

Cada liquidação gera um evento selado. O evento entra em uma corrente criptográfica, ligada ao evento anterior, para que alterações posteriores sejam detectáveis. Assim, pergunta, probabilidade, regra de resolução, fonte oficial, resultado e erro medido formam uma trilha auditável.

O próprio roteiro dos produtos também é medido: no corte selado de 19/08, 71,7% dos pesos estavam concluídos. A medição virou evento na corrente; seu hash público impede que avanço declarado seja confundido com entrega realizada.

### Para quem precisa decidir sem apagar o histórico

O THE EYE Markets serve operações que precisam acompanhar previsões e provar, depois, o que era conhecido em cada momento: mesas de decisão, pesquisa econômica, planejamento e monitoramento de cenários. A proposta não é prometer acerto; é tornar cada previsão explicável, cada liquidação reproduzível e cada erro mensurável.

---

© 2026 Mateus Menezes Figueiredo, AGPL-3.0.
