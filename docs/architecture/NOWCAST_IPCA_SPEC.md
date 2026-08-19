# Especificação exploratória — nowcast mensal do IPCA

**Estado:** especificação; nenhum modelo foi treinado, registrado ou promovido.

**Corte da exploração:** 19/08/2026, America/Sao_Paulo.

**Canal de dados:** API pública BCData/SGS do Banco Central do Brasil, sem chave.

**Papel pretendido:** somente `desafiante`; peso zero no WPAM até cumprir a
régua prospectiva da seção 6.

## 1. Pergunta, alvo e regra temporal

O alvo é a variação percentual mensal do IPCA cheio no mês `t`, série SGS
**433**. A consulta real confirmou nome, unidade mensal e observações até
julho de 2026. Um nowcast válido para `t` só pode usar informação que já fosse
pública no seu instante de corte. A primeira versão terá um único corte:
**fim do último dia útil de `t`**, depois da divulgação do IGP-M e antes da
divulgação do IPCA cheio, que normalmente ocorre no mês seguinte.

Isso é importante porque o campo `data` devolvido pelo SGS é a **referência da
observação**, não o instante em que ela entrou na API. O SGS consultado não
fornece vintage nem `published_at`. Portanto:

- o coletor futuro deve salvar resposta bruta, URL, instante UTC, status HTTP e
  SHA-256 a cada corte;
- o backtest só pode usar calendários oficiais de divulgação e observações
  diárias com data menor ou igual ao corte;
- uma série publicada junto com o IPCA não é feature, ainda que sua correlação
  seja alta.

## 2. Séries verificadas e disponibilidade

Todas as séries numeradas abaixo foram consultadas de verdade em
`https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`, com
`formato=json`. Para as séries correntes, a extração usada na análise foi de
01/07/2021 a 19/08/2026. Para as duas séries descontinuadas, foi de 01/03/2015
a 29/02/2020. A API respondeu HTTP 200 em todas essas consultas.

| Papel | SGS confirmado | Nome e unidade confirmados no SGS | Transformação candidata | Disponibilidade versus IPCA cheio | Decisão exploratória |
|---|---:|---|---|---|---|
| alvo | 433 | IPCA, variação % mensal | nenhuma | divulgado no mês `t+1` | alvo, nunca feature |
| prévia | 7478 | IPCA-15, variação % mensal | valor de `t` | em 2026, jan–jul, saiu 13–16 dias antes do IPCA de mesmo mês; mediana 14 dias | candidata principal |
| câmbio | 1 | câmbio livre, dólar dos EUA (venda), diária, unidade monetária corrente/US$ | variação % da média diária de `t` contra a média de `t-1` | observações ao longo de `t`; no corte de 31/07/2026, 11 dias antes do IPCA de julho | candidata; arquivar vintage |
| juros | 432 | meta Selic, % a.a., diária | média diária em `t` | vigente e observável durante `t`; no corte de 31/07/2026, 11 dias antes do IPCA de julho | candidata; provável sinal lento |
| preços gerais | 189 | IGP-M, variação % mensal | valor de `t` | julho/2026: 30/07, 12 dias antes do IPCA de julho em 11/08 | candidata |
| energia e combustíveis agregados | 4449 | IPCA — preços administrados, variação % mensal | valor de `t` | divulgado com o próprio IPCA: vantagem 0 dia | **excluir: vazamento de alvo** |
| energia | 4453 | IPCA — preços monitorados — energia elétrica, variação % mensal | nenhuma | última observação em fev/2020; além disso integrava a divulgação do IPCA | **excluir: descontinuada e vazamento** |
| combustível | 4458 | IPCA — preços monitorados — gasolina, variação % mensal | nenhuma | última observação em fev/2020; além disso integrava a divulgação do IPCA | **excluir: descontinuada e vazamento** |

A expressão “PTAX (1)” do pedido é preservada como atalho de domínio; o nome
exato confirmado no catálogo SGS para a série 1 é “taxa de câmbio — livre —
dólar dos Estados Unidos (venda) — 1”. A modelagem e a proveniência devem usar
o nome oficial, não ampliar seu significado por suposição.

A defasagem de 14 dias do IPCA-15 é uma derivação do calendário oficial do
IBGE de 2026: para janeiro a julho, comparou-se a data do IPCA-15 do próprio
mês com a data posterior do IPCA cheio daquele mês. Para IGP-M foi medido o
caso verificável de julho de 2026 no calendário do FGV IBRE. Não se generaliza
esse único caso para toda a história. Para câmbio e Selic, “11 dias” é a
diferença entre o corte proposto de 31/07/2026 e 11/08/2026; não é uma alegação
de latência do SGS, que permanece **UNKNOWN** sem vintages capturados.

### 2.1 Últimos 12 valores devolvidos ou derivados

Valores percentuais usam ponto decimal. Os mensais abaixo são os últimos 12
disponíveis no corte; para as séries descontinuadas, são os últimos 12
históricos, não valores atuais.

| Série | Últimos 12 valores `AAAA-MM: valor` |
|---|---|
| 433, IPCA alvo (%) | 2025-08: -0.11; 2025-09: 0.48; 2025-10: 0.09; 2025-11: 0.18; 2025-12: 0.33; 2026-01: 0.33; 2026-02: 0.70; 2026-03: 0.88; 2026-04: 0.67; 2026-05: 0.58; 2026-06: 0.16; 2026-07: 0.07 |
| 7478, IPCA-15 (%) | 2025-08: -0.14; 2025-09: 0.48; 2025-10: 0.18; 2025-11: 0.20; 2025-12: 0.25; 2026-01: 0.20; 2026-02: 0.84; 2026-03: 0.44; 2026-04: 0.89; 2026-05: 0.62; 2026-06: 0.41; 2026-07: 0.06 |
| 189, IGP-M (%) | 2025-08: 0.36; 2025-09: 0.42; 2025-10: -0.36; 2025-11: 0.27; 2025-12: -0.01; 2026-01: 0.41; 2026-02: -0.73; 2026-03: 0.52; 2026-04: 2.73; 2026-05: 0.84; 2026-06: -0.50; 2026-07: -1.16 |
| 4449, administrados (%) | 2025-08: -0.61; 2025-09: 1.87; 2025-10: -0.16; 2025-11: 0.21; 2025-12: -0.22; 2026-01: 0.53; 2026-02: 0.17; 2026-03: 1.22; 2026-04: 1.00; 2026-05: 0.44; 2026-06: 0.29; 2026-07: 0.27 |
| 4453, energia elétrica (%) | 2019-03: 0.04; 2019-04: 0.10; 2019-05: 2.18; 2019-06: -1.11; 2019-07: 4.48; 2019-08: 3.85; 2019-09: 0.00; 2019-10: -3.22; 2019-11: 2.15; 2019-12: -4.24; 2020-01: 0.16; 2020-02: -1.71 |
| 4458, gasolina (%) | 2019-03: 2.88; 2019-04: 2.66; 2019-05: 2.60; 2019-06: -2.04; 2019-07: -2.80; 2019-08: -0.45; 2019-09: -0.04; 2019-10: 1.28; 2019-11: 0.42; 2019-12: 3.36; 2020-01: 0.89; 2020-02: -0.72 |

Para as duas séries diárias, estes são os últimos 12 valores **brutos** da API:

| Série | Últimos 12 valores `AAAA-MM-DD: valor` |
|---|---|
| 1, dólar venda | 2026-08-04: 5.1053; 2026-08-05: 5.1154; 2026-08-06: 5.1017; 2026-08-07: 5.0908; 2026-08-10: 5.0963; 2026-08-11: 5.1285; 2026-08-12: 5.1639; 2026-08-13: 5.1859; 2026-08-14: 5.2236; 2026-08-17: 5.2014; 2026-08-18: 5.2043; 2026-08-19: 5.1714 |
| 432, meta Selic (% a.a.) | 2026-08-08: 14.00; 2026-08-09: 14.00; 2026-08-10: 14.00; 2026-08-11: 14.00; 2026-08-12: 14.00; 2026-08-13: 14.00; 2026-08-14: 14.00; 2026-08-15: 14.00; 2026-08-16: 14.00; 2026-08-17: 14.00; 2026-08-18: 14.00; 2026-08-19: 14.00 |

As transformações mensais efetivamente correlacionadas, nos últimos 12 meses
com alvo disponível, foram:

| Feature derivada | 2025-08 a 2026-07, na ordem |
|---|---|
| dólar: variação % da média mensal contra mês anterior | -1.475402; -1.459810; 0.337537; -0.829510; 2.101505; -2.110126; -2.574120; 0.595500; -3.794477; -0.981011; 2.886840; -0.265693 |
| meta Selic: média diária mensal (% a.a.) | 15.000000; 15.000000; 15.000000; 15.000000; 15.000000; 15.000000; 15.000000; 14.895161; 14.741667; 14.500000; 14.391667; 14.250000 |

## 3. Análise simples de sinal

### Método reproduzível

1. Baixar 433, 7478, 1, 432, 189 e 4449 no intervalo iniciado em
   01/07/2021; usar os 60 meses fechados de agosto/2021 a julho/2026.
2. Converter `valor` para número decimal e `data` para data civil.
3. Manter as séries mensais no mês de referência. Para a série 1, calcular a
   média aritmética das observações diárias de cada mês e então
   `100 * (media_t / media_t-1 - 1)`. Para a 432, calcular a média aritmética
   de todos os valores diários do mês.
4. Fazer inner join por `AAAA-MM` com o alvo 433 do **mesmo mês**.
5. Calcular Pearson
   `r = sum((x-x_bar)(y-y_bar)) / sqrt(sum((x-x_bar)^2) sum((y-y_bar)^2))`,
   sem arredondar entradas; arredondar apenas a apresentação a seis casas.

| Candidata / controle | Janela comum | n | Pearson com IPCA 433 do mesmo mês | Leitura limitada |
|---|---|---:|---:|---|
| IPCA-15 7478 | 2021-08 a 2026-07 | 60 | **0.849742** | sinal contemporâneo forte; correlação não é Brier nem causalidade |
| dólar venda 1, transformação acima | 2021-08 a 2026-07 | 60 | -0.232849 | relação simples fraca e negativa nesta janela |
| meta Selic 432, média mensal | 2021-08 a 2026-07 | 60 | -0.420624 | política reage à inflação; sinal e causalidade se confundem |
| IGP-M 189 | 2021-08 a 2026-07 | 60 | 0.426858 | sinal moderado nesta janela |
| administrados 4449 | 2021-08 a 2026-07 | 60 | 0.730710 | controle positivo, mas indisponível antes do alvo: não entra |
| energia elétrica 4453 | 2015-03 a 2020-02 | 60 | 0.359618 | janela histórica diferente; série descontinuada e contemporânea ao alvo |
| gasolina 4458 | 2015-03 a 2020-02 | 60 | 0.431865 | janela histórica diferente; série descontinuada e contemporânea ao alvo |

As duas últimas correlações são mostradas para não esconder a consulta, mas
**não são comparáveis diretamente** às cinco primeiras, pois o período é outro.
Nenhuma correlação autoriza peso no WPAM. Em particular, 4449 demonstra por que
uma variável pode parecer boa e ainda assim ser inválida para nowcast.

## 4. Desenho proposto do primeiro desafiante

### 4.1 Modelo e features

Começar com regressão linear **ridge**, não deep learning. Duas especificações
pré-declaradas evitam uma busca oportunista grande:

- `R2`: IPCA-15 7478 + IGP-M 189;
- `R4`: as duas anteriores + depreciação mensal do dólar 1 + média mensal da
  meta Selic 432.

Todas as features serão padronizadas usando média e desvio calculados apenas na
janela de treino. O intercepto não será penalizado. O hiperparâmetro `alpha`
será escolhido dentro de cada fold, apenas entre `{0.01, 0.1, 1, 10, 100}`, por
validação temporal interna. Série 4449, eletricidade e gasolina ficam fora.

### 4.2 Janela e walk-forward

- janela de treino móvel: **120 meses imediatamente anteriores** ao mês
  previsto;
- mínimo para emitir: 120 linhas completas; ausência não recebe imputação
  silenciosa e produz `UNKNOWN`/sem sinal;
- avaliação: walk-forward de uma etapa, refazendo padronização, escolha de
  `alpha` e ajuste a cada mês;
- nenhuma observação do mês-alvo ou posterior entra no treino;
- todo fold grava meses de treino, corte de dados, URLs, hashes, parâmetros,
  previsão e resultado oficial.

Dez anos equilibram dois problemas: oferecem só 120 pontos, mas reduzem o peso
de regimes muito antigos. Isso é uma **recomendação a testar**, não um ótimo
medido. A comparação R2/R4 também é parte da validação; correlação isolada não
seleciona feature.

### 4.3 Da previsão pontual à probabilidade e ao Brier

Para cada claim `IPCA_t >= limiar_t`, o ridge produz `y_hat_t`. A probabilidade
deve ser derivada somente dos erros walk-forward anteriores do próprio modelo:

`p_t = (1 + quantidade de residuos_i >= limiar_t - y_hat_t) / (n_residuos + 2)`.

É a distribuição empírica de resíduos com suavização de Laplace. Antes de 24
resíduos fora da amostra, a probabilidade é `UNKNOWN` e o WPAM não recebe
sinal. O desfecho é `o_t = 1` se a série oficial 433 for maior ou igual ao
limiar e `0` caso contrário. O Brier na janela declarada é
`mean((p_t - o_t)^2)`.

O baseline Focus deve ser construído sem vantagem informacional: para cada mês,
usar a mediana Focus mais recente que já existia no **mesmo corte** do modelo,
reconstruída pelo campo de data da Olinda e arquivada com hash. A mediana é
convertida em probabilidade pela mesma regra empírica, usando apenas erros
Focus anteriores. Modelo e baseline são avaliados nos mesmos meses, limiares e
desfechos. Sem vintage Focus reproduzível, o Brier comparativo é **BLOCKED**, não
estimado por dados revistos.

Relatar pelo menos `n_meses`, início/fim, cobertura, Brier do ridge, Brier Focus,
diferença pareada média e `skill = 1 - Brier_ridge / Brier_focus`. Se o Brier
Focus for zero, skill é indefinida; registrar o fato e não dividir.

### 4.4 Por que não deep learning agora

Há 12 observações novas por ano. Mesmo uma janela de dez anos contém só 120
linhas antes de reservar qualquer avaliação. Uma rede adicionaria muitos graus
de liberdade, instabilidade e custo de explicação sem evidência de ganho.
Ridge oferece coeficientes inspecionáveis, regularização explícita e reprodução
barata. Deep learning só volta à pauta se houver muito mais observações
legítimas de maior frequência, validação walk-forward e ganho de Brier fora da
amostra contra ridge e Focus. “Deep learning platform” descreve a categoria;
não substitui evidência.

## 5. Integração no registry `ml_*`

Quando existir implementação e uma corrida real — não nesta exploração — a
ordem obrigatória é:

1. `registrar_modelo(Modelo(...))`, com `modelo_id="ipca-nowcast-linear"`, área
   e objetivo explícito;
2. `registrar_versao(Versao(...))`, cuja origem nomeie commit, especificação,
   código e manifesto dos snapshots;
3. `registrar_corrida(Corrida(...))`, com janela, corte, conjunto R2/R4,
   `alpha`, limiares, métricas e artefatos SHA-256;
4. somente após corrida concluída e selada,
   `promover(modelo_id=..., versao=..., papel="desafiante", motivo=...,
   promovido_em=...)`.

Registrar como `desafiante` **não** concede peso, não substitui Focus e não o
torna campeão. Falha de selagem deve impedir o registro, conforme o contrato
atual de `src/asus_theye/mlops/rastreio.py`. Artefatos mínimos da corrida:
manifesto de dados/vintages, matriz de folds, previsões por mês/limiar,
resíduos, métricas pareadas, coeficientes por fold e relatório de limitações.

## 6. Porta para ganhar peso no WPAM

Proposta: **N = 24 meses consecutivos resolvidos fora da amostra**, contados
após o congelamento da versão. Vinte e quatro meses cobrem duas voltas do ciclo
sazonal e fornecem 24 decisões mensais independentes no tempo; ainda é uma
amostra pequena, razão pela qual a regra é porta mínima, não prova definitiva.

O sinal fica com peso zero até satisfazer simultaneamente:

- 24 meses consecutivos e sem substituição retroativa de versão;
- cobertura completa nos mesmos claims avaliados pelo Focus;
- `Brier_nowcast <= Brier_focus` na janela pareada completa;
- nenhum vazamento temporal ou hash de artefato ausente;
- aprovação humana registrada para alterar o peso.

Cumprir a porta apenas torna o peso **elegível**. O valor do peso é `UNKNOWN`
até ser medido e aprovado; esta especificação não inventa `5`, `10` ou outro
número. Mesmo depois disso, o modelo permanece desafiante. Promoção a campeão
exigiria decisão separada, evidência adicional e a aprovação de governança.

## 7. Registro auditável das conclusões materiais

| Questão | Classe e conclusão | Evidência primária / melhor evidência contrária | Justificativa, confiança e limitações | O que mudaria a conclusão |
|---|---|---|---|---|
| Os códigos e valores existem? | **FACT:** 433, 7478, 1, 432, 189, 4449, 4453 e 4458 responderam; 4453/4458 terminam em fev/2020. | API BCData consultada e catálogo SGS oficial; contrário: API não expõe instante de publicação. | Confiança alta para identidade/valor no corte; baixa para vintage. | Metadado oficial corrigido ou resposta reproduzível divergente. |
| Há sinal linear contemporâneo? | **DERIVED:** correlações da seção 3. | Respostas SGS + fórmula e alinhamento declarados; contrário: só 60 meses, regime específico e correlação não causal. | Confiança alta no cálculo, moderada/baixa na estabilidade futura. | Reexecução com mesmos dados não reproduzir; outras janelas inverterem materialmente o sinal. |
| 4449, 4453 e 4458 servem ao nowcast? | **FACT/INFERENCE:** não, no desenho atual. | Catálogo SGS e calendário: são componentes divulgados com o alvo; 4453/4458 ainda estão descontinuadas. | Confiança alta; correlação positiva é a principal evidência contrária, mas resulta de informação indisponível no corte. | Nova série antecedente oficial, com publicação comprovadamente anterior e vintages auditáveis. |
| Ridge deve vir antes de DL? | **RECOMMENDATION:** sim. | Frequência de 12 pontos/ano e auditabilidade; contrário: relações podem ser não lineares. | Confiança moderada; nenhum modelo foi treinado. | DL superar ridge e Focus em walk-forward legítimo, com dados suficientes e complexidade justificada. |
| A janela de 120 meses é ótima? | **UNKNOWN/RECOMMENDATION:** é ponto de partida, não ótimo. | Compromisso entre 120 amostras e mudança de regime; contrário: janelas menores adaptam mais rápido, maiores estabilizam. | Confiança baixa até backtest. | Validação temporal pré-declarada favorecer consistentemente outra janela. |
| Quando conceder peso? | **RECOMMENDATION:** após 24 meses e a porta completa. | Dois ciclos sazonais e comparação pareada com Focus; contrário: 24 observações ainda têm baixo poder. | Confiança moderada como guarda mínima, não como prova estatística. | Política de risco aprovada exigir janela maior ou evidência pareada mais forte. |
| Qual é a latência real do SGS? | **UNKNOWN.** | O payload tem referência, não `published_at`; calendários dão datas de divulgação, não ingestão no SGS. | Não estimar. | Captura prospectiva e hash-chain estabelecerem timestamps por fonte. |

## 8. Fontes consultadas

- Banco Central do Brasil, API pública BCData/SGS:
  `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados`;
  consultas reais descritas nas seções 2 e 3.
- Banco Central do Brasil, catálogo público SGS: [433 — IPCA](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?hdOidSeriesSelecionadas=433&method=consultarGraficoPorId),
  [7478 — IPCA-15](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?hdOidSeriesSelecionadas=7478&method=consultarGraficoPorId),
  [1 — dólar venda](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?hdOidSeriesSelecionadas=1&method=consultarGraficoPorId),
  [432 — meta Selic](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?hdOidSeriesSelecionadas=432&method=consultarGraficoPorId),
  [189 — IGP-M](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?hdOidSeriesSelecionadas=189&method=consultarGraficoPorId),
  [4449 — administrados](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?hdOidSeriesSelecionadas=4449&method=consultarGraficoPorId),
  [4453 — energia elétrica](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?hdOidSeriesSelecionadas=4453&method=consultarGraficoPorId) e
  [4458 — gasolina](https://www3.bcb.gov.br/sgspub/consultarvalores/consultarValoresSeries.do?hdOidSeriesSelecionadas=4458&method=consultarGraficoPorId).
- IBGE, [calendário de indicadores conjunturais de 2026](https://www.ibge.gov.br/calendario/conjunturais.html)
  e páginas oficiais do [IPCA-15](https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9260-indice-nacional-de-precos-ao-consumidor-amplo-15.html)
  e do [IPCA](https://www.ibge.gov.br/estatisticas/economicas/precos-e-custos/9256-indice-nacional-de-precos-ao-consumidor-amplo.html).
- FGV IBRE, [calendário de divulgação](https://portalibre.fgv.br/calendario-de-divulgacao),
  consultado para o IGP-M de julho de 2026.
- Repositório local: `src/asus_theye/markets/sinais_ipca.py` (Focus peso 20;
  IPCA-15 peso 10) e `src/asus_theye/mlops/rastreio.py` (registro, corrida e
  papel desafiante), ambos inspecionados em 19/08/2026.

---

© 2026 Mateus Menezes Figueiredo. Código do projeto sob AGPL-3.0; dados e
curadoria sujeitos às licenças próprias indicadas no repositório.
