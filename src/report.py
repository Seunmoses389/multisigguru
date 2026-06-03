"""
report.py - Format a multisig health report for human or agent consumption.

Input: a JSON object with these top-level keys:
  - safe: dict mirroring SafeState fields
  - timelock: dict mirroring TimelockState fields (or null)
  - findings: list of {name, severity, detail}
  - score: int 0-100
  - score_label: "HEALTHY" / "ACCEPTABLE" / "AT_RISK" / "CRITICAL"
  - counts: {ok, warn, critical}
  - owners_with_nonce: [{address, nonce}]   (per-signer activity)
"""
from __future__ import annotations
import argparse
import json
import sys
from typing import Any, Dict


SEV_COLOR = {
    "OK":       "\033[32m",  # green
    "WARN":     "\033[33m",  # yellow
    "CRITICAL": "\033[31m",  # red
}
RESET = "\033[0m"


def _short_addr(a: str, head: int = 6, tail: int = 4) -> str:
    if not a or len(a) < head + tail + 2:
        return a or ""
    return f"{a[:2+head]}…{a[-tail:]}"


def render_text(r: Dict[str, Any], use_color: bool = True) -> str:
    safe = r["safe"]
    tl   = r.get("timelock")
    findings = r.get("findings", [])
    score = r.get("score", 0)
    label = r.get("score_label", "")
    counts = r.get("counts", {})
    owners = r.get("owners_with_nonce", [])

    lines = []
    lines.append("=" * 64)
    lines.append(f"  MULTISIG HEALTH REPORT — {_short_addr(safe['address'])}")
    lines.append(f"  Chain ID: {safe['chain_id']}    Safe version: {safe.get('version','?')}")
    lines.append("=" * 64)
    lines.append("")
    lines.append(f"  Threshold:        {safe['threshold']} of {len(safe['owners'])}")
    lines.append(f"  Executed txs:     {safe['nonce']}")
    lines.append(f"  Native balance:   {safe['eth_balance']/1e18:.6f}")
    if tl:
        if tl.get("is_timelock"):
            lines.append(f"  Timelock:         {tl['address']}  delay={tl['min_delay']}s")
        else:
            lines.append(f"  Timelock:         {tl['address']}  (not a valid TimelockController)")
    else:
        lines.append("  Timelock:         none")
    lines.append("")
    if owners:
        lines.append("  Owners")
        lines.append("  " + "-" * 60)
        for o in owners:
            lines.append(f"    {_short_addr(o['address'])}   tx-count={o['nonce']}")
    lines.append("")
    lines.append(f"  >>> HEALTH SCORE: {score} / 100  ({label}) <<<")
    lines.append(f"      {counts.get('ok',0)} OK  /  {counts.get('warn',0)} WARN  /  {counts.get('critical',0)} CRITICAL")
    lines.append("")
    lines.append("  Per-check findings")
    lines.append("  " + "-" * 60)
    for f in findings:
        color = SEV_COLOR.get(f["severity"], "") if use_color else ""
        reset = RESET if use_color else ""
        lines.append(f"  [{color}{f['severity']:>8}{reset}] {f['name']}")
        lines.append(f"             {f['detail']}")
    return "\n".join(lines) + "\n"


def render_markdown(r: Dict[str, Any]) -> str:
    safe = r["safe"]
    tl   = r.get("timelock")
    findings = r.get("findings", [])
    score = r.get("score", 0)
    label = r.get("score_label", "")
    counts = r.get("counts", {})
    owners = r.get("owners_with_nonce", [])

    lines = []
    lines.append(f"# Multisig Health Report — `{safe['address']}`")
    lines.append("")
    lines.append(f"- **Chain ID:** {safe['chain_id']}")
    lines.append(f"- **Safe version:** {safe.get('version','?')}")
    lines.append(f"- **Threshold:** {safe['threshold']} of {len(safe['owners'])}")
    lines.append(f"- **Executed txs:** {safe['nonce']}")
    lines.append(f"- **Native balance:** {safe['eth_balance']/1e18:.6f}")
    if tl and tl.get("is_timelock"):
        lines.append(f"- **Timelock:** `{tl['address']}` (delay {tl['min_delay']}s)")
    else:
        lines.append(f"- **Timelock:** none")
    lines.append("")
    lines.append(f"## 🎯 Health score: **{score} / 100** ({label})")
    lines.append("")
    lines.append(f"- {counts.get('ok',0)} OK")
    lines.append(f"- {counts.get('warn',0)} WARN")
    lines.append(f"- {counts.get('critical',0)} CRITICAL")
    lines.append("")
    if owners:
        lines.append("## Owners")
        lines.append("")
        lines.append("| Address | tx-count |")
        lines.append("|---------|----------|")
        for o in owners:
            lines.append(f"| `{o['address']}` | {o['nonce']} |")
        lines.append("")
    lines.append("## Findings")
    lines.append("")
    lines.append("| Severity | Check | Detail |")
    lines.append("|----------|-------|--------|")
    for f in findings:
        lines.append(f"| {f['severity']} | `{f['name']}` | {f['detail']} |")
    return "\n".join(lines) + "\n"


def render_html(r: Dict[str, Any]) -> str:
    safe = r["safe"]
    tl   = r.get("timelock")
    findings = r.get("findings", [])
    score = r.get("score", 0)
    label = r.get("score_label", "")
    counts = r.get("counts", {})
    owners = r.get("owners_with_nonce", [])

    sev_color = {
        "OK":       "#1e8e3e",
        "WARN":     "#f9ab00",
        "CRITICAL": "#d93025",
    }
    label_color = {
        "HEALTHY":    "#1e8e3e",
        "ACCEPTABLE": "#1a73e8",
        "AT_RISK":    "#f9ab00",
        "CRITICAL":   "#d93025",
    }.get(label, "#202124")

    owner_rows = "".join(
        f"<tr><td><code>{o['address']}</code></td><td>{o['nonce']}</td></tr>"
        for o in owners
    )
    finding_rows = "".join(
        f"<tr><td style='color:{sev_color.get(f['severity'],'#202124')}; font-weight:600;'>{f['severity']}</td>"
        f"<td><code>{f['name']}</code></td>"
        f"<td>{f['detail']}</td></tr>"
        for f in findings
    )

    timelock_html = (
        f"<li><strong>Timelock:</strong> <code>{tl['address']}</code> (delay {tl['min_delay']}s)</li>"
        if tl and tl.get("is_timelock")
        else "<li><strong>Timelock:</strong> none</li>"
    )

    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<title>Multisig Health Report — {safe['address']}</title>
<style>
  body {{ font: 14px/1.4 system-ui, sans-serif; max-width: 900px; margin: 32px auto; padding: 0 16px; color: #202124; }}
  h1 {{ border-bottom: 2px solid #202124; padding-bottom: 4px; }}
  .score {{ font-size: 36px; font-weight: 800; color: {label_color}; margin: 12px 0 4px; }}
  .label {{ font-size: 16px; color: #5f6368; margin-bottom: 16px; }}
  .meta {{ background: #f8f9fa; border-left: 3px solid #1a73e8; padding: 8px 12px; font-size: 13px; }}
  .meta ul {{ margin: 0; padding-left: 18px; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
  th, td {{ border: 1px solid #dadce0; padding: 6px 8px; text-align: left; font-size: 13px; vertical-align: top; }}
  th {{ background: #f8f9fa; }}
  code {{ background: #f1f3f4; padding: 1px 4px; border-radius: 3px; }}
</style></head><body>
<h1>Multisig Health Report</h1>

<p class="score">{score} / 100</p>
<p class="label">{label} &middot; {counts.get('ok',0)} OK, {counts.get('warn',0)} WARN, {counts.get('critical',0)} CRITICAL</p>

<div class="meta">
<ul>
<li><strong>Safe:</strong> <code>{safe['address']}</code></li>
<li><strong>Chain ID:</strong> {safe['chain_id']}</li>
<li><strong>Safe version:</strong> {safe.get('version','?')}</li>
<li><strong>Threshold:</strong> {safe['threshold']} of {len(safe['owners'])}</li>
<li><strong>Executed txs:</strong> {safe['nonce']}</li>
<li><strong>Native balance:</strong> {safe['eth_balance']/1e18:.6f}</li>
{timelock_html}
</ul>
</div>

<h2>Owners</h2>
<table>
<thead><tr><th>Address</th><th>tx-count</th></tr></thead>
<tbody>
{owner_rows or "<tr><td colspan='2'>No owners</td></tr>"}
</tbody>
</table>

<h2>Findings</h2>
<table>
<thead><tr><th>Severity</th><th>Check</th><th>Detail</th></tr></thead>
<tbody>
{finding_rows or "<tr><td colspan='3'>No findings</td></tr>"}
</tbody>
</table>
</body></html>
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="input", default="-")
    p.add_argument("--format", choices=["text", "markdown", "html", "json"], default="text")
    p.add_argument("--out", default="-")
    p.add_argument("--no-color", action="store_true")
    args = p.parse_args()

    raw = sys.stdin.read() if args.input == "-" else open(args.input).read()
    r = json.loads(raw)

    if args.format == "json":
        out = json.dumps(r, indent=2)
    elif args.format == "markdown":
        out = render_markdown(r)
    elif args.format == "html":
        out = render_html(r)
    else:
        out = render_text(r, use_color=not args.no_color)

    if args.out == "-":
        sys.stdout.write(out)
    else:
        with open(args.out, "w") as f:
            f.write(out)


if __name__ == "__main__":
    main()
