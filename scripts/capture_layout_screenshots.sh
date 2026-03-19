#!/usr/bin/env bash
set -euo pipefail

# Page-by-page wrapper with verbose progress.
# Default behavior is optimized for retakes (no render/install) and can be
# overridden with --render / --install-browser.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RENDER=0
INSTALL_BROWSER=0
PROFILES="desktop,mobile"
OUTPUT_DIR=""
PASS_ARGS=()

while (($# > 0)); do
  case "$1" in
    --render)
      RENDER=1
      shift
      ;;
    --install-browser)
      INSTALL_BROWSER=1
      shift
      ;;
    --profiles)
      PROFILES="${2:?missing value for --profiles}"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="${2:?missing value for --output-dir}"
      shift 2
      ;;
    *)
      PASS_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="tmp/page_screenshots/$(date -u +%Y-%m-%d_%H-%M-%S)"
fi

if (( RENDER )); then
  echo "[STEP] safe quarto render"
  python3 scripts/quarto_render_safe.py
fi

if (( INSTALL_BROWSER )); then
  echo "[STEP] playwright browser install (chromium)"
  npx -y playwright@latest install chromium
fi

mapfile -t PAGES < <(python3 - <<'PY'
import sys
from pathlib import Path
sys.path.append(str(Path("scripts").resolve()))
from capture_quarto_screenshots import discover_site_pages, DEFAULT_SITE_DIR, DEFAULT_QUARTO_CONFIG
for page in discover_site_pages(DEFAULT_SITE_DIR, DEFAULT_QUARTO_CONFIG):
    print(page)
PY
)

TOTAL="${#PAGES[@]}"
if (( TOTAL == 0 )); then
  echo "No pages discovered under _site."
  exit 1
fi

MANIFEST_DIR="${OUTPUT_DIR}/.page_manifests"
mkdir -p "$MANIFEST_DIR"

STATUS=0
for i in "${!PAGES[@]}"; do
  page="${PAGES[$i]}"
  idx=$((i + 1))
  echo "[PAGE ${idx}/${TOTAL}] ${page}"

  if python3 scripts/capture_quarto_screenshots.py \
    --skip-install \
    --profiles "$PROFILES" \
    --output-dir "$OUTPUT_DIR" \
    --page "$page" \
    --verbose \
    "${PASS_ARGS[@]}"; then
    :
  else
    STATUS=1
  fi

  if [[ -f "${OUTPUT_DIR}/manifest.json" ]]; then
    cp "${OUTPUT_DIR}/manifest.json" "${MANIFEST_DIR}/${page%.html}.json"
  fi
done

python3 - <<'PY' "$OUTPUT_DIR" "$PROFILES"
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

output_dir = Path(sys.argv[1])
profiles = [p.strip() for p in sys.argv[2].split(",") if p.strip()]
manifest_dir = output_dir / ".page_manifests"

captures = []
failures = []
pages = []
base_url = None

for mf in sorted(manifest_dir.glob("*.json")):
    data = json.loads(mf.read_text(encoding="utf-8"))
    pages.extend(data.get("pages", []))
    captures.extend(data.get("captures", []))
    failures.extend(data.get("failures", []))
    if base_url is None:
        base_url = data.get("base_url")

manifest = {
    "captured_at_utc": datetime.now(timezone.utc).isoformat(),
    "mode": "page-by-page",
    "profiles": profiles,
    "pages": sorted(set(pages)),
    "base_url": base_url,
    "captures": captures,
    "failures": failures,
}
(output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
PY

echo "[DONE] output=${OUTPUT_DIR}"
echo "[DONE] manifest=${OUTPUT_DIR}/manifest.json"
exit "$STATUS"
