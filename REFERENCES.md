# Official references

Validated on 2026-08-02. Links are normative/input references; architecture decisions
and legal applicability still require review.

## Cloudflare

- [R2 event notifications](https://developers.cloudflare.com/r2/buckets/event-notifications/) — object changes delivered to Queues.
- [R2 data security](https://developers.cloudflare.com/r2/reference/data-security/) — provider encryption at rest/in transit; application envelope encryption remains required here.
- [Queues delivery guarantees](https://developers.cloudflare.com/queues/reference/delivery-guarantees/) — at-least-once and idempotency guidance.
- [Queues dead-letter queues](https://developers.cloudflare.com/queues/configuration/dead-letter-queues/) — retry exhaustion behavior and DLQ configuration.
- [SQLite-backed Durable Object storage](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/) — transactional SQLite storage and PITR interface.
- [Durable Object alarms](https://developers.cloudflare.com/durable-objects/api/alarms/) — at-least-once alarm execution/retry behavior.

## Canonicalization and cryptography

- [RFC 8785 — JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785) — canonical I-JSON representation.
- [RFC 6962 — Certificate Transparency](https://www.rfc-editor.org/info/rfc6962/) — precedent for leaf/node domain separation and inclusion proofs. This project deliberately differs by using Keccak-256, sorted child hashes and odd-node duplication, all versioned in the manifest.
- [NIST FIPS 180-4 — Secure Hash Standard](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) — SHA-256 definition.

## Contract and networks

- [OpenZeppelin Contracts 5.x access control](https://docs.openzeppelin.com/contracts/5.x/access-control) — role control and `AccessControlDefaultAdminRules` safeguards.
- [OpenZeppelin Contracts 5.x utilities](https://docs.openzeppelin.com/contracts/5.x/api/utils) — `Pausable` API.
- [Base official network configuration](https://docs.base.org/base-chain/quickstart/connecting-to-base) — Base Mainnet chain ID 8453 and Base Sepolia 84532. Public RPC examples are rate-limited and are not configured in this repository.

## Brazilian privacy authority

- [ANPD — Relatório de Impacto à Proteção de Dados Pessoais](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/relatorio-de-impacto-a-protecao-de-dados-pessoais-ripd) — controller responsibility, high-risk assessment and safeguards.
- [ANPD — Comunicação de Incidente de Segurança](https://www.gov.br/anpd/pt-br/canais_atendimento/agente-de-tratamento/comunicado-de-incidente-de-seguranca-cis) — official incident communication guidance and required content.
