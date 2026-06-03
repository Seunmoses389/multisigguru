"""
scorer.py - Aggregate per-check findings into a 0-100 health score.

Severity weights (sum to 100 if all checks were OK):

  OK        = full points for that check
  WARN      = half points
  CRITICAL  = 0 points

A "points" budget is allocated per check; see SCORER_WEIGHTS below
for the exact allocation. The final score is the sum of earned
points across all checks, clamped to [0, 100].
"""
from __future__ import annotations
from typing import List

from checks import Finding, SEV_OK, SEV_WARN, SEV_CRITICAL


# Points budget per check. Sum to 100.
SCORER_WEIGHTS = {
    "safe_version":     8,
    "owner_count":      16,
    "threshold":        20,
    "owner_uniqueness": 14,
    "zero_owner":       10,
    "timelock":         12,
    "balance":          5,
    "nonce":            3,
    "owner_activity":   12,
}


SEVERITY_FACTOR = {
    SEV_OK:       1.0,
    SEV_WARN:     0.5,
    SEV_CRITICAL: 0.0,
}


def score(findings: List[Finding]) -> int:
    earned = 0.0
    for f in findings:
        w = SCORER_WEIGHTS.get(f.name, 0)
        factor = SEVERITY_FACTOR.get(f.severity, 0.0)
        earned += w * factor
    return max(0, min(100, int(round(earned))))


def label(score_val: int) -> str:
    if score_val >= 85:
        return "HEALTHY"
    if score_val >= 65:
        return "ACCEPTABLE"
    if score_val >= 40:
        return "AT_RISK"
    return "CRITICAL"


def summary_counts(findings: List[Finding]) -> dict:
    out = {"ok": 0, "warn": 0, "critical": 0}
    for f in findings:
        out[f.severity.lower()] = out.get(f.severity.lower(), 0) + 1
    return out
