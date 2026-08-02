# ADR-002 — RFC 8785 canonicalization and SHA-256

Status: accepted for prototype.

Events/manifests use I-JSON and RFC 8785-compatible canonical bytes before SHA-256.
Non-finite numbers, lone surrogates, oversized interoperable integers and unknown schema
fields fail. This yields portable hashes but requires versioned vectors and independent
implementation checks before staging.
