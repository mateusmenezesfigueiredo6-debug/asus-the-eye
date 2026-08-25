# Proveniência — termos da OpenAI e da Anthropic no caminho remoto de LLM

Registro da análise dos termos dos **dois terceiros** para quem
`asus_theye.llm.remote_client` envia conteúdo do titular quando a porta
`THE_EYE_REMOTE_LLM=1` é aberta.

Este arquivo existe porque o projeto já fez exatamente esta análise uma vez, para
a Kalshi (`Kalshi-dados-expurgo.md`), e o resultado foi expurgo. A mesma pergunta
nunca tinha sido feita sobre os provedores de modelo — e eles recebem mais do que
a Kalshi jamais recebeu: recebem o texto do titular.

A conclusão é diferente da conclusão da Kalshi, e o motivo dessa diferença é o
conteúdo deste registro.

## A pergunta

Quando a porta é aberta, o prompt e o prompt de sistema saem desta máquina para
`api.openai.com` e `api.anthropic.com`. Quatro perguntas decidem se isso é
compatível com a política de direitos do projeto:

1. Quem é dono do que **volta** (o Output)?
2. O terceiro **treina** modelo com o que recebe?
3. Por quanto tempo ele **retém** o que recebe?
4. O uso **comercial** é permitido?

## O que foi lido, e o que não foi

| Provedor | Documento | Como foi lido | Data |
|---|---|---|---|
| Anthropic | *API and data retention* (`platform.claude.com/docs/en/manage-claude/api-and-data-retention`) | **fonte primária, lida integralmente** | 23/08/2026 |
| Anthropic | *Commercial Terms of Service* (`anthropic.com/legal/commercial-terms`) | **NÃO LIDA** — domínio bloqueado pela política de egresso deste ambiente | — |
| OpenAI | *Business terms* / *Enterprise privacy* (`openai.com/policies/business-terms`, `openai.com/enterprise-privacy`) | **NÃO LIDAS** — domínio bloqueado pela política de egresso deste ambiente | — |

Isto importa e não se disfarça: **só a linha de retenção da Anthropic tem fonte
primária.** O resto veio de busca, que devolve resumo de terceiro sobre o
documento, não o documento. A regra do projeto é não afirmar o que não foi
medido, então cada item abaixo carrega a sua classe de alegação.

## O que a fonte primária diz — Anthropic, retenção (FACT)

Citações textuais da página lida:

- *"Retained data is never used for model training without your express
  permission."*
- *"Conversation content (your prompts and Claude's outputs) is not retained by
  default; the exception is Covered Models, which require 30-day retention."*
- Retenção zero (ZDR) existe, é habilitada **por organização** e mediante
  pedido ao time comercial da Anthropic.
- *"Claude Fable 5 and Claude Mythos 5 are designated Covered Models (...) and
  require 30-day data retention; ZDR is therefore not available for either
  model."*

**Consequência direta para este projeto (DERIVED):** o modelo padrão daqui é
`claude-opus-5`, que **não** está na lista de Covered Models. A escolha padrão
preserva a opção de retenção zero. Trocar `THE_EYE_ANTHROPIC_MODEL` para
`claude-fable-5` ou `claude-mythos-5` abre mão dessa opção e passa a obrigar 30
dias de retenção do texto do titular.

Essa troca deixou de ser silenciosa: `_require_retention_consent` recusa um
Covered Model a menos que `THE_EYE_ACCEPT_RETENTION=1` seja definida. A decisão
continua sendo do titular; ela apenas não acontece mais por descuido.

## O que a busca indica, e ainda precisa de verificação (UNKNOWN)

Os pontos abaixo **não foram lidos na fonte** e não sustentam afirmação do
projeto até que o titular os confirme diretamente:

| Item | O que a busca indica | Classe |
|---|---|---|
| Propriedade do Output — OpenAI | cliente mantém direitos sobre o Input e é dono do Output | UNKNOWN |
| Treinamento — OpenAI | não treina com dado de API por padrão | UNKNOWN |
| Retenção — OpenAI | até 30 dias, depois removido; ZDR mediante elegibilidade | UNKNOWN |
| Propriedade do Output — Anthropic | a Anthropic cede ao cliente o direito que porventura tenha sobre os Outputs | UNKNOWN |

**O que mudaria a conclusão:** o titular abrir as duas páginas de termos de uma
máquina sem a restrição de egresso e confirmar (ou desmentir) cada linha. Até
lá, elas são indicação, não fundamento.

## Por que isto NÃO leva a expurgo, ao contrário da Kalshi

A diferença é de direção, e é inteira:

- Os termos da Kalshi **proibiam os verbos que o pipeline praticava** —
  armazenar, exibir publicamente, derivar, e desenvolver software. O uso era
  incompatível com o produto por construção.
- Aqui, pela evidência disponível, os provedores **atribuem ao cliente** o que
  volta e **não treinam** com o que recebem por padrão. Não há verbo proibido
  sendo praticado.

Some-se a isso o que o projeto faz por conta própria: o registro de auditoria
grava **apenas hashes** de prompt e resposta, nunca o texto. Nada de conteúdo
alheio entra no produto — o que satisfaz o item 5 da política de direitos pelo
mesmo mecanismo que já satisfazia no grafo de fontes.

## O que este caminho garante ao titular

O que o projeto pode **provar sozinho**, sem depender da palavra de nenhum
provedor: para toda chamada remota, a corrente encadeada registra o provedor, o
modelo real devolvido pela API, o instante, a duração, a contagem de tokens e os
hashes SHA-256 do prompt, do prompt de sistema e da resposta.

Isso sustenta a autoria declarada em `POLITICA_DIREITOS.md`: o titular consegue
demonstrar **o que** mandou, **quando**, **para quem** e **o que voltou**, com
prova criptográfica, sem que o texto tenha saído da máquina em claro para o
próprio registro.

## Limite que continua aberto

A proibição de mandar dado da Fase G (contexto decisório judicial, LGPD) por
este caminho está escrita no cabeçalho do `remote_client.py` e aqui — mas
**continua sendo documentação, não trava**. Nada no código impede alguém de
passar esse conteúdo. Registrado como lacuna conhecida; fechá-la é trabalho em
aberto.
