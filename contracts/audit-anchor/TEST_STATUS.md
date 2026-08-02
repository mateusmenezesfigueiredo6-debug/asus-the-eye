# Contract test status

`SKIPPED`: Forge/Solc and vendored OpenZeppelin 5.x/forge-std were unavailable during
the local bootstrap. Safe future command after dependencies are reviewed and vendored:

```bash
forge test --root contracts/audit-anchor -vvv
```

Do not add `--broadcast`. Static repository tests still assert the narrow ABI, role,
pause, duplicate protections and absence of arbitrary content parameters/private keys.
