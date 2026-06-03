# Scoring rules

This file documents how `src/scorer.py` turns the per-check
findings into a single 0–100 health score.

## Method

Each check is assigned a point budget. A check passing
(`severity = OK`) earns 100% of its budget. A warning
(`severity = WARN`) earns 50%. A critical finding
(`severity = CRITICAL`) earns 0%.

```
earned_points = sum(weight * severity_factor for each finding)
final_score   = clamp(round(earned_points), 0, 100)
```

where `severity_factor` is `{OK: 1.0, WARN: 0.5, CRITICAL: 0.0}`.

The weights are calibrated so a perfect run (all OK) scores 100
and a 9-check all-CRITICAL run scores 0.

## Weights

| Check              | Weight | Why                                                      |
|--------------------|--------|----------------------------------------------------------|
| `safe_version`     | 8      | Old Safe versions have known vulns; not a deal-breaker   |
| `owner_count`      | 16     | < 2 owners is a critical misconfiguration                |
| `threshold`        | 20     | M=1 with N≥2 is the single biggest footgun               |
| `owner_uniqueness` | 14     | Duplicate owners silently weaken the multisig            |
| `zero_owner`       | 10     | A zero address in the owners list is almost always a bug |
| `timelock`         | 12     | Best practice for any high-value Safe                    |
| `balance`          | 5      | A Safe with 0 native can't pay gas; informational        |
| `nonce`            | 3      | Mostly informational; useful to detect dead Safes        |
| `owner_activity`   | 12     | Dormant signers are a real risk if you can't verify why  |
| **Total**          | **100**|                                                          |

## Score label

| Range   | Label         | Meaning                                                |
|---------|---------------|--------------------------------------------------------|
| 85–100  | `HEALTHY`     | Ship it. Review the WARN findings once a year.         |
| 65–84   | `ACCEPTABLE`  | No CRITICALs, but address the WARNs in the next quarter. |
| 40–64   | `AT_RISK`     | At least one CRITICAL or multiple WARNs. Act soon.     |
| 0–39    | `CRITICAL`    | Multiple CRITICALs or one severe one. Fix immediately. |

## Worked example

A 3-of-5 Safe with no timelock and one dormant signer:

| Check            | Weight | Severity | Factor | Earned |
|------------------|--------|----------|--------|--------|
| safe_version     | 8      | OK       | 1.0    | 8      |
| owner_count      | 16     | OK       | 1.0    | 16     |
| threshold        | 20     | OK       | 1.0    | 20     |
| owner_uniqueness | 14     | OK       | 1.0    | 14     |
| zero_owner       | 10     | OK       | 1.0    | 10     |
| timelock         | 12     | WARN     | 0.5    | 6      |
| balance          | 5      | OK       | 1.0    | 5      |
| nonce            | 3      | OK       | 1.0    | 3      |
| owner_activity   | 12     | WARN     | 0.5    | 6      |
| **Total**        |        |          |        | **88** |

Score = 88 → `HEALTHY`. Add a timelock and verify the dormant
signer is a hardware wallet, and you'll be at 100.

## Why not ML?

Same answer as the other skills in this repo: a 30-line audit
table is auditable in seconds. A trained model trained on a
handful of "this multisig is healthy" labels is not. If a future
version adds a model, it should run *alongside* the rule-based
score, not replace it.

## Limitations

- The weights are an opinion. Different organizations weight
  threshold risk, timelock presence, and signer activity
  differently. Adjust `SCORER_WEIGHTS` in `src/scorer.py` to match
  your org's policy.
- The label boundaries (85 / 65 / 40) are also an opinion. A
  conservative org might call 80–100 `HEALTHY` and 60–80
  `ACCEPTABLE`. Tune to taste.
- The score does not look at historical txs. A Safe that drained
  itself 6 months ago still gets a high score today. (Future
  work: read `TransactionExecuted` events to compute a
  "drain-rate" adjustment.)
