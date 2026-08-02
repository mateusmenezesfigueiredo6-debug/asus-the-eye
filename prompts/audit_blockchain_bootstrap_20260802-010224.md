# ASUS + THE EYE — AUDIT & BLOCKCHAIN BOOTSTRAP

Atue como arquiteto principal, engenheiro de segurança e plataforma. Readeque este
repositório para uma arquitetura high-end, auditável, privacy-by-design e
blockchain-anchored. Trabalhe autonomamente, somente neste repositório, até concluir
tudo o que for possível localmente. Não pare no planejamento: produza documentação,
schemas, scaffolding, migrações, bibliotecas, testes e contrato local.

## Restrições obrigatórias

- Não faça deploy, commit, push, merge, PR, transmissão blockchain, `forge --broadcast`,
  `wrangler deploy`, criação/modificação de Cloudflare/R2 ou chamadas pagas.
- Não use sudo, instalação global, credenciais, segredos, chaves AWS nem `.env` real.
- Não procure nem acesse objetos/pastas `chaves`.
- Não apague/sobrescreva trabalho do usuário nem use reset/clean/checkout destrutivo.
- Produção e mainnet permanecem desativadas. Broadcast exige
  `BLOCKCHAIN_BROADCAST_ENABLED=true`, sendo `false` por padrão.
- Se faltar segredo, rede, pacote ou autorização: crie interface/mock/documentação/teste
  local, registre `SKIPPED` e continue.

Blockchain não é banco documental: conteúdo fica off-chain e criptografado; metadados
e índices ficam em banco/busca; auditoria em ledger append-only; somente raízes Merkle,
intervalos, versões e identificadores não pessoais vão on-chain. Nunca coloque PII,
documentos, prompts/respostas completos ou segredos on-chain.

## Inspeção e arquitetura

Antes de editar, leia README, AGENTS, manifests, configurações, testes e convenções.
Preserve o existente e não crie monorepo redundante. Documente:

- `docs/architecture/CURRENT_STATE.md` e `GAP_ANALYSIS.md`;
- `ASUS_THE_EYE_AUDIT_BLOCKCHAIN.md`, `IMPLEMENTATION_ROADMAP.md`,
  `DEPLOYMENT_GATES.md`, `OPERATIONAL_RUNBOOK.md`, `INCIDENT_RESPONSE.md` e
  `AUDIT_VERIFICATION_GUIDE.md`;
- ADR-001 a ADR-010 cobrindo off-chain/on-chain, canonicalização, ledger, Merkle,
  rede, chaves, LGPD, outbox, multi-tenant e revisão humana;
- Mermaid: `PLATFORM_ARCHITECTURE.mmd`, `AUDIT_SEQUENCE.mmd`,
  `VERIFICATION_SEQUENCE.mmd`, `THREAT_BOUNDARIES.mmd`;
- `REFERENCES.md` com fontes oficiais de Cloudflare R2/Queues/Durable Objects,
  RFC 8785/6962, FIPS 180-4, OpenZeppelin 5, Base e ANPD.

Adapte sem redundância: `apps/audit-worker`, `apps/verifier`, `packages/audit-core`,
`packages/audit-sdk`, `packages/canonical-json`, `packages/merkle`,
`packages/event-schemas`, `contracts/audit-anchor`, `infra/cloudflare`,
`docs/{architecture,security}`, `tests/audit` e `migrations`.

## Núcleo auditável

Crie schema versionado sem PII crua com: schema_version, event_id, idempotency_key,
tenant_id, sequence, event_type, action, occurred_at, recorded_at, actor_type,
actor_id_pseudonymous, actor_role, source_system, resource_type,
resource_id_pseudonymous, resource_version, jurisdiction, legal_area_ids,
classification, retention_policy_id, lawful_basis_reference, content_hash_sha256,
metadata_hash_sha256, previous_event_hash_sha256, event_hash_sha256, correlation_id,
causation_id, model_provider/name/version, prompt_template_version,
source_citation_hashes, human_review_status/reviewer_pseudonymous, result_status,
error_code, created_by_service e build_version.

Implemente RFC 8785 compatível, SHA-256 de conteúdo/metadados/evento/manifesto e hash
chain (`SHA256(canonical_event_without_event_hash)`). Valide sequência e corrente.
Inclua vetores determinísticos e testes de alteração de byte, reordenação semântica,
sequência e previous hash adulterados.

Implemente Merkle determinística: ordenar por tenant/sequence; leaf
`keccak256(0x00 || event_hash_bytes)`; nó
`keccak256(0x01 || min(left,right) || max(left,right))`; detectar duplicidade; criar e
verificar proof; golden vectors. Manifesto: batch_id, tenant_id, schema_version,
first/last_sequence, event_count, merkle_root, previous_batch_root,
manifest_hash_sha256, generated_at, generator_version, proof_format_version,
storage_reference e campos blockchain nulos antes do anchor.

Modele/migre `audit_events`, `audit_outbox`, `audit_batches`, `audit_batch_events`,
`audit_anchors`, `audit_verification_runs`, `resource_versions`, `retention_policies`,
`audit_failures`. Garanta imutabilidade, correção por novo evento, tombstone, chaves
únicas de idempotência/tenant-sequence, outbox transacional, retry/falhas,
multi-tenancy e índices.

Crie Audit SDK único: `record`, `recordMutation`, `recordAIExecution`,
`recordSourceSnapshot`, `recordHumanReview`, `verifyEvent`, `verifyResourceHistory`,
`verifyBatch`. Redija dados sensíveis, pseudonimize IDs, exija correlation_id, gere
idempotência, canonicalize/hash/outbox/receipt e falhe explicitamente se mutação crítica
não puder ser auditada. Auditoria de IA registra finalidade, identificadores
pseudonimizados, modelo/template/parâmetros, hashes de inputs/fontes/resposta,
citações/ferramentas, confiança, guardrails, avaliação/revisão/limitações; nunca CoT.

## Cobertura, Cloudflare e verificador

Crie `packages/event-schemas/audit-coverage-manifest.json` e teste que exige schema,
versão, classificação, retenção, documentação e handler ou `planned`. Cubra auth/logout,
usuário/RBAC, casos/processos/movimentos/prazos/tarefas, documentos/versões/upload/
download/exclusão, contratos/cláusulas, fontes jurídicas e OSINT, prompts/modelos/
citações/avaliação/guardrails/revisão humana, agentes/ferramentas/workflows/config/release/
deploy/rollback, Worker/D1/R2/Vectorize/índices, Merkle/anchor/proof, incidentes,
retenção/anonimização/bloqueio/eliminação/exportação.

Prepare somente templates locais Cloudflare: R2 notifications → Queue
`the-eye-audit-events` → validação/idempotência → Durable Object SQLite sequenciador →
ledger → batcher → adapter; DLQ `the-eye-audit-dlq`, alarms, D1/R2 bindings,
observabilidade, métricas, alertas e replay. Trate at-least-once. Use
`wrangler.toml.example` sem IDs/segredos.

Implemente verificador e CLI local para evento, previous hash, cadeia por recurso/tenant,
leaf/proof/manifest/root e receipt JSON/relatório, com estados valid/invalid/incomplete/
not_anchored/anchor_unconfirmed. Prepare sem deploy endpoints GET event/proof/history/
batch/health/metrics e POST verify.

## Contrato e redes

Crie `TheEyeAuditAnchor.sol` atual/OpenZeppelin 5.x, simples e não-upgradeable, com
AccessControlDefaultAdminRules ou equivalente, ANCHOR_ROLE, Pausable, prevenção de batch
duplicado/root substituída, custom errors, NatSpec, armazenamento e evento completo.
`anchorBatch(bytes32 batchId, bytes32 merkleRoot, bytes32 manifestHash, uint64
firstSequence, uint64 lastSequence, uint64 eventCount, uint32 schemaVersion)`. Não aceite
conteúdo arbitrário/PII. Teste autorização, duplicidade, pausa, parâmetros, evento e root
se toolchain existir; caso contrário SKIPPED com comando seguro.

Exemplos apenas: Anvil local, Base Sepolia 84532 staging, Base Mainnet 8453 desativada.
`.env.example` somente com broadcast false, network local, chain/rpc/address vazios,
signer disabled, confirmations e limites de lote; nunca private key. Produção usa
KMS/HSM/keystore/serviço equivalente apenas documentado.

## Privacidade, ameaças, CI e testes

Crie `LGPD_BLOCKCHAIN.md`, `DATA_CLASSIFICATION.md`, `RETENTION_AND_DELETION.md`,
`PSEUDONYMIZATION.md`. Trate minimização/finalidade/retenção/crypto-shredding,
segregação, RBAC e revisão jurídica.

Crie `THREAT_MODEL.md` com ativo/agente/vetor/impacto/prevenção/detecção/resposta/risco
residual para tamper/reordenação/exclusão/duplicidade/replay, signer/RPC/reorg,
Queue/DLQ/bypass SDK, PII/correlação tenant/admin/supply-chain/clock/canonicalização/
idempotência/retenção/gas/indisponibilidade/anchor atrasada/proof corrompida.

Prepare CI sem ativar externos: lint, typecheck, testes, secret scanning, dependency
review, CodeQL, contratos, SBOM, cobertura de eventos e broadcast-off. Deve falhar para
schema faltante, contrato aceitando conteúdo arbitrário, mainnet default, private key,
`.env` real ou bypass de mutação crítica.

Execute unit, canonicalization/hash/Merkle/tamper/idempotency/duplicate/boundary/schema/
privacy e contratos quando disponíveis, além de lint/typecheck. Preserve lockfile,
dependências mínimas e testes determinísticos. TODO permitido deve ter responsável,
razão, risco, pré-condição e critério de conclusão.

Roadmap: Fase 0 protótipo local; 1 integração; 2 Cloudflare staging; 3 Base Sepolia; 4
auditoria independente; 5 piloto; 6 mainnet/chain aprovada. Sem promoção automática.

## Entrega

Crie `reports/AUDIT_BLOCKCHAIN_BOOTSTRAP_REPORT.md` com resumo, arquitetura, arquivos,
decisões, testes pass/fail/skipped, ausências, riscos, questões jurídicas/LGPD/
blockchain/custos/aprovações, comandos seguros/proibidos, checklists staging/produção e
planos 48h/30d.

Só conclua após documentar estado/arquitetura, schema, canonicalização/hash chain/Merkle
com provas e testes, ledger/outbox, cobertura/teste, contrato/teste quando disponível,
LGPD/threat model e relatório de riscos. Ao final retorne resumo, alterações, testes,
bloqueios, riscos críticos, caminho do relatório, dez comandos sem deploy e confirme:
nenhum deploy, transação, recurso cloud modificado ou segredo gravado.
