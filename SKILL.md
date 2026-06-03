---
name: multisig-health-check
description: >
  REQUIRED for any task that requires auditing a Gnosis Safe (or
  Safe-compatible) multisig wallet for security, signer, and
  time-lock hygiene. Invoke when the user asks to "check my multisig",
  "audit the safe", "is this wallet healthy", "signer distribution",
  "threshold risk", "is there a timelock", "multisig health report",
  or wants a per-check breakdown of an M-of-N multisig including
  signer diversity, threshold safety, time-lock status, and
  per-signer activity. Use the bundled `src/multisig_health.py`
  engine to read Safe state via JSON-RPC (works with any
  EVM-compatible RPC URL, including Pharos Pacific mainnet and
  Atlantic testnet).
  Do not attempt multisig health analysis without reading this skill.
version: 0.1.0
requires:
  - python >= 3.9
  - requests
  - anyBins:
      - cast   # optional, used for manual cross-check of owner / threshold
      - jq     # optional, used for ergonomic RPC URL extraction
---

# Multisig Health Check

Audit a Gnosis Safe (or Safe-compatible) multisig wallet for
signer-distribution risk, threshold safety, and time-lock status.

The skill ships a Python engine that:

1. Identifies the Safe version (v1.x / v2.x / custom) by reading
   `VERSION()` and `domainSeparator()`.
2. Reads the current `owners[]` array, `threshold`, and `nonce`.
3. Reads the linked `TimelockController` (if any) and its
   `getMinDelay()`.
4. Computes per-signer activity (`eth_getTransactionCount`) to
   flag dormant signers.
5. Aggregates everything into a 0–100 **health score** plus a list
   of per-check findings (each tagged `OK` / `WARN` / `CRITICAL`).

## When to use

- The user asks "is my multisig healthy?"
- The user wants a per-signer risk view.
- The user wants to know if a Safe has a time-lock in front of it.
- The user wants to know if any single EOA controls a majority
  of the keys.

## When NOT to use

- Pre-deployment Safe configuration (use the Safe UI's deploy
  preview instead — it has its own validation).
- Non-Safe multisigs (this skill assumes Gnosis Safe ABI; for
  custom multisigs, only the generic owner / threshold reads will
  work).
- Zodiac Modifier audits (out of scope; this skill reads the base
  Safe, not the modifier stack on top of it).

## Inputs

| Input           | Required | Description                                            |
|-----------------|----------|--------------------------------------------------------|
| `safe`          | yes      | 0x address of the Safe (or Safe-compatible) wallet    |
| `rpc_url`       | yes      | JSON-RPC endpoint (any EVM-compatible chain)           |
| `timelock`      | no       | Address of an attached TimelockController (auto-detect otherwise) |
| `check_tx_activity` | no   | Set to `false` to skip per-signer `eth_getTransactionCount` calls (faster) |
| `format`        | no       | `text` (default), `json`, `markdown`, `html`           |

## Outputs

A structured report with:

- Safe metadata: address, version, nonce, ETH balance.
- Signer list: each owner address + last-seen tx count.
- Threshold: M of N, plus a label (`LOW` / `HEALTHY` / `STRICT`).
- Time-lock status: `none` / `present` with delay in seconds.
- Per-check findings: 8+ checks, each tagged `OK` / `WARN` / `CRITICAL`.
- **Health score** 0–100.
- Recommended actions.

### Findings taxonomy

Each finding has a severity:

| Severity   | Meaning                                                  |
|------------|----------------------------------------------------------|
| `OK`       | No issue; the check passed.                              |
| `WARN`     | Suboptimal but not exploitable. Recommend a follow-up.   |
| `CRITICAL` | Immediate action required (e.g. M=1 with N≥2).           |

### Health score

A weighted sum of the per-check severities, mapped to 0–100. The
exact weights are documented in `references/scoring-rules.md`.

## Quick start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Audit a Safe on Pharos mainnet
python src/multisig_health.py \
  --safe 0xYourSafeAddress \
  --rpc-url https://rpc.pharos.xyz

# 3. Audit a Safe with an explicit TimelockController
python src/multisig_health.py \
  --safe 0xYourSafeAddress \
  --timelock 0xTimelockAddress \
  --rpc-url https://rpc.pharos.xyz

# 4. Get a JSON report
python src/multisig_health.py \
  --safe 0xYourSafeAddress \
  --rpc-url https://rpc.pharos.xyz \
  --format json > health-report.json
```

## Agent invocation pattern

When the user asks for a multisig health check, the Agent should:

1. Resolve the RPC URL from the chain the user mentions (e.g.
   Pharos mainnet → `https://rpc.pharos.xyz`).
2. Ask the user for the Safe address (never invent one).
3. Optionally ask the user for a TimelockController address; if
   not supplied, attempt auto-detection by reading the Safe's
   `getStorageAt` for the executor slot.
4. Run `src/multisig_health.py` with the parameters above.
5. Pipe the JSON output through `src/report.py` for a formatted
   report.
6. Surface the health score and any `CRITICAL` findings as the
   top of the response.

## Error handling

| Error                       | Cause                                  | Action |
|-----------------------------|----------------------------------------|--------|
| `not a contract`            | Address has no code                    | Tell the user the address is an EOA, not a Safe |
| `unknown safe version`      | `VERSION()` did not return a string    | Use `--no-version-check` and proceed; some custom safes don't implement VERSION |
| `no owners`                 | `getOwners()` returned empty           | Safe is misconfigured or not actually a Safe; report and stop |
| `threshold > owners`        | Threshold set above owner count        | Surface as a `CRITICAL` finding |
| `rpc unreachable`           | Bad / dead RPC URL                     | Ask user for a working RPC |

## Limitations

- Only reads the base Safe contract. Zodiac modifiers, custom
  modules, and guards are not analyzed.
- Per-signer activity is read from `eth_getTransactionCount`,
  which doesn't tell you *what* the signer did — only how many
  txs they've sent. A signer with 0 txs on the chain might be a
  hardware wallet (good) or a freshly generated key (also fine);
  the skill flags both as "dormant" without judgment.
- Time-lock auto-detection is best-effort; if the Safe uses a
  non-standard executor pattern, supply `--timelock` explicitly.
- The health score is a heuristic. Real audits need protocol-
  specific review (e.g. signers should match the DAO's multisig
  policy doc).
