# Proveniência — expurgo dos dados da Kalshi (decisão de conformidade)

Registro da decisão de **remover** dado de terceiro do projeto, e do porquê.
Este arquivo é o par do `Kalshi-calibration-method.md`: aquele registra a leitura
de uma **publicação** (que continua permitida e continua valendo); este registra
a remoção dos **dados de mercado**, que é caso diferente.

## O que foi lido

| campo | valor |
|---|---|
| Documento | *Kalshi Data Terms of Use* |
| Onde | `https://kalshi-public-docs.s3.amazonaws.com/kalshi-data-terms-of-service.pdf` |
| Lido em | 20/08/2026 |

## O que os termos dizem

Os pontos que decidem o caso, em resumo (o documento é a fonte, não este texto):

- o acesso é permitido apenas para **uso pessoal e não-comercial**;
- "não-comercial" **exclui explicitamente** o desenvolvimento de qualquer
  programa de software, e o fornecimento de conjuntos de dados arquivados ou
  em cache a terceiros;
- estão proibidos, sem autorização escrita prévia: coletar, copiar, armazenar,
  transmitir, distribuir, **exibir publicamente**, publicar, **compilar por
  recuperação sistemática** em coleções ou bases de dados, e **criar obras
  derivadas**;
- há vedação específica a uso para treinar ou operar sistemas de IA/ML;
- a seção de propriedade declara que nenhum direito é transferido ao usuário.

## Por que isso conflita com este projeto

O pipeline daqui **buscava** o preço, **gravava** em `comparador.jsonl`,
**selava** na corrente, **espelhava** e **exibiria** em painel — e o projeto é
software destinado a virar produto. Quase todos os verbos da lista proibida
descrevem o que fazíamos.

**Ambiguidade declarada, não escondida:** os termos falam de conteúdo do *site*
`kalshi.com`, e o consumo era de `external-api.kalshi.com`. Se os termos do site
governam a API é questão jurídica que este registro **não resolve** — e a
incerteza, por si só, é motivo suficiente para não construir produto em cima.

## A decisão do titular

Trocar o comparador por fonte de licença compatível e **expurgar** o dado já
coletado. Alternativas consideradas e descartadas: pedir autorização escrita
(possível, mas dependeria de resposta de terceiro); manter sem persistir (não
elimina, já que "desenvolvimento de software" é excluído do uso permitido).

**Metaculus foi avaliado e descartado**: os termos dele são igualmente
restritivos (licença pessoal e não-comercial, redistribuição proibida).
**Manifold Markets** é substancialmente mais permissivo — leitura sem
autenticação, bots e integrações explicitamente permitidos, restrição apenas a
treinar IA com fim comercial — e fica como candidato secundário.

**O substituto escolhido é o consenso Focus do Banco Central**, e ele é melhor
por dois motivos independentes da questão jurídica:

1. é **dado público** de banco central, da mesma família de fontes que já usamos
   para *resolver* (BCB/SGS/Olinda);
2. é comparação **direta**. A nota de mapeamento que nós mesmos havíamos escrito
   admitia que a comparação com a Kalshi era *indireta*: o contrato dela media o
   CPI dos Estados Unidos, o nosso mede o IPCA do Brasil — países e índices
   distintos, que não respondem à mesma pergunta.

## O que foi removido, e como

O expurgo usou `src/asus_theye/audit/redacao.py`, criado para isto e reutilizável:

| item | destino |
|---|---|
| Observação em `comparador.jsonl` | removida; recibo selado como `data.redaction` |
| `markets/fonte_kalshi.py` + testes | removidos |
| `docs/architecture/KALSHI_COMPARATOR_API.md` | removido |
| Busca ao vivo na CLI `markets-comparar` | removida |
| Ticker e preços reais em fixtures e docs | substituídos por valores sintéticos |
| Fase M4 em `produtos.json` | rebaixada de 1,0 para 0,5, com o motivo declarado |

**Por que a corrente não foi reescrita.** A corrente guarda apenas o
`content_hash_sha256`, nunca o conteúdo em claro. Remover a linha do store apaga
o dado de verdade e não toca em nenhum hash: o encadeamento permanece íntegro e
a âncora on-chain (que compromete a raiz Merkle dos eventos) continua válida.
Remover o *evento* e re-selar seria o pior dos mundos — quebraria a âncora e
faria a prova temporal acusar adulteração, ou seja, a plataforma testemunharia
contra si mesma por ter feito a coisa certa.

**Verificado após o expurgo:** 78 eventos, `verify_chain=True`, evento original
preservado, recibo selado, e zero ocorrências do ticker ou dos preços no
repositório. O `hash_do_removido` no recibo coincide com o `content_hash_sha256`
que o evento original selou — prova de identidade do material sem manter cópia.

**Nada foi transmitido a terceiro:** `corpo_do_espelho` em
`audit/sync_ledger.py` envia ao D1 apenas hashes, sequência e timestamps. Nenhum
dado da Kalshi saiu da máquina do titular.

## O que continua permitido e não foi tocado

Ler as **publicações** de pesquisa da Kalshi, interpretar conceitos e
reimplementar de forma independente — registrado em
`Kalshi-calibration-method.md`. Ler não é copiar, e conceito não é dado.
Citar o nome da empresa em texto próprio também permanece.

---

© 2026 Mateus Menezes Figueiredo — projeto ASUS THE EYE, AGPL-3.0-or-later.
Este registro descreve uma decisão de conformidade; não é parecer jurídico.
