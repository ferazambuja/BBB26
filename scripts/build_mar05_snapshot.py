#!/usr/bin/env python3
"""
Build a synthetic snapshot for 2026-03-05 from GShow queridometro article.

WHY THIS IS NEEDED:
The GloboPlay API broke after the Paredao Falso (Mar 3). Breno went to
Quarto Secreto and returned Mar 4 night, but the API never reintegrated him
into the queridometro system. Additionally, the API got stuck serving the
Mar 4 Raio-X data and never updated to the Mar 5 Raio-X.

The GShow editorial team published the correct Mar 5 queridometro data at:
https://gshow.globo.com/realities/bbb/bbb-26/dentro-da-casa/noticia/
queridometro-do-bbb-26-e-recheado-de-coracao-apos-fim-de-quarto-secreto-
e-sisters-disparam-vomitos-e-malas.ghtml

This script reconstructs a complete snapshot from that article.

HOW TO CREATE FUTURE SYNTHETIC SNAPSHOTS (when API is broken):
1. Find the GShow queridometro article for the day
2. Scrape it: python scripts/scrape_gshow.py <url> -o docs/scraped/
3. Copy this script, update the reactions and metadata
4. Run: python scripts/build_marXX_snapshot.py
5. Run: python scripts/build_derived_data.py
6. Verify: check data/derived/ files updated correctly

SCRAPING TIPS:
- The scraper can garble names split across HTML elements (e.g. "Solange Couto"
  becomes "Breno;ge Couto"). Always verify sender counts = N-1.
- Cross-reference missing pairs with adjacent API snapshots.
- GShow articles list ALL reactions by type (coracao, mentiroso, etc.).
- If Cobra or Biscoito sections are absent, nobody used them that day.
"""

import json
import hashlib
from pathlib import Path
from copy import deepcopy

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"

# ── Load base snapshot (for structural data: avatars, balance, roles, group) ──
# Use the latest snapshot that has all 14 participants
BASE_SNAPSHOT = "2026-03-05_21-27-58.json"
with open(DATA_DIR / BASE_SNAPSHOT, encoding="utf-8") as f:
    base_raw = json.load(f)
    base_participants = base_raw["participants"]

base_by_name = {p["name"]: p for p in base_participants}

# ── Reaction icon URLs (from existing snapshot) ──────────────────────────────
REACTION_ICONS = {}
for p in base_participants:
    for r in p.get("characteristics", {}).get("receivedReactions", []):
        REACTION_ICONS[r["label"]] = r["icon"]

# ── Participants active on Mar 5 (14 total, including Breno back from QS) ──
MAR05_NAMES = sorted(base_by_name.keys())
assert len(MAR05_NAMES) == 14, f"Expected 14 participants, got {len(MAR05_NAMES)}"

# ── All reactions from GShow article (parsed + scraping fixes applied) ────────
# Source: queridometro-do-bbb-26-e-recheado-de-coracao-apos-fim-de-quarto-
#         secreto-e-sisters-disparam-vomitos-e-malas.md
#
# Scraping fixes applied:
#   1. "Alberto Cowboy enviou vomito para Breno;ge Couto" was garbled.
#      Original: "Jordana enviou vomito para Solange Couto" (Jordana had 8
#      vomitos in parsed data, article says 9 — Solange was the 9th).
#      Alberto's duplicate "Breno" entry removed.
#   2. "Ana Paula Reanult" typo in article → corrected to "Ana Paula Renault"
#
# Missing pairs (not in scraped article, likely scraper artifacts):
#   - Babu Santana → Gabriela: inferred as Coração (see note below)
#   - Solange Couto → Ana Paula Renault: inferred as Coração (see note)
#   - Solange Couto → Jordana: inferred as Coração (see note)
#   - Solange Couto → Marciele: inferred as Coração (see note)
#
# Inference rationale: These 4 pairs were lost to scraping artifacts. Since the
# article only lists non-heart reactions by section (coracao section is
# explicitly listed), and these senders already appear in ALL negative sections
# without these targets, the missing pairs are hearts. Solange Couto's article
# pattern: 8 coracao + 2 mala = 10 listed. With 3 more coracao = 13. Babu: 6
# coracao + 6 others = 12 listed. With 1 more coracao = 13.

giver_reactions: dict[str, dict[str, str]] = {}


def add(giver: str, reaction: str, target: str) -> None:
    giver_reactions.setdefault(giver, {})[target] = reaction


# ── Coracao ──────────────────────────────────────────────────────────────────
add("Babu Santana", "Coração", "Breno")
add("Babu Santana", "Coração", "Chaiany")
add("Babu Santana", "Coração", "Juliano Floss")
add("Babu Santana", "Coração", "Leandro")
add("Babu Santana", "Coração", "Samira")
add("Babu Santana", "Coração", "Solange Couto")
add("Breno", "Coração", "Babu Santana")
add("Breno", "Coração", "Chaiany")
add("Breno", "Coração", "Juliano Floss")
add("Breno", "Coração", "Leandro")
add("Breno", "Coração", "Milena")
add("Breno", "Coração", "Samira")
add("Breno", "Coração", "Solange Couto")
add("Milena", "Coração", "Ana Paula Renault")
add("Milena", "Coração", "Breno")
add("Milena", "Coração", "Juliano Floss")
add("Milena", "Coração", "Samira")
add("Jonas Sulzbach", "Coração", "Alberto Cowboy")
add("Jonas Sulzbach", "Coração", "Babu Santana")
add("Jonas Sulzbach", "Coração", "Chaiany")
add("Jonas Sulzbach", "Coração", "Gabriela")
add("Jonas Sulzbach", "Coração", "Jordana")
add("Jonas Sulzbach", "Coração", "Marciele")
add("Jonas Sulzbach", "Coração", "Samira")
add("Jonas Sulzbach", "Coração", "Solange Couto")
add("Samira", "Coração", "Ana Paula Renault")
add("Samira", "Coração", "Breno")
add("Samira", "Coração", "Chaiany")
add("Samira", "Coração", "Juliano Floss")
add("Samira", "Coração", "Milena")
add("Chaiany", "Coração", "Ana Paula Renault")
add("Chaiany", "Coração", "Babu Santana")
add("Chaiany", "Coração", "Breno")
add("Chaiany", "Coração", "Gabriela")
add("Chaiany", "Coração", "Jonas Sulzbach")
add("Chaiany", "Coração", "Juliano Floss")
add("Chaiany", "Coração", "Leandro")
add("Chaiany", "Coração", "Samira")
add("Chaiany", "Coração", "Solange Couto")
add("Jordana", "Coração", "Alberto Cowboy")
add("Jordana", "Coração", "Gabriela")
add("Jordana", "Coração", "Jonas Sulzbach")
add("Jordana", "Coração", "Marciele")
add("Solange Couto", "Coração", "Alberto Cowboy")
add("Solange Couto", "Coração", "Babu Santana")
add("Solange Couto", "Coração", "Breno")
add("Solange Couto", "Coração", "Chaiany")
add("Solange Couto", "Coração", "Jonas Sulzbach")
add("Solange Couto", "Coração", "Juliano Floss")
add("Solange Couto", "Coração", "Leandro")
add("Solange Couto", "Coração", "Samira")
add("Leandro", "Coração", "Babu Santana")
add("Leandro", "Coração", "Breno")
add("Leandro", "Coração", "Chaiany")
add("Leandro", "Coração", "Juliano Floss")
add("Leandro", "Coração", "Solange Couto")
add("Juliano Floss", "Coração", "Ana Paula Renault")
add("Juliano Floss", "Coração", "Babu Santana")
add("Juliano Floss", "Coração", "Breno")
add("Juliano Floss", "Coração", "Chaiany")
add("Juliano Floss", "Coração", "Leandro")
add("Juliano Floss", "Coração", "Milena")
add("Juliano Floss", "Coração", "Samira")
add("Juliano Floss", "Coração", "Solange Couto")
add("Alberto Cowboy", "Coração", "Gabriela")
add("Alberto Cowboy", "Coração", "Jonas Sulzbach")
add("Alberto Cowboy", "Coração", "Jordana")
add("Alberto Cowboy", "Coração", "Marciele")
add("Alberto Cowboy", "Coração", "Solange Couto")
add("Gabriela", "Coração", "Alberto Cowboy")
add("Gabriela", "Coração", "Chaiany")
add("Gabriela", "Coração", "Jonas Sulzbach")
add("Gabriela", "Coração", "Jordana")
add("Gabriela", "Coração", "Marciele")
add("Marciele", "Coração", "Alberto Cowboy")
add("Marciele", "Coração", "Gabriela")
add("Marciele", "Coração", "Jonas Sulzbach")
add("Marciele", "Coração", "Jordana")
add("Ana Paula Renault", "Coração", "Juliano Floss")
add("Ana Paula Renault", "Coração", "Milena")
add("Ana Paula Renault", "Coração", "Samira")

# ── Inferred Coração (scraping gaps — see rationale above) ───────────────────
add("Babu Santana", "Coração", "Gabriela")           # missing from scrape
add("Solange Couto", "Coração", "Ana Paula Renault")  # missing from scrape
add("Solange Couto", "Coração", "Jordana")            # missing from scrape
add("Solange Couto", "Coração", "Marciele")           # missing from scrape

# ── Mentiroso ────────────────────────────────────────────────────────────────
add("Babu Santana", "Mentiroso", "Jonas Sulzbach")
add("Milena", "Mentiroso", "Jonas Sulzbach")
add("Samira", "Mentiroso", "Alberto Cowboy")
add("Samira", "Mentiroso", "Jonas Sulzbach")
add("Juliano Floss", "Mentiroso", "Alberto Cowboy")
add("Juliano Floss", "Mentiroso", "Gabriela")
add("Juliano Floss", "Mentiroso", "Jonas Sulzbach")
add("Juliano Floss", "Mentiroso", "Jordana")

# ── Coracao partido ──────────────────────────────────────────────────────────
add("Babu Santana", "Coração partido", "Milena")
add("Leandro", "Coração partido", "Ana Paula Renault")
add("Leandro", "Coração partido", "Milena")
add("Leandro", "Coração partido", "Samira")
add("Alberto Cowboy", "Coração partido", "Babu Santana")
add("Alberto Cowboy", "Coração partido", "Chaiany")

# ── Mala ─────────────────────────────────────────────────────────────────────
add("Milena", "Mala", "Babu Santana")
add("Milena", "Mala", "Chaiany")
add("Milena", "Mala", "Leandro")
add("Milena", "Mala", "Solange Couto")
add("Samira", "Mala", "Babu Santana")
add("Chaiany", "Mala", "Milena")
add("Solange Couto", "Mala", "Gabriela")
add("Solange Couto", "Mala", "Milena")
add("Gabriela", "Mala", "Ana Paula Renault")
add("Gabriela", "Mala", "Babu Santana")
add("Gabriela", "Mala", "Breno")
add("Gabriela", "Mala", "Juliano Floss")
add("Gabriela", "Mala", "Leandro")
add("Gabriela", "Mala", "Milena")
add("Gabriela", "Mala", "Samira")
add("Gabriela", "Mala", "Solange Couto")

# ── Planta ───────────────────────────────────────────────────────────────────
add("Babu Santana", "Planta", "Marciele")
add("Milena", "Planta", "Marciele")
add("Jonas Sulzbach", "Planta", "Breno")
add("Jonas Sulzbach", "Planta", "Juliano Floss")
add("Jonas Sulzbach", "Planta", "Leandro")
add("Samira", "Planta", "Leandro")
add("Samira", "Planta", "Marciele")
add("Samira", "Planta", "Solange Couto")
add("Chaiany", "Planta", "Marciele")
add("Juliano Floss", "Planta", "Marciele")
add("Marciele", "Planta", "Ana Paula Renault")
add("Marciele", "Planta", "Babu Santana")
add("Marciele", "Planta", "Breno")
add("Marciele", "Planta", "Chaiany")
add("Marciele", "Planta", "Juliano Floss")
add("Marciele", "Planta", "Leandro")
add("Marciele", "Planta", "Milena")
add("Marciele", "Planta", "Samira")
add("Marciele", "Planta", "Solange Couto")
add("Ana Paula Renault", "Planta", "Chaiany")
add("Ana Paula Renault", "Planta", "Marciele")
add("Ana Paula Renault", "Planta", "Solange Couto")

# ── Alvo ─────────────────────────────────────────────────────────────────────
add("Babu Santana", "Alvo", "Ana Paula Renault")
add("Breno", "Alvo", "Alberto Cowboy")
add("Breno", "Alvo", "Ana Paula Renault")
add("Breno", "Alvo", "Gabriela")
add("Breno", "Alvo", "Jonas Sulzbach")
add("Breno", "Alvo", "Jordana")
add("Breno", "Alvo", "Marciele")
add("Leandro", "Alvo", "Alberto Cowboy")
add("Leandro", "Alvo", "Gabriela")
add("Leandro", "Alvo", "Jonas Sulzbach")
add("Leandro", "Alvo", "Jordana")
add("Leandro", "Alvo", "Marciele")
add("Ana Paula Renault", "Alvo", "Alberto Cowboy")
add("Ana Paula Renault", "Alvo", "Babu Santana")
add("Ana Paula Renault", "Alvo", "Breno")
add("Ana Paula Renault", "Alvo", "Gabriela")
add("Ana Paula Renault", "Alvo", "Jonas Sulzbach")
add("Ana Paula Renault", "Alvo", "Jordana")
add("Ana Paula Renault", "Alvo", "Leandro")

# ── Vomito ───────────────────────────────────────────────────────────────────
add("Babu Santana", "Vômito", "Alberto Cowboy")
add("Babu Santana", "Vômito", "Jordana")
add("Milena", "Vômito", "Alberto Cowboy")
add("Milena", "Vômito", "Gabriela")
add("Milena", "Vômito", "Jordana")
add("Jonas Sulzbach", "Vômito", "Ana Paula Renault")
add("Jonas Sulzbach", "Vômito", "Milena")
add("Samira", "Vômito", "Gabriela")
add("Samira", "Vômito", "Jordana")
add("Chaiany", "Vômito", "Alberto Cowboy")
add("Chaiany", "Vômito", "Jordana")
add("Jordana", "Vômito", "Ana Paula Renault")
add("Jordana", "Vômito", "Babu Santana")
add("Jordana", "Vômito", "Breno")
add("Jordana", "Vômito", "Chaiany")
add("Jordana", "Vômito", "Juliano Floss")
add("Jordana", "Vômito", "Leandro")
add("Jordana", "Vômito", "Milena")
add("Jordana", "Vômito", "Samira")
add("Jordana", "Vômito", "Solange Couto")  # scraping fix #1
add("Alberto Cowboy", "Vômito", "Ana Paula Renault")
add("Alberto Cowboy", "Vômito", "Breno")
add("Alberto Cowboy", "Vômito", "Juliano Floss")
add("Alberto Cowboy", "Vômito", "Leandro")
add("Alberto Cowboy", "Vômito", "Milena")
add("Alberto Cowboy", "Vômito", "Samira")

# ── No Cobra or Biscoito in article (nobody used them on Mar 5) ──────────────

# ── Validate: every participant sends exactly 13 reactions ───────────────────
print("-- Reactions given per participant --")
expected = len(MAR05_NAMES) - 1  # 13
all_ok = True
for name in MAR05_NAMES:
    given = giver_reactions.get(name, {})
    n = len(given)
    hearts = sum(1 for r in given.values() if r == "Coração")
    neg = n - hearts
    status = "OK" if n == expected else "MISMATCH"
    if n != expected:
        all_ok = False
        missing = set(MAR05_NAMES) - {name} - set(given.keys())
        print(f"  {status} {name}: {n}/{expected} (missing: {missing})")
    else:
        print(f"  {status} {name}: {n} ({hearts} coracao + {neg} neg)")

assert all_ok, "Reaction count mismatch — fix data above before saving"


# ── Build receivedReactions for each participant ─────────────────────────────
def get_participant_info(name: str) -> dict:
    p = base_by_name[name]
    return {"id": p["id"], "name": p["name"], "avatar": p["avatar"]}


def build_received_reactions(target_name: str) -> list[dict]:
    reactions_by_type: dict[str, list[str]] = {}
    for giver in MAR05_NAMES:
        if giver == target_name:
            continue
        reaction = giver_reactions.get(giver, {}).get(target_name)
        if reaction:
            reactions_by_type.setdefault(reaction, []).append(giver)

    result = []
    # Coracao first (API convention)
    if "Coração" in reactions_by_type:
        givers = reactions_by_type.pop("Coração")
        result.append({
            "label": "Coração",
            "icon": REACTION_ICONS.get("Coração", ""),
            "amount": len(givers),
            "participants": [get_participant_info(g) for g in givers],
        })
    for label, givers in reactions_by_type.items():
        result.append({
            "label": label,
            "icon": REACTION_ICONS.get(label, ""),
            "amount": len(givers),
            "participants": [get_participant_info(g) for g in givers],
        })
    return result


# ── Build synthetic participants ─────────────────────────────────────────────
synthetic_participants = []
for name in MAR05_NAMES:
    base = deepcopy(base_by_name[name])
    base["characteristics"]["receivedReactions"] = build_received_reactions(name)
    # Keep balance, roles, group, etc. from base snapshot (non-reaction fields)
    synthetic_participants.append(base)

# ── Stats ────────────────────────────────────────────────────────────────────
total_reactions = sum(
    sum(r["amount"] for r in p["characteristics"]["receivedReactions"])
    for p in synthetic_participants
)

reaction_counts: dict[str, int] = {}
for p in synthetic_participants:
    for r in p["characteristics"]["receivedReactions"]:
        reaction_counts[r["label"]] = reaction_counts.get(r["label"], 0) + r["amount"]

print(f"\n-- Total reactions: {total_reactions} --")
print("Breakdown:")
for label, count in sorted(reaction_counts.items(), key=lambda x: -x[1]):
    print(f"  {label}: {count}")

expected_total = len(MAR05_NAMES) * (len(MAR05_NAMES) - 1)  # 14 * 13 = 182
assert total_reactions == expected_total, (
    f"Total {total_reactions} != expected {expected_total}"
)
print(f"\nTotal matches expected: 14 x 13 = {expected_total}")

# ── Save snapshot ────────────────────────────────────────────────────────────
data_hash = hashlib.md5(
    json.dumps(synthetic_participants, sort_keys=True, ensure_ascii=False).encode()
).hexdigest()

save_data = {
    "_metadata": {
        "captured_at": "2026-03-06T05:59:00+00:00",
        "api_url": "SYNTHETIC - built from GShow queridometro article",
        "data_hash": data_hash,
        "participant_count": len(synthetic_participants),
        "total_reactions": total_reactions,
        "synthetic": True,
        "source": (
            "https://gshow.globo.com/realities/bbb/bbb-26/dentro-da-casa/noticia/"
            "queridometro-do-bbb-26-e-recheado-de-coracao-apos-fim-de-quarto-"
            "secreto-e-sisters-disparam-vomitos-e-malas.ghtml"
        ),
        "source_date": "2026-03-05",
        "methodology": [
            "177/182 reaction pairs directly from GShow article (scraped + parsed)",
            "1 pair fixed from scraping artifact (Jordana->Solange vomito)",
            "4 pairs inferred as Coracao (scraper lost them; senders already in all "
            "negative sections without these targets, so hearts by elimination)",
            "Non-reaction fields (balance, roles, group) from base snapshot",
        ],
        "scraping_fixes": [
            "Garbled text 'Alberto Cowboy enviou vomito para Breno;ge Couto' was "
            "actually 'Jordana enviou vomito para Solange Couto' (article says "
            "Jordana sent 9 vomitos, parsed data had 8, Solange was the 9th)",
            "Duplicate Alberto Cowboy->Breno vomito entry removed",
            "'Ana Paula Reanult' typo corrected to 'Ana Paula Renault'",
        ],
        "inferred_pairs": [
            "Babu Santana -> Gabriela: Coracao (12/13 parsed, missing from scrape)",
            "Solange Couto -> Ana Paula Renault: Coracao (10/13 parsed)",
            "Solange Couto -> Jordana: Coracao (10/13 parsed)",
            "Solange Couto -> Marciele: Coracao (10/13 parsed)",
        ],
        "why_synthetic": (
            "GloboPlay API broke after Paredao Falso (Mar 3). Breno returned "
            "Mar 4 night but API never reintegrated him into queridometro. "
            "API also stuck on Mar 4 Raio-X data (38 non-Breno mismatches "
            "vs article). GShow website has correct data from different backend."
        ),
        "base_snapshot": BASE_SNAPSHOT,
    },
    "participants": synthetic_participants,
}

# Timestamp: Mar 5 15:00 UTC (12:00 BRT) — synthetic, representing the
# morning Raio-X that the API failed to serve
# Timestamp: 05:59 UTC (02:59 BRT) on Mar 6 — still game date Mar 5
# (before 06:00 BRT cutoff). Sorts AFTER the last broken API snapshot
# (2026-03-06_02-49-48) so the pipeline picks this as the daily snapshot.
output_path = DATA_DIR / "2026-03-06_05-59-00.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(save_data, f, indent=2, ensure_ascii=False)

print(f"\nSaved synthetic snapshot: {output_path}")
print(f"  Participants: {len(synthetic_participants)}")
print(f"  Total reactions: {total_reactions}")
print(f"  Hash: {data_hash[:16]}")
