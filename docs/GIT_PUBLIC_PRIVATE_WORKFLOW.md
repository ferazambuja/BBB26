# Git Workflow: Main-First + Local Private Files

This project now uses a **main-first workflow**:

- `main` → normal working branch and public branch
- `feature/*` → optional short-lived review/PR branches
- `local/*` → optional local-only archive/recovery branches, never push

The separation between public and private material happens through **tracking state**, not through a daily dual-branch workflow:

- public-safe work lives on tracked files in `main`
- private notes and scratch material stay local via `.gitignore` and denylist checks

## Daily Work

Work directly on `main` unless you are intentionally recovering old local history or using a short-lived `feature/*` branch for review.

```bash
git checkout main
git pull --rebase origin main

# Make your edits
python scripts/build_derived_data.py

git add data/ docs/MANUAL_EVENTS_AUDIT.md docs/SCORING_AND_INDEXES.md
git commit -m "<description>"
git push origin main

# Optional: trigger deploy immediately instead of waiting for cron
gh workflow run daily-update.yml
```

Human commits on `main` use normal descriptive subjects. GitHub Actions bot commits on `main` still use the `data:` prefix.

## Private Material

Keep local-only material out of public history:

- `.private/**`
- `CLAUDE.md`
- `.claude/**`
- `.worktrees/**`
- `docs/superpowers/**`
- other planning, review, or WIP docs that are not explicitly public

If visibility is unclear, keep the file under `.private/docs/` first.

## Safety Checks

The main protections are structural:

- `.gitignore` keeps local-only files out of normal staging
- denylist rules define what must never be tracked on public history
- `.githooks/pre-push`, when installed locally, blocks pushes from `local/*` branches
- `.githooks/pre-push`, when installed locally, blocks private/denylist paths in pushed history and on the branch tip
- `.githooks/pre-push`, when installed locally, blocks bot commits on `main` that do not start with `data:`
- `.githooks/pre-push`, when installed locally, blocks embedded git repositories/gitlinks
- `.github/workflows/public-policy-report.yml` reports the same policy class on pushes to `main`

## Legacy Recovery Flow

If you still have an old `local/private-main`, treat it as **archival history**, not the normal working branch.

Useful inspection commands:

```bash
git cherry -v main local/private-main
git log --oneline --no-merges main..local/private-main
git stash list
```

`scripts/sync_public.sh` remains available as a **legacy reconciliation helper** for reviewed commits from `local/private-main`, but it is no longer the recommended daily workflow.

```bash
scripts/sync_public.sh
scripts/sync_public.sh --apply --report .private/docs/CONFLICT_REPORTS/<report>.md
```

Use it only when you are intentionally reconciling old local commits back onto `main`.
