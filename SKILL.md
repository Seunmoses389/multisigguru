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
version: 2.0.0
requires: read
bins: [bash, cast, jq]
author: Seunmoses389
network: pharos
tags: [pharos, blockchain, multisig, safe, gnosis, agent-skill, foundry]
agents: [claude, codex, gemini, openclaw]
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

## Prerequisites

```bash
python3 --version   # 3.10+
```

The skill uses only the Python standard library (`urllib.request`,
`json`, `argparse`). No third-party packages, no Foundry, no
`pip install` step.

The skill is **read-only** — no private key is required or accepted.

## Network Configuration

Network RPC URLs and chain IDs are sourced from
`assets/networks.json` (canonical Pharos Skill Engine schema). To
add a new network, append a new object to the `networks` array and
update `defaultNetwork` if needed.

## Capability Index

| User Need | Capability | Detailed Instructions |
|---|---|---|
| Default entry point | CLI with a `--wallet` / `--safe` / `--governor` flag | See the `Usage` section in the README; the CLI takes a target identifier and prints a Markdown or JSON report |
| JSON for an agent | `--format json` | Output is a structured payload that an agent can import directly |
| Markdown report | pipe to `report.py` | `python3 src/... --format json \| python3 src/report.py --format markdown --out X.md` |
| Bounded scan | `--max-blocks` / `--lookback` / `--block-count` | Default scans are bounded to stay within the public Pharos RPC's request rate |
| Network switch | `--chain mainnet\|testnet` | Default is Atlantic testnet; pass `--chain mainnet` to switch |

## General Error Handling

| Error Scenario | CLI Error Signature | Handling |
|---|---|---|
| Target not on the specified chain | `null` receipt / no data returned | Exit with "not found on chain=X; try `--chain <other>`" |
| RPC rate-limited (HTTP 429) | Backoff response from RPC | Built-in exponential backoff (0.4s, 0.8s, 1.6s, 3.2s) with 4 retry attempts |
| Bad target format | Validator rejects the input | CLI prints a usage hint; no RPC call is made |
| Missing required arg | `argparse` exits with usage | CLI prints required args; user re-invokes with the right flags |
| No matches (clean target) | Empty result / `verdict: clean` | Normal case — emit the "no issues" report, no error |

## Security Reminders

- **Private Key Protection** — the skill is read-only and never
  accepts a private key. Do not paste keys into chat.
- **Network Confirmation** — before any future write-skill
  integration, confirm the network with the user.
- **No External API** — the skill does not call any third-party
  service beyond the Pharos RPC and PharosScan (where applicable).
  All data is fetched directly.

## Write Operation Pre-checks

This skill is **read-only** and never submits a transaction, so the
full 4-step write pre-check is not applicable. If a future version
adds a write path, the pre-checks must include:

1. **Private Key Check** — `--private-key` / `$PRIVATE_KEY` must be
   set; warn if the key has zero balance.
2. **Derive Public Address** — `cast wallet address`; confirm the
   key is for the intended network.
3. **Network Confirmation** — prompt the user with "You are about
   to write to Pacific mainnet. Continue? (y/N)".
4. **Automatic Balance Check** — `cast balance`; if below the
   operation cost + gas, abort with a clear error.
