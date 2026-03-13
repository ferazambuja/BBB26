"""Verify that all cross-page anchor links in Python and QMD files resolve to
real anchors in target QMD pages.

Scans every ``*.py`` under ``scripts/`` and every ``*.qmd`` in the repo root
for patterns like ``page.html#anchor``, then checks the corresponding
``.qmd`` file for:

1. An explicit Quarto anchor attribute ``{#anchor}`` on a heading, **or**
2. A heading whose text slugifies to the anchor (Quarto/Pandoc rules).

Cell labels (``#| label: anchor``) are noted as *fragile* but still accepted.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Directories / globs to scan for links
PYTHON_DIRS = [REPO_ROOT / "scripts"]
QMD_DIR = REPO_ROOT

# ---------------------------------------------------------------------------
# Quarto slugification (mirrors Pandoc behaviour)
# ---------------------------------------------------------------------------

def quarto_slugify(text: str) -> str:
    """Slugify a heading the way Quarto/Pandoc does.

    Rules:
    - Strip leading/trailing whitespace
    - Convert to lowercase
    - Replace spaces and underscores with hyphens
    - Remove characters that are not alphanumeric, hyphens, periods, or
      Unicode letters/marks (Pandoc keeps accented chars like ``ã``)
    - Collapse consecutive hyphens
    - Strip leading/trailing hyphens
    """
    text = text.strip().lower()
    # Remove emoji (Quarto strips most Symbol/Other chars)
    cleaned = []
    for ch in text:
        cat = unicodedata.category(ch)
        # Keep: letters (L*), marks (M*), numbers (N*), hyphens, periods, spaces
        if (cat.startswith(("L", "M", "N"))
                or ch in ("-", ".", " ", "_")):
            cleaned.append(ch)
    text = "".join(cleaned)
    text = text.replace(" ", "-").replace("_", "-")
    text = re.sub(r"-{2,}", "-", text)
    text = text.strip("-")
    return text


# ---------------------------------------------------------------------------
# Link extraction
# ---------------------------------------------------------------------------

_LINK_RE = re.compile(
    r"""
    (?:                          # optional prefix (href=, markdown [](), etc.)
        href\s*=\s*["']          # href="..." or href='...'
      | \]\(                     # markdown [text](link)
      | ["']                     # bare Python string
    )
    ([a-zA-Z0-9_-]+\.html\#     # page.html#
     [a-zA-Z0-9_\u00C0-\u024F-]+)  # anchor (may include accented chars)
    """,
    re.VERBOSE,
)


def _extract_links(text: str) -> list[tuple[str, str]]:
    """Return list of (page_stem, anchor) from cross-page links in *text*."""
    results = []
    for m in _LINK_RE.finditer(text):
        full = m.group(1)
        page_part, anchor = full.split("#", 1)
        stem = page_part.replace(".html", "")
        results.append((stem, anchor))
    return results


# ---------------------------------------------------------------------------
# Anchor resolution in QMD files
# ---------------------------------------------------------------------------

# Matches explicit anchor attributes: {#some-anchor}
_EXPLICIT_ANCHOR_RE = re.compile(r"\{#([a-zA-Z0-9_\u00C0-\u024F-]+)\}")

# Matches headings: lines starting with one or more '#'
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s*\{#[^}]+\})?\s*$", re.MULTILINE)

# Matches cell labels: #| label: some-label
_CELL_LABEL_RE = re.compile(r"^#\|\s*label:\s*(\S+)", re.MULTILINE)


def _collect_anchors(qmd_path: Path) -> dict[str, str]:
    """Return {anchor: source_type} for all anchors in *qmd_path*.

    source_type is one of: "explicit", "heading-slug", "cell-label".
    """
    text = qmd_path.read_text(encoding="utf-8")
    anchors: dict[str, str] = {}

    # 1. Explicit anchors {#foo} — highest priority
    for m in _EXPLICIT_ANCHOR_RE.finditer(text):
        anchors[m.group(1)] = "explicit"

    # 2. Heading slugs (only if not already explicit)
    for m in _HEADING_RE.finditer(text):
        heading_text = m.group(2).strip()
        # Remove any trailing {#...} that was already captured
        heading_text = re.sub(r"\s*\{#[^}]+\}\s*$", "", heading_text).strip()
        slug = quarto_slugify(heading_text)
        if slug and slug not in anchors:
            anchors[slug] = "heading-slug"

    # 3. Cell labels (fragile — only if not already present)
    for m in _CELL_LABEL_RE.finditer(text):
        label = m.group(1)
        if label not in anchors:
            anchors[label] = "cell-label"

    return anchors


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _gather_all_links() -> list[tuple[str, str, str, int]]:
    """Return [(source_file, page_stem, anchor, line_number), ...]."""
    links: list[tuple[str, str, str, int]] = []

    # Scan Python files under scripts/
    for scripts_dir in PYTHON_DIRS:
        for py_file in sorted(scripts_dir.rglob("*.py")):
            # Skip __pycache__ and hidden dirs
            if any(p.startswith((".","__")) for p in py_file.parts):
                continue
            try:
                lines = py_file.read_text(encoding="utf-8").splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(lines, 1):
                for stem, anchor in _extract_links(line):
                    links.append((str(py_file.relative_to(REPO_ROOT)), stem, anchor, i))

    # Scan QMD files in repo root
    for qmd_file in sorted(QMD_DIR.glob("*.qmd")):
        try:
            lines = qmd_file.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(lines, 1):
            for stem, anchor in _extract_links(line):
                links.append((str(qmd_file.relative_to(REPO_ROOT)), stem, anchor, i))

    return links


def test_all_cross_page_anchors_exist():
    """Every cross-page link ``page.html#anchor`` must resolve in the target QMD."""
    links = _gather_all_links()
    assert links, "No cross-page links found — scan logic may be broken"

    # Cache QMD anchor maps
    anchor_cache: dict[str, dict[str, str]] = {}

    dead: list[str] = []
    fragile: list[str] = []

    for source, page_stem, anchor, lineno in links:
        qmd_path = REPO_ROOT / f"{page_stem}.qmd"
        if not qmd_path.exists():
            dead.append(
                f"  {source}:{lineno} -> {page_stem}.html#{anchor}  "
                f"(target file {page_stem}.qmd not found)"
            )
            continue

        if page_stem not in anchor_cache:
            anchor_cache[page_stem] = _collect_anchors(qmd_path)

        anchors = anchor_cache[page_stem]
        if anchor not in anchors:
            dead.append(
                f"  {source}:{lineno} -> {page_stem}.html#{anchor}  "
                f"(anchor not found in {page_stem}.qmd)"
            )
        elif anchors[anchor] == "cell-label":
            fragile.append(
                f"  {source}:{lineno} -> {page_stem}.html#{anchor}  "
                f"(fragile: cell-label only in {page_stem}.qmd)"
            )

    # Fragile links are warnings, not failures — print them for visibility
    if fragile:
        import warnings
        warnings.warn(
            f"\n{len(fragile)} fragile anchor link(s) (cell-label only, no heading anchor):\n"
            + "\n".join(fragile),
            stacklevel=2,
        )

    assert not dead, (
        f"\n{len(dead)} dead cross-page anchor link(s) found:\n"
        + "\n".join(dead)
        + "\n\nFix by adding explicit {{#anchor}} attributes to headings in the target QMD files."
    )


def test_quarto_slugify_basics():
    """Sanity-check the slugification helper."""
    assert quarto_slugify("VIP vs Xepa") == "vip-vs-xepa"
    assert quarto_slugify("Sincerão × Queridômetro") == "sincerão-queridômetro"
    assert quarto_slugify("Precisão das Enquetes (Votalhada)") == "precisão-das-enquetes-votalhada"
    assert quarto_slugify("Ganhadores & Perdedores") == "ganhadores-perdedores"
    assert quarto_slugify("## Not a heading") == "not-a-heading"
    assert quarto_slugify("  spaces  ") == "spaces"
    assert quarto_slugify("Hello---World") == "hello-world"
    assert quarto_slugify("📊 Impacto por Participante") == "impacto-por-participante"
