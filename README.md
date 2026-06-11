# MultisigGuru — Multisig Health Check

> Audit a Gnosis Safe (or Safe-compatible) multisig for signer
> distribution, threshold safety, and time-lock status.

[![python](https://img.shields.io/badge/python-3.9%2B-blue)]()
[![license](https://img.shields.io/badge/license-MIT--0-green)]()
[![rpc](https://img.shields.io/badge/RPC-JSON--RPC%20%7C%20EVM-orange)]()

## Overview

MultisigGuru reads the live state of a Safe via JSON-RPC and runs
nine audit checks on it — version, owner count, threshold, owner
uniqueness, zero-address guard, time-lock presence, gas reserve,
executed-tx count, and per-signer activity. Each check is tagged
`OK` / `WARN` / `CRITICAL`, and the lot is rolled up into a single
0–100 health score.

It works against any EVM-compatible JSON-RPC endpoint and ships
with first-class support for the Pharos networks (see
[Supported networks](#supported-networks)).

## Features

- **Safe v1.x and v2.x support** — same ABI, same read functions;
  no `masterCopy` handling needed.
- **Nine health checks** — version, owner count, threshold,
  uniqueness, zero-address guard, time-lock, balance, nonce,
  per-signer activity.
- **0–100 health score** with a four-tier label (`HEALTHY` /
  `ACCEPTABLE` / `AT_RISK` / `CRITICAL`).
- **TimelockController auto-detection** — supply an address or
  skip; the skill flags absence as a `WARN`.
- **Multi-format output** — text (with ANSI colors), JSON,
  Markdown, or HTML via the `report.py` formatter.
- **Agent-ready** — ships a `SKILL.md` at the repo root with the
  invocation contract an agent runtime needs to drive the tool.
- **No web3 framework dependency** — plain `eth_call` over
  `requests`.

## Supported networks

The tool runs against any EVM-compatible JSON-RPC endpoint. The
following networks are explicitly supported out of the box and
used in the examples below.

| Network                 | Chain ID | RPC URL                                | Native token | Explorer                          |
|-------------------------|----------|----------------------------------------|--------------|-----------------------------------|
| Pharos Pacific Mainnet  | `1672`   | `https://rpc.pharos.xyz`               | PROS         | https://www.pharosscan.xyz/       |
| Pharos Atlantic Testnet | `688689` | `https://atlantic.dplabs-internal.com` | PHRS         | https://atlantic.pharosscan.xyz/  |

You can target either by passing the matching `--rpc-url` flag
(see [Usage](#usage)).

## Framework

- **Language:** Python 3.9+
- **RPC protocol:** JSON-RPC (`eth_call`, `eth_getCode`,
  `eth_getBalance`, `eth_getTransactionCount`, `eth_chainId`)
- **External CLIs (optional):** `cast` from
  [Foundry](https://book.getfoundry.xyz/) for manual cross-checks
  of owner / threshold; `jq` for ergonomic RPC URL extraction in
  shell pipelines.
- **No web3 framework required** — the engine speaks JSON-RPC
  directly over `requests` so it has the smallest possible install
  footprint.

## Dependencies

Runtime (Python):

- `requests>=2.31` — HTTP client used by `src/rpc.py`.

External (only if you want the optional CLIs):

- `cast` / `forge` — Foundry CLI (https://book.getfoundry.xyz/getting-started/installation).
- `jq` — command-line JSON processor, used in README shell snippets.

Everything is pinned in `requirements.txt` at the repo root.

## Install

### 1. Install Python 3.9+ and pip

```bash
# macOS
brew install python@3.11
# Debian/Ubuntu/Termux
apt install -y python3 python3-pip
```

Verify with `python3 --version`.

### 2. (Optional) Install Foundry if you want cast/forge fallback

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

Verify with `cast --version`. Foundry is OPTIONAL for this skill — the bash CLI in `scripts/cli.sh` works without it.

### 3. Get the skill

```bash
git clone https://github.com/Seunmoses389/multisigguru
cd multisigguru
pip install -r requirements.txt
chmod +x scripts/*.sh
```

That's it. No build step, no native compilation. The skill is a Python 3.9+ module wrapped by a bash CLI for easy invocation.
### 1. Install Foundry (the engine the skill is built on)

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

Verify with `cast --version`. This gives you `cast`, `forge`, `anvil`, and `chisel` on your `$PATH`.

### 2. Install jq (used to parse JSON)

```bash
# macOS
brew install jq
# Debian/Ubuntu/Termux
apt install -y jq
# Alpine
apk add jq
```

Verify with `jq --version`.

## Usage

### Audit a Safe on Pharos mainnet

```bash
python src/multisig_health.py \
  --safe 0xYourSafeAddress \
  --rpc-url https://rpc.pharos.xyz
```

### Audit a Safe on Pharos Atlantic testnet

```bash
python src/multisig_health.py \
  --safe 0xYourSafeAddress \
  --rpc-url https://atlantic.dplabs-internal.com
```

### Audit a Safe with an explicit TimelockController

```bash
python src/multisig_health.py \
  --safe 0xYourSafeAddress \
  --timelock 0xTimelockAddress \
  --rpc-url https://rpc.pharos.xyz
```

### Skip per-signer activity (faster scan)

```bash
python src/multisig_health.py \
  --safe 0xYourSafeAddress \
  --rpc-url https://rpc.pharos.xyz \
  --no-tx-activity
```

### Output as JSON, then format as Markdown

```bash
python src/multisig_health.py \
  --safe 0xYourSafeAddress \
  --rpc-url https://rpc.pharos.xyz \
  --format json \
  | python src/report.py --format markdown --out health-report.md
```

### Output as HTML

```bash
python src/multisig_health.py \
  --safe 0xYourSafeAddress \
  --rpc-url https://rpc.pharos.xyz \
  --format json \
  | python src/report.py --format html --out health-report.html
```

### Command-line flags

| Flag                | Required | Default | Description                                       |
|---------------------|----------|---------|---------------------------------------------------|
| `--safe`            | yes      | —       | 0x address of the Safe                            |
| `--rpc-url`         | yes      | —       | JSON-RPC endpoint                                 |
| `--timelock`        | no       | —       | Address of an attached TimelockController         |
| `--no-tx-activity`  | no       | false   | Skip per-signer `eth_getTransactionCount` (faster) |
| `--format`          | no       | text    | `text`, `json`, `markdown`, `html`                |
| `--out`             | no       | -       | Output file (`-` for stdout)                      |

### Sample output

See `examples/sample-output.md` for what a real report looks like.

## AI Agent Integration

This repository ships a `SKILL.md` at the root that any agent
runtime can load to discover the skill. The flow is:

1. The agent reads `SKILL.md` to learn the capability and required
   arguments (`--safe`, `--rpc-url`).
2. The agent collects the Safe address from the user (it never
   invents one).
3. Optionally, the agent collects a TimelockController address.
4. The agent runs `python src/multisig_health.py` with the
   parameters and captures stdout (or `--out` to a file).
5. The agent surfaces the health score, score label, and any
   `CRITICAL` findings as the top of its reply.
6. If a formatted report is needed, the agent pipes the JSON
   output through `python src/report.py --format <fmt>`.

A typical prompt that triggers the skill:

> "Is the Pharos DAO Safe at `0xYourSafeAddress` healthy? RPC is
> `https://rpc.pharos.xyz`."

A typical reply:

> **Health score: 88 / 100 — HEALTHY** — 7 OK, 2 WARN, 0 CRITICAL.
> Threshold 3-of-5, Safe v1.3.0, all owners unique. Two `WARN`
> findings: no timelock detected, and 1/5 owners have 0
> transactions on this chain (likely a hardware wallet; verify).
> See `health-report.md` for the full breakdown.

## Repository layout

```
multisigguru/
├── SKILL.md                       # Agent-facing skill spec
├── README.md                      # This file
├── LICENSE                        # MIT-0
├── requirements.txt
├── src/
│   ├── multisig_health.py         # CLI entry point
│   ├── safe.py                    # Gnosis Safe reader
│   ├── timelock.py                # TimelockController reader
│   ├── checks.py                  # Per-check finding logic
│   ├── scorer.py                  # 0-100 health score aggregator
│   ├── rpc.py                     # JSON-RPC client with precomputed selectors
│   └── report.py                  # Text / JSON / Markdown / HTML formatter
├── references/
│   ├── safe-abi.md                # Safe + TimelockController selectors
│   └── scoring-rules.md           # Health score weights + worked example
└── examples/
    └── sample-output.md           # What a real report looks like
```

## How detection works

See `references/safe-abi.md` for the Safe + TimelockController
selectors used, and `references/scoring-rules.md` for the exact
weights and label boundaries.

## Roadmap

- [ ] Read `TransactionExecuted` events for a "drain rate" check.
- [ ] Verify the Safe holds `PROPOSER_ROLE` on the TimelockController.
- [ ] Surface Zodiac modifier stack (Roles, Delay, Pausable).
- [ ] Add a `--policy` flag to load org-specific scoring weights.

## Contributing

PRs welcome — especially new checks, additional Safe-compatible
contracts (Zodiac, custom multisigs), and benchmarks against real
DAOs.

## License

[MIT-0](https://opensource.org/licenses/MIT-0) — free to use, modify,
redistribute. No attribution required.

---

**Author:** Seunmoses389
**Built with:** Python 3.9+, plain JSON-RPC, and a healthy distrust
of single-key multisigs.
