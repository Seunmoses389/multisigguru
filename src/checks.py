"""
checks.py - Individual multisig health checks.

Each check takes a SafeState (and optionally a TimelockState) and
returns a Finding(name, severity, detail) with severity in
{OK, WARN, CRITICAL}.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from safe import SafeState
from timelock import TimelockState
from rpc import RpcClient


SEV_OK       = "OK"
SEV_WARN     = "WARN"
SEV_CRITICAL = "CRITICAL"


@dataclass
class Finding:
    name: str
    severity: str   # OK / WARN / CRITICAL
    detail: str


def check_threshold(state: SafeState) -> Finding:
    n = len(state.owners)
    m = state.threshold
    if n == 0:
        return Finding("threshold", SEV_CRITICAL, "Safe has 0 owners; misconfigured.")
    if m == 0:
        return Finding("threshold", SEV_CRITICAL,
                       f"Threshold is 0; the Safe cannot execute any transaction.")
    if m == 1 and n >= 2:
        return Finding("threshold", SEV_CRITICAL,
                       f"Threshold is 1-of-{n}; any single key can move all funds.")
    if m == n and n > 2:
        return Finding("threshold", SEV_WARN,
                       f"Threshold is {m}-of-{n}; a single lost key bricks the Safe.")
    if m > n:
        return Finding("threshold", SEV_CRITICAL,
                       f"Threshold {m} is greater than owner count {n}; Safe is bricked.")
    if m < n / 2:
        return Finding("threshold", SEV_WARN,
                       f"Threshold {m}-of-{n} is a bare majority; consider raising to 2/3 for stronger consensus.")
    return Finding("threshold", SEV_OK,
                   f"Threshold is {m}-of-{n}; a healthy supermajority.")


def check_owner_count(state: SafeState) -> Finding:
    n = len(state.owners)
    if n < 2:
        return Finding("owner_count", SEV_CRITICAL,
                       f"Safe has only {n} owner(s); a multisig with 1 owner is just a regular wallet.")
    if n < 3:
        return Finding("owner_count", SEV_WARN,
                       f"Safe has only {n} owners; recommend at least 3 for redundancy.")
    if n > 20:
        return Finding("owner_count", SEV_WARN,
                       f"Safe has {n} owners; coordination may be slow. Consider a sub-multisig.")
    return Finding("owner_count", SEV_OK, f"Safe has {n} owners.")


def check_owner_uniqueness(state: SafeState) -> Finding:
    seen = set()
    dups = []
    for o in state.owners:
        ol = o.lower()
        if ol in seen:
            dups.append(ol)
        seen.add(ol)
    if dups:
        return Finding("owner_uniqueness", SEV_CRITICAL,
                       f"Duplicate owners detected: {', '.join(dups)}. Threshold is meaningless if the same key is counted twice.")
    return Finding("owner_uniqueness", SEV_OK, "All owners are unique.")


def check_zero_owner(state: SafeState) -> Finding:
    bad = [o for o in state.owners if o == "0x" + "0" * 40]
    if bad:
        return Finding("zero_owner", SEV_CRITICAL,
                       f"Owner list contains the zero address: {bad}. This is a misconfiguration.")
    return Finding("zero_owner", SEV_OK, "No zero address in owner list.")


def check_owner_activity(
    rpc: RpcClient, state: SafeState
) -> List[Finding]:
    """Read eth_getTransactionCount for each owner. We don't know
    what they did — only how many txs they've sent. Flag owners
    with zero txs as dormant (could be a hardware wallet, which is
    actually healthy, or a freshly minted key)."""
    findings = []
    dormant = []
    for o in state.owners:
        try:
            n = rpc.get_tx_count(o)
        except Exception:  # noqa: BLE001
            continue
        if n == 0:
            dormant.append(o)
    if dormant:
        sev = SEV_WARN if len(dormant) < len(state.owners) else SEV_CRITICAL
        findings.append(Finding(
            "owner_activity", sev,
            f"{len(dormant)}/{len(state.owners)} owner(s) have 0 transactions on this chain. "
            f"May indicate a hardware wallet (healthy) or a lost key (not). Verify with the signers: "
            f"{', '.join(dormant[:3])}{'…' if len(dormant) > 3 else ''}."
        ))
    else:
        findings.append(Finding("owner_activity", SEV_OK, "All owners have on-chain activity."))
    return findings


def check_timelock(
    state: SafeState, timelock: Optional[TimelockState]
) -> Finding:
    if timelock is None:
        return Finding("timelock", SEV_WARN,
                       "No TimelockController detected. Funds can move as soon as threshold is met; "
                       "consider a 24-48h timelock in front of any high-value Safe.")
    if not timelock.is_timelock:
        return Finding("timelock", SEV_WARN,
                       f"Address {timelock.address} supplied as timelock did not return a valid delay. "
                       "Treating as no timelock.")
    if timelock.min_delay < 24 * 60 * 60:
        return Finding("timelock", SEV_WARN,
                       f"Timelock delay is {timelock.min_delay}s (under 24h). "
                       "Consider 24-48h for safer user-exit windows.")
    return Finding("timelock", SEV_OK,
                   f"TimelockController at {timelock.address} with {timelock.min_delay}s delay.")


def check_safe_version(state: SafeState) -> Finding:
    v = state.version
    if v in ("", "unknown"):
        return Finding("safe_version", SEV_WARN,
                       "Could not read Safe version. Custom Safe or older deployment.")
    # Parse major.minor
    try:
        major = int(v.split(".")[0])
    except (ValueError, IndexError):
        return Finding("safe_version", SEV_WARN, f"Could not parse Safe version '{v}'.")
    if major < 1:
        return Finding("safe_version", SEV_CRITICAL, f"Safe version {v} is unsupported.")
    if major == 1:
        return Finding("safe_version", SEV_WARN,
                       f"Safe v1.x detected (version {v}); consider migrating to v2.x for better audit + recover.")
    return Finding("safe_version", SEV_OK, f"Safe version {v}.")


def check_balance(state: SafeState) -> Finding:
    if state.eth_balance == 0:
        return Finding("balance", SEV_WARN,
                       "Safe holds 0 native; it cannot pay gas for any transaction.")
    return Finding("balance", SEV_OK,
                   f"Safe holds {state.eth_balance / 1e18:.6f} native (gas reserve).")


def check_nonce(state: SafeState) -> Finding:
    # High nonce on a brand-new Safe is normal; high nonce on a
    # long-lived Safe is a sign of activity (healthy). We don't
    # have a "max nonce" so this is just informational.
    if state.nonce == 0:
        return Finding("nonce", SEV_OK, "Safe has executed 0 transactions (fresh).")
    return Finding("nonce", SEV_OK, f"Safe has executed {state.nonce} transactions.")


def run_all(
    rpc: RpcClient,
    state: SafeState,
    timelock: Optional[TimelockState],
    check_tx_activity: bool = True,
) -> List[Finding]:
    findings: List[Finding] = []
    findings.append(check_safe_version(state))
    findings.append(check_owner_count(state))
    findings.append(check_threshold(state))
    findings.append(check_owner_uniqueness(state))
    findings.append(check_zero_owner(state))
    findings.append(check_timelock(state, timelock))
    findings.append(check_balance(state))
    findings.append(check_nonce(state))
    if check_tx_activity:
        findings.extend(check_owner_activity(rpc, state))
    return findings
