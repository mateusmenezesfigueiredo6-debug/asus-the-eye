# THE EYE Markets

## Mercados preditivos evidence-first

Uma probabilidade só é útil quando também é possível responder: **de onde ela veio, como será liquidada e quem pode conferir o resultado?** O THE EYE Markets foi construído para responder às três perguntas no próprio registro do mercado.

### Probabilidade com proveniência

O gerador WPAM transforma sinais nomeados em probabilidade. Para o mercado mensal de IPCA, a implementação consulta fontes do Banco Central do Brasil:

- mediana das expectativas do IPCA no Focus, via API Olinda;
- IPCA-15, prévia oficial disponível na série SGS 7478.

Cada sinal conserva direção, peso e descrição da fonte. Quando a emissão usa o gerador, o registro recebe o bloco `gerador`, com probabilidade, prior, pesos e fontes. Se não houver sinal disponível, o sistema não inventa convicção: retorna 0,50 e marca incerteza máxima. O roteiro do produto registra esta integração como parcial até que o próximo contrato real nasça do gerador; a expansão para Selic e câmbio também está em roteiro.

### Liquidação contra o mundo, não contra outra opinião

Cada pergunta declara antes do resultado o critério, o prazo e a fonte oficial de resolução. No mercado de IPCA, a liquidação usa exclusivamente a série 433 do BCB SGS. A Kalshi pertence à categoria e pode servir como comparador; **nunca é fonte de resolução**.

O Brier permanece nulo enquanto o contrato está aberto. Só passa a existir após a publicação do dado oficial e a liquidação. No caso real já registrado, “IPCA de julho de 2026 em 0,50% ou mais?”, a probabilidade era 0,50, o IPCA observado foi 0,07%, o resultado foi “não” e o Brier foi **0,25**. O número mede esse contrato; não é apresentado como desempenho geral.

### Da pergunta à prova verificável

Cada liquidação gera um evento selado. O evento entra em uma corrente criptográfica, ligada ao evento anterior, para que alterações posteriores sejam detectáveis. Assim, pergunta, probabilidade, regra de resolução, fonte oficial, resultado e erro medido formam uma trilha auditável.

### Para quem precisa decidir sem apagar o histórico

O THE EYE Markets serve operações que precisam acompanhar previsões e provar, depois, o que era conhecido em cada momento: mesas de decisão, pesquisa econômica, planejamento e monitoramento de cenários. A proposta não é prometer acerto; é tornar cada previsão explicável, cada liquidação reproduzível e cada erro mensurável.

---

© 2026 Mateus Menezes Figueiredo, AGPL-3.0.
