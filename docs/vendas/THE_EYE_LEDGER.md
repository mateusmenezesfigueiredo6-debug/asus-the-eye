# THE EYE Ledger

## Cadeia auditável e ontologia de evidência

O THE EYE Ledger transforma operações críticas em evidência verificável. Em vez de pedir confiança em um painel ou banco controlado pelo fornecedor, entrega uma trilha que relaciona evento, artefato, fonte e prova criptográfica.

### Um evento que denuncia alteração

Cada evento é validado com **37 campos obrigatórios antes da selagem**. O hash selado é o 38º campo do schema. A representação JSON é canonicalizada conforme RFC 8785 e resumida com SHA-256. Cada evento aponta para o hash anterior, com sequência isolada por tenant.

O efeito prático é direto: mudar conteúdo, metadados, ordem ou vínculo quebra a verificação. Correções entram como novos eventos; não reescrevem silenciosamente o passado.

### Linhagem, não apenas log

O painel `/evidencia` apresenta a linhagem de cada evento selado até a fonte primária. A ontologia conecta Fonte, Mercado, Resolução, Evento Selado, Lote Merkle e Âncora, deixando visível onde a prova chega e onde ainda é parcial.

Artefato e Recibo já são entidades reais no painel. O primeiro Artefato preserva a resposta bruta da série SGS 433 do BCB, com SHA-256 `5aeb3a97…`, e a relaciona à Fonte. O Recibo materializa o resultado do verificador, atesta o topo da corrente e informa honestamente `not_anchored`. A indicação “Fonte provada + ancorada” continua **em roteiro**: corrente íntegra não é sinônimo de conteúdo verdadeiro nem de prova on-chain concluída.

### Verificação independente, local e pública

Qualquer clone do repositório pode executar `verify_chain` e conferir sozinho a integridade e a continuidade da corrente. Há também um verificador offline, acionado por `asus-theye audit-verify`, que produz recibo de verificação.

No corte selado da medição de 19/08, a corrente tinha 25 eventos. O espelho no Cloudflare D1 é idempotente por `event_hash`: o artefato versionado comprova oito espelhos e uma segunda sincronização sem duplicatas. A confirmação remota de todos os 25 não está registrada no repo e, portanto, não é afirmada aqui. O verificador público está no ar e valida a corrente real sem credencial; seu contrato de leitura expõe verificação e, quando existirem, raízes confirmadas, sem publicar documentos ou dados pessoais.

O roteiro dos dois produtos também é dado auditável, não apresentação editável sem rastro. A medição selada de 19/08 registra **71,7%** dos pesos concluídos; o evento tem hash público `980078bd…` e referencia o hash de conteúdo `4cc419eb…`. Alterar o roteiro muda o hash e exige um novo evento.

### Ancoragem pronta, transmissão pendente

O contrato para Base Sepolia está compilado e testado, e o ensaio offline foi concluído. A transmissão da primeira raiz Merkle aguarda gás de teste via faucet do proprietário e está **em roteiro**. Até isso ocorrer, o produto não afirma que a corrente esteja ancorada on-chain.

### Para operações em que “confie em nós” não basta

O THE EYE Ledger atende sistemas que precisam demonstrar proveniência, sequência e integridade de decisões, modelos, documentos e resultados. É uma base de evidência no padrão arquitetural da categoria Palantir: relações explícitas, linhagem até a fonte primária e recusa em afirmar o que a prova ainda não sustenta.

---

© 2026 Mateus Menezes Figueiredo, AGPL-3.0.
