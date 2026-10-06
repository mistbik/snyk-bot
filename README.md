# Snyk Security Bot

An automated GitHub Actions bot that scans your repos for vulnerabilities using Snyk, opens fix PRs, creates tracking issues, and waits for a human to review and merge.

**The bot never auto-merges. Every fix requires human approval.**

---

## How it works

1. **Triggers** — runs on a weekly schedule (Monday 9am UTC), on pushes to `main` that touch dependency files, or manually via `workflow_dispatch`
2. **Scans** — runs `snyk test --all-projects --json` and counts vulnerabilities by severity
3. **Fixes** — runs `snyk fix` to apply auto-patchable dependency upgrades
4. **PR** — opens a **draft PR** on a `snyk/fix-YYYY-MM-DD` branch with the patched files
5. **Issue** — creates a GitHub Issue with the full vulnerability report, severity breakdown, and link to the PR
6. **You** — review the PR, run tests, and merge (or close) manually

---

## Setup

### 1. Add secrets to your repository

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Value |
|--------|-------|
| `SNYK_TOKEN` | Your Snyk API token (get it from [app.snyk.io/account](https://app.snyk.io/account)) |

The `GITHUB_TOKEN` is provided automatically by GitHub Actions — no setup needed.

### 2. Add labels to your repo

Create these labels in **Issues → Labels** (or they'll be created as plain text):

- `security` — red (#d73a4a)
- `snyk-bot` — purple (#6f42c1)
- `needs-review` — yellow (#e4e669)

Or run this one-liner (requires `gh` CLI):

```bash
gh label create security --color d73a4a --description "Security vulnerability"
gh label create snyk-bot --color 6f42c1 --description "Created by Snyk bot"
gh label create needs-review --color e4e669 --description "Requires human review before action"
```

### 3. Copy the files into your repo

```
.github/
  workflows/
    snyk-bot.yml       ← the workflow
scripts/
  generate-issue-body.py  ← issue body generator
  pr-template.md          ← PR description template
```

### 4. Configure (optional)

In `snyk-bot.yml`, you can change:

| Setting | Where | Default |
|---------|-------|---------|
| Schedule | `cron` line | Every Monday 9am UTC |
| Severity threshold | `workflow_dispatch` input default | `high` |
| Reviewers on PR | `gh pr create --reviewer` flag | (none set — add your team) |
| Base branch | `github.event.repository.default_branch` | auto-detected |

---

## Adding reviewers automatically

Edit the `gh pr create` command in the workflow to add reviewers:

```yaml
gh pr create \
  --title "..." \
  --reviewer your-team-slug \  # add this
  --label "security,snyk-bot,needs-review" \
  ...
```

---

## Running it manually

Go to **Actions → Snyk Security Bot → Run workflow** and optionally set a severity threshold (`low`, `medium`, `high`, or `critical`).

---

## What the bot can and can't fix automatically

| Package manager | Auto-fix supported |
|----------------|--------------------|
| npm / yarn | ✅ Yes (`snyk fix`) |
| pip (requirements.txt) | ✅ Yes |
| Go modules | ⚠️ Partial |
| Maven / Gradle | ❌ Manual only |
| Docker base images | ❌ Manual only |

For non-fixable issues, the bot still creates an issue with the full report so your team knows what needs attention.

---

## Permissions required

The workflow uses `permissions: contents: write, issues: write, pull-requests: write`. These are scoped to the repository and use the built-in `GITHUB_TOKEN` — no extra GitHub App or PAT needed.
