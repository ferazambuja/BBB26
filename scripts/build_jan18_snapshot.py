#!/usr/bin/env python3
"""
Build a COMPLETE synthetic snapshot for 2026-01-18 from GShow queridômetro article.

Source: https://gshow.globo.com/realities/bbb/bbb-26/dentro-da-casa/noticia/
        queridometro-do-bbb-26-tem-pedro-tachado-de-mentiroso-e-novo-brother-disparando-biscoitos.ghtml

Key facts about the queridômetro (Raio-X dynamic):
- Every active participant gives EXACTLY ONE reaction to every other participant
- With N participants, each gives N-1 reactions → total = N × (N-1)
- GShow article only publishes NEGATIVE/MILD reactions
- Hearts are inferred: if giver X gave negative to targets A, B, C → X gave hearts to everyone else
- Milena was PUNISHED and did not participate → she gave ZERO reactions
  Source: https://gshow.globo.com/realities/bbb/bbb-26/dentro-da-casa/noticia/
          milena-recebe-punicao-gravissima-no-bbb-26-e-tem-crise-de-choro.ghtml
- Chaiany entered the house the same day as Gabriela, Leandro, Matheus
  Not mentioned in article → gave only hearts (100% positive)

Participants on Jan 18: 24
- 20 from Jan 17 + 4 new entrants (Chaiany, Gabriela, Leandro, Matheus)
- Pedro still active (eliminated between Jan 18-19)

Expected total reactions: 23 × 23 = 529 (24 participants, each rates 23 others)
Minus Milena's 23 = 506 (she didn't participate)
"""

import json
import hashlib
from pathlib import Path
from copy import deepcopy

DATA_DIR = Path(__file__).parent.parent / "data" / "snapshots"

# ── Load base snapshots ──────────────────────────────────────────────
with open(DATA_DIR / "2026-01-17_17-46-39.json", encoding="utf-8") as f:
    jan17_data = json.load(f)

with open(DATA_DIR / "2026-01-19_22-34-41.json", encoding="utf-8") as f:
    jan19_raw = json.load(f)
    jan19_data = jan19_raw["participants"] if isinstance(jan19_raw, dict) else jan19_raw

# Build lookup dicts
jan17_by_name = {p["name"]: p for p in jan17_data}
jan19_by_name = {p["name"]: p for p in jan19_data}

# ── Reaction icon URLs (from existing snapshots) ────────────────────
REACTION_ICONS = {}
for p in jan17_data:
    for r in p.get("characteristics", {}).get("receivedReactions", []):
        REACTION_ICONS[r["label"]] = r["icon"]
for p in jan19_data:
    for r in p.get("characteristics", {}).get("receivedReactions", []):
        if r["label"] not in REACTION_ICONS:
            REACTION_ICONS[r["label"]] = r["icon"]

# ── Name mapping: article short names → API full names ───────────────
NAME_MAP = {
    "Jonas": "Jonas Sulzbach",
    "Sarah": "Sarah Andrade",
    "Babu": "Babu Santana",
}


def api_name(article_name):
    return NAME_MAP.get(article_name, article_name)


# ── Jan 18 participants (24 total) ──────────────────────────────────
JAN18_NAMES = sorted(set(jan17_by_name.keys()) | {"Chaiany", "Gabriela", "Leandro", "Matheus"})
print(f"Jan 18 participants ({len(JAN18_NAMES)}): {JAN18_NAMES}")

# ── Negative/mild reactions from GShow article ──────────────────────
# Build a giver→target→reaction mapping
# giver_reactions[giver_name][target_name] = reaction_label
giver_reactions = {}


def add_reaction(giver_article, reaction_label, receiver_article):
    giver = api_name(giver_article)
    receiver = api_name(receiver_article)
    if giver not in giver_reactions:
        giver_reactions[giver] = {}
    giver_reactions[giver][receiver] = reaction_label


# 🤮 Vômito
add_reaction("Pedro", "Vômito", "Ana Paula Renault")
add_reaction("Jordana", "Vômito", "Pedro")
add_reaction("Juliano Floss", "Vômito", "Pedro")
add_reaction("Milena", "Vômito", "Sol Vega")

# 🐍 Cobra
add_reaction("Breno", "Cobra", "Pedro")
add_reaction("Aline Campos", "Cobra", "Ana Paula Renault")
add_reaction("Brigido", "Cobra", "Ana Paula Renault")
add_reaction("Ana Paula Renault", "Cobra", "Alberto Cowboy")
add_reaction("Jonas", "Cobra", "Ana Paula Renault")

# 💔 Coração partido
add_reaction("Pedro", "Coração partido", "Breno")
add_reaction("Pedro", "Coração partido", "Brigido")
add_reaction("Pedro", "Coração partido", "Edilson")
add_reaction("Pedro", "Coração partido", "Jonas")
add_reaction("Pedro", "Coração partido", "Jordana")
add_reaction("Pedro", "Coração partido", "Juliano Floss")
add_reaction("Pedro", "Coração partido", "Marcelo")
add_reaction("Pedro", "Coração partido", "Marciele")
add_reaction("Pedro", "Coração partido", "Maxiane")
add_reaction("Pedro", "Coração partido", "Milena")
add_reaction("Pedro", "Coração partido", "Paulo Augusto")
add_reaction("Pedro", "Coração partido", "Samira")
add_reaction("Pedro", "Coração partido", "Sarah")
add_reaction("Pedro", "Coração partido", "Sol Vega")
add_reaction("Pedro", "Coração partido", "Solange Couto")
add_reaction("Babu", "Coração partido", "Pedro")
add_reaction("Breno", "Coração partido", "Alberto Cowboy")
add_reaction("Aline Campos", "Coração partido", "Pedro")
add_reaction("Aline Campos", "Coração partido", "Samira")
add_reaction("Brigido", "Coração partido", "Pedro")
add_reaction("Paulo Augusto", "Coração partido", "Alberto Cowboy")
add_reaction("Paulo Augusto", "Coração partido", "Pedro")
add_reaction("Sol Vega", "Coração partido", "Milena")
add_reaction("Sol Vega", "Coração partido", "Pedro")
add_reaction("Samira", "Coração partido", "Alberto Cowboy")
add_reaction("Samira", "Coração partido", "Aline Campos")
add_reaction("Samira", "Coração partido", "Pedro")

# 🌱 Planta
add_reaction("Leandro", "Planta", "Milena")
add_reaction("Babu", "Planta", "Sol Vega")
add_reaction("Breno", "Planta", "Paulo Augusto")
add_reaction("Brigido", "Planta", "Samira")
add_reaction("Brigido", "Planta", "Sol Vega")
add_reaction("Ana Paula Renault", "Planta", "Aline Campos")
add_reaction("Ana Paula Renault", "Planta", "Jonas")
add_reaction("Ana Paula Renault", "Planta", "Paulo Augusto")
add_reaction("Ana Paula Renault", "Planta", "Sarah")
add_reaction("Paulo Augusto", "Planta", "Breno")
add_reaction("Paulo Augusto", "Planta", "Jonas")
add_reaction("Solange Couto", "Planta", "Marciele")
add_reaction("Milena", "Planta", "Aline Campos")
add_reaction("Maxiane", "Planta", "Juliano Floss")
add_reaction("Maxiane", "Planta", "Paulo Augusto")
add_reaction("Alberto Cowboy", "Planta", "Marcelo")
add_reaction("Sarah", "Planta", "Juliano Floss")
add_reaction("Sarah", "Planta", "Paulo Augusto")
add_reaction("Sarah", "Planta", "Solange Couto")

# 💼 Mala
add_reaction("Aline Campos", "Mala", "Marcelo")
add_reaction("Brigido", "Mala", "Breno")
add_reaction("Ana Paula Renault", "Mala", "Sol Vega")
add_reaction("Gabriela", "Mala", "Milena")
add_reaction("Gabriela", "Mala", "Pedro")
add_reaction("Paulo Augusto", "Mala", "Maxiane")
add_reaction("Paulo Augusto", "Mala", "Milena")
add_reaction("Solange Couto", "Mala", "Pedro")
add_reaction("Solange Couto", "Mala", "Sol Vega")
add_reaction("Jordana", "Mala", "Leandro")
add_reaction("Milena", "Mala", "Alberto Cowboy")
add_reaction("Milena", "Mala", "Brigido")
add_reaction("Milena", "Mala", "Jonas")
add_reaction("Milena", "Mala", "Paulo Augusto")
add_reaction("Alberto Cowboy", "Mala", "Jonas")
add_reaction("Jonas", "Mala", "Milena")

# 🎯 Alvo
add_reaction("Ana Paula Renault", "Alvo", "Brigido")
add_reaction("Solange Couto", "Alvo", "Jonas")
add_reaction("Alberto Cowboy", "Alvo", "Breno")
add_reaction("Alberto Cowboy", "Alvo", "Maxiane")
add_reaction("Alberto Cowboy", "Alvo", "Milena")
add_reaction("Alberto Cowboy", "Alvo", "Paulo Augusto")
add_reaction("Alberto Cowboy", "Alvo", "Samira")
add_reaction("Jonas", "Alvo", "Marcelo")
add_reaction("Jonas", "Alvo", "Pedro")

# 🤥 Mentiroso
add_reaction("Ana Paula Renault", "Mentiroso", "Pedro")
add_reaction("Milena", "Mentiroso", "Pedro")
add_reaction("Maxiane", "Mentiroso", "Pedro")
add_reaction("Matheus", "Mentiroso", "Pedro")
add_reaction("Brigido", "Mentiroso", "Marcelo")

# 🍪 Biscoito
add_reaction("Solange Couto", "Biscoito", "Jordana")
add_reaction("Solange Couto", "Biscoito", "Paulo Augusto")
add_reaction("Solange Couto", "Biscoito", "Samira")
add_reaction("Solange Couto", "Biscoito", "Sarah")
add_reaction("Alberto Cowboy", "Biscoito", "Pedro")
add_reaction("Sarah", "Biscoito", "Ana Paula Renault")
add_reaction("Leandro", "Biscoito", "Alberto Cowboy")
add_reaction("Leandro", "Biscoito", "Brigido")
add_reaction("Leandro", "Biscoito", "Edilson")
add_reaction("Leandro", "Biscoito", "Jonas")
add_reaction("Leandro", "Biscoito", "Jordana")
add_reaction("Leandro", "Biscoito", "Paulo Augusto")
add_reaction("Leandro", "Biscoito", "Pedro")
add_reaction("Aline Campos", "Biscoito", "Milena")

# ── Milena did NOT participate (punição gravíssima) ──────────────────
# She appears as a GIVER in the article for some reactions. However, the article
# reports reactions that were visible/published that day. The punishment was for
# not participating in the Raio-X on time. Let's check what the article says:
# The article lists Milena as giving: Vômito→Sol Vega, Planta→Aline Campos,
# Mala→Alberto Cowboy, Mala→Brigido, Mala→Jonas, Mala→Paulo Augusto,
# Mentiroso→Pedro
#
# IMPORTANT: The GShow article headline says "Milena recebe punição gravíssima"
# and "não participar a tempo da dinâmica". This could mean she participated LATE
# (and her reactions were still recorded) or she didn't participate at all.
# Since the article explicitly lists her reactions, we include them.
# The punishment was losing 500 estalecas, not having reactions voided.
MILENA_PARTICIPATED = True  # Article lists her reactions — she participated late

# ── Build complete giver→target→reaction map (filling hearts) ───────

# For each active participant (except Milena if she didn't participate),
# fill in hearts for all targets they didn't give negative/mild reactions to.
GIVERS_WHO_DIDNT_PARTICIPATE = set()
if not MILENA_PARTICIPATED:
    GIVERS_WHO_DIDNT_PARTICIPATE.add("Milena")

full_reactions = {}  # giver → {target → reaction_label}

for giver in JAN18_NAMES:
    if giver in GIVERS_WHO_DIDNT_PARTICIPATE:
        full_reactions[giver] = {}  # Empty — didn't participate
        continue

    full_reactions[giver] = {}
    # Start with known negative/mild reactions from article
    known = giver_reactions.get(giver, {})
    for target in JAN18_NAMES:
        if target == giver:
            continue  # No self-reactions
        if target in known:
            full_reactions[giver][target] = known[target]
        else:
            full_reactions[giver][target] = "Coração"  # Fill with heart

# ── Validate reaction counts ────────────────────────────────────────
print("\n── Reactions given per participant ──")
expected_per_giver = len(JAN18_NAMES) - 1  # 23
for giver in JAN18_NAMES:
    given = full_reactions[giver]
    hearts = sum(1 for r in given.values() if r == "Coração")
    non_hearts = sum(1 for r in given.values() if r != "Coração")
    status = "✓" if len(given) == expected_per_giver or giver in GIVERS_WHO_DIDNT_PARTICIPATE else "⚠️"
    if giver in GIVERS_WHO_DIDNT_PARTICIPATE:
        print(f"  {status} {giver}: DID NOT PARTICIPATE (0 reactions)")
    else:
        print(f"  {status} {giver}: {len(given)} reactions ({hearts} ❤️ + {non_hearts} negative/mild)")


# ── Build receivedReactions for each participant ─────────────────────
def get_participant_info(name):
    """Get id/name/avatar for a participant."""
    if name in jan17_by_name:
        p = jan17_by_name[name]
    elif name in jan19_by_name:
        p = jan19_by_name[name]
    else:
        raise ValueError(f"Unknown participant: {name}")
    return {"id": p["id"], "name": p["name"], "avatar": p["avatar"]}


def build_received_reactions(target_name):
    """Build receivedReactions array for a target from the complete reaction graph."""
    # Collect all reactions this target received, grouped by reaction type
    reactions_by_type = {}  # label → [giver_name, ...]
    for giver in JAN18_NAMES:
        if giver == target_name:
            continue
        if giver in GIVERS_WHO_DIDNT_PARTICIPATE:
            continue
        reaction = full_reactions[giver].get(target_name)
        if reaction:
            if reaction not in reactions_by_type:
                reactions_by_type[reaction] = []
            reactions_by_type[reaction].append(giver)

    # Build the receivedReactions array
    result = []
    # Put Coração first (matching API convention)
    if "Coração" in reactions_by_type:
        givers = reactions_by_type.pop("Coração")
        result.append({
            "label": "Coração",
            "icon": REACTION_ICONS.get("Coração", ""),
            "amount": len(givers),
            "participants": [get_participant_info(g) for g in givers]
        })
    # Then other reactions
    for label, givers in reactions_by_type.items():
        result.append({
            "label": label,
            "icon": REACTION_ICONS.get(label, ""),
            "amount": len(givers),
            "participants": [get_participant_info(g) for g in givers]
        })
    return result


# ── Build synthetic participants ─────────────────────────────────────
synthetic_participants = []
for name in JAN18_NAMES:
    if name in jan17_by_name:
        base = deepcopy(jan17_by_name[name])
    elif name in jan19_by_name:
        base = deepcopy(jan19_by_name[name])
        base["characteristics"]["balance"] = 0
        base["characteristics"]["roles"] = []
        base["characteristics"]["mainRole"] = None
    else:
        raise ValueError(f"Cannot find base data for: {name}")

    base["characteristics"]["receivedReactions"] = build_received_reactions(name)
    base["characteristics"]["eliminated"] = False
    synthetic_participants.append(base)

# ── Compute and display stats ────────────────────────────────────────
total_reactions = sum(
    sum(r["amount"] for r in p["characteristics"]["receivedReactions"])
    for p in synthetic_participants
)

reaction_counts = {}
for p in synthetic_participants:
    for r in p["characteristics"]["receivedReactions"]:
        reaction_counts[r["label"]] = reaction_counts.get(r["label"], 0) + r["amount"]

print(f"\n── Total reactions: {total_reactions} ──")
print("Breakdown:")
for label, count in sorted(reaction_counts.items(), key=lambda x: -x[1]):
    print(f"  {label}: {count}")

# Validate completeness
active_givers = len(JAN18_NAMES) - len(GIVERS_WHO_DIDNT_PARTICIPATE)
expected_total = active_givers * (len(JAN18_NAMES) - 1)
if total_reactions == expected_total:
    print(f"\n✓ Total matches expected: {active_givers} givers × {len(JAN18_NAMES)-1} targets = {expected_total}")
else:
    print(f"\n⚠️ Total {total_reactions} ≠ expected {expected_total}")

# Show received reactions per participant
print("\n── Received reactions per participant ──")
for p in synthetic_participants:
    reactions = p["characteristics"]["receivedReactions"]
    total_recv = sum(r["amount"] for r in reactions)
    hearts = sum(r["amount"] for r in reactions if r["label"] == "Coração")
    neg = total_recv - hearts
    print(f"  {p['name']}: {total_recv} received ({hearts} ❤️, {neg} neg/mild)")

# ── Save snapshot ────────────────────────────────────────────────────
data_hash = hashlib.md5(
    json.dumps(synthetic_participants, sort_keys=True, ensure_ascii=False).encode()
).hexdigest()

save_data = {
    "_metadata": {
        "captured_at": "2026-01-18T12:00:00",
        "api_url": "SYNTHETIC — built from GShow queridômetro article",
        "data_hash": data_hash,
        "participant_count": len(synthetic_participants),
        "total_reactions": total_reactions,
        "synthetic": True,
        "source": "https://gshow.globo.com/realities/bbb/bbb-26/dentro-da-casa/noticia/queridometro-do-bbb-26-tem-pedro-tachado-de-mentiroso-e-novo-brother-disparando-biscoitos.ghtml",
        "methodology": [
            "Negative/mild reactions: exact data from GShow queridômetro article",
            "Heart reactions: inferred — each giver rates all others, hearts fill remaining targets",
            "Milena: participated late (punished with -500 estalecas, but reactions were recorded)",
            "Chaiany: gave hearts to all (not in article = 100% positive)",
            "Complete graph: 24 participants, each rates 23 others (except non-participants)"
        ],
        "limitations": [
            "Heart reactions are INFERRED (not directly from article), but logically certain",
            "balance and roles carried from Jan 17 snapshot (not verified for Jan 18)",
            "New entrants structural data (avatar, job, group) from Jan 19 snapshot",
            "Exact API capture time unknown — using 12:00:00 as synthetic placeholder"
        ],
        "base_snapshots": [
            "2026-01-17_17-46-39.json (structural data for 20 original participants)",
            "2026-01-19_22-34-41.json (structural data for 4 new entrants)"
        ]
    },
    "participants": synthetic_participants
}

output_path = DATA_DIR / "2026-01-18_12-00-00.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(save_data, f, indent=2, ensure_ascii=False)

print(f"\n✓ Saved synthetic snapshot: {output_path}")
print(f"  Participants: {len(synthetic_participants)}")
print(f"  Total reactions: {total_reactions}")
print(f"  Hearts: {reaction_counts.get('Coração', 0)}")
print(f"  Negative/mild: {total_reactions - reaction_counts.get('Coração', 0)}")
print(f"  Hash: {data_hash[:16]}")
