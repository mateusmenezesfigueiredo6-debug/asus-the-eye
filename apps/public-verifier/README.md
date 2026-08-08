# Verificador público do THE EYE

Superfície de leitura da etapa 7 da plataforma unificada THE EYE. Ela permite
que terceiros verifiquem integridade criptográfica sem credencial e sem acesso
a eventos, tenants, documentos ou dados pessoais. Não é um produto jurídico.

## Contrato

- `GET /health`: retorna somente `{"status":"ok"}`.
- `POST /verify`: recebe um documento de auditoria JSON, verifica evento,
  cadeia/histórico ou prova Merkle e sempre responde documento inválido com HTTP
  200, `valido: false` e o primeiro ponto da ruptura.
- `GET /root/AAAA-MM-DD`: retorna somente raízes Merkle, hashes de manifesto,
  transação e bloco de âncoras confirmadas naquela data. Ausência retorna 404.
- `GET /`: explica o alcance e os limites da verificação.

O corpo de `/verify` é processado em memória, limitado a 1 MiB, não é persistido
e nunca é repetido na resposta. Motivos de falha podem mostrar apenas sequência
e hashes esperados/recebidos. O binding D1 executa uma única consulta `SELECT`
sobre lotes e âncoras confirmadas; o código não lê a tabela de eventos.

`valido` descreve as verificações criptográficas solicitadas. `estado` preserva
as distinções do verificador offline: `valido`, `invalido`, `incompleto`,
`nao_ancorado` e `ancora_nao_confirmada`. Uma âncora ausente ou ainda não
confirmada não transforma uma cadeia íntegra em cadeia adulterada.

Uma prova de integridade demonstra compromisso e ausência de alteração. Ela não
demonstra que o conteúdo original era verdadeiro, lícito ou completo.

## Teste offline

Requer Node.js 22 ou posterior e não usa rede:

```bash
node --test apps/public-verifier/worker.test.mjs
```

O teste usa um evento fixo selado pela implementação Python, cobre cadeia desde
a gênese, quebra de encadeamento com hashes esperado/recebido, prova Merkle,
rotas públicas e filtragem da resposta de raízes.

## Validação local e publicação posterior

Verificar os tipos, quando as dependências locais do Wrangler estiverem
disponíveis:

```bash
tsc --noEmit --target es2022 --module es2022 --moduleResolution bundler --strict --lib es2022,webworker apps/public-verifier/worker.ts
```

Não executar deploy a partir desta entrega. A publicação é uma decisão humana e
deve passar por `scripts/publish_lock.py`; a classe do projeto permanece L5.
