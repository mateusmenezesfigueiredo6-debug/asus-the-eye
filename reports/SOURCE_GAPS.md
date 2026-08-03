# Lacunas de fonte

Gerado em 2026-08-03 · metodologia 1.0.0 · snapshot `4fb49afdef7372ca…`

Cada lacuna com o motivo e o que a destravaria. Uma lacuna sem saída
declarada é uma lacuna escondida.

| Motivo | Lacuna | O que destravaria |
| --- | --- | --- |
| exige fonte paga | Volume de vendas de livros e tamanho de mercado por nicho | Assinatura de Circana BookScan ou Nielsen BookData |
| exige fonte paga | Produção científica em escala para ranquear universidades | Ingestão do dump CC0 do OpenAlex no S3 (grátis, sem chave) |
| exige DPIA humana | Ranking de acadêmicos, praticantes e árbitros | RIPD/DPIA concluída por profissional humano + aprovação de DPO/jurídico |
| não existe fonte gratuita | Algoritmos proprietários de recomendação de plataformas sociais | Nada: não são públicos. O indexável são as publicações dessas empresas e as divulgações obrigatórias do art. 40 do DSA |
| ainda não tentado | Qualquer categoria — nenhum conector foi executado ainda | Estágio 2: habilitar conectores e executar a primeira corrida limitada |
