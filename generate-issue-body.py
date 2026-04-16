#!/usr/bin/env python3
"""
generate-issue-body.py
Parses a snyk test --json report and generates a rich GitHub Issue body
summarizing all vulnerabilities, their severity, and fix status.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from collections import Counter


SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
}

SEVERITY_ORDER = ["critical", "high", "medium", "low"]


def load_report(path: str) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    # snyk test --all-projects returns a list; single project returns a dict
    if isinstance(data, dict):
        return [data]
    return data


def extract_vulns(reports: list[dict]) -> list[dict]:
    all_vulns = []
    for report in reports:
        project_name = report.get("projectName", "unknown")
        for vuln in report.get("vulnerabilities", []):
            vuln["_project"] = project_name
            all_vulns.append(vuln)
    return all_vulns


def severity_counts(vulns: list[dict]) -> Counter:
    return Counter(v.get("severity", "unknown") for v in vulns)


def format_vuln_table(vulns: list[dict]) -> str:
    lines = [
        "| Severity | Package | CVE / ID | Title | Fixable |",
        "|----------|---------|----------|-------|---------|",
    ]
    # Sort by severity
    sorted_vulns = sorted(
        vulns,
        key=lambda v: SEVERITY_ORDER.index(v.get("severity", "low"))
        if v.get("severity") in SEVERITY_ORDER
        else 99,
    )
    for v in sorted_vulns:
        sev = v.get("severity", "?")
        emoji = SEVERITY_EMOJI.get(sev, "⚪")
        pkg = v.get("packageName", "unknown")
        pkg_version = v.get("version", "")
        pkg_str = f"`{pkg}@{pkg_version}`" if pkg_version else f"`{pkg}`"
        cve = v.get("identifiers", {}).get("CVE", [])
        cve_str = ", ".join(cve) if cve else v.get("id", "N/A")
        title = v.get("title", "Unknown vulnerability")[:80]
        fixable = "✅" if v.get("isUpgradable") or v.get("isPatchable") else "❌"
        lines.append(f"| {emoji} {sev} | {pkg_str} | {cve_str} | {title} | {fixable} |")
    return "\n".join(lines)


def format_project_breakdown(vulns: list[dict]) -> str:
    by_project: dict[str, list] = {}
    for v in vulns:
        proj = v.get("_project", "unknown")
        by_project.setdefault(proj, []).append(v)

    lines = []
    for proj, pvulns in sorted(by_project.items()):
        counts = severity_counts(pvulns)
        summary = ", ".join(
            f"{SEVERITY_EMOJI[s]} {counts[s]} {s}"
            for s in SEVERITY_ORDER
            if counts[s] > 0
        )
        lines.append(f"- **{proj}**: {summary}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True, help="Path to snyk-report.json")
    parser.add_argument("--pr-url", default="", help="URL of the fix PR (if created)")
    parser.add_argument("--branch", default="", help="Fix branch name")
    args = parser.parse_args()

    try:
        reports = load_report(args.report)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"## ⚠️ Snyk Bot — Parse Error\n\nCould not read report: {e}", file=sys.stdout)
        sys.exit(0)

    vulns = extract_vulns(reports)
    counts = severity_counts(vulns)
    total = len(vulns)
    fixable = sum(1 for v in vulns if v.get("isUpgradable") or v.get("isPatchable"))
    scan_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    pr_section = ""
    if args.pr_url:
        pr_section = f"""
## 🔧 Fix PR

A draft pull request has been automatically created with dependency patches applied:
**➡️ {args.pr_url}**

> This PR is a **draft** and requires human review before merging.
> Please review the changes, run your test suite, and approve if everything looks good.
"""
    else:
        pr_section = """
## 🔧 Fix Status

No automatic fixes could be applied (vulnerabilities may require manual remediation or are not auto-fixable).
"""

    body = f"""## 🔒 Snyk Security Scan — {scan_time}

> **This issue was created automatically by the Snyk Bot.**
> A human must review and merge any fix PRs — the bot will never auto-merge.

---

## Summary

| Metric | Count |
|--------|-------|
| 🔴 Critical | {counts.get("critical", 0)} |
| 🟠 High | {counts.get("high", 0)} |
| 🟡 Medium | {counts.get("medium", 0)} |
| 🔵 Low | {counts.get("low", 0)} |
| **Total** | **{total}** |
| ✅ Auto-fixable | {fixable} |
| ❌ Manual fix needed | {total - fixable} |

{pr_section}

---

## Project Breakdown

{format_project_breakdown(vulns)}

---

## Vulnerability Details

<details>
<summary>Click to expand full vulnerability table ({total} issues)</summary>

{format_vuln_table(vulns)}

</details>

---

## What to do

1. **Review the fix PR** (linked above) — check that the version bumps don't break anything
2. **Run your test suite** on the PR branch before merging
3. **For non-fixable issues** — manually assess risk and create follow-up tickets if needed
4. **Close this issue** once the fix PR is merged or the vulnerabilities are resolved

---

*Generated by [snyk-bot](../.github/workflows/snyk-bot.yml) · [Snyk](https://snyk.io)*
"""

    print(body)


if __name__ == "__main__":
    main()
