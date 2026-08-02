# Retention and deletion

Each event names a reviewed retention policy; the seeded five-year value is a prototype
placeholder requiring legal validation, not a production decision. Holds suspend normal
disposal and must be scoped, approved, reviewable and lifted explicitly.

Authoritative content uses per-object/per-tenant envelope encryption. At expiry or an
approved rights request: verify identity/authority off the audit path, check holds and
statutory needs, delete indexes/replicas under provider semantics, destroy the envelope
key, verify unavailability and append a minimal tombstone/outcome event. The integrity
ledger is not rewritten. Backup expiry and restore must not resurrect destroyed keys.

On-chain commitments cannot be erased and must never encode individual identity or
content. A privacy export includes accessible off-chain records and verification
receipts, with other subjects and security details redacted.
