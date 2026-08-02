# ADR-006 — Separated key domains and managed signing

Status: proposed beyond local.

Envelope encryption, pseudonymization and blockchain signing use different versioned
keys and roles. Production keys live only in approved KMS/HSM/keystore/signing service;
no private key or real environment file is accepted. Rotation, revocation, quorum,
limits and break-glass require separation of duties and drills.
