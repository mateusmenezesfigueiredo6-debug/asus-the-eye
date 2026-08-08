# Contradições — uma plataforma, 12 recortes de medição

## X101 — 100% de arquivos não significa projeto completo

Onze recortes têm todos os artefatos declarados, mas a medição não valida
conteúdo, testes, dados reais, produção ou aprovação L0-L6. O percentual deve ser
lido somente como presença dos caminhos.

## X102 — Toque estrutural versus avanço de domínio

O commit `1666450` de 03/08 toca vários recortes ao reorganizar o layout para
`src/`. O Git o conta; a análise substantiva não o trata como evolução funcional
em cada recorte. O relatório mostra as duas datas.

## X103 — “145 nichos” versus 145 áreas

O nome do projeto taxonômico usa “145 nichos”, mas seu arquivo contém áreas. A
operação tem 15 nichos que agregam 39 dessas áreas. Cobertura e quantidade de
produtos não são medidas equivalentes. THE EYE continua sendo uma plataforma
única; nichos são uma opção de entrada no mercado, não sua arquitetura.

## X104 — Fonte única versus equivalência por área

O recorte atual consulta Querido Diário para todos os nichos, mas isso não prova
que o corpus seja adequado a cada área nem que exista uma fonte equivalente para
as demais. Sem critérios de cobertura e resolução, a contagem é UNKNOWN.

## X105 — Número de variáveis versus dificuldade efetiva

A QKP tem 138 variáveis, mas isso não basta para classificá-la como difícil. Os
pesos são unitários, a capacidade efetiva é 13 e as sinergias positivas existem
somente dentro dos grupos taxonômicos. Para cada quantidade escolhida num grupo,
os maiores valores dominam; uma DP entre 22 grupos prova o ótimo 39.087. A
dimensão bruta não justifica QPU.

## X106 — Ótimo matemático versus sinal comercial confiável

O recozimento encontrou e a DP confirmou o ótimo da formulação. Ainda assim,
quatro das 13 áreas escolhidas usam termos marcados como genéricos e concentram
77,8% da demanda-base da seleção. Sem os seis termos suspeitos do conjunto, o
ótimo cai 52,6%. Correção matemática não implica validade do proxy.

## X107 — Resultado relatado versus artefato auditável

O quadro afirma resultados QAOA para N=10, 14 e 16, mas o JSON oficial de
escalada mantém score, tempo e qualidade QAOA como `null` nessas linhas. Sem
comando, log e saída persistida, os percentuais são `UNKNOWN`. A recomendação de
não usar QPU continua sustentada pela DP exata, independentemente desse relato.

## X108 — Verificador Python de recorte versus continuidade até a gênese

`verify_chain` inicia a sequência esperada no primeiro evento recebido e pode
validar um recorte que comece depois de 1. A tarefa da superfície pública exige
explicitamente ausência de buracos até a gênese. O Worker público começa sempre
em sequência 1 e exige `previous_event_hash_sha256` igual aos 64 zeros; isso é
uma restrição adicional documentada, não uma mudança silenciosa no núcleo.

## X109 — Binding D1 versus privilégio SQL somente leitura

O código do Worker contém apenas `SELECT` e não expõe uma rota de SQL, mas um
binding D1 não é, por si só, uma função de banco restrita a leitura. Portanto,
“somente leitura” está confirmado como propriedade da implementação local, não
como controle de infraestrutura independente. Um banco/serviço de réplica
somente de raízes reduziria esse risco após decisão de publicação.
