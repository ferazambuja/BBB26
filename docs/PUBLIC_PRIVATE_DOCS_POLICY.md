# Public vs Private Documentation Policy

This repository is public. Documentation is split into two classes:

- **Public docs**: safe to publish on GitHub.
- **Private docs**: local-only working material, never pushed.

## Public Docs (Allowlist)

Only these documentation files/directories are public by default:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/OPERATIONS_GUIDE.md`
- `docs/MANUAL_EVENTS_GUIDE.md`
- `docs/SCORING_AND_INDEXES.md`
- `docs/PROGRAMA_BBB26.md`
- `docs/PUBLIC_PRIVATE_DOCS_POLICY.md`
- `docs/GIT_PUBLIC_PRIVATE_WORKFLOW.md`
- `docs/MANUAL_EVENTS_AUDIT.md`
- `data/CHANGELOG.md`
- `data/votalhada/README.md`

## Private Docs (Denylist)

These are local-only and must not be pushed:

- `CLAUDE.md`
- `.private/**`
- planning/review/WIP docs (for example: TODO trackers, code review notes, tech debt scratch docs, layout audits, implementation plans)

## Default Rule

If document visibility is unclear, treat it as **private** and place it under `.private/docs/`.

## AI Agent Pre-Commit / Pre-Push Checklist

Before `git commit` or `git push`, agents must:

1. Confirm branch is pushable public branch (`main`), not `local/*`.
2. Run `git diff --cached --name-only` and verify no private paths are staged.
3. Run `git ls-files` checks (or hook) to confirm denylist files are not tracked on the public branch tip.
4. If a private doc is needed for execution context, keep it under `.private/docs/` only.
