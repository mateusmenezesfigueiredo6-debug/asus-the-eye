# Audit anchor contract

Non-upgradeable OpenZeppelin 5.x contract for commitments only. The ABI accepts exactly
three `bytes32` identifiers/hashes and bounded integer metadata—no strings or arbitrary
bytes. Operational anchoring needs `ANCHOR_ROLE`; pause is admin-only; default-admin
transfer is delayed.

Networks are informational gates, never defaults: Anvil `31337` local, Base Sepolia
`84532` staging and Base Mainnet `8453` disabled. Every transaction requires an
independent change approval and `BLOCKCHAIN_BROADCAST_ENABLED=true`; this repository
does not include a broadcaster.
