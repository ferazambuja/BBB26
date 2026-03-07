# Git Workflow: Local Private + Public GitHub

This project uses a dual-branch workflow:

- `main` → public branch, push to GitHub
- `local/private-main` → local-only branch, never push

## One-time Setup

```bash
# Create local-only branch from main
git checkout -b local/private-main main

# Return to public branch when preparing public releases
git checkout main
```

## Daily Work (private + public mixed)

1. Work on `local/private-main`.
2. Commit private/internal changes with message prefix `private:`.
3. Commit publishable changes with message prefix `public:`.

## Public Release Flow

```bash
# 1) Move to public branch
git checkout main

# 2) Pull latest public state
git pull --rebase origin main

# 3) Cherry-pick only public commits from local branch
git cherry-pick <public-commit-sha-1> <public-commit-sha-2>

# 4) Push public branch
git push origin main
```

## Rules

- Never push `local/private-main`.
- Never commit private docs into `main`.
- Never track local tooling/worktree paths in `main` (`.claude/**`, `.worktrees/**`).
- If uncertain whether a document is public-safe, keep it in `.private/docs/`.

## Optional Safety Hook

Use a pre-push hook (see `.githooks/pre-push`) to block:

- pushes from `local/*` branches
- pushes where private denylist files are tracked on branch tip
