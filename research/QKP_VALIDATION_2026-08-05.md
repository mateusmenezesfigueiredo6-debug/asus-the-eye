# Validação da QKP da taxonomia

Data de corte: 5 de agosto de 2026, após o commit `0be11c2`.

## Avaliação geral: precisa de revisão antes de orientar decisão

O valor **39.087 está correto e é o ótimo global** da formulação salva. O
recozimento simulado chegou ao ótimo em 12 de 12 partidas, mas não era necessário
para prová-lo: pesos unitários, sinergias positivas e relações somente dentro de
22 grupos tornam a instância exatamente tratável por programação dinâmica entre
grupos.

A formulação não está pronta para justificar QPU nem alocação real. A dificuldade
foi superestimada pelo número bruto de 138 variáveis; a estrutura reduz o problema.
Além disso, quatro das 13 áreas escolhidas usam termos marcados pelo próprio
pipeline como possivelmente genéricos e concentram 77,8% da demanda-base da
seleção. Ao excluir os seis termos suspeitos, o ótimo cai de 39.087 para 18.523,
uma redução de 52,6%.

## Questão, população e fontes

- Questão: o resultado da QKP é matematicamente correto e confiável para decidir
  alocação ou justificar um método quântico?
- Unidade: área da taxonomia.
- População: 145 áreas; 138 com contagem, das quais 94 positivas e 44 zero; sete
  consultas falharam.
- Janela: 30 dias encerrados na geração de
  `reports/commercial/sinal_taxonomia.json` às 16:29 locais.
- Valor: maior contagem obtida entre aliases no Querido Diário; é proxy de
  menções, não receita, conversão, ticket ou demanda privada total.
- Formulação: capacidade 10%, peso 1 por área, sinergia 3 vezes o menor valor para
  cada par no mesmo grupo taxonômico.

## Cálculos verificados

| Verificação | Resultado |
|---|---:|
| Linhas / ids únicos | 145 / 145 |
| Cobertura de ids contra a taxonomia | 145/145 |
| Contagens ausentes | 7 (4,8%) |
| Contagens zero | 44 (30,3%) |
| Contagens positivas | 94 (64,8%) |
| Termos suspeitos | 6 (4,1%) |
| Capacidade efetiva | 13 áreas |
| Autoteste DP contra força bruta | 50/50 casos sintéticos |
| Ótimo exato por DP de grupos | 39.087 |
| Melhor do recozimento | 39.087 |
| Partidas no ótimo | 12/12 |
| Áreas suspeitas na solução | 4/13 |
| Parcela da demanda-base vinda das suspeitas | 77,8% |
| Ótimo sem os seis termos suspeitos | 18.523 |
| Queda sem os termos suspeitos | 52,6% |

Reprodução: `python3 research/validate_qkp_taxonomy.py`.

## Por que o ótimo é calculável exatamente

Dentro de um grupo, ordene os valores escolhidos como
`v1 >= v2 >= ... >= vk`. A contribuição é:

`sum(vr * (1 + 3 * (r - 1)))`.

Para um `k` fixo, os `k` maiores valores do grupo dominam qualquer outra escolha.
Assim, calculam-se as opções `k=0..13` de cada grupo e uma programação dinâmica
distribui 13 vagas pelos 22 grupos. A complexidade depende de grupos e capacidade,
não de `2^138`. O script independente reproduz 39.087 e a mesma seleção salva.

## Problemas que afetam a decisão

1. **Alta — proxy dominada por termos genéricos.** `administrativo`, `contrato`,
   `transporte` e `obra` entram na solução e respondem por 77,8% da soma-base.
   O próprio coletor os marca como suspeitos. A solução otimiza ruído potencial.
2. **Alta — sinergia não medida.** Pertencer ao mesmo grupo taxonômico não mede
   ganho comercial conjunto. A intensidade 3,0 é um parâmetro declarado e produz
   grande parte do valor objetivo.
3. **Alta — peso não representa custo.** Todas as áreas custam exatamente 1. A
   capacidade limita quantidade, não equipe, tempo, dinheiro ou risco.
4. **Alta — claim de dificuldade/QPU não se sustenta.** A instância é grande em
   bits, mas separável por grupos e capacidade pequena; existe solução exata
   clássica barata.
5. **Média — falha e zero são diferentes.** Sete áreas tiveram todas as consultas
   falhas; 44 tiveram retorno zero. Misturá-las alteraria cobertura e seleção.
6. **Média — máximo entre aliases cria viés de seleção.** Áreas com mais aliases
   têm mais oportunidades de obter uma contagem alta, especialmente com palavras
   genéricas. O snapshot testou de zero a seis aliases por área.

## Conclusão e continuação segura

- **FACT:** 39.087 é o ótimo da formulação atual.
- **FACT:** nenhum resultado salvo usa QPU real; o benchmark anterior registra
  `local_simulator`, `hardware_execution=false` e `qpu_time_ms=0`.
- **INFERENCE:** a convergência 12/12 é consistente com o ótimo, agora confirmado
  exatamente.
- **RECOMMENDATION:** não executar QPU nesta instância. Primeiro substituir peso
  unitário e sinergia declarada por medidas defensáveis, revisar termos suspeitos
  e manter falhas distintas de zeros.
- **UNKNOWN:** se a QKP representa uma decisão comercial útil após essas
  correções. O que mudaria a conclusão: custo medido, sinergia validada e fonte
  adequada por área.
