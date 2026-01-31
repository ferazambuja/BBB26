#!/bin/bash
# fix_claude_code_cache.sh — Fix Claude Code infinite loop from corrupted project cache
#
# PURPOSE: Resolve Claude Code 2.1.27 bug where orphaned session files in
# ~/.claude/projects/ cause infinite CPU loop (99% CPU, ignores SIGTERM).
#
# BUG REF: https://github.com/anthropics/claude-code/issues/22054
#
# SYMPTOMS: UI freezes after first prompt; process uses 99% CPU; kill fails (need kill -9).
# ROOT CAUSE: sessions-index.json references fewer sessions than exist on disk (orphaned files).
#
# USAGE:
#   ./scripts/fix_claude_code_cache.sh              # Dry-run: show what would be removed
#   ./scripts/fix_claude_code_cache.sh --execute    # Remove corrupted cache (session history lost)
#   ./scripts/fix_claude_code_cache.sh --backup     # Backup to /tmp before removing
#
# WARNING: Deleting the cache removes Claude Code session history for this project.
#
# REFERENCE: anthropics/claude-code#22054

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CLAUDE_PROJECTS="${CLAUDE_PROJECTS_DIR:-$HOME/.claude/projects}"

# Parse arguments
EXECUTE=false
BACKUP=false

for arg in "$@"; do
    case "$arg" in
        --execute|-x) EXECUTE=true ;;
        --backup|-b) BACKUP=true ;;
        --help|-h)
            echo "Usage: $0 [--execute] [--backup]"
            echo ""
            echo "Fix Claude Code infinite loop from corrupted project cache (anthropics/claude-code#22054)."
            echo ""
            echo "Options:"
            echo "  --execute   Actually remove the cache (default: dry-run only)"
            echo "  --backup    Copy cache to /tmp before removing"
            echo "  --help      Show this help"
            echo ""
            echo "Project: $PROJECT_ROOT"
            exit 0
            ;;
    esac
done

# Derive cache path: /Users/foo/bar/baz -> -Users-foo-bar-baz
PROJECT_PATH_ENCODED="-${PROJECT_ROOT#/}"
PROJECT_PATH_ENCODED="${PROJECT_PATH_ENCODED//\//-}"

CACHE_DIR="$CLAUDE_PROJECTS/$PROJECT_PATH_ENCODED"

if [[ ! -d "$CACHE_DIR" ]]; then
    echo "No Claude Code project cache found at:"
    echo "  $CACHE_DIR"
    echo "Nothing to fix."
    exit 0
fi

# Count session files (SC2155: separate declaration from assignment)
SESSION_COUNT=0
SESSION_COUNT=$(find "$CACHE_DIR" -maxdepth 1 -name "*.jsonl" 2>/dev/null | wc -l | tr -d ' ')
SESSION_COUNT=${SESSION_COUNT:-0}

# Count indexed sessions (grep -c exits 1 on zero matches; use || true per DF-344)
# Match both "id" and "sessionId" for different index formats
INDEX_FILE="$CACHE_DIR/sessions-index.json"
INDEX_SESSIONS=0
if [[ -f "$INDEX_FILE" ]]; then
    INDEX_SESSIONS=$(grep -cE '"id"|"sessionId"' "$INDEX_FILE" 2>/dev/null || true)
    INDEX_SESSIONS=${INDEX_SESSIONS:-0}
fi

echo "Claude Code project cache:"
echo "  Path:     $CACHE_DIR"
echo "  Sessions: $SESSION_COUNT files on disk"
echo "  Indexed:  $INDEX_SESSIONS in sessions-index.json"
echo ""

if [[ "$EXECUTE" != "true" ]]; then
    echo "DRY-RUN: Would remove cache to fix infinite loop."
    echo "Run with --execute to actually remove."
    echo ""
    echo "  $0 --execute"
    exit 0
fi

# Confirm before destructive action
if [[ "$BACKUP" == "true" ]]; then
    BACKUP_PATH="/tmp/claude-code-cache-backup-$(date +%Y%m%d-%H%M%S)-${PROJECT_PATH_ENCODED}.tar.gz"
    echo "Backing up to: $BACKUP_PATH"
    tar -czf "$BACKUP_PATH" -C "$CLAUDE_PROJECTS" -- "$PROJECT_PATH_ENCODED"
    echo "Backup complete."
    echo ""
fi

echo "Removing corrupted cache..."
rm -rf "$CACHE_DIR"
echo "Done. Claude Code should start normally (session history was removed)."
