# Audit verification guide

Verification is layered and reports the first failed boundary without treating an
anchor as proof that content was lawful or correct.

1. Validate schema/I-JSON and recompute `SHA256(canonical_event_without_event_hash)`.
2. Check tenant sequence and `previous_event_hash_sha256`; for resource history also
   verify each selected event belongs to a valid tenant chain.
3. Recompute `keccak256(0x00 || event_hash_bytes)`, apply each proof sibling as
   `keccak256(0x01 || min || max)`, and compare the manifest root.
4. Recompute the canonical manifest SHA-256; compare counts/ranges/version/storage
   checksum and previous batch root.
5. If chain access is authorized, compare contract address/chain ID, batch fields,
   block hash, confirmation threshold and reorg state using independent RPC sources.

Statuses: `valid` means every requested layer including a confirmed anchor passed;
`invalid` means a contradiction; `incomplete` means required evidence is missing;
`not_anchored` means off-chain integrity passes but no anchor was supplied;
`anchor_unconfirmed` means a matching submission lacks finality policy.

Safe offline example:

```bash
python3 -m asus_theye.cli audit-verify evidence.json --receipt receipt.json
```

Receipts contain checks and identifiers, never raw documents. Preserve the input digest,
tool/build version and verification time when exporting a human-readable report.
