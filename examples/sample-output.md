# Example: Multisig Health Report

> Generated against a sample Safe on Pharos mainnet. See `SKILL.md`
> for the full command line.

```
================================================================
  MULTISIG HEALTH REPORT — 0xSafeAd…7890
  Chain ID: 1672    Safe version: 1.3.0
================================================================

  Threshold:        3 of 5
  Executed txs:     42
  Native balance:   0.500000
  Timelock:         none

  Owners
  ------------------------------------------------------------
    0xaaaa1111   tx-count=312
    0xbbbb2222   tx-count=201
    0xcccc3333   tx-count=178
    0xdddd4444   tx-count=92
    0xeeee5555   tx-count=0

  >>> HEALTH SCORE: 88 / 100  (HEALTHY) <<<
      7 OK  /  2 WARN  /  0 CRITICAL

  Per-check findings
  ------------------------------------------------------------
  [      OK] safe_version
             Safe version 1.3.0.
  [      OK] owner_count
             Safe has 5 owners.
  [      OK] threshold
             Threshold is 3-of-5; a healthy supermajority.
  [      OK] owner_uniqueness
             All owners are unique.
  [      OK] zero_owner
             No zero address in owner list.
  [    WARN] timelock
             No TimelockController detected. Funds can move as soon as threshold is met; consider a 24-48h timelock in front of any high-value Safe.
  [      OK] balance
             Safe holds 0.500000 native (gas reserve).
  [      OK] nonce
             Safe has executed 42 transactions.
  [    WARN] owner_activity
             1/5 owner(s) have 0 transactions on this chain. May indicate a hardware wallet (healthy) or a lost key (not). Verify with the signers: 0xeeee…5555.
```

## Reading the report

- **Health score** is 0–100, higher is better. 88 → `HEALTHY`.
- **Threshold** of 3-of-5 is a healthy supermajority.
- **Timelock** warning means funds can move as soon as 3 signers
  sign. Consider deploying an OpenZeppelin TimelockController
  with a 24-48h delay in front of this Safe.
- **owner_activity** warning means 1 signer has 0 transactions on
  this chain. This is *usually* a hardware wallet (which is
  healthy), but verify with the signers that they have access.

## Next steps for the user

1. **CRITICAL findings** (none in this example) — fix immediately.
2. **WARN findings** — schedule a follow-up; the Safe is not
   unsafe today, but trends matter.
3. **Re-run** this skill quarterly as a hygiene check; track the
   score over time.
