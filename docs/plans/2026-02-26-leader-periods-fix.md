# Leader Periods Fix + Source Citations — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the leader_periods bug (Jonas 3x consecutive Líder not detected), migrate `fontes` to rich objects with local file references, and update documentation.

**Architecture:** Replace fragile API-based Líder transition detection with deterministic derivation from `WEEK_END_DATES` + `paredoes.json` Líder field. Migrate `fontes` schema from string array to object array. Update CLAUDE.md and schemas.

**Tech Stack:** Python 3.12, pytest, JSON schema validation

**Design doc:** `docs/plans/2026-02-26-leader-periods-fix-design.md`

---

### Task 1: Add `get_week_start_date()` helper to data_utils.py

**Files:**
- Modify: `scripts/data_utils.py:275-305`
- Test: `tests/test_data_utils.py`

**Step 1: Write the failing tests**

Add to `tests/test_data_utils.py` after the existing `TestGetWeekNumber` class:

```python
from data_utils import get_week_start_date

class TestGetWeekStartDate:
    """Test get_week_start_date() — derives start date for each game week."""

    def test_week_1_starts_at_premiere(self):
        assert get_week_start_date(1) == "2026-01-13"

    def test_week_2_starts_after_week_1_end(self):
        assert get_week_start_date(2) == "2026-01-22"

    def test_week_3_starts_after_week_2_end(self):
        assert get_week_start_date(3) == "2026-01-29"

    def test_week_4_jonas_first_term(self):
        assert get_week_start_date(4) == "2026-02-05"

    def test_week_5_jonas_second_term(self):
        assert get_week_start_date(5) == "2026-02-13"

    def test_week_6_jonas_third_term(self):
        assert get_week_start_date(6) == "2026-02-19"

    def test_open_week_after_last_boundary(self):
        assert get_week_start_date(7) == "2026-02-26"

    def test_week_0_clamps_to_premiere(self):
        assert get_week_start_date(0) == "2026-01-13"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_data_utils.py::TestGetWeekStartDate -v`
Expected: FAIL — `ImportError: cannot import name 'get_week_start_date'`

**Step 3: Implement `get_week_start_date` in data_utils.py**

Add after `get_week_number()` (after line 304):

```python
BBB26_PREMIERE = "2026-01-13"


def get_week_start_date(week_num: int) -> str:
    """Return the start date (YYYY-MM-DD) of the given game week.

    Week 1 starts at BBB26 premiere. Week N (N>1) starts the day after
    WEEK_END_DATES[N-2]. Weeks beyond the last known boundary use the
    day after the last entry.
    """
    if week_num <= 1:
        return BBB26_PREMIERE
    idx = week_num - 2  # WEEK_END_DATES[0] = end of week 1
    if idx < len(WEEK_END_DATES):
        prev_end = WEEK_END_DATES[idx]
    else:
        prev_end = WEEK_END_DATES[-1] if WEEK_END_DATES else BBB26_PREMIERE
    # Day after the previous week's end date
    from datetime import date as _date
    d = _date.fromisoformat(prev_end)
    return (d + __import__('datetime').timedelta(days=1)).isoformat()
```

Note: move the `datetime` import to the file top-level imports if not already there. The `date` and `timedelta` imports likely already exist — check and reuse.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_data_utils.py::TestGetWeekStartDate -v`
Expected: All 8 PASS

**Step 5: Commit**

```bash
git add scripts/data_utils.py tests/test_data_utils.py
git commit -m "feat: add get_week_start_date() helper to data_utils"
```

---

### Task 2: Replace leader_periods detection in build_index_data.py

**Files:**
- Modify: `scripts/build_index_data.py:398-450`

**Step 1: Read the current code block**

The block to replace is `build_index_data.py` lines 398–450 — the `transition_dates` detection loop and the `leader_periods.append(...)` loop.

**Step 2: Replace with WEEK_END_DATES-based derivation**

Replace lines 398–450 (from `# VIP weeks selected` through the `leader_periods.append(...)` block) with:

```python
    # VIP weeks selected — based on WEEK_END_DATES boundaries (not API role changes).
    # This correctly handles consecutive same-person Líder (e.g., Jonas weeks 4–6).
    vip_weeks_selected = defaultdict(int)
    xepa_weeks = defaultdict(int)
    leader_periods = []

    daily_snap_by_date = {snap["date"]: snap for snap in daily_snapshots}

    paredoes_list = paredoes.get("paredoes", []) if paredoes else []
    lider_by_paredao = {}
    for par in paredoes_list:
        lider_by_paredao[par["numero"]] = par.get("formacao", {}).get("lider")

    n_weeks = len(WEEK_END_DATES)
    for week_num in range(1, n_weeks + 2):  # +1 for open current week
        start_date = get_week_start_date(week_num)

        if week_num <= n_weeks:
            end_date = WEEK_END_DATES[week_num - 1]
        else:
            # Open week (current, no end boundary yet)
            end_date = daily_snapshots[-1]["date"] if daily_snapshots else start_date

        # Only include if we have data for this start date (or later)
        if daily_snapshots and start_date > daily_snapshots[-1]["date"]:
            break

        leader_name = lider_by_paredao.get(week_num)

        # VIP from snapshot on start_date (or nearest available after)
        snap = daily_snap_by_date.get(start_date)
        if not snap:
            # Find nearest snapshot on or after start_date
            for ds in daily_snapshots:
                if ds["date"] >= start_date:
                    snap = ds
                    break

        period_vip = []
        period_xepa = []
        if snap:
            for p in snap["participants"]:
                nm = p.get("name")
                if not nm:
                    continue
                grp = (p.get("characteristics", {}).get("group") or "").lower()
                if grp == "vip":
                    period_vip.append(nm)
                elif grp == "xepa":
                    period_xepa.append(nm)

        for nm in period_vip:
            vip_weeks_selected[nm] += 1
        for nm in period_xepa:
            xepa_weeks[nm] += 1

        leader_periods.append({
            "leader": leader_name,
            "start": start_date,
            "end": end_date,
            "week": week_num,
            "vip": sorted(period_vip),
            "xepa": sorted(period_xepa),
        })
```

Add imports at top of file if not present:
```python
from data_utils import WEEK_END_DATES, get_week_start_date
```

**Step 3: Also fix `leader_start_date` detection (lines 456–464)**

The block right after (finding when current Líder started) also uses fragile API detection. Replace:

```python
    house_leader = None
    if roles_current.get("Líder"):
        house_leader = roles_current["Líder"][0]

    # leader_start_date: derived from WEEK_END_DATES for the current open week.
    current_open_week = len(WEEK_END_DATES) + 1
    leader_start_date = get_week_start_date(current_open_week)
```

**Step 4: Run build to verify no errors**

Run: `python scripts/build_derived_data.py`
Expected: Completes without error. Check output for correct leader_periods count.

**Step 5: Verify leader_periods now has 6 entries (was 5)**

Run:
```bash
python3 -c "
import json
with open('data/derived/index_data.json') as f:
    idx = json.load(f)
lp = idx.get('leader_periods', [])
print(f'leader_periods count: {len(lp)}')
for p in lp:
    print(f'  Week {p.get(\"week\",\"?\")}: {p[\"start\"]} → {p[\"end\"]}: {p[\"leader\"]}  VIP: {p.get(\"vip\",[])}')
"
```
Expected: 6 (or 7 if current open week included) entries. Jonas should have **3 separate entries** (weeks 4, 5, 6) with distinct VIP compositions.

**Step 6: Commit**

```bash
git add scripts/build_index_data.py
git commit -m "fix: derive leader_periods from WEEK_END_DATES instead of API role changes

Fixes Jonas 3x consecutive Líder detection. Week 6 was previously merged
into week 5's period because API never cleared the Líder role between terms."
```

---

### Task 3: Downstream null-leader safety in evolucao.qmd

**Files:**
- Modify: `evolucao.qmd` (lines referencing `lp['leader']`)

**Step 1: Check all leader_periods usages in evolucao.qmd**

Search for `lp['leader']` and `lp["leader"]` references. The key line is:

```python
col_labels = [f"👑 {lp['leader'].split()[0]}<br><sub>{lp['start'][5:]}</sub>" for lp in leader_periods]
```

This will crash if `lp['leader']` is `None` (end-of-season week).

**Step 2: Add null safety**

Replace the col_labels line (evolucao.qmd ~line 1015) with:

```python
col_labels = [
    f"👑 {lp['leader'].split()[0]}<br><sub>{lp['start'][5:]}</sub>"
    if lp.get('leader')
    else f"🏠 Sem Líder<br><sub>{lp['start'][5:]}</sub>"
    for lp in leader_periods
]
```

Also check other `lp['leader']` references (lines ~982, ~988, ~1110) and add `.get('leader')` or `or "—"` guards where needed.

**Step 3: Commit**

```bash
git add evolucao.qmd
git commit -m "fix: null-safe leader_periods access in evolucao.qmd for end-of-season"
```

---

### Task 4: Migrate fontes schema in paredoes.json

**Files:**
- Modify: `data/paredoes.json`
- Modify: `scripts/schemas.py`
- Modify: `scripts/data_utils.py` (load_paredoes_transformed fontes field)

**Step 1: Write migration script (one-shot)**

```python
import json
with open('data/paredoes.json') as f:
    data = json.load(f)

for p in data['paredoes']:
    old_fontes = p.get('fontes', [])
    new_fontes = []
    for item in old_fontes:
        if isinstance(item, str):
            new_fontes.append({"url": item, "arquivo": None, "titulo": None})
        else:
            new_fontes.append(item)  # already migrated
    p['fontes'] = new_fontes

with open('data/paredoes.json', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write('\n')
```

Run this as a one-shot script. Verify the output.

**Step 2: Update schemas.py**

The `PAREDAO_SCHEMA` does not currently validate `fontes`. Add it inside the paredão item properties (after line 41 in schemas.py):

```python
"fontes": {
    "type": "array",
    "items": {
        "oneOf": [
            {"type": "string"},  # backward compat (shouldn't exist after migration)
            {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {"type": "string", "format": "uri"},
                    "arquivo": {"type": ["string", "null"]},
                    "titulo": {"type": ["string", "null"]},
                },
            },
        ],
    },
},
```

**Step 3: Update `load_paredoes_transformed` in data_utils.py**

In `data_utils.py` line 390, `fontes` is passed through as-is:
```python
'fontes': p.get('fontes', []),
```

This line still works (objects pass through). No change needed here — the downstream QMD pages that render fontes will need to handle objects. Check if any QMD page renders fontes as raw URLs:

Search: `grep -rn fontes *.qmd` — if `provas.qmd` is the only hit and it uses its own fontes, no QMD change needed for paredão fontes.

**Step 4: Commit**

```bash
git add data/paredoes.json scripts/schemas.py
git commit -m "refactor: migrate paredoes.json fontes from string[] to object[]

Each source is now {url, arquivo, titulo} for local file tracking."
```

---

### Task 5: Update CLAUDE.md documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Add Source Citations section**

After the "Game Week Boundaries" section, add:

```markdown
### Source Citations (fontes)

`paredoes.json` stores source references as objects in the `fontes` array:

```json
"fontes": [
  {"url": "https://gshow.globo.com/.../slug.ghtml", "arquivo": "docs/scraped/slug.md", "titulo": "Article Title"},
  {"url": "https://gshow.globo.com/.../outro.ghtml", "arquivo": null, "titulo": null}
]
```

- `url` — required, the web source URL
- `arquivo` — relative path to local scraped `.md` copy (in `docs/scraped/`), or `null`
- `titulo` — optional article title, or `null`

**When adding new sources**: scrape with `python scripts/scrape_gshow.py <url> -o docs/scraped/`, then add the entry with both `url` and `arquivo` filled. Older entries may have `arquivo: null` — fill retroactively when convenient.
```

**Step 2: Update "Game Week Boundaries" section**

Add a note about consecutive same-person Líder handling:

> **Consecutive Líder**: When the same person wins multiple Prova do Líder, each term is a separate week with its own WEEK_END_DATES entry. The `leader_periods` in `index_data.json` are derived from `WEEK_END_DATES` + `paredoes.json` (not from API role changes), so consecutive same-person terms are correctly separated.

**Step 3: Update "Known Issues" or add note**

If there's a Known Issues section, clear the note about Jonas detection. The fix resolves it.

**Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add source citations schema + consecutive Líder note to CLAUDE.md"
```

---

### Task 6: Rebuild derived data and run full test suite

**Files:**
- Rebuild: `data/derived/index_data.json` (and all derived data)
- Test: full suite

**Step 1: Rebuild all derived data**

Run: `python scripts/build_derived_data.py`
Expected: Completes without error. No audit failures.

**Step 2: Verify leader_periods correctness**

```bash
python3 -c "
import json
with open('data/derived/index_data.json') as f:
    idx = json.load(f)
lp = idx.get('leader_periods', [])
print(f'Total periods: {len(lp)}')
for p in lp:
    print(f'  Week {p.get(\"week\",\"?\")}: {p[\"start\"]} → {p[\"end\"]}: {p[\"leader\"]}')
# Verify Jonas has 3 separate entries
jonas_periods = [p for p in lp if p.get('leader') == 'Jonas Sulzbach']
assert len(jonas_periods) == 3, f'Expected 3 Jonas periods, got {len(jonas_periods)}'
print('✓ Jonas has 3 separate leader periods')
"
```

**Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests pass (244+)

**Step 4: Commit rebuilt data**

```bash
git add data/derived/
git commit -m "data: rebuild derived data with corrected leader_periods (6 weeks)"
```

---

### Task 7: Update memory file

**Files:**
- Modify: `~/.claude/projects/-Users-fernandovoltolinideazambuja-Documents-GitHub-BBB26/memory/MEMORY.md`

**Step 1: Update relevant entries**

- Update the `leader_periods` bug note (now fixed)
- Update the fontes schema note
- Confirm `WEEK_END_DATES` reference is current

**Step 2: No commit needed** (memory file is outside repo)
