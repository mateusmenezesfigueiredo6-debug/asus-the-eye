# Despachantes e plataformas de autorizacao ANVISA — panorama e recomendacao

Resposta a pergunta: existem apps/servicos de despachantes que
automatizam o pedido de autorizacao (RDC 660) e quais servem ao projeto
Gota Verde. Pesquisado em 25/08/2026 em fontes publicas; o que nao pode
ser confirmado esta marcado como NAO CONFIRMADO. Nenhuma das plataformas
abaixo publica API aberta ou intake por email documentado — a integracao,
quando existe, e comercial e negociada caso a caso.

## 1. Fato central sobre a "automacao"

O proprio fluxo do Gov.br ja e quase instantaneo: seguindo os passos
corretos no portal, a autorizacao RDC 660 sai de forma automatica, sem
analise humana, em minutos (nos casos limpos; casos com pendencia caem
em analise de ate 10 dias uteis). Ou seja: o valor dos "despachantes"
nao esta em burlar fila — esta em preencher certo na primeira vez,
anexar a receita no formato aceito e acompanhar pendencias. E exatamente
o que o nosso wizard /api/autorizacao + despachante humano ja faz.

## 2. Quem existe no mercado

| Servico | Modelo | O que faz | Relevancia para o projeto |
|---|---|---|---|
| Blis (appblis.com.br) | App B2C, criado por pacientes | Consulta por chat, receita digital, autorizacao ANVISA "automatica" em minutos, importacao e entrega; 500 mil+ downloads, 1.800+ cidades | Benchmark de UX do nosso app; concorrente direto no B2C |
| Cannect (cannect.life) | Healthtech B2C/B2B2C, 100 mil+ pacientes | Jornada completa: consulta, indicacao de produto, autorizacao de importacao; absorveu a Dr. Cannabis (educacao medica, 12 mil+ medicos) | Benchmark de escala; possivel canal de medicos prescritores |
| CannaCare (cannacare.com.br) | Parceiro operacional do MEDICO | Assume o pos-prescricao: autorizacao ANVISA, importacao, entrega e acompanhamento do paciente do medico | Modelo mais proximo do nosso: e um "despachante white label" para consultorios. Candidato a parceria ou referencia de proposta comercial |
| Cannalink (cannalink.com.br) | Assessoria de importacao | Assessoria a pacientes no processo de importacao | NAO CONFIRMADO em detalhe (site bloqueado na sessao); verificar antes de contactar |
| CANNAID (cannaid.app) | App de acesso | Jornada de acesso a cannabis medicinal | NAO CONFIRMADO em detalhe |
| SouCannabis (ONG) | Associacao com tutorial publico | Publica passo a passo gratuito do pedido no Gov.br | Referencia de conteudo educativo para nossa area do paciente |

Sobre "API de despachante": nenhum dos servicos acima publica API
publica ou endereco de intake por email documentado. A automacao que
anunciam e interna (robotizacao do proprio fluxo deles ou operacao
humana rapida). Integracao com terceiros existe apenas como parceria
comercial negociada. UNKNOWN: termos e precos de parceria — so se
descobrem em contato comercial direto.

## 3. Recomendacao para a Gota Verde

1. Nao terceirizar o intake: o wizard proprio (site + app) ja coleta e
   formata tudo; terceirizar entregaria o relacionamento com o paciente
   ao concorrente.
2. Despachante humano proprio com procuracao continua sendo o motor:
   com o pacote formatado, o protocolo no Gov.br leva minutos e a
   autorizacao dos casos limpos sai quase na hora.
3. Parceria a explorar (nessa ordem): CannaCare (modelo operacional
   compativel, serve medicos que ja prescrevem — pode operar a
   logistica dos nossos pacientes no inicio); Cannect/Dr. Cannabis
   (canal de recrutamento de medicos treinados); Blis apenas como
   benchmark — e concorrente, nao parceiro.
4. Nunca robotizar o login Gov.br do paciente: viola os termos do
   portal e usa credencial alheia. A linha ja tracada permanece.

## 4. O novo marco de 2026 muda o tabuleiro

Entre 30/01 e 03/02/2026 a ANVISA publicou as RDCs 1.011 a 1.015/2026,
em vigor desde 04/08/2026:

- RDC 1.012 — pesquisa cientifica com cannabis (universidades, ICTs e
  industria, com Autorizacao Especial e requisitos de seguranca).
- RDC 1.013 — cultivo nacional de Cannabis sativa (THC ate 0,3%) por
  EMPRESAS para fins medicinais, com AE.
- RDC 1.014 — Sandbox Regulatorio EXCLUSIVO para associacoes de
  pacientes sem fins lucrativos: ambiente experimental de ate 5 anos,
  sob supervisao direta da ANVISA, sem comercializacao. Requisito de
  corte: pessoa juridica constituida ha no minimo 2 anos na data da
  publicacao da RDC. A entrada depende de edital de chamamento publico
  aprovado pela Diretoria Colegiada — ainda nao publicado ate
  25/08/2026.

Consequencias para o roadmap:

- A associacao Gota Verde, fundada agora, NAO alcanca o requisito de 2
  anos deste primeiro sandbox. O HC preventivo continua sendo a via de
  cultivo realista no horizonte de 1 a 2 anos — e o historico RDC 660
  continua sendo o combustivel do HC.
- Monitorar o edital do sandbox e cada novo chamamento: um segundo
  ciclo pode ter corte diferente, e a associacao deve nascer ja com a
  papelada no formato que o edital pedir (mais um argumento para a
  trilha de evidencia auditavel).
- A RDC 1.013 abre, em paralelo, a via EMPRESARIAL de cultivo nacional
  — relevante para a fase comercial do grupo (empresa, nao associacao),
  com custo regulatorio de industria farmaceutica.

## 5. Fontes

- Gov.br — servico "Solicitar autorizacao para importacao de produtos
  derivados de Cannabis" (gov.br/pt-br/servicos/...)
- Medicina S/A — novo marco regulatorio da ANVISA (medicinasa.com.br)
- RDC 1.014/2026 no Datalegis (anvisalegis.datalegis.net)
- APEPI — noticia sobre a RDC das associacoes (apepi.org)
- Sites das plataformas: appblis.com.br, cannacare.com.br,
  cannalink.com.br, cannaid.app, soucannabis.ong.br
- Sinteses de mercado: fitocanabica.com.br, smokebuddies.com.br,
  vitapharmaconsulting.com

Nota de auditoria: cannalink.com.br, cannaid.app e cannabisesaude.com.br
estavam inacessiveis pela rede desta sessao; os dados dessas fontes vem
de resultados de busca e devem ser reconferidos antes de qualquer
contato comercial.
