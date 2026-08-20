# API pública do verificador (`the-eye-public-verifier`)

Documentação dos endpoints **públicos** do verificador, confirmados no código em
`apps/public-verifier/worker.ts`.

Base URL (exemplo): `https://SEU_DOMINIO`

## GET `/health`

Liveness anônimo.

### curl

```bash
curl -sS https://SEU_DOMINIO/health
```

### Corpo

Sem corpo.

### Resposta real (200)

```json
{"status":"ok"}
```

### O que NÃO faz

- Não valida documentos.
- Não consulta âncoras.
- Não expõe dados internos, eventos ou mercado.

## POST `/verify`

Verifica localmente documento de auditoria (`event`, `chain`/`history` ou
`proof`) e retorna recibo. O payload é limitado a **1 MiB** e **nada é
persistido**.

### curl

```bash
curl -sS -X POST https://SEU_DOMINIO/verify \
  -H 'content-type: application/json' \
  -d '{"kind":"chain","events":[{"schema_version":"1.0.0","event_id":"evt-fixed-1","idempotency_key":"fixed-idempotency-key-0001","tenant_id":"tenant-fixture","sequence":1,"event_type":"discovery.observed","action":"observe","occurred_at":"2026-08-08T12:00:00Z","recorded_at":"2026-08-08T12:00:01Z","actor_type":"service","actor_id_pseudonymous":"1111111111111111111111111111111111111111111111111111111111111111","actor_role":"collector","source_system":"fixture","resource_type":"innovation","resource_id_pseudonymous":"2222222222222222222222222222222222222222222222222222222222222222","resource_version":"1","jurisdiction":"global","legal_area_ids":[],"classification":"public","retention_policy_id":"audit-default-v1","lawful_basis_reference":"public-source-fixture","content_hash_sha256":"3333333333333333333333333333333333333333333333333333333333333333","metadata_hash_sha256":"4444444444444444444444444444444444444444444444444444444444444444","previous_event_hash_sha256":"0000000000000000000000000000000000000000000000000000000000000000","correlation_id":"fixture-correlation","causation_id":null,"model_provider":null,"model_name":null,"model_version":null,"prompt_template_version":null,"source_citation_hashes":[],"human_review_status":"not_required","reviewer_pseudonymous":null,"result_status":"success","error_code":null,"created_by_service":"public-verifier-test","build_version":"test","event_hash_sha256":"6ec98f4884e8b8f7a58e381e2fe7df79fe9990fc79352515f424b56942298b91"}]}'
```

### Corpo

```json
{"kind":"event|chain|history|proof","...":"documento de auditoria JSON"}
```

### Resposta real (200)

```json
{"valido":true,"motivo":"1 evento(s) íntegro(s) desde a gênese; âncora não fornecida","estado":"nao_ancorado","verificacoes":{"event_chain":true}}
```

### O que NÃO faz

- Não persiste o documento enviado.
- Não repete o conteúdo completo do payload no recibo.
- Não transforma prova de integridade em prova de veracidade material.

## GET `/root/AAAA-MM-DD`

Consulta raízes Merkle ancoradas e confirmadas em um dia. Quando existe registro
confirmado: HTTP 200 com `encontrada:true`.

### curl

```bash
curl -sS https://SEU_DOMINIO/root/2026-08-08
```

### Corpo

Sem corpo.

### Resposta real quando encontrada (200)

```json
{"encontrada":true,"roots":[{"merkle_root":"1111111111111111111111111111111111111111111111111111111111111111","manifest_hash_sha256":"2222222222222222222222222222222222222222222222222222222222222222","tx_hash":"3333333333333333333333333333333333333333333333333333333333333333","block_hash":"4444444444444444444444444444444444444444444444444444444444444444"}]}
```

Quando não existe âncora confirmada para o dia, responde:

```json
{"encontrada":false}
```

### O que NÃO faz

- Não retorna eventos.
- Não retorna tenant, manifesto bruto ou JSON de auditoria completo.
- Não entrega dados de mercado.

## O que este serviço não revela

- Só valida o que a pessoa já tem em mãos.
- Não faz busca investigativa de documentos.
- Não entrega dados de mercado.
