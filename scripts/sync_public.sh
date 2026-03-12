#!/usr/bin/env bash
set -euo pipefail

SCRIPT_NAME="$(basename "$0")"

REMOTE="origin"
SOURCE="local/private-main"
TARGET="main"
PUSH_AFTER=true
REBUILD_AFTER=true
RETURN_TO_START=true
MODE="report"
REPORT_PATH=""
FETCH_REMOTE=true

REPORT_SAFE_TO_PROCEED="no"
REPORT_REASON="not evaluated"
SOURCE_SHA=""
TARGET_SHA=""
MERGE_BASE_SHA=""
ANALYSIS_TARGET_REF=""

declare -a PUBLIC_COMMITS=()
declare -a SIMULATION_ROWS=()
declare -a CONFLICT_ROWS=()

print_usage() {
  cat <<USAGE
Usage: $SCRIPT_NAME [options]

Default mode is report-first (no repository mutations). It analyzes pending
public commits and writes a conflict report. Use --apply only after reviewing
the report.

Options:
  --source <branch>       Source branch to cherry-pick from (default: $SOURCE)
  --target <branch>       Target/public branch to publish (default: $TARGET)
  --remote <name>         Remote to sync/push against (default: $REMOTE)
  --report <path>         Report output path (default: .private/docs/CONFLICT_REPORTS/...)
  --apply                 Apply mode (requires --report)
  --no-push               Apply mode: do not run git push at the end
  --no-rebuild            Apply mode: skip automatic python scripts/build_derived_data.py
  --stay-on-target        Apply mode: keep checked out on target branch after completion
  --no-fetch              Skip git fetch before analysis/apply
  -h, --help              Show this help
USAGE
}

log() {
  printf '[sync_public] %s\n' "$*"
}

die() {
  printf '[sync_public] ERROR: %s\n' "$*" >&2
  exit 1
}

has_rg() {
  command -v rg >/dev/null 2>&1
}

stream_matches_regex() {
  local regex="$1"
  if has_rg; then
    rg -q "$regex"
  else
    grep -Eq "$regex"
  fi
}

first_file_match() {
  local regex="$1"
  local file="$2"
  if has_rg; then
    rg -N "$regex" "$file" | head -n1 || true
  else
    grep -E -m1 "$regex" "$file" || true
  fi
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
  git show --pretty='' --name-only "$sha" | stream_matches_regex \
    '^(data/manual_events\.json|data/paredoes\.json|data/provas\.json|data/votalhada/polls\.json|data/derived/.*\.json)$'
}

all_generated_conflicts() {
  local file
  for file in "$@"; do
    case "$file" in
      data/derived/*.json|data/latest.json|data/snapshots/*.json)
        ;;
      *)
        return 1
        ;;
    esac
  done
  return 0
}

classify_path() {
  local file="$1"
  case "$file" in
    data/derived/*|data/latest.json|data/snapshots/*)
      printf 'generated'
      ;;
    data/manual_events.json|data/paredoes.json|data/provas.json|data/votalhada/polls.json)
      printf 'manual-critical'
      ;;
    *)
      printf 'other'
      ;;
  esac
}

ensure_report_path() {
  if [[ -z "$REPORT_PATH" ]]; then
    local source_slug target_slug
    source_slug="$(printf '%s' "$SOURCE" | tr '/:' '__')"
    target_slug="$(printf '%s' "$TARGET" | tr '/:' '__')"
    REPORT_PATH=".private/docs/CONFLICT_REPORTS/$(date -u +%Y-%m-%d_%H-%M-%S)_${source_slug}_to_${target_slug}.md"
  fi
  mkdir -p "$(dirname "$REPORT_PATH")"
}

fetch_if_needed() {
  if [[ "$FETCH_REMOTE" == true ]]; then
    git fetch "$REMOTE" "$TARGET" >/dev/null 2>&1 || die "failed to fetch $REMOTE/$TARGET"
  fi
}

resolve_analysis_refs() {
  if git rev-parse --verify --quiet "refs/remotes/$REMOTE/$TARGET" >/dev/null; then
    ANALYSIS_TARGET_REF="refs/remotes/$REMOTE/$TARGET"
  else
    ANALYSIS_TARGET_REF="$TARGET"
  fi

  SOURCE_SHA="$(git rev-parse "$SOURCE")"
  TARGET_SHA="$(git rev-parse "$ANALYSIS_TARGET_REF")"
  MERGE_BASE_SHA="$(git merge-base "$ANALYSIS_TARGET_REF" "$SOURCE")"
}

collect_public_commits() {
  mapfile -t candidate_commits < <(git rev-list --reverse --no-merges "${ANALYSIS_TARGET_REF}..${SOURCE}")

  PUBLIC_COMMITS=()
  local sha
  for sha in "${candidate_commits[@]}"; do
    if is_public_commit "$sha"; then
      PUBLIC_COMMITS+=("$sha")
    fi
  done
}

simulate_cherry_picks() {
  local tmp_dir wt_dir
  tmp_dir="$(mktemp -d)"
  wt_dir="$tmp_dir/worktree"

  git worktree add --detach "$wt_dir" "$ANALYSIS_TARGET_REF" >/dev/null 2>&1
  trap 'git worktree remove --force "$wt_dir" >/dev/null 2>&1 || true; rm -rf "$tmp_dir"' RETURN

  SIMULATION_ROWS=()
  CONFLICT_ROWS=()

  local sha subject
  for sha in "${PUBLIC_COMMITS[@]}"; do
    subject="$(git show --quiet --format=%s "$sha")"
    if (cd "$wt_dir" && git cherry-pick "$sha" >/dev/null 2>&1); then
      SIMULATION_ROWS+=("$sha|clean|none|$subject")
      continue
    fi

    mapfile -t conflicts < <(cd "$wt_dir" && git diff --name-only --diff-filter=U || true)
    if [[ ${#conflicts[@]} -eq 0 ]]; then
      SIMULATION_ROWS+=("$sha|error|other|$subject")
      REPORT_SAFE_TO_PROCEED="no"
      REPORT_REASON="cherry-pick failed without conflict files"
      (cd "$wt_dir" && git cherry-pick --abort >/dev/null 2>&1 || true)
      break
    fi

    local highest_class="generated"
    local file file_class
    for file in "${conflicts[@]}"; do
      file_class="$(classify_path "$file")"
      CONFLICT_ROWS+=("$sha|$subject|$file|$file_class")
      case "$file_class" in
        manual-critical)
          highest_class="manual-critical"
          ;;
        other)
          if [[ "$highest_class" != "manual-critical" ]]; then
            highest_class="other"
          fi
          ;;
      esac
    done
    SIMULATION_ROWS+=("$sha|conflict|$highest_class|$subject")

    if [[ "$highest_class" == "generated" ]] && all_generated_conflicts "${conflicts[@]}"; then
      (cd "$wt_dir" && git checkout --ours -- "${conflicts[@]}" >/dev/null 2>&1 && git add -- "${conflicts[@]}" >/dev/null 2>&1)
      if ! (cd "$wt_dir" && git cherry-pick --continue >/dev/null 2>&1); then
        if (cd "$wt_dir" && git diff --cached --quiet); then
          (cd "$wt_dir" && git cherry-pick --skip >/dev/null 2>&1 || true)
          SIMULATION_ROWS+=("$sha|generated-empty-skip|generated|$subject")
        else
          REPORT_SAFE_TO_PROCEED="no"
          REPORT_REASON="generated conflict could not continue"
          (cd "$wt_dir" && git cherry-pick --abort >/dev/null 2>&1 || true)
          break
        fi
      fi
      continue
    fi

    REPORT_SAFE_TO_PROCEED="no"
    REPORT_REASON="manual intervention required (${highest_class} conflict)"
    (cd "$wt_dir" && git cherry-pick --abort >/dev/null 2>&1 || true)
    break
  done

  if [[ "$REPORT_SAFE_TO_PROCEED" != "no" ]]; then
    REPORT_SAFE_TO_PROCEED="yes"
    REPORT_REASON="no blocking conflicts detected"
  elif [[ ${#CONFLICT_ROWS[@]} -eq 0 ]] && [[ "$REPORT_REASON" == "not evaluated" ]]; then
    REPORT_REASON="manual intervention required"
  fi
}

write_report() {
  ensure_report_path

  {
    printf '# sync_public Conflict Report\n\n'
    printf 'generated_at_utc: %s\n' "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    printf 'remote: %s\n' "$REMOTE"
    printf 'source_branch: %s\n' "$SOURCE"
    printf 'source_sha: %s\n' "$SOURCE_SHA"
    printf 'target_branch: %s\n' "$TARGET"
    printf 'target_ref: %s\n' "$ANALYSIS_TARGET_REF"
    printf 'target_sha: %s\n' "$TARGET_SHA"
    printf 'merge_base_sha: %s\n' "$MERGE_BASE_SHA"
    printf 'safe_to_proceed: %s\n' "$REPORT_SAFE_TO_PROCEED"
    printf 'reason: %s\n\n' "$REPORT_REASON"

    printf '## Pending public commits\n\n'
    if [[ ${#PUBLIC_COMMITS[@]} -eq 0 ]]; then
      printf -- '- none\n\n'
    else
      local sha subject
      for sha in "${PUBLIC_COMMITS[@]}"; do
        subject="$(git show --quiet --format=%s "$sha")"
        printf -- '- `%s` %s\n' "$sha" "$subject"
      done
      printf '\n'
    fi

    printf '## Simulation results\n\n'
    if [[ ${#SIMULATION_ROWS[@]} -eq 0 ]]; then
      printf -- '- no simulation rows generated\n\n'
    else
      printf '| Commit | Status | Highest Class | Subject |\n'
      printf '|---|---|---|---|\n'
      local row c_sha c_status c_class c_subject
      for row in "${SIMULATION_ROWS[@]}"; do
        IFS='|' read -r c_sha c_status c_class c_subject <<<"$row"
        printf '| `%s` | `%s` | `%s` | %s |\n' "$c_sha" "$c_status" "$c_class" "$c_subject"
      done
      printf '\n'
    fi

    printf '## Conflict details\n\n'
    if [[ ${#CONFLICT_ROWS[@]} -eq 0 ]]; then
      printf -- '- none\n\n'
    else
      printf '| Commit | Class | File |\n'
      printf '|---|---|---|\n'
      local crow r_sha r_subject r_file r_class
      for crow in "${CONFLICT_ROWS[@]}"; do
        IFS='|' read -r r_sha r_subject r_file r_class <<<"$crow"
        printf '| `%s` | `%s` | `%s` |\n' "$r_sha" "$r_class" "$r_file"
      done
      printf '\n'
    fi

    printf '## Recommended next step\n\n'
    if [[ "$REPORT_SAFE_TO_PROCEED" == "yes" ]]; then
      printf 'Run:\n\n'
      printf '```bash\n'
      printf '%s --apply --source %q --target %q --remote %q --report %q\n' "$SCRIPT_NAME" "$SOURCE" "$TARGET" "$REMOTE" "$REPORT_PATH"
      printf '```\n'
    else
      printf 'Manual intervention required before apply. Resolve or decide strategy, then rerun report.\n'
    fi
  } >"$REPORT_PATH"

  log "report written: $REPORT_PATH"
  if [[ "$REPORT_SAFE_TO_PROCEED" == "yes" ]]; then
    log "report result: safe_to_proceed=yes"
  else
    log "report result: safe_to_proceed=no (${REPORT_REASON})"
  fi
}

report_value() {
  local key="$1"
  local line value
  line="$(first_file_match "^${key}:" "$REPORT_PATH")"
  value="$(printf '%s' "$line" | sed -E "s/^${key}:[[:space:]]*//")"
  [[ -n "$value" ]] || die "missing ${key} in report: $REPORT_PATH"
  printf '%s' "$value"
}

validate_report_for_apply() {
  [[ -n "$REPORT_PATH" ]] || die "--apply requires --report <path>"
  [[ -f "$REPORT_PATH" ]] || die "report file not found: $REPORT_PATH"

  local report_remote report_source_branch report_target_branch report_source_sha report_target_sha report_safe
  report_remote="$(report_value "remote")"
  report_source_branch="$(report_value "source_branch")"
  report_target_branch="$(report_value "target_branch")"
  report_source_sha="$(report_value "source_sha")"
  report_target_sha="$(report_value "target_sha")"
  report_safe="$(report_value "safe_to_proceed")"

  [[ "$report_remote" == "$REMOTE" ]] || die "report remote mismatch: expected $REMOTE got $report_remote"
  [[ "$report_source_branch" == "$SOURCE" ]] || die "report source_branch mismatch: expected $SOURCE got $report_source_branch"
  [[ "$report_target_branch" == "$TARGET" ]] || die "report target_branch mismatch: expected $TARGET got $report_target_branch"
  [[ "$report_safe" == "yes" ]] || die "report is not safe_to_proceed=yes; rerun report after manual review"

  fetch_if_needed
  resolve_analysis_refs

  [[ "$SOURCE_SHA" == "$report_source_sha" ]] || die "source branch moved since report (expected $report_source_sha, got $SOURCE_SHA). Rerun report."
  [[ "$TARGET_SHA" == "$report_target_sha" ]] || die "target branch moved since report (expected $report_target_sha, got $TARGET_SHA). Rerun report."
}

apply_changes() {
  local start_branch
  start_branch="$(git rev-parse --abbrev-ref HEAD)"

  require_clean_worktree
  safe_checkout "$TARGET"
  log "pulling latest $TARGET from $REMOTE with rebase"
  git pull --rebase "$REMOTE" "$TARGET"

  collect_public_commits
  if [[ ${#PUBLIC_COMMITS[@]} -eq 0 ]]; then
    log "no public commits to cherry-pick from $SOURCE"
  else
    log "public commits to cherry-pick: ${#PUBLIC_COMMITS[@]}"
    local sha
    for sha in "${PUBLIC_COMMITS[@]}"; do
      log "cherry-picking $(git show --quiet --format='%h %s' "$sha")"
      if ! git cherry-pick "$sha"; then
        mapfile -t conflicts < <(git diff --name-only --diff-filter=U || true)
        if [[ ${#conflicts[@]} -gt 0 ]] && all_generated_conflicts "${conflicts[@]}"; then
          log "auto-resolving generated conflicts with ours (rebuild may run next)"
          git checkout --ours -- "${conflicts[@]}"
          git add -- "${conflicts[@]}"
          if ! git cherry-pick --continue; then
            if git diff --cached --quiet; then
              log "resolved cherry-pick became empty; skipping commit"
              git cherry-pick --skip
            else
              die "unable to continue cherry-pick after generated conflict resolution"
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

  local should_rebuild=false
  if [[ "$REBUILD_AFTER" == true ]]; then
    local sha
    for sha in "${PUBLIC_COMMITS[@]}"; do
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

  if [[ "$RETURN_TO_START" == true ]] && [[ "$start_branch" != "$TARGET" ]]; then
    log "returning to starting branch: $start_branch"
    git checkout "$start_branch" >/dev/null
  fi
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
      --report)
        [[ $# -ge 2 ]] || die "--report requires a path value"
        REPORT_PATH="$2"
        shift 2
        ;;
      --apply)
        MODE="apply"
        shift
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
      --no-fetch)
        FETCH_REMOTE=false
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

branch_exists "$SOURCE" || die "source branch not found: $SOURCE"
branch_exists "$TARGET" || die "target branch not found: $TARGET"
git remote get-url "$REMOTE" >/dev/null 2>&1 || die "remote not found: $REMOTE"

log "source=$SOURCE target=$TARGET remote=$REMOTE"
log "mode=$MODE"

if [[ "$MODE" == "report" ]]; then
  fetch_if_needed
  resolve_analysis_refs
  collect_public_commits
  REPORT_SAFE_TO_PROCEED="yes"
  REPORT_REASON="no blocking conflicts detected"
  if [[ ${#PUBLIC_COMMITS[@]} -gt 0 ]]; then
    simulate_cherry_picks
  fi
  write_report
else
  validate_report_for_apply
  apply_changes
fi

log "done"
