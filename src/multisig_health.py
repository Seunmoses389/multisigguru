"""
multisig_health.py - CLI entry point.

Usage:
  python multisig_health.py --safe 0x... --rpc-url https://...
                             [--timelock 0x...] [--format json]
"""
from __future__ import annotations
import argparse
import json
import sys
from typing import Any, Dict, Optional

from rpc import RpcClient, RpcError
from safe import read as read_safe, SafeState
from timelock import read as read_timelock, TimelockState
from checks import run_all, Finding
from scorer import score, label as label_for, summary_counts


def _safe_to_dict(s: SafeState) -> Dict[str, Any]:
    return {
        "address":     s.address,
        "chain_id":    s.chain_id,
        "version":     s.version,
        "owners":      s.owners,
        "threshold":   s.threshold,
        "nonce":       s.nonce,
        "eth_balance": s.eth_balance,
        "is_contract": s.is_contract,
        "has_code":    s.has_code,
    }


def _timelock_to_dict(t: Optional[TimelockState]) -> Optional[Dict[str, Any]]:
    if t is None:
        return None
    return {
        "address":     t.address,
        "min_delay":   t.min_delay,
        "is_timelock": t.is_timelock,
    }


def _findings_to_dict(findings: list[Finding]) -> list[Dict[str, Any]]:
    return [{"name": f.name, "severity": f.severity, "detail": f.detail} for f in findings]


def run(args: argparse.Namespace) -> Dict[str, Any]:
    rpc = RpcClient(args.rpc_url)
    try:
        state = read_safe(rpc, args.safe)
    except RpcError as e:
        raise SystemExit(f"error reading Safe: {e}")

    timelock: Optional[TimelockState] = None
    if args.timelock:
        try:
            timelock = read_timelock(rpc, args.timelock)
        except RpcError as e:
            print(f"[!] could not read timelock: {e}", file=sys.stderr)

    findings = run_all(rpc, state, timelock, check_tx_activity=not args.no_tx_activity)

    # Per-signer activity table
    owners_with_nonce = []
    for o in state.owners:
        try:
            n = rpc.get_tx_count(o)
        except Exception:  # noqa: BLE001
            n = -1
        owners_with_nonce.append({"address": o, "nonce": n})

    s = score(findings)
    return {
        "safe":     _safe_to_dict(state),
        "timelock": _timelock_to_dict(timelock),
        "findings": _findings_to_dict(findings),
        "score":    s,
        "score_label": label_for(s),
        "counts":   summary_counts(findings),
        "owners_with_nonce": owners_with_nonce,
    }


def main():
    p = argparse.ArgumentParser(
        description="Audit a Gnosis Safe (or Safe-compatible) multisig."
    )
    p.add_argument("--safe", required=True, help="0x address of the Safe")
    p.add_argument("--rpc-url", required=True, help="JSON-RPC endpoint")
    p.add_argument("--timelock", default=None,
                   help="Address of an attached TimelockController (optional)")
    p.add_argument("--no-tx-activity", action="store_true",
                   help="Skip per-signer eth_getTransactionCount (faster scan)")
    p.add_argument("--format", choices=["text", "json", "markdown", "html"], default="text")
    p.add_argument("--out", default="-")
    args = p.parse_args()

    payload = run(args)

    if args.format == "json":
        out = json.dumps(payload, indent=2)
    elif args.format == "markdown":
        from report import render_markdown
        out = render_markdown(payload)
    elif args.format == "html":
        from report import render_html
        out = render_html(payload)
    else:
        from report import render_text
        out = render_text(payload, use_color=sys.stdout.isatty())

    if args.out == "-":
        sys.stdout.write(out)
    else:
        with open(args.out, "w") as f:
            f.write(out)


if __name__ == "__main__":
    main()
