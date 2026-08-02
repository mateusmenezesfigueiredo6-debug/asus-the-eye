# Pseudonymization

Actor/resource identifiers use `HMAC-SHA-256(versioned_key,
tenant_id || 0x00 || identifier)` so tenants cannot correlate the same subject. This is
deterministic for history lookup but is not anonymization. Keys are separate from
encryption/signing, never logged, stored in an approved managed service in production,
and rotated with explicit key versions and a bounded dual-read migration.

Access to the re-identification mapping/key is a separate privileged purpose with
approval and audit. Low-entropy identifiers remain vulnerable if the key leaks; rate
limits, key isolation, tenant scoping and incident revocation reduce risk. Analytics
should use aggregation/noise or purpose-specific pseudonyms, never reuse audit IDs.
