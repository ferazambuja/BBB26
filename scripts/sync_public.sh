#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

REMOTE="origin"
SOURCE="local/private-main"
TARGET="main"
PUSH_AFTER=true
REBUILD_AFTER=true
RETURN_TO_START=true

print_usage() {
  cat <<EOF
Usage: $SCRIPT_NAME [options]

Sync public commits from a source branch into target branch, handling recurring
data/derived conflicts and pushing the result.

Options:
  --source <branch>       Source branch to cherry-pick from (default: $SOURCE)
  --target <branch>       Target/public branch to publish (default: $TARGET)
  --remote <name>         Remote to sync/push against (default: $REMOTE)
  --no-push               Do not run git push at the end
  --no-rebuild            Skip automatic python scripts/build_derived_data.py
  --stay-on-target        Keep checked out on target branch after completion
  -h, --help              Show this help
EOF
}

log() {
  printf '[sync_public] %s\n' "$*"
}

die() {
  printf '[sync_public] ERROR: %s\n' "$*" >&2
  exit 1
}

require_clean_worktree() {
  if ! git diff --quiet || ! git diff --cached --quiet; then
    die "working tree is not clean. Commit or stash changes first."
  fi
}

branch_exists() {
  git rev-parse --verify --quiet "$1" >/dev/null
}

safe_checkout() {
  local branch="$1"
  if [[ "$(git rev-parse --abbrev-ref HEAD)" != "$branch" ]]; then
    git checkout "$branch" >/dev/null
  fi
}

is_public_commit() {
  local sha="$1"
  local subject
  subject="$(git show --quiet --format=%s "$sha")"
  [[ "$subject" == public:* ]]
}

needs_rebuild_for_commit() {
  local sha="$1"
  git show --pretty='' --name-only "$sha" | rg -q \
    '^(data/manual_events\.json|data/paredoes\.json|data/provas\.json|data/votalhada/polls\.json|data/derived/.*\.json)$'
}

all_derived_conflicts() {
  local file
  for file in "$@"; do
    [[ "$file" =~ ^data/derived/.*\.json$ ]] || return 1
  done
  return 0
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --source)
        [[ $# -ge 2 ]] || die "--source requires a value"
        SOURCE="$2"
        shift 2
        ;;
      --target)
        [[ $# -ge 2 ]] || die "--target requires a value"
        TARGET="$2"
        shift 2
        ;;
      --remote)
        [[ $# -ge 2 ]] || die "--remote requires a value"
        REMOTE="$2"
        shift 2
        ;;
      --no-push)
        PUSH_AFTER=false
        shift
        ;;
      --no-rebuild)
        REBUILD_AFTER=false
        shift
        ;;
      --stay-on-target)
        RETURN_TO_START=false
        shift
        ;;
      -h|--help)
        print_usage
        exit 0
        ;;
      *)
        die "unknown option: $1"
        ;;
    esac
  done
}

parse_args "$@"

command -v rg >/dev/null || die "rg is required"

START_BRANCH="$(git rev-parse --abbrev-ref HEAD)"

require_clean_worktree
branch_exists "$SOURCE" || die "source branch not found: $SOURCE"
branch_exists "$TARGET" || die "target branch not found: $TARGET"
git remote get-url "$REMOTE" >/dev/null 2>&1 || die "remote not found: $REMOTE"

log "source=$SOURCE target=$TARGET remote=$REMOTE"

safe_checkout "$TARGET"
log "pulling latest $TARGET from $REMOTE with rebase"
git pull --rebase "$REMOTE" "$TARGET"

mapfile -t candidate_commits < <(git rev-list --reverse --no-merges "${TARGET}..${SOURCE}")

public_commits=()
for sha in "${candidate_commits[@]}"; do
  if is_public_commit "$sha"; then
    public_commits+=("$sha")
  fi
done

if [[ ${#public_commits[@]} -eq 0 ]]; then
  log "no public commits to cherry-pick from $SOURCE"
else
  log "public commits to cherry-pick: ${#public_commits[@]}"
  for sha in "${public_commits[@]}"; do
    log "cherry-picking $(git show --quiet --format='%h %s' "$sha")"
    if ! git cherry-pick "$sha"; then
      mapfile -t conflicts < <(git diff --name-only --diff-filter=U || true)
      if [[ ${#conflicts[@]} -gt 0 ]] && all_derived_conflicts "${conflicts[@]}"; then
        log "auto-resolving derived-data conflicts with ours (rebuild will run next)"
        git checkout --ours -- "${conflicts[@]}"
        git add -- "${conflicts[@]}"
        if ! git cherry-pick --continue; then
          if git diff --cached --quiet; then
            log "resolved cherry-pick became empty; skipping commit"
            git cherry-pick --skip
          else
            die "unable to continue cherry-pick after derived conflict resolution"
          fi
        fi
      else
        printf '[sync_public] Conflicts require manual resolution:\n' >&2
        printf '  %s\n' "${conflicts[@]}" >&2
        printf '[sync_public] Resolve, then run: git cherry-pick --continue\n' >&2
        exit 2
      fi
    fi
  done
fi

should_rebuild=false
if [[ "$REBUILD_AFTER" == true ]]; then
  for sha in "${public_commits[@]}"; do
    if needs_rebuild_for_commit "$sha"; then
      should_rebuild=true
      break
    fi
  done
fi

if [[ "$should_rebuild" == true ]]; then
  log "running python scripts/build_derived_data.py"
  python scripts/build_derived_data.py
  git add -A data/derived
  if [[ -f docs/MANUAL_EVENTS_AUDIT.md ]]; then
    git add docs/MANUAL_EVENTS_AUDIT.md
  fi
  if ! git diff --cached --quiet; then
    git commit -m "public: data: rebuild derived after sync_public"
    log "committed rebuilt derived artifacts"
  else
    log "derived rebuild produced no new diff"
  fi
fi

if [[ "$PUSH_AFTER" == true ]]; then
  log "pushing $TARGET to $REMOTE"
  git push "$REMOTE" "$TARGET"
fi

if [[ "$RETURN_TO_START" == true ]] && [[ "$START_BRANCH" != "$TARGET" ]]; then
  log "returning to starting branch: $START_BRANCH"
  git checkout "$START_BRANCH" >/dev/null
fi

log "done"
