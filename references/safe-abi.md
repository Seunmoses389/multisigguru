# Safe ABI (selectors used by this skill)

This file documents the function selectors `src/safe.py` and
`src/timelock.py` call. All selectors are precomputed in
`src/rpc.py:SELECTORS`.

## Gnosis Safe (v1.x and v2.x)

The v1 and v2 ABIs are compatible for the read functions this
skill uses. The CLI is `masterCopy`-agnostic — it works against
any deployed Safe, regardless of which master copy was used.

| Function       | Selector       | Returns                              |
|----------------|----------------|--------------------------------------|
| `getOwners()`  | `0xa0e67e2b`   | `address[]`                          |
| `getThreshold()` | `0xe75235b8` | `uint256`                            |
| `nonce()`      | `0xaffed0e0`   | `uint256`                            |
| `domainSeparator()` | `0xf698da25` | `bytes32`                         |
| `VERSION()`    | `0xffa1a74c`   | `string` (e.g. `"1.3.0"`, `"2.0.0"`) |

`VERSION()` was added in v1.3.0; older deployments may not have
it. The reader returns `"unknown"` in that case and emits a
`WARN` finding.

### Storage slots we read indirectly

- `eth_getBalance(safe)` — for the gas reserve check.
- `eth_getTransactionCount(safe)` — for the executed-tx count.
- `eth_getCode(safe)` — to confirm the address is a contract.

## OpenZeppelin TimelockController

| Function           | Selector       | Returns    |
|--------------------|----------------|------------|
| `getMinDelay()`    | `0x8d928af2`   | `uint256`  |
| `PROPOSER_ROLE()`  | `0x9781ce82`   | `bytes32`  |
| `EXECUTOR_ROLE()`  | `0x63a4a6f9`   | `bytes32`  |
| `TIMELOCK_ADMIN_ROLE()` | `0xf3ae03f1` | `bytes32` |

Only `getMinDelay()` is read by the skill. The role selectors are
included for completeness; a future version could verify that
the Safe holds the PROPOSER_ROLE on the timelock.

The timelock reader treats any contract that returns a uint256 in
`[0, 30 days]` from `getMinDelay()` as a TimelockController. This
is heuristic — true validation would require also checking
`supportsInterface` against the TimelockController interface id.

## EIP-1967 (proxy) storage slot

`EIP1967_IMPL_SLOT` is defined in `src/rpc.py` for completeness but
is not currently used by any of the checks. The skill reads the
Safe directly via its own `getOwners()` etc., so a proxy in front
of the Safe does not affect results.

## Decoding helpers

`src/rpc.py` provides three decoders:

- `decode_uint256(hexstr)` — read a 32-byte word as int.
- `decode_address(hexstr)` — read the lower 20 bytes as address.
- `decode_address_array(hexstr)` — read an ABI-encoded `address[]`
  (offset + length + words). Used for `getOwners()`.
- `decode_string(hexstr)` — read an ABI-encoded dynamic string.
  Used for `VERSION()`.

All decoders tolerate empty/zero inputs (return 0 or empty list)
so a `getOwners()` on a misconfigured Safe doesn't crash the CLI.

## Adding a new check

To add a new Safe-related read:

1. Compute the function selector and add it to `SELECTORS` in
   `src/rpc.py`.
2. Add a `_read_*(rpc, safe, …)` helper to `src/safe.py` (or
   `src/timelock.py` for TimelockController).
3. Add a `check_*(state)` function in `src/checks.py` returning
   a `Finding`.
4. Wire the check into `run_all`.
5. Add a row to the `SCORER_WEIGHTS` dict in `src/scorer.py`,
   keeping the sum at 100.

PRs welcome.
