# Politica de direitos: nada se paga a terceiro

Decisao do titular, registrada em 08/08/2026: **o projeto nao paga royalty,
assinatura de dado, licenca de software nem direito autoral a ninguem.** Tudo
que entra e de fonte livre, e a autoria de tudo que sai e do titular.

Isto nao e economia de custo apenas. E condicao de existencia: uma plataforma
de verificacao cujo dado depende de assinatura paga nao pode ser auditada por
quem nao paga, e uma plataforma preditiva que aluga a materia-prima nao e dona
do proprio produto.

Copyright (c) 2026 Mateus Menezes Figueiredo.

## O que isso proibe

1. **Dado pago.** Nenhuma assinatura de base comercial. Onde o dado so existe
   atras de pagamento, a lacuna e registrada como lacuna, com o motivo
   `requires_paid_api`, e o numero fica `UNKNOWN`. Nunca se estima o que se
   deixou de comprar. Ja registrados assim: volume de vendas de livros
   (Circana BookScan, Nielsen BookData) e producao cientifica em escala para
   ranquear universidades.
2. **Dependencia de runtime.** O `pyproject.toml` declara
   `dependencies = []` — a plataforma roda na biblioteca padrao do Python.
   Cada dependencia nova e uma licenca de terceiro entrando no produto e um
   fornecedor com poder sobre ele. Acrescentar exige justificativa escrita e
   licenca permissiva ou copyleft compativel com AGPL-3.0.
3. **Ativo de midia licenciado.** Nenhuma fonte tipografica, icone, imagem ou
   trilha com cobranca. As paginas usam pilha de fontes do sistema
   (`ui-sans-serif, system-ui`) e desenho proprio em CSS e SVG, sem CDN.
4. **Servico externo com custo.** Nenhum recurso pago criado sem decisao do
   dono — ja e regra em `COORDENACAO.md`, item 5 do que nenhum agente faz
   sozinho.
5. **Conteudo de terceiro reproduzido.** Nao se copia texto protegido para
   dentro do produto. O grafo de fontes guarda identificador, URL oficial e
   hash da resposta — ponteiro e prova, nunca o conteudo alheio.

## O que isso permite, e ja e a base do projeto

Fontes livres, sem chave e sem cobranca, com licenca compativel:

| Fonte | O que da | Licenca |
|---|---|---|
| ROR | instituicoes de pesquisa, identificador estavel | CC0-1.0 |
| Crossref | metadado de publicacao com DOI | aberta |
| arXiv | preprints | aberta, por artigo |
| DOAJ | periodicos de acesso aberto verificados | aberta |
| OpenAlex | producao cientifica em escala, dump CC0 no S3 | CC0 |
| Querido Diario | diarios oficiais municipais brasileiros | dado publico |
| DataJud, LexML | dado judicial e legislativo brasileiro | dado publico |
| ~~Kalshi trade-api/v2~~ | **PROIBIDA desde 20/08/2026** | Os Data Terms of Use restringem a uso pessoal e nao-comercial, excluem desenvolvimento de software, e proibem armazenar, exibir publicamente e derivar. Sem autenticacao NAO significa sem restricao. Ver `reports/provenance/Kalshi-dados-expurgo.md`. |
| World Bank Open Data | indicadores macro de dezenas de paises | **CC-BY 4.0** — permite uso comercial; atribuicao viaja no proprio dado |

Ato publicado em diario oficial e publico por definicao legal. Dado de governo
brasileiro e publico pela Lei de Acesso a Informacao. Nenhum deles cobra, e
nenhum deles cria dependencia de fornecedor.

## Autoria do que sai

Todo codigo produzido neste projeto — inclusive o escrito por agentes, seja
Claude ou Codex — e obra do titular. Os agentes assinam como
`Co-Authored-By` no commit por transparencia de processo, o que registra COMO
o trabalho foi feito e nao transfere titularidade alguma.

O licenciamento e AGPL-3.0 para codigo e licenca restrita para dados, com o
titular detendo a totalidade dos direitos e podendo conceder licenca comercial
em separado. Ver `LICENSE.md`.

## Registro formal

Registro de programa de computador no INPI ou deposito na Biblioteca Nacional
exigem formulario com dado pessoal do autor. Esse formulario e preenchido pelo
proprio titular, diretamente no orgao. Documento de identidade e CPF nao entram
neste repositorio, nem em commit, nem em pagina gerada: repositorio se clona,
se espelha e se publica, e dado pessoal em historico de git nao se apaga.
