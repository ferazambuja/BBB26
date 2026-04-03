#!/usr/bin/env python3
"""Build derived index data for index.qmd (lightweight tables)."""

from __future__ import annotations

import json
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict, Counter
from typing import Any, Callable

UTC = timezone.utc
BRT = timezone(timedelta(hours=-3))

from data_utils import (
    load_snapshot, build_reaction_matrix, parse_roles, calc_sentiment,
    REACTION_EMOJI, REACTION_SLUG_TO_LABEL, SENTIMENT_WEIGHTS, POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE,
    POWER_EVENT_EMOJI, POWER_EVENT_LABELS,
    utc_to_game_date, get_cycle_number, get_cycle_start_date, get_effective_cycle_end_dates,
    normalize_actors, get_daily_snapshots, get_all_snapshots_with_data,
    genero, resolve_leaders, compute_protected_names, load_paredoes_transformed, load_votalhada_polls, get_poll_for_paredao, GROUP_COLORS,
    get_bv_winners,
)
from builders.paredao_exposure import (
    compute_paredao_exposure_stats,
    compute_house_vote_exposure,
    build_participant_windows,
    build_nunca_paredao_items,
    build_figurinha_repetida_items,
)
from paredao_viz import build_paredao_history, build_paredao_card_payload

_PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = _PROJECT_ROOT / "data" / "snapshots"
DERIVED_DIR = _PROJECT_ROOT / "data" / "derived"

MANUAL_EVENTS_FILE = _PROJECT_ROOT / "data" / "manual_events.json"
AUTO_EVENTS_FILE = DERIVED_DIR / "auto_events.json"
SINCERAO_FILE = DERIVED_DIR / "sincerao_edges.json"
DAILY_METRICS_FILE = DERIVED_DIR / "daily_metrics.json"
ROLES_DAILY_FILE = DERIVED_DIR / "roles_daily.json"
PARTICIPANTS_INDEX_FILE = DERIVED_DIR / "participants_index.json"
PLANT_INDEX_FILE = DERIVED_DIR / "plant_index.json"
RELATIONS_FILE = DERIVED_DIR / "relations_scores.json"
PAREDOES_FILE = _PROJECT_ROOT / "data" / "paredoes.json"
CARTOLA_FILE = DERIVED_DIR / "cartola_data.json"
PROVA_FILE = DERIVED_DIR / "prova_rankings.json"
PROVAS_RAW_FILE = _PROJECT_ROOT / "data" / "provas.json"

PULSO_MANUAL_FACT_OVERRIDES: dict[tuple[str, str], dict[str, Any]] = {
    ("chaos_day", "2026-01-20"): {
        "support": "17 💔, 15 🧳, 14 🌱, 12 🍪, 9 🐍, 7 🤥, 1 🎯",
        "summary": (
            "Ressaca do 1º Sincerão: 75 ❤️ mudaram de lugar, e o maior baque foi de Leandro (-16.5)."
        ),
        "context": {
            "moment": "Ressaca do 1º Sincerão",
            "chips": ["Líder: Alberto Cowboy", "Pós-Sincerão"],
            "timeline": [
                {
                    "date": "2026-01-18",
                    "summary": "Entrou com 22 ❤️ e 1 🧳.",
                },
                {
                    "date": "2026-01-19",
                    "summary": (
                        "No 1º Sincerão, cravou Alberto Cowboy como quem não ganha; "
                        "depois levou 2x não ganha, de Gabriela (planta) e Jordana "
                        "(disse que ele mentiu sobre o Quarto Branco), e ficou sem pódio."
                    ),
                },
                {
                    "date": "2026-01-20",
                    "summary": (
                        "10 ❤️ viraram outra coisa ao redor de Leandro: Juliano ❤️→🌱, Solange ❤️→🧳, "
                        "Sarah ❤️→🍪, Chaiany ❤️→🌱, Aline ❤️→🧳, Breno ❤️→🐍, Marciele ❤️→🌱, "
                        "Samira ❤️→🌱, Jordana ❤️→🤥, Gabriela ❤️→🌱."
                    ),
                },
            ],
        },
        "participants": ["Leandro"],
    },
    ("volatile_giver", "2026-02-02"): {
        "match": {"support": "Juliano Floss", "value": "19"},
        "title": "Maior redesenho do queridômetro",
        "value_label": "casas preenchidas",
        "support": "8 ❤️, 4 🌱, 3 🤮, 2 🤥, 1 🐍, 1 💔",
        "summary": (
            "No auge do 3º Paredão, Juliano saiu de 19 espaços vazios para um tabuleiro completo: "
            "abriu ❤️ para aliados, mas pesou a mão em Brigido 🤮, Jonas 🤮, Alberto 🤥, Sarah 🤥 e Jordana 🐍."
        ),
        "context": {
            "moment": "Big Fone, 3º Paredão e Sincerão",
            "chips": ["Líder: Maxiane", "Big Fone na véspera", "Dia de Sincerão", "Tá Com Nada"],
            "timeline": [
                {
                    "date": "2026-01-31",
                    "summary": "Atendeu o Big Fone azul e, com Babu e Marcelo, ajudou a colocar Jonas no 3º Paredão.",
                },
                {
                    "date": "2026-02-01",
                    "summary": "Na formação, votou em Brigido; a berlinda fechou com Ana Paula, Leandro e o próprio Brigido.",
                },
                {
                    "date": "2026-02-02",
                    "summary": (
                        "Dia de Tá Com Nada e Sincerão de futebol. Juliano virou alvo de 2x Bola Murcha "
                        "e 1x Goleiro Frangueiro; na comparação diária, preencheu os 19 espaços com "
                        "8 ❤️ e 11 negativas."
                    ),
                },
            ],
        },
        "participants": ["Juliano Floss"],
    },
}

ROLE_TYPES = {
    "Líder": "lider",
    "Anjo": "anjo",
    "Monstro": "monstro",
    "Imune": "imunidade",
    "Paredão": "emparedado",
}

BLINDADOS_REASON_ORDER = ["Autoimune", "Líder", "Imune"]
VISADOS_RECENT_WINDOW = 3

# Deliberate individual power event types (used for aggressor and animosity scoring)
DELIBERATE_POWER_TYPES = frozenset({
    "indicacao", "contragolpe", "monstro", "veto_prova",
    "mira_do_lider", "barrado_baile", "veto_ganha_ganha",
    "duelo_de_risco", "imunidade", "troca_xepa", "troca_vip",
})

# Types that count as deliberate negative targeting (for Mais Alvo / Mais Agressor cards)
POWER_TARGET_TYPES = frozenset({
    "indicacao", "contragolpe", "monstro", "barrado_baile",
    "mira_do_lider", "veto_prova",
    "consenso_anjo_monstro", "troca_xepa",
})

POWER_TAG_LABELS: dict[str, str] = {
    "indicacao": "Indicação",
    "contragolpe": "Contragolpe",
    "monstro": "Monstro",
    "barrado_baile": "Barrado",
    "mira_do_lider": "Na Mira",
    "veto_prova": "Veto Prova",
    "consenso_anjo_monstro": "Consenso A+M",
    "troca_xepa": "Troca Xepa",
}

SINC_TYPE_META: dict[str, dict[str, str]] = {
    "elogio":            {"label": "elogio",             "emoji": "🏆", "valence": "pos"},
    "regua":             {"label": "regua",              "emoji": "📏", "valence": "pos"},
    "ataque":            {"label": "ataque",             "emoji": "💣", "valence": "neg"},
    "nao_ganha":         {"label": "não ganha",           "emoji": "🚫", "valence": "neg"},
    "paredao_perfeito":  {"label": "paredão perfeito",   "emoji": "🏛️", "valence": "neg"},
    "regua_fora":        {"label": "fora da régua",      "emoji": "❌", "valence": "neg"},
    "quem_sai":          {"label": "quem sai",           "emoji": "🚪", "valence": "neg"},
    "prova_eliminou":    {"label": "eliminado na prova", "emoji": "⚡", "valence": "neg"},
}

# Derived view for downstream code that only needs valence
SINC_VALENCE: dict[str, str] = {k: v["valence"] for k, v in SINC_TYPE_META.items()}


def _resolve_gendered_tema(tema: str, target: str) -> str:
    """Resolve '(a)' suffix based on target gender."""
    if '(a)' not in tema:
        return tema
    return tema.replace('(a)', 'a') if genero(target) == 'f' else tema.replace('(a)', '')


def resolve_sinc_label(edge_type: str, tema: str | None, target: str) -> str:
    """Produce a human-readable label for a Sincerao interaction.

    If the edge has a tema (e.g. ataque themes), use it with gender resolution.
    Otherwise, fall back to SINC_TYPE_META label. Unknown types are humanized
    (underscores replaced with spaces) and a warning is logged.
    """
    if tema:
        return _resolve_gendered_tema(tema, target)
    meta = SINC_TYPE_META.get(edge_type)
    if meta:
        return meta["label"]
    import sys
    print(f"WARNING: Unknown Sincerao edge type '{edge_type}' — add it to SINC_TYPE_META", file=sys.stderr)
    return edge_type.replace("_", " ")


def _normalize_text_token(value: str) -> str:
    """Normalize text for tolerant token comparisons."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().strip().split())


SINC_NEGATIVE_LANE_LABELS = {
    "faz alguem de bobo": "Quem faz alguém de bobo",
    "esta sendo feito de bobo": "Quem está sendo feito de bobo",
}


def _label_sinc_negative_lane(tema: str) -> str:
    token = _normalize_text_token(tema)
    if token in SINC_NEGATIVE_LANE_LABELS:
        return SINC_NEGATIVE_LANE_LABELS[token]
    cleaned = " ".join(tema.strip().split())
    return cleaned[:1].upper() + cleaned[1:] if cleaned else "Atacados"


def _is_positive_heart_reaction(label: str | None) -> bool:
    """Return True when reaction label represents a positive heart reaction."""
    if not label:
        return False
    if label in POSITIVE or label == "❤️":
        return True
    token = _normalize_text_token(label)
    slug = token.replace(" ", "-")
    canonical = REACTION_SLUG_TO_LABEL.get(slug)
    if canonical in POSITIVE:
        return True
    return token in {"coracao", "heart"}


def _canonical_reaction_label(label: str | None) -> str:
    """Normalize reaction labels to canonical forms used by SENTIMENT_WEIGHTS."""
    if not label:
        return ""
    if label in SENTIMENT_WEIGHTS:
        return label
    token = _normalize_text_token(label)
    slug = token.replace(" ", "-")
    return REACTION_SLUG_TO_LABEL.get(slug, label)


def _build_profile_sincerao(name: str, sinc_data: dict, current_cycle: int,
                             latest_matrix: dict[tuple[str, str], str],
                             sinc_weeks_meta: dict[int, str]) -> dict[str, Any]:
    """Build the complete sincerao view-model for a participant profile.

    Returns dict with: current_cycle, summary, current, season.
    """
    all_edges = sinc_data.get("edges", [])

    # Partition edges into received (target==name) and given (actor==name)
    received_edges = [e for e in all_edges if e.get("target") == name]
    given_edges = [e for e in all_edges if e.get("actor") == name]

    def _build_interaction(edge: dict, perspective: str) -> dict:
        etype = edge.get("type", "")
        target_for_gender = name if perspective == "received" else edge.get("target", "")
        label = resolve_sinc_label(etype, edge.get("tema"), target_for_gender)
        meta = SINC_TYPE_META.get(etype, {})
        item: dict[str, Any] = {
            "type": etype,
            "label": label,
            "emoji": meta.get("emoji", ""),
            "valence": meta.get("valence", "neg"),
        }
        if perspective == "received":
            item["actor"] = edge.get("actor", "")
        else:
            item["target"] = edge.get("target", "")
        return item

    def _group_by_week(edges: list[dict], perspective: str) -> list[dict]:
        by_week: dict[int, list[dict]] = defaultdict(list)
        for edge in edges:
            wk = edge.get("cycle")
            if wk is None:
                continue
            by_week[wk].append(_build_interaction(edge, perspective))
        result = []
        for wk in sorted(by_week.keys(), reverse=True):
            interactions = by_week[wk]
            pos_count = sum(1 for ix in interactions if ix.get("valence") == "pos")
            neg_count = len(interactions) - pos_count
            result.append({
                "cycle": wk,
                "format_short": sinc_weeks_meta.get(wk, ""),
                "meta": {
                    "count_total": len(interactions),
                    "count_pos": pos_count,
                    "count_neg": neg_count,
                },
                "interactions": interactions,
            })
        return result

    # Current week interactions
    current_received = [_build_interaction(e, "received")
                        for e in received_edges if (e.get("cycle")) == current_cycle]
    current_given = [_build_interaction(e, "given")
                     for e in given_edges if (e.get("cycle")) == current_cycle]

    # Season: all weeks grouped
    season_received = _group_by_week(received_edges, "received")
    season_given = _group_by_week(given_edges, "given")

    # Summary counts
    def _count_valence(interactions: list[dict]) -> tuple[int, int]:
        pos = sum(1 for i in interactions if i.get("valence") == "pos")
        neg = len(interactions) - pos
        return pos, neg

    all_received_items = [i for wg in season_received for i in wg["interactions"]]
    all_given_items = [i for wg in season_given for i in wg["interactions"]]
    r_pos, r_neg = _count_valence(all_received_items)
    g_pos, g_neg = _count_valence(all_given_items)

    # Contradiction detection: current-week edges where actor==name gave negative
    # but latest_matrix shows positive heart reaction for that pair
    contradiction_targets: set[str] = set()
    for edge in given_edges:
        if (edge.get("cycle")) != current_cycle:
            continue
        etype = edge.get("type", "")
        if SINC_VALENCE.get(etype) != "neg":
            continue
        target = edge.get("target")
        if target and _is_positive_heart_reaction(latest_matrix.get((name, target))):
            contradiction_targets.add(target)

    return {
        "current_cycle": current_cycle,
        "summary": {
            "received_total": len(all_received_items),
            "received_pos": r_pos,
            "received_neg": r_neg,
            "given_total": len(all_given_items),
            "given_pos": g_pos,
            "given_neg": g_neg,
            "contradiction_count": len(contradiction_targets),
            "contradiction_targets": sorted(contradiction_targets),
        },
        "current": {
            "received": current_received,
            "given": current_given,
        },
        "season": {
            "received_by_week": season_received,
            "given_by_week": season_given,
        },
    }


def _compute_sincerao_radar(week_edges: list[dict], week: int,
                             latest_matrix: dict[tuple[str, str], str],
                             active_set: set[str] | None = None) -> dict:
    """Compute weekly Sincerao radar: ranked targets, praised, contradictions, not-targeted."""
    neg_counts: dict[str, int] = defaultdict(int)
    neg_counts_by_tema: dict[str, Counter[str]] = {}
    neg_actors: dict[str, set[str]] = defaultdict(set)
    neg_actors_by_tema: dict[str, dict[str, set[str]]] = {}
    neg_unthemed_counts: Counter[str] = Counter()
    neg_unthemed_actors: dict[str, set[str]] = defaultdict(set)
    neg_labels_by_tema: dict[str, str] = {}
    pos_counts: dict[str, int] = defaultdict(int)
    pos_actors: dict[str, set[str]] = defaultdict(set)
    contradiction_counts: dict[str, int] = defaultdict(int)
    actors: set[str] = set()

    for edge in week_edges:
        if (edge.get("cycle")) != week:
            continue
        etype = edge.get("type", "")
        actor = edge.get("actor", "")
        target = edge.get("target", "")
        if active_set and (actor not in active_set or target not in active_set):
            continue
        valence = SINC_VALENCE.get(etype, "neg")
        if actor:
            actors.add(actor)

        if valence == "neg":
            neg_counts[target] += 1
            if actor and target:
                neg_actors[target].add(actor)
            tema = edge.get("tema")
            if tema:
                tema_token = _normalize_text_token(tema)
                neg_counts_by_tema.setdefault(tema_token, Counter())
                neg_counts_by_tema[tema_token][target] += 1
                neg_actors_by_tema.setdefault(tema_token, defaultdict(set))
                if actor and target:
                    neg_actors_by_tema[tema_token][target].add(actor)
                neg_labels_by_tema.setdefault(tema_token, _label_sinc_negative_lane(tema))
            else:
                neg_unthemed_counts[target] += 1
                if actor and target:
                    neg_unthemed_actors[target].add(actor)
            if _is_positive_heart_reaction(latest_matrix.get((actor, target))):
                contradiction_counts[actor] += 1
        else:
            pos_counts[target] += 1
            if actor and target:
                pos_actors[target].add(actor)

    def _ranked(counts: dict[str, int], actors_by_target: dict[str, set[str]] | None = None) -> list[dict]:
        """Return all entries sorted by count descending, then name."""
        return sorted(
            [
                {
                    "name": n,
                    "count": c,
                    **({"actors": sorted(actors_by_target.get(n, []))} if actors_by_target is not None else {}),
                }
                for n, c in counts.items()
            ],
            key=lambda x: (-x["count"], x["name"]),
        )

    def _top(counts: dict[str, int]) -> dict:
        if not counts:
            return {"names": [], "count": 0}
        max_val = max(counts.values())
        names = sorted(n for n, c in counts.items() if c == max_val)
        return {"names": names, "count": max_val}

    # "Not targeted" = participated (is an actor) but nobody targeted them negatively
    all_targeted = set(neg_counts.keys()) | set(pos_counts.keys())
    not_targeted = sorted(actors - all_targeted)
    neg_lanes = []
    if len(neg_counts_by_tema) > 1:
        neg_lanes = [
            {
                "key": tema_token,
                "label": neg_labels_by_tema.get(tema_token, tema_token),
                "ranked": _ranked(counts, neg_actors_by_tema.get(tema_token, {})),
                "top": _top(counts),
            }
            for tema_token, counts in neg_counts_by_tema.items()
        ]
        if neg_unthemed_counts:
            neg_lanes.append(
                {
                    "key": "__unlabeled__",
                    "label": "Atacados",
                    "ranked": _ranked(neg_unthemed_counts, neg_unthemed_actors),
                    "top": _top(neg_unthemed_counts),
                }
            )

    return {
        "most_targeted_neg": _top(neg_counts),
        "most_praised": _top(pos_counts),
        "most_contradictions": _top(contradiction_counts),
        "neg_ranked": _ranked(neg_counts, neg_actors),
        "neg_lanes": neg_lanes,
        "pos_ranked": _ranked(pos_counts, pos_actors),
        "not_targeted": not_targeted,
        "n_actors": len(actors),
        "cycle": week,
    }


def _compute_sinc_type_coverage(sinc_data: dict) -> dict[str, Any]:
    """Return observed Sincerao types and unknown types for quick QA."""
    type_counts: Counter[str] = Counter()
    for edge in sinc_data.get("edges", []) if isinstance(sinc_data, dict) else []:
        etype = edge.get("type")
        if etype:
            type_counts[etype] += 1

    seen = sorted(type_counts.keys())
    unknown = sorted(t for t in seen if t not in SINC_TYPE_META)
    return {
        "seen": seen,
        "unknown": unknown,
        "counts": {t: type_counts[t] for t in seen},
    }


def load_json(path: Path, default: Any) -> Any:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def _iter_cycle_entries(manual_events: dict | None) -> list[dict]:
    """Return canonical cycle entries."""
    if not isinstance(manual_events, dict):
        return []
    cycles = manual_events.get("cycles", [])
    return [item for item in cycles if isinstance(item, dict)]


def _get_event_cycle(item: dict, fallback: int = 0) -> int:
    """Read canonical cycle key."""
    value = item.get("cycle")
    if isinstance(value, int):
        return value
    return fallback


def _resolve_current_cycle(current_cycle: int, manual_events: dict | None, paredoes: dict | None) -> int:
    """Pick the active cycle from live paredão state or the manually opened cycle."""
    active_paredao = next(
        (p for p in reversed((paredoes or {}).get("paredoes", [])) if p.get("status") == "em_andamento"),
        None,
    )
    if isinstance(active_paredao, dict):
        active_cycle = _get_event_cycle(active_paredao)
        if active_cycle:
            return active_cycle

    manual_open_cycles = sorted(
        _get_event_cycle(item)
        for item in _iter_cycle_entries(manual_events)
        if not item.get("end_date") and _get_event_cycle(item)
    )
    if manual_open_cycles:
        return max(current_cycle, manual_open_cycles[-1])

    return current_cycle


def build_big_fone_consensus(
    manual_events: dict,
    current_cycle: int | None,
    active_names: list[str],
    active_set: set[str],
    avatars: dict[str, str],
    member_of: dict[str, str],
    roles_current: dict[str, list[str]],
    latest_matrix: dict[tuple[str, str], str],
    pair_sentiment_fn: Callable[[str, str], float],
) -> dict | None:
    """Build Big Fone consensus analysis for the current week.

    Returns a dict with attendees, target analysis, potential 3rd persons,
    and facilitator/disruptor lists — or None if fewer than 2 bracelet holders.
    """
    big_fone_attendees = []
    for wev in _iter_cycle_entries(manual_events):
        wev_week = get_cycle_number(wev["start_date"]) if wev.get("start_date") else _get_event_cycle(wev)
        if wev_week == current_cycle:
            for bf in wev.get("big_fone", []) or []:
                att = bf.get("atendeu", "")
                cons = (bf.get("consequencia", "") or "").lower()
                if att and att in active_set and ("consenso" in cons or "pulseira" in cons):
                    big_fone_attendees.append(att)
            break

    if len(big_fone_attendees) < 2:
        return None

    bf_set = set(big_fone_attendees)
    possible_targets = [n for n in active_names if n not in bf_set]

    # Immune participants can't be nominated
    immune_roles = {"Imune", "Líder", "Anjo"}
    immune_names = set()
    for role_name, holders in roles_current.items():
        if role_name in immune_roles:
            immune_names.update(holders)

    target_analysis = []
    for target in possible_targets:
        entry = {
            "name": target,
            "avatar": avatars.get(target, ""),
            "member_of": member_of.get(target, "?"),
            "immune": target in immune_names,
            "scores": {},
            "emojis": {},
            "target_emojis": {},
        }
        combined = 0.0
        all_negative = True
        for att in big_fone_attendees:
            sc = pair_sentiment_fn(att, target)
            entry["scores"][att] = round(sc, 2)
            combined += sc
            if sc >= 0:
                all_negative = False
            rxn_label = latest_matrix.get((att, target), "")
            entry["emojis"][att] = REACTION_EMOJI.get(rxn_label, "?")
            rxn_back = latest_matrix.get((target, att), "")
            entry["target_emojis"][att] = REACTION_EMOJI.get(rxn_back, "?")

        entry["combined_score"] = round(combined, 2)
        entry["all_negative"] = all_negative
        target_analysis.append(entry)

    target_analysis.sort(key=lambda x: x["combined_score"])

    # Classify into tiers
    for entry in target_analysis:
        if entry["immune"]:
            entry["tier"] = "immune"
        elif entry["all_negative"]:
            entry["tier"] = "consensus"
        elif all(entry["scores"].get(att, 0) < 0 for att in big_fone_attendees[:2]):
            entry["tier"] = "likely"
        elif any(entry["scores"].get(att, 0) < 0 for att in big_fone_attendees):
            entry["tier"] = "split"
        else:
            entry["tier"] = "safe"

    # Potential 3rd attendees
    potential_3rd = []
    for candidate in active_names:
        if candidate in bf_set or candidate in immune_names:
            continue
        agreement_targets = []
        disagreement_targets = []
        target_scores = {}
        consensus_targets = [t for t in target_analysis if t["tier"] == "consensus" and not t["immune"]]
        for ct in consensus_targets:
            tname = ct["name"]
            if tname == candidate:
                continue
            cand_score = pair_sentiment_fn(candidate, tname)
            target_scores[tname] = round(cand_score, 2)
            if cand_score < 0:
                agreement_targets.append(tname)
            else:
                disagreement_targets.append(tname)

        potential_3rd.append({
            "name": candidate,
            "avatar": avatars.get(candidate, ""),
            "member_of": member_of.get(candidate, "?"),
            "is_consensus_target": candidate in {t["name"] for t in consensus_targets},
            "agrees_on": agreement_targets,
            "disagrees_on": disagreement_targets,
            "target_scores": target_scores,
            "n_agrees": len(agreement_targets),
            "n_disagrees": len(disagreement_targets),
            "difficulty": len(disagreement_targets) / max(len(consensus_targets), 1),
        })

    potential_3rd.sort(key=lambda x: (-x["n_disagrees"], x["n_agrees"]))

    # Per-target consensus probability
    consensus_targets_list = [t for t in target_analysis if t["tier"] == "consensus" and not t["immune"]]
    non_target_3rds = [p for p in potential_3rd if not p.get("is_consensus_target")]
    n_possible_3rds = len(non_target_3rds)

    for ct in consensus_targets_list:
        tname = ct["name"]
        n_agree = sum(1 for p in non_target_3rds if tname in p.get("agrees_on", []))
        ct["consensus_pct"] = round(100.0 * n_agree / n_possible_3rds, 1) if n_possible_3rds > 0 else 0
        ct["n_3rds_agree"] = n_agree
        ct["n_possible_3rds"] = n_possible_3rds
        ct["facilitators"] = [p["name"] for p in non_target_3rds if tname in p.get("agrees_on", [])]
        ct["blockers"] = [p["name"] for p in non_target_3rds if tname not in p.get("agrees_on", [])]

    # Mutual hostility analysis
    for ct in consensus_targets_list:
        mutual = {}
        for att in big_fone_attendees:
            back_emoji = ct["target_emojis"].get(att, "?")
            back_rxn = latest_matrix.get((ct["name"], att), "")
            is_negative_back = back_rxn in MILD_NEGATIVE or back_rxn in STRONG_NEGATIVE
            is_strong_back = back_rxn in STRONG_NEGATIVE
            mutual[att] = {
                "emoji": back_emoji,
                "reaction": back_rxn,
                "is_negative": is_negative_back,
                "is_strong": is_strong_back,
            }
        ct["mutual_hostility"] = mutual
        ct["is_fully_mutual"] = all(m["is_negative"] for m in mutual.values())

    # Top disruptors/facilitators summary
    facilitators = [p for p in non_target_3rds if p["n_disagrees"] == 0 and p["n_agrees"] > 0]
    disruptors = [p for p in non_target_3rds if p["n_agrees"] == 0 and p["n_disagrees"] > 0]

    return {
        "attendees": big_fone_attendees,
        "targets": target_analysis,
        "potential_3rd": potential_3rd,
        "n_consensus_targets": sum(1 for t in target_analysis if t["tier"] == "consensus"),
        "n_possible_3rds": n_possible_3rds,
        "facilitators": [p["name"] for p in facilitators],
        "disruptors": [p["name"] for p in disruptors],
    }


def get_all_snapshots() -> list[dict]:
    """Wrapper for backward-compatible call sites."""
    return get_all_snapshots_with_data(DATA_DIR)


def build_alignment(participants: list[dict], sinc_data: dict, week: int) -> list[dict] | None:
    if not sinc_data:
        return None
    agg = next((a for a in sinc_data.get("aggregates", []) if (a.get("cycle")) == week), None)
    if not agg:
        return None
    scores = agg.get("scores", {})
    if not scores:
        return None
    rows = []
    for p in participants:
        name = p.get("name")
        if name in scores:
            rows.append({
                "name": name,
                "sincerao_score": scores[name],
                "sentiment_score": calc_sentiment(p),
                "grupo": p.get("characteristics", {}).get("memberOf", "?"),
            })
    if not rows:
        return None
    max_sinc = max(abs(r["sincerao_score"]) for r in rows) or 1e-6
    max_sent = max(abs(r["sentiment_score"]) for r in rows) or 1e-6
    for r in rows:
        r["sinc_norm"] = r["sincerao_score"] / max_sinc
        r["sent_norm"] = r["sentiment_score"] / max_sent
        r["alignment"] = round(1 - abs(r["sinc_norm"] - r["sent_norm"]), 2)
    return rows


# ── Sub-functions for build_index_data() ──────────────────────────────────


def _load_and_parse_snapshots(snapshots: list[dict]) -> dict[str, Any]:
    """Label snapshots, extract member_of/avatars, load all derived JSONs.

    Returns a dict with loaded data and basic lookups.
    """
    for snap in snapshots:
        meta = snap.get("metadata") or {}
        label = snap["date"]
        if meta.get("synthetic"):
            label += " (sintético)"
        snap["label"] = label

    latest = snapshots[-1]
    latest_date = latest["date"]
    current_cycle = get_cycle_number(latest_date)

    member_of = {}
    avatars = {}
    for snap in snapshots:
        for p in snap["participants"]:
            name = p.get("name")
            if not name:
                continue
            if name not in member_of:
                member_of[name] = p.get("characteristics", {}).get("memberOf", "?")
            if name not in avatars and p.get("avatar"):
                avatars[name] = p.get("avatar")

    manual_events = load_json(MANUAL_EVENTS_FILE, {})
    auto_events = load_json(AUTO_EVENTS_FILE, {"events": []})
    sinc_data = load_json(SINCERAO_FILE, {})
    daily_metrics = load_json(DAILY_METRICS_FILE, {"daily": []})
    roles_daily = load_json(ROLES_DAILY_FILE, {"daily": []})
    participants_index = load_json(PARTICIPANTS_INDEX_FILE, {"participants": []})
    plant_index = load_json(PLANT_INDEX_FILE, {})
    relations_data = load_json(RELATIONS_FILE, {})
    paredoes = load_json(PAREDOES_FILE, {"paredoes": []})
    cartola_data = load_json(CARTOLA_FILE, {})
    prova_data = load_json(PROVA_FILE, {})
    provas_raw = load_json(PROVAS_RAW_FILE, {"provas": []})

    if isinstance(relations_data, dict):
        relations_pairs = relations_data.get("pairs_daily") or relations_data.get("pairs", {})
        received_impact = relations_data.get("received_impact", {})
    else:
        relations_pairs = {}
        received_impact = {}

    power_events = manual_events.get("power_events", []) + auto_events.get("events", [])

    return {
        "latest": latest,
        "latest_date": latest_date,
        "current_cycle": current_cycle,
        "member_of": member_of,
        "avatars": avatars,
        "manual_events": manual_events,
        "auto_events": auto_events,
        "sinc_data": sinc_data,
        "daily_metrics": daily_metrics,
        "roles_daily": roles_daily,
        "participants_index": participants_index,
        "plant_index": plant_index,
        "relations_data": relations_data,
        "paredoes": paredoes,
        "cartola_data": cartola_data,
        "prova_data": prova_data,
        "provas_raw": provas_raw,
        "relations_pairs": relations_pairs,
        "received_impact": received_impact,
        "power_events": power_events,
    }


def _aggregate_latest_state(parsed: dict[str, Any], daily_snapshots: list[dict]) -> dict[str, Any]:
    """Compute active participants, roles, VIP/Xepa days, leader periods, plant scores.

    Returns a dict with aggregated state lookups.
    """
    latest = parsed["latest"]
    latest_date = parsed["latest_date"]
    current_cycle = parsed["current_cycle"]
    plant_index = parsed["plant_index"]
    roles_daily = parsed["roles_daily"]
    participants_index = parsed["participants_index"]
    paredoes = parsed["paredoes"]
    manual_events = parsed.get("manual_events", {})

    def plant_week_has_signals(week_entry: dict | None) -> bool:
        if not week_entry:
            return False
        for info in week_entry.get("scores", {}).values():
            raw = info.get("raw", {})
            if raw.get("power_events", 0) > 0:
                return True
            if raw.get("sincerao_edges", 0) > 0:
                return True
            if raw.get("plateia_planta"):
                return True
        return False

    plant_week = None
    for w in plant_index.get("weeks", []):
        if (w.get("cycle")) == current_cycle:
            plant_week = w
            break
    if plant_week is None or not plant_week_has_signals(plant_week):
        candidates = [w for w in plant_index.get("weeks", []) if plant_week_has_signals(w)]
        if candidates:
            plant_week = candidates[-1]
        elif plant_index.get("weeks"):
            plant_week = plant_index.get("weeks", [])[-1]
    plant_scores = plant_week.get("scores", {}) if plant_week else {}

    active = [p for p in latest["participants"] if not p.get("characteristics", {}).get("eliminated")]
    active_names = sorted([p["name"] for p in active])
    active_set = set(active_names)

    roles_current = defaultdict(list)
    for p in latest["participants"]:
        roles = parse_roles(p.get("characteristics", {}).get("roles", []))
        for role in roles:
            roles_current[role].append(p.get("name"))

    # VIP/Xepa days
    vip_days = defaultdict(int)
    xepa_days = defaultdict(int)
    total_days = defaultdict(int)
    for snap in daily_snapshots:
        for p in snap["participants"]:
            name = p.get("name")
            if not name:
                continue
            group = (p.get("characteristics", {}).get("group") or "").lower()
            total_days[name] += 1
            if group == "vip":
                vip_days[name] += 1
            elif group == "xepa":
                xepa_days[name] += 1

    # VIP weeks selected — based on CYCLE_END_DATES boundaries (not API role changes).
    # This correctly handles consecutive same-person Líder (e.g., Jonas weeks 4–6).
    vip_cycles_selected = defaultdict(int)
    xepa_cycles = defaultdict(int)
    leader_periods = []

    daily_snap_by_date = {snap["date"]: snap for snap in daily_snapshots}

    paredoes_list = paredoes.get("paredoes", []) if paredoes else []
    lider_by_paredao: dict[int, str | None] = {}
    lideres_by_paredao: dict[int, list[str]] = {}
    for par in paredoes_list:
        cycle_num = par.get("cycle", par["numero"])
        formacao = par.get("formacao", {})
        lider_by_paredao[cycle_num] = formacao.get("lider")
        lideres_by_paredao[cycle_num] = resolve_leaders(formacao)

    effective_cycle_ends = get_effective_cycle_end_dates()
    n_cycles = len(effective_cycle_ends)
    for cyc_num in range(1, n_cycles + 2):  # +1 for open current cycle
        start_date = get_cycle_start_date(cyc_num)

        if cyc_num <= n_cycles:
            end_date = effective_cycle_ends[cyc_num - 1]
        else:
            # Open week (current, no end boundary yet)
            end_date = daily_snapshots[-1]["date"] if daily_snapshots else start_date

        # Only include if we have data for this start date (or later)
        if daily_snapshots and start_date > daily_snapshots[-1]["date"]:
            break

        leader_name = lider_by_paredao.get(cyc_num)
        leader_names = lideres_by_paredao.get(cyc_num, [leader_name] if leader_name else [])

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

        # Cold-start fix: if start_date snapshot has all-VIP (no Xepa), the API
        # hadn't set up VIP/Xepa yet (premiere night). Scan forward within the
        # period to find a snapshot with a proper VIP/Xepa split.
        if period_vip and not period_xepa and len(period_vip) > 10:
            for ds in daily_snapshots:
                if ds["date"] < start_date or ds["date"] > end_date:
                    continue
                if ds is snap:
                    continue
                _vip, _xepa = [], []
                for p in ds["participants"]:
                    nm = p.get("name")
                    if not nm:
                        continue
                    grp = (p.get("characteristics", {}).get("group") or "").lower()
                    if grp == "vip":
                        _vip.append(nm)
                    elif grp == "xepa":
                        _xepa.append(nm)
                if _xepa:  # Found a snapshot with proper split
                    period_vip = _vip
                    period_xepa = _xepa
                    break

        for nm in period_vip:
            vip_cycles_selected[nm] += 1
        for nm in period_xepa:
            xepa_cycles[nm] += 1

        # Display name: "A + B" for dual leaders, single name otherwise
        _lp_display = " + ".join(leader_names) if leader_names else leader_name
        leader_periods.append({
            "leader": _lp_display,
            "leaders": leader_names,
            "start": start_date,
            "end": end_date,
            "cycle": cyc_num,
            "vip": sorted(period_vip),
            "xepa": sorted(period_xepa),
        })

    house_leaders = roles_current.get("Líder", [])
    house_leader = " + ".join(house_leaders) if house_leaders else None

    # leader_start_date: derived from effective week boundaries for current open week.
    current_open_cycle = len(effective_cycle_ends) + 1
    leader_start_date = get_cycle_start_date(current_open_cycle)

    first_seen = {p["name"]: p.get("first_seen") for p in participants_index.get("participants", []) if p.get("name")}
    vip_group = {p.get("name") for p in latest["participants"]
                 if (p.get("characteristics", {}).get("group") or "").lower() == "vip"}
    vip_recipients = set(vip_group)
    for _hl in house_leaders:
        vip_recipients.discard(_hl)
    if leader_start_date:
        vip_recipients = {n for n in vip_recipients if first_seen.get(n, leader_start_date) <= leader_start_date}
    current_cycle = _resolve_current_cycle(current_cycle, manual_events, paredoes)

    return {
        "plant_week": plant_week,
        "plant_scores": plant_scores,
        "active": active,
        "active_names": active_names,
        "active_set": active_set,
        "roles_current": roles_current,
        "vip_days": vip_days,
        "xepa_days": xepa_days,
        "total_days": total_days,
        "vip_cycles_selected": vip_cycles_selected,
        "xepa_cycles": xepa_cycles,
        "leader_periods": leader_periods,
        "house_leader": house_leader,
        "house_leaders": house_leaders,
        "leader_start_date": leader_start_date,
        "vip_recipients": vip_recipients,
        "current_cycle": current_cycle,
    }


def _build_shared_context(snapshots: list[dict], daily_snapshots: list[dict], daily_matrices: list[dict]) -> dict[str, Any]:
    """Load JSONs, compute shared lookups (member_of, avatars, roles, VIP, plant scores).

    Returns a ctx dict that other sub-functions use.
    """
    parsed = _load_and_parse_snapshots(snapshots)
    aggregated = _aggregate_latest_state(parsed, daily_snapshots)

    # Use the most recent daily matrix that has complete reaction data.
    # When the API is broken (e.g. Breno/Quarto Secreto gap), the latest
    # daily snapshot may have missing reactions. Walk backwards through
    # daily snapshots to find one with a full set (N*(N-1) pairs for N
    # active participants). Synthetic snapshots built from GShow articles
    # provide this when the API fails.
    latest_matrix = {}
    matrix_date = parsed["latest_date"]
    if daily_matrices:
        n_active = len([p for p in parsed["latest"]["participants"]
                        if not p.get("characteristics", {}).get("eliminated")])
        expected_pairs = n_active * (n_active - 1)
        for i, mat in enumerate(reversed(daily_matrices)):
            if len(mat) >= expected_pairs:
                latest_matrix = mat
                matrix_date = daily_snapshots[len(daily_matrices) - 1 - i]["date"]
                break
        if not latest_matrix:
            latest_matrix = daily_matrices[-1]

    # If the matrix came from an earlier day (API gap), update latest_date
    # so that display labels reflect the actual data date, not today.
    if matrix_date != parsed["latest_date"]:
        parsed["latest_date"] = matrix_date

    ctx = {
        "snapshots": snapshots,
        "daily_snapshots": daily_snapshots,
        "daily_matrices": daily_matrices,
        "latest_matrix": latest_matrix,
    }
    ctx.update(parsed)
    ctx.update(aggregated)
    return ctx


def _parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _format_short_date(date_str: str | None) -> str:
    parsed = _parse_iso_date(date_str)
    return parsed.strftime("%d/%m") if parsed else (date_str or "")


def _short_name(name: str | None) -> str:
    text = (name or "").strip()
    return text.split()[0] if text else ""


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _format_day_count(value: int) -> str:
    n = max(0, int(value or 0))
    return f"{n} dia" if n == 1 else f"{n} dias"


def _reaction_display_emoji(label: str | None) -> str:
    canonical = _canonical_reaction_label(label)
    return REACTION_EMOJI.get(canonical, label or "")


def _classify_hostility_pairs(matrix: dict[tuple[str, str], str], active_names: set[str]) -> tuple[set[frozenset[str]], set[tuple[str, str]]]:
    mutual: set[frozenset[str]] = set()
    blind_spots: set[tuple[str, str]] = set()
    checked: set[frozenset[str]] = set()

    for (actor, target), reaction in matrix.items():
        if actor not in active_names or target not in active_names:
            continue
        pair = frozenset([actor, target])
        if pair in checked:
            continue

        reverse_reaction = matrix.get((target, actor), "")
        actor_negative = reaction not in POSITIVE and reaction != ""
        target_negative = reverse_reaction not in POSITIVE and reverse_reaction != ""
        actor_positive = reaction in POSITIVE
        target_positive = reverse_reaction in POSITIVE

        if actor_negative and target_negative:
            mutual.add(pair)
        else:
            if actor_negative and target_positive:
                blind_spots.add((actor, target))
            if target_negative and actor_positive:
                blind_spots.add((target, actor))
        checked.add(pair)

    return mutual, blind_spots


def _comparison_source_tag(from_date: str, to_date: str, latest_snapshot_date: str) -> str:
    from_parsed = _parse_iso_date(from_date)
    to_parsed = _parse_iso_date(to_date)
    latest_parsed = _parse_iso_date(latest_snapshot_date)
    if from_parsed and to_parsed and latest_parsed:
        if (to_parsed - from_parsed).days == 1 and to_parsed == latest_parsed:
            return "📅 Ontem → Hoje"
    return f"📅 {_format_short_date(from_date)} → {_format_short_date(to_date)}"


def _count_pair_streak_days(
    pair: tuple[str, str],
    reaction_label: str,
    daily_matrices: list[dict[tuple[str, str], str]],
    *,
    end_idx: int,
) -> int:
    canonical = _canonical_reaction_label(reaction_label)
    if not canonical:
        return 0

    streak = 0
    for idx in range(end_idx, -1, -1):
        current = _canonical_reaction_label(daily_matrices[idx].get(pair, ""))
        if current != canonical:
            break
        streak += 1
    return streak


def _viradas_meta_line(item: dict[str, Any]) -> str:
    parts: list[str] = []
    prior_heart_days = int(item.get("prior_heart_days") or 0)
    prior_same_days = int(item.get("prior_same_emoji_days") or 0)
    old_emoji = item.get("old_emoji", "")
    if prior_heart_days > 0 and old_emoji == "❤️":
        parts.append(f"Depois de {_format_day_count(prior_heart_days)} de ❤️")
    elif prior_same_days > 0 and old_emoji:
        parts.append(f"Depois de {_format_day_count(prior_same_days)} de {old_emoji}")

    if item.get("other_side_kept_heart"):
        receiver = _short_name(item.get("receiver", ""))
        parts.append(f"{receiver} manteve ❤️")

    parts.append(_format_short_date(item.get("date", "")))
    return " · ".join(part for part in parts if part)


def _viradas_group_sort_key(kind: str, item: dict[str, Any]) -> tuple[Any, ...]:
    severity = item.get("severity_score")
    severity_rank = float(severity) if isinstance(severity, (int, float)) else -1.0
    other_side_kept = item.get("other_side_kept_heart")
    other_rank = 2 if other_side_kept is True else (1 if other_side_kept is False else 0)
    giver = item.get("giver", "")
    receiver = item.get("receiver", "")

    if kind == "dramatic":
        return (
            -severity_rank,
            -int(item.get("prior_same_emoji_days") or 0),
            -int(item.get("prior_heart_days") or 0),
            giver,
            receiver,
        )

    return (
        -int(item.get("prior_heart_days") or 0),
        -other_rank,
        -severity_rank,
        giver,
        receiver,
    )


def _viradas_item_tier(item: dict[str, Any]) -> int:
    kind = item.get("kind")
    if (
        kind in {"hostilities", "breaks"}
        and item.get("other_side_kept_heart") is True
        and int(item.get("prior_heart_days") or 0) >= 3
    ):
        return 0
    if kind == "breaks":
        return 1
    if kind == "dramatic":
        return 2
    return 3


def _viradas_partition_precedence(item: dict[str, Any]) -> int:
    kind = item.get("kind")
    tier = _viradas_item_tier(item)
    if tier == 0:
        return 0 if kind == "hostilities" else 1
    return 0


def _viradas_candidate_sort_key(item: dict[str, Any]) -> tuple[Any, ...]:
    severity = item.get("severity_score")
    severity_rank = float(severity) if isinstance(severity, (int, float)) else -1.0
    return (
        _viradas_item_tier(item),
        -int(item.get("prior_heart_days") or 0),
        -severity_rank,
        -int(item.get("prior_same_emoji_days") or 0),
        item.get("giver", ""),
        item.get("receiver", ""),
    )


def _build_viradas_hero_fields(item: dict[str, Any]) -> dict[str, Any]:
    giver = _short_name(item.get("giver", ""))
    receiver = _short_name(item.get("receiver", ""))
    old_emoji = item.get("old_emoji", "")
    new_emoji = item.get("new_emoji", "")
    prior_heart_days = int(item.get("prior_heart_days") or 0)
    prior_same_days = int(item.get("prior_same_emoji_days") or 0)
    other_side_kept_heart = item.get("other_side_kept_heart") is True
    kind = item.get("kind")

    if prior_heart_days > 0 and old_emoji == "❤️":
        stat_value = str(prior_heart_days)
        stat_label = "dias de ❤️"
    elif prior_same_days > 0 and old_emoji:
        stat_value = str(prior_same_days)
        stat_label = f"dias de {old_emoji}"
    else:
        stat_value = new_emoji or "1"
        stat_label = "emoji"

    chips = []
    if other_side_kept_heart:
        chips.append({"text": f"{receiver} manteve ❤️", "tone": "accent"})

    if kind == "breaks":
        title = "Ruptura com ❤️ ainda do outro lado" if other_side_kept_heart else "Fim de uma sequência de ❤️"
        kicker = "Aliança rompida"
        if prior_heart_days > 0:
            body = (
                f"{giver} vinha de {_format_day_count(prior_heart_days)} seguidos de ❤️ para {receiver} "
                f"e mudou para {new_emoji}."
            )
        else:
            body = f"{giver} trocou ❤️ por {new_emoji} contra {receiver}."
        if other_side_kept_heart:
            body += f" {receiver} ainda manteve ❤️."
    elif kind == "hostilities":
        title = "Hostilidade com ❤️ ainda do outro lado" if other_side_kept_heart else "Nova hostilidade no queridômetro"
        kicker = "Nova hostilidade"
        if prior_heart_days > 0:
            body = (
                f"{giver} vinha de {_format_day_count(prior_heart_days)} seguidos de ❤️ para {receiver} "
                f"e virou para {new_emoji}."
            )
        else:
            body = f"{giver} trocou {old_emoji} por {new_emoji} contra {receiver}."
        if other_side_kept_heart:
            body += f" {receiver} ainda manteve ❤️."
    else:
        title = "Mudança forte de emoji"
        kicker = "Mudança dramática"
        if prior_heart_days > 0:
            body = (
                f"{giver} vinha de {_format_day_count(prior_heart_days)} seguidos de ❤️ para {receiver} "
                f"e virou para {new_emoji}."
            )
        elif prior_same_days > 0:
            body = (
                f"{giver} ficou {_format_day_count(prior_same_days)} com {old_emoji} para {receiver} "
                f"antes de mudar para {new_emoji}."
            )
        else:
            body = f"{giver} trocou {old_emoji} por {new_emoji} contra {receiver}."

    return {
        "kicker": kicker,
        "title": title,
        "body": body,
        "stat_value": stat_value,
        "stat_label": stat_label,
        "chips": chips,
    }


def _build_viradas_summary_note(kind: str, items: list[dict[str, Any]]) -> str:
    if not items:
        return "sem casos"
    if kind == "dramatic":
        max_days = max(
            max(int(item.get("prior_heart_days") or 0), int(item.get("prior_same_emoji_days") or 0))
            for item in items
        )
        return f"máx {max_days} dias antes da troca" if max_days > 0 else "trocas fortes no topo"
    if kind == "hostilities":
        kept = sum(1 for item in items if item.get("other_side_kept_heart"))
        return f"{kept} com ❤️ do outro lado" if kept > 0 else "sem ❤️ do outro lado"
    max_heart_days = max(int(item.get("prior_heart_days") or 0) for item in items)
    return f"máx {max_heart_days} dias de ❤️" if max_heart_days > 0 else "rompimentos recentes"


def _build_viradas_card(
    *,
    daily_snapshots: list[dict],
    daily_matrices: list[dict[tuple[str, str], str]],
    yesterday_idx: int,
    today_idx: int,
    latest_snapshot_date: str,
) -> dict[str, Any] | None:
    if today_idx <= 0 or today_idx >= len(daily_snapshots) or yesterday_idx < 0:
        return None

    today = daily_snapshots[today_idx]
    yesterday = daily_snapshots[yesterday_idx]
    today_mat = daily_matrices[today_idx]
    yesterday_mat = daily_matrices[yesterday_idx]
    common_pairs = today_mat.keys() & yesterday_mat.keys()

    grouped_items: dict[str, list[dict[str, Any]]] = {
        "dramatic": [],
        "hostilities": [],
        "breaks": [],
    }

    for giver, receiver in sorted(common_pairs):
        old_label = _canonical_reaction_label(yesterday_mat.get((giver, receiver), ""))
        new_label = _canonical_reaction_label(today_mat.get((giver, receiver), ""))
        if old_label == new_label:
            continue

        old_weight = SENTIMENT_WEIGHTS.get(old_label, 0)
        new_weight = SENTIMENT_WEIGHTS.get(new_label, 0)
        severity_score = abs(new_weight - old_weight)
        prior_same_days = _count_pair_streak_days((giver, receiver), old_label, daily_matrices, end_idx=yesterday_idx)
        prior_heart_days = _count_pair_streak_days((giver, receiver), old_label, daily_matrices, end_idx=yesterday_idx) if old_label in POSITIVE else 0

        other_side_label_raw = today_mat.get((receiver, giver))
        other_side_label = _canonical_reaction_label(other_side_label_raw) if other_side_label_raw is not None else None
        other_side_emoji = _reaction_display_emoji(other_side_label) if other_side_label else None
        other_side_kept_heart = None
        if other_side_label is not None:
            other_side_kept_heart = _is_positive_heart_reaction(other_side_label)

        base_item = {
            "date": today.get("date", ""),
            "giver": giver,
            "receiver": receiver,
            "old_emoji": _reaction_display_emoji(old_label),
            "new_emoji": _reaction_display_emoji(new_label),
            "prior_same_emoji_days": prior_same_days,
            "prior_heart_days": prior_heart_days,
            "other_side_current_emoji": other_side_emoji,
            "other_side_kept_heart": other_side_kept_heart,
        }

        is_dramatic = (
            (old_label in POSITIVE and new_label in STRONG_NEGATIVE)
            or (old_label in STRONG_NEGATIVE and new_label in POSITIVE)
            or (old_label in POSITIVE and new_label in MILD_NEGATIVE)
            or (old_label in MILD_NEGATIVE and new_label in POSITIVE)
        )
        if is_dramatic:
            dramatic_item = dict(base_item)
            dramatic_item.update({
                "kind": "dramatic",
                "severity_score": severity_score,
                "severity_label": "alta" if severity_score >= 1.5 else ("média" if severity_score >= 1.0 else "leve"),
            })
            dramatic_item["meta_line"] = _viradas_meta_line(dramatic_item)
            grouped_items["dramatic"].append(dramatic_item)

        is_hostility = old_label in POSITIVE and new_label not in POSITIVE and new_label != "" and other_side_kept_heart is True
        if is_hostility:
            hostility_item = dict(base_item)
            hostility_item.update({
                "kind": "hostilities",
                "severity_score": 2.0 if old_label == "Coração" else 1.0,
                "severity_label": "hostilidade",
            })
            hostility_item["meta_line"] = _viradas_meta_line(hostility_item)
            grouped_items["hostilities"].append(hostility_item)

        is_break = old_label in POSITIVE and new_label in (MILD_NEGATIVE | STRONG_NEGATIVE) and prior_heart_days >= 5
        if is_break:
            break_item = dict(base_item)
            break_item.update({
                "kind": "breaks",
                "severity_score": 2.0 if new_label in STRONG_NEGATIVE else 1.0,
                "severity_label": "grave" if new_label in STRONG_NEGATIVE else "leve",
            })
            break_item["meta_line"] = _viradas_meta_line(break_item)
            grouped_items["breaks"].append(break_item)

    counts = {kind: len(items) for kind, items in grouped_items.items()}
    total = counts["dramatic"] + counts["hostilities"] + counts["breaks"]
    if total <= 0:
        return None

    for kind in ("dramatic", "hostilities", "breaks"):
        grouped_items[kind].sort(key=lambda item, k=kind: _viradas_group_sort_key(k, item))

    partitions: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for kind in ("dramatic", "hostilities", "breaks"):
        for item in grouped_items[kind]:
            key = (
                item.get("date", ""),
                item.get("giver", ""),
                item.get("receiver", ""),
                item.get("old_emoji", ""),
                item.get("new_emoji", ""),
            )
            partitions[key].append(item)

    hero_candidates = []
    for dup_items in partitions.values():
        best_tier = min(_viradas_item_tier(item) for item in dup_items)
        tier_items = [item for item in dup_items if _viradas_item_tier(item) == best_tier]
        tier_items.sort(key=lambda item: (_viradas_partition_precedence(item), item.get("kind", "")))
        hero_candidates.append(tier_items[0])

    hero_candidates.sort(key=_viradas_candidate_sort_key)
    hero = dict(hero_candidates[0])
    hero.update(_build_viradas_hero_fields(hero))

    titles = {
        "dramatic": "Mudanças Dramáticas",
        "hostilities": "Novas Hostilidades",
        "breaks": "Alianças Rompidas",
    }
    summary = [
        {
            "kind": kind,
            "title": titles[kind],
            "count": counts[kind],
            "note": _build_viradas_summary_note(kind, grouped_items[kind]),
        }
        for kind in ("dramatic", "hostilities", "breaks")
    ]
    groups = [
        {
            "kind": kind,
            "title": titles[kind],
            "count": counts[kind],
            "items": grouped_items[kind],
        }
        for kind in ("dramatic", "hostilities", "breaks")
    ]

    return {
        "type": "viradas",
        "icon": "🔄",
        "title": "Viradas",
        "color": "#e74c3c",
        "link": "evolucao.html#pulso",
        "source_tag": _comparison_source_tag(yesterday.get("date", ""), today.get("date", ""), latest_snapshot_date),
        "subtitle": "As principais viradas de um dia para o outro no queridômetro.",
        "from_date": yesterday.get("date", ""),
        "to_date": today.get("date", ""),
        "reference_date": today.get("date", ""),
        "state": "today" if all(counts.values()) else "partial",
        "total": total,
        "counts": counts,
        "hero": hero,
        "summary": summary,
        "groups": groups,
    }


def _lookup_cycle_entry(manual_events: dict | None, cycle: int) -> dict[str, Any] | None:
    if cycle <= 0:
        return None
    entries = _iter_cycle_entries(manual_events)
    if not entries:
        return None

    explicit = [item for item in entries if _get_event_cycle(item)]
    if explicit:
        return next((item for item in explicit if _get_event_cycle(item) == cycle), None)

    idx = cycle - 1
    if 0 <= idx < len(entries):
        return entries[idx]
    return None


def _relative_event_chip(target_date: date | None, event_date_str: str | None, label: str) -> str:
    event_date = _parse_iso_date(event_date_str)
    if not target_date or not event_date:
        return ""
    delta = (target_date - event_date).days
    if delta == 0:
        return f"Dia de {label}"
    if delta == -1:
        return f"Pré-{label}"
    if delta == 1:
        return f"Pós-{label}"
    return ""


def _pulso_event_chip(item: dict[str, Any]) -> str:
    if not isinstance(item, dict):
        return ""
    if item.get("name"):
        return str(item["name"])
    if item.get("title"):
        return str(item["title"])
    source = item.get("source")
    if isinstance(source, str) and source and source not in {"api_roles", "api"}:
        return source

    label_map = {
        "lider": "Prova do Líder",
        "anjo": "Prova do Anjo",
        "monstro": "Monstro",
        "big_fone": "Big Fone",
        "dinamica": "Dinâmica",
        "entrada_novos": "Entrada de participantes",
        "contragolpe": "Contragolpe",
        "indicacao": "Indicação direta",
        "bate_volta": "Bate e Volta",
        "lider_classificatoria": "Classificatórias do Líder",
    }
    key = item.get("type") or item.get("category")
    return label_map.get(str(key), "")


def _build_pulso_context(
    date_str: str,
    *,
    manual_events: dict | None,
    auto_events: dict | None,
    paredoes: dict | None,
) -> dict[str, Any]:
    cycle = get_cycle_number(date_str)
    target_date = _parse_iso_date(date_str)
    paredoes_list = (paredoes or {}).get("paredoes", [])
    paredao = None
    for item in paredoes_list:
        cyc = _get_event_cycle(item, fallback=item.get("cycle", 0) or 0)
        if cyc == cycle:
            paredao = item
            break
    if not paredao:
        for item in paredoes_list:
            if item.get("data_formacao") == date_str or item.get("data") == date_str:
                paredao = item
                break
    if not paredao and target_date:
        ranked_candidates: list[tuple[int, int, dict[str, Any]]] = []
        for item in paredoes_list:
            formation_date = _parse_iso_date(item.get("data_formacao"))
            elimination_date = _parse_iso_date(item.get("data"))
            if formation_date and target_date <= formation_date:
                ranked_candidates.append(((formation_date - target_date).days, 0, item))
            elif elimination_date and target_date <= elimination_date:
                ranked_candidates.append(((elimination_date - target_date).days, 1, item))
        if ranked_candidates:
            ranked_candidates.sort(key=lambda row: (row[0], row[1], row[2].get("numero", 0)))
            paredao = ranked_candidates[0][2]
            cycle = _get_event_cycle(paredao, fallback=paredao.get("cycle", cycle) or cycle)

    numero = (paredao or {}).get("numero") or cycle
    moment = f"Ciclo do {numero}º Paredão" if numero else "Arquivo do queridômetro"
    if paredao:
        formation_date = _parse_iso_date(paredao.get("data_formacao"))
        elimination_date = _parse_iso_date(paredao.get("data"))
        if target_date and formation_date and target_date == formation_date:
            moment = f"Formação do {numero}º Paredão"
        elif target_date and elimination_date and target_date == elimination_date:
            moment = f"Eliminação do {numero}º Paredão"
        elif target_date and formation_date and elimination_date and formation_date < target_date < elimination_date:
            moment = f"{numero}º Paredão em aberto"

    chips: list[str] = []
    leader_name = ((paredao or {}).get("formacao") or {}).get("lider")
    if leader_name:
        chips.append(f"Líder: {leader_name}")

    cycle_entry = _lookup_cycle_entry(manual_events, cycle)
    if cycle_entry:
        notes_token = _normalize_text_token(str(cycle_entry.get("notes", "")))
        if "modo turbo" in notes_token:
            chips.append("Modo turbo")
        elif "top 10" in notes_token:
            chips.append("Top 10")

        sincerao = cycle_entry.get("sincerao")
        if isinstance(sincerao, dict):
            chip = _relative_event_chip(target_date, sincerao.get("date"), "Sincerão")
            if chip:
                chips.append(chip)

        big_fone = cycle_entry.get("big_fone")
        if isinstance(big_fone, dict):
            chip = _relative_event_chip(target_date, big_fone.get("date"), "Big Fone")
            if chip:
                chips.append(chip)
        elif isinstance(big_fone, list):
            for event in big_fone:
                chip = _relative_event_chip(target_date, event.get("date"), "Big Fone")
                if chip:
                    chips.append(chip)
                    break

        anjo = cycle_entry.get("anjo")
        if isinstance(anjo, dict):
            chip = _relative_event_chip(target_date, anjo.get("prova_date"), "Prova do Anjo")
            if chip:
                chips.append(chip)

    event_sources: list[dict[str, Any]] = []
    if isinstance(auto_events, dict):
        event_sources.extend(item for item in auto_events.get("events", []) if item.get("date") == date_str)
    if isinstance(manual_events, dict):
        for key in ("special_events", "scheduled_events", "power_events"):
            event_sources.extend(item for item in manual_events.get(key, []) if item.get("date") == date_str)
    for event in event_sources:
        chip = _pulso_event_chip(event)
        if chip:
            chips.append(chip)

    return {
        "date": date_str,
        "date_label": _format_short_date(date_str),
        "cycle": cycle,
        "moment": moment,
        "chips": _dedupe_keep_order(chips)[:4],
    }


def _build_pulso_participants(names: list[str], active_set: set[str]) -> list[dict[str, str]]:
    participants: list[dict[str, str]] = []
    seen: set[str] = set()
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        participants.append({
            "name": name,
            "status": "active" if name in active_set else "eliminated",
        })
    return participants


def _reaction_glyph(label: str) -> str:
    return REACTION_EMOJI.get(label, label or "❓")


def _apply_pulso_fact_override(
    fact: dict[str, Any],
    *,
    kind: str,
    date_str: str,
    active_set: set[str],
) -> dict[str, Any]:
    override = PULSO_MANUAL_FACT_OVERRIDES.get((kind, date_str))
    if not override:
        return fact

    match = override.get("match") or {}
    for field, expected in match.items():
        if fact.get(field) != expected:
            return fact

    updated = dict(fact)
    for field in ("title", "summary", "support", "value", "value_label"):
        if field in override:
            updated[field] = override[field]

    if "context" in override:
        context = dict(updated.get("context") or {})
        context.update(override["context"])
        updated["context"] = context

    if "participants" in override:
        updated["participants"] = _build_pulso_participants(list(override["participants"]), active_set)

    return updated


def _season_percentile(rows: list[dict[str, Any]], key: str, quantile: float) -> float:
    values = sorted(float(item.get(key, 0) or 0) for item in rows)
    if not values:
        return 0.0
    idx = min(len(values) - 1, max(0, int((len(values) - 1) * quantile)))
    return values[idx]


def _build_history_fact(
    *,
    kind: str,
    title: str,
    value: str,
    value_label: str,
    support: str,
    summary: str,
    date_str: str,
    participants: list[str],
    active_set: set[str],
    manual_events: dict | None,
    auto_events: dict | None,
    paredoes: dict | None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "scope": "history",
        "date": date_str,
        "date_label": _format_short_date(date_str),
        "title": title,
        "value": value,
        "value_label": value_label,
        "support": support,
        "summary": summary,
        "context": _build_pulso_context(
            date_str,
            manual_events=manual_events,
            auto_events=auto_events,
            paredoes=paredoes,
        ),
        "participants": _build_pulso_participants(participants, active_set),
    }


def _build_today_pulso_chips(current: dict[str, Any]) -> list[str]:
    chips: list[str] = []
    dramatic_count = int(current.get("dramatic_count") or 0)
    if dramatic_count > 0:
        chips.append(f"{dramatic_count} dramáticas")

    streak_breaks = current.get("new_streak_breaks") or []
    if streak_breaks:
        max_streak = max(int(item.get("previous_streak") or 0) for item in streak_breaks)
        chips.append(f"{len(streak_breaks)} quebras longas (máx {max_streak} dias)")

    mutual_hostilities = current.get("new_mutual_hostilities") or []
    if mutual_hostilities:
        chips.append(f"{len(mutual_hostilities)} hostilidades novas")

    top_receiver = current.get("top_receiver") or {}
    if top_receiver.get("name") and float(top_receiver.get("delta") or 0) > 0:
        chips.append(f"{top_receiver['name'].split()[0]} {float(top_receiver['delta']):+.1f}")

    top_loser = current.get("top_loser") or {}
    if top_loser.get("name") and float(top_loser.get("delta") or 0) < 0:
        chips.append(f"{top_loser['name'].split()[0]} {float(top_loser['delta']):+.1f}")

    volatile = current.get("top_volatile_giver") or {}
    if volatile.get("name") and int(volatile.get("changes") or 0) > 0:
        chips.append(f"{volatile['name'].split()[0]} {int(volatile['changes'])} trocas")

    return _dedupe_keep_order(chips)[:5]


def _build_pulso_history_facts(
    history: list[dict[str, Any]],
    *,
    active_set: set[str],
    manual_events: dict | None,
    auto_events: dict | None,
    paredoes: dict | None,
) -> list[dict[str, Any]]:
    if not history:
        return []

    facts: list[dict[str, Any]] = []

    chaos_day = max(history, key=lambda item: (int(item.get("total_changes") or 0), int(item.get("dramatic_count") or 0)))
    chaos_receiver = (chaos_day.get("top_receiver") or {}).get("name", "")
    chaos_loser = (chaos_day.get("top_loser") or {}).get("name", "")
    chaos_volatile = (chaos_day.get("top_volatile_giver") or {}).get("name", "")
    chaos_fact = _build_history_fact(
        kind="chaos_day",
        title="Maior caos da temporada",
        value=str(int(chaos_day.get("total_changes") or 0)),
        value_label="reações mudaram",
        support=f"{int(chaos_day.get('dramatic_count') or 0)} dramáticas",
        summary=(
            (
                f"{int(chaos_day.get('hearts_lost') or 0)} ❤️ viraram outra reação; "
                f"{chaos_loser.split()[0]} levou o maior tombo {float((chaos_day.get('top_loser') or {}).get('delta') or 0):+.1f}."
            )
            if chaos_loser and int(chaos_day.get("hearts_lost") or 0) > 0
            else (
                f"Maior tombo entre esse dia e o anterior: {chaos_loser.split()[0]} "
                f"{float((chaos_day.get('top_loser') or {}).get('delta') or 0):+.1f}."
                if chaos_loser else "Comparação diária mais instável do queridômetro."
            )
        ),
        date_str=chaos_day.get("date", ""),
        participants=[chaos_loser, chaos_receiver, chaos_volatile],
        active_set=active_set,
        manual_events=manual_events,
        auto_events=auto_events,
        paredoes=paredoes,
    )
    facts.append(_apply_pulso_fact_override(
        chaos_fact,
        kind="chaos_day",
        date_str=chaos_day.get("date", ""),
        active_set=active_set,
    ))

    gain_row = max(history, key=lambda item: float((item.get("top_receiver") or {}).get("delta") or 0))
    gain_target = (gain_row.get("top_receiver") or {}).get("name", "")
    gain_value = float((gain_row.get("top_receiver") or {}).get("delta") or 0)
    if gain_target and gain_value > 0:
        gain_fact = _build_history_fact(
            kind="receiver_gain",
            title="Maior alta de um dia para o outro",
            value=f"{gain_value:+.1f}",
            value_label="saldo recebido",
            support=gain_target,
            summary=f"{gain_target.split()[0]} teve o melhor salto entre esse dia e o anterior.",
            date_str=gain_row.get("date", ""),
            participants=[gain_target],
            active_set=active_set,
            manual_events=manual_events,
            auto_events=auto_events,
            paredoes=paredoes,
        )
        facts.append(_apply_pulso_fact_override(
            gain_fact,
            kind="receiver_gain",
            date_str=gain_row.get("date", ""),
            active_set=active_set,
        ))

    loss_row = min(history, key=lambda item: float((item.get("top_loser") or {}).get("delta") or 0))
    loss_target = (loss_row.get("top_loser") or {}).get("name", "")
    loss_value = float((loss_row.get("top_loser") or {}).get("delta") or 0)
    if loss_target and loss_value < 0:
        loss_fact = _build_history_fact(
            kind="receiver_loss",
            title="Maior tombo de um dia para o outro",
            value=f"{loss_value:+.1f}",
            value_label="saldo recebido",
            support=loss_target,
            summary=f"{loss_target.split()[0]} sofreu o pior tombo entre esse dia e o anterior.",
            date_str=loss_row.get("date", ""),
            participants=[loss_target],
            active_set=active_set,
            manual_events=manual_events,
            auto_events=auto_events,
            paredoes=paredoes,
        )
        facts.append(_apply_pulso_fact_override(
            loss_fact,
            kind="receiver_loss",
            date_str=loss_row.get("date", ""),
            active_set=active_set,
        ))

    volatility_row = max(history, key=lambda item: int((item.get("top_volatile_giver") or {}).get("changes") or 0))
    volatile_name = (volatility_row.get("top_volatile_giver") or {}).get("name", "")
    volatile_changes = int((volatility_row.get("top_volatile_giver") or {}).get("changes") or 0)
    if volatile_name and volatile_changes > 0:
        volatile_fact = _build_history_fact(
            kind="volatile_giver",
            title="Quem mais trocou reações de um dia para o outro",
            value=str(volatile_changes),
            value_label="trocas feitas",
            support=volatile_name,
            summary=(
                f"Entre esse dia e o anterior, {volatile_name.split()[0]} foi quem mais trocou reações: "
                f"{volatile_changes} mudanças na comparação diária."
            ),
            date_str=volatility_row.get("date", ""),
            participants=[volatile_name],
            active_set=active_set,
            manual_events=manual_events,
            auto_events=auto_events,
            paredoes=paredoes,
        )
        facts.append(_apply_pulso_fact_override(
            volatile_fact,
            kind="volatile_giver",
            date_str=volatility_row.get("date", ""),
            active_set=active_set,
        ))

    streak_candidates: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for row in history:
        for item in row.get("new_streak_breaks") or []:
            streak_candidates.append((row, item))
    if streak_candidates:
        streak_row, streak_item = max(
            streak_candidates,
            key=lambda pair: int(pair[1].get("previous_streak") or 0),
        )
        giver = streak_item.get("giver", "")
        receiver = streak_item.get("receiver", "")
        previous_streak = int(streak_item.get("previous_streak") or 0)
        new_emoji = streak_item.get("new_emoji", "")
        new_glyph = _reaction_glyph(new_emoji)
        streak_fact = _build_history_fact(
            kind="streak_break",
            title="Maior sequência de ❤️ quebrada",
            value=str(previous_streak),
            value_label="dias seguidos de ❤️",
            support=f"{giver.split()[0]} → {receiver.split()[0]}",
            summary=(
                f"{giver.split()[0]} passou {previous_streak} dias seguidos dando ❤️ para "
                f"{receiver.split()[0]} e, nessa virada, trocou para {new_glyph}."
            ),
            date_str=streak_row.get("date", ""),
            participants=[giver, receiver],
            active_set=active_set,
            manual_events=manual_events,
            auto_events=auto_events,
            paredoes=paredoes,
        )
        facts.append(_apply_pulso_fact_override(
            streak_fact,
            kind="streak_break",
            date_str=streak_row.get("date", ""),
            active_set=active_set,
        ))

    return facts


def _build_today_snapshot_fact(
    current: dict[str, Any],
    *,
    active_set: set[str],
    manual_events: dict | None,
    auto_events: dict | None,
    paredoes: dict | None,
) -> dict[str, Any]:
    top_receiver = current.get("top_receiver") or {}
    top_loser = current.get("top_loser") or {}
    volatile = current.get("top_volatile_giver") or {}
    total = int(current.get("total") or current.get("total_changes") or 0)
    dramatic_count = int(current.get("dramatic_count") or 0)
    pct = int(round(float(current.get("pct") or current.get("pct_changed") or 0)))
    ref_date = current.get("to_date") or current.get("reference_date") or current.get("date") or ""

    summary = f"{dramatic_count} dramáticas e {pct}% do elenco trocando reação."
    if top_loser.get("name") and float(top_loser.get("delta") or 0) < 0:
        summary = f"Maior tombo da última comparação: {top_loser['name'].split()[0]} {float(top_loser['delta']):+.1f}."
    else:
        summary = f"{dramatic_count} trocas dramáticas e {pct}% do elenco mudando reação de um dia para o outro."

    return {
        "kind": "today_snapshot",
        "scope": "today",
        "date": ref_date,
        "date_label": _format_short_date(ref_date),
        "title": "A última comparação fugiu do padrão",
        "value": str(total),
        "value_label": "reações mudaram",
        "support": f"{dramatic_count} dramáticas · {pct}%",
        "summary": summary,
        "context": _build_pulso_context(
            ref_date,
            manual_events=manual_events,
            auto_events=auto_events,
            paredoes=paredoes,
        ),
        "participants": _build_pulso_participants(
            [top_receiver.get("name", ""), top_loser.get("name", ""), volatile.get("name", "")],
            active_set,
        ),
    }


def _build_pulso_changes_card(
    current: dict[str, Any],
    history: list[dict[str, Any]],
    *,
    active_set: set[str],
    current_cycle: int,
    latest_date: str,
    manual_events: dict | None = None,
    auto_events: dict | None = None,
    paredoes: dict | None = None,
) -> dict[str, Any]:
    history_rows = [row for row in history if isinstance(row, dict) and row.get("date")]
    history_facts = _build_pulso_history_facts(
        history_rows,
        active_set=active_set,
        manual_events=manual_events,
        auto_events=auto_events,
        paredoes=paredoes,
    )

    total_p90 = _season_percentile(history_rows, "total_changes", 0.9)
    pct_p90 = _season_percentile(history_rows, "pct_changed", 0.9)
    dramatic_p90 = _season_percentile(history_rows, "dramatic_count", 0.9)

    current_total = float(current.get("total") or current.get("total_changes") or 0)
    current_pct = float(current.get("pct") or current.get("pct_changed") or 0)
    current_dramatic = float(current.get("dramatic_count") or 0)
    hot_day = bool(history_rows) and (
        current_total >= total_p90 or
        current_pct >= pct_p90 or
        current_dramatic >= dramatic_p90
    )

    ordered_facts = history_facts[:]
    if ordered_facts:
        rotate_date = _parse_iso_date(latest_date) or _parse_iso_date(current.get("to_date") or current.get("reference_date") or "")
        rotate_idx = rotate_date.toordinal() % len(ordered_facts) if rotate_date else 0
        ordered_facts = ordered_facts[rotate_idx:] + ordered_facts[:rotate_idx]

    hero = _build_today_snapshot_fact(
        current,
        active_set=active_set,
        manual_events=manual_events,
        auto_events=auto_events,
        paredoes=paredoes,
    )
    if not hot_day and ordered_facts:
        chaos_hero = next((fact for fact in ordered_facts if fact.get("kind") == "chaos_day"), ordered_facts[0])
        ordered_facts = [chaos_hero] + [fact for fact in ordered_facts if fact is not chaos_hero]
        hero = ordered_facts[0]

    today = {
        "date": current.get("to_date") or current.get("reference_date") or current.get("date") or latest_date,
        "date_label": _format_short_date(current.get("to_date") or current.get("reference_date") or current.get("date") or latest_date),
        "total": int(current_total),
        "pct": int(round(current_pct)),
        "improve": int(current.get("improve") or current.get("n_melhora") or 0),
        "worsen": int(current.get("worsen") or current.get("n_piora") or 0),
        "lateral": int(current.get("lateral") or current.get("n_lateral") or 0),
        "net": int(current.get("net") or ((current.get("improve") or current.get("n_melhora") or 0) - (current.get("worsen") or current.get("n_piora") or 0))),
        "hearts_gained": int(current.get("hearts_gained") or 0),
        "hearts_lost": int(current.get("hearts_lost") or 0),
        "chips": _build_today_pulso_chips(current),
    }

    history_count = len(ordered_facts)
    subtitle = (
        (
            f"{history_count} curiosidades do queridômetro alimentam o arquivo. "
            "A última comparação só sobe quando foge do padrão."
        )
        if not hot_day else
        (
            "A última comparação ficou acima da curva histórica. "
            f"O arquivo segue com {history_count} curiosidades rotativas."
        )
    )

    return {
        "type": "changes",
        "icon": "📊",
        "title": "Arquivo do Queridômetro",
        "color": "#3498db",
        "link": "evolucao.html#pulso",
        "mode": "today" if hot_day else "history",
        "source_tag": "📚 Arquivo + última comparação" if not hot_day else "📅 Última comparação",
        "subtitle": subtitle,
        "hero": hero,
        "facts": ordered_facts,
        "today": today,
        "history_count": history_count,
        "current_cycle": current_cycle,
        "reference_date": current.get("reference_date") or current.get("date") or latest_date,
        "from_date": current.get("from_date"),
        "to_date": current.get("to_date") or current.get("reference_date") or current.get("date") or latest_date,
        "total": int(current_total),
        "pct": int(round(current_pct)),
        "total_possible": int(current.get("total_possible") or 0),
        "improve": today["improve"],
        "worsen": today["worsen"],
        "lateral": today["lateral"],
        "net": today["net"],
        "hearts_gained": today["hearts_gained"],
        "hearts_lost": today["hearts_lost"],
        "dramatic_count": int(current.get("dramatic_count") or 0),
        "top_receiver": current.get("top_receiver") or {},
        "top_loser": current.get("top_loser") or {},
        "top_volatile_giver": current.get("top_volatile_giver") or {},
    }


def _compute_daily_movers_cards(
    daily_snapshots: list[dict],
    daily_matrices: list[dict],
    active_names: list[str],
    *,
    active_set: set[str] | None = None,
    current_cycle: int = 0,
    latest_date: str = "",
    manual_events: dict | None = None,
    auto_events: dict | None = None,
    paredoes: dict | None = None,
    daily_changes_history: list[dict[str, Any]] | None = None,
) -> tuple[list[str], list[dict]]:
    """Ranking leader, podium, movers, reaction changes, dramatic changes, hostilities.

    Returns (highlights, cards) lists for the daily comparison section.
    """
    highlights = []
    cards = []
    active_set = active_set or set(active_names)

    if len(daily_snapshots) < 2:
        return highlights, cards

    n_days = min(len(daily_snapshots), len(daily_matrices))
    if n_days < 2:
        return highlights, cards

    def _expected_pairs_for_snapshot(snapshot: dict) -> int:
        participants = snapshot.get("participants", [])
        if isinstance(participants, list):
            n_active = len(
                [p for p in participants if not p.get("characteristics", {}).get("eliminated")]
            )
            if n_active <= 0:
                n_active = len(active_names)
        else:
            n_active = len(active_names)
        return max(0, n_active * (n_active - 1))

    complete_indices = []
    for i in range(n_days):
        expected_pairs = _expected_pairs_for_snapshot(daily_snapshots[i])
        if expected_pairs == 0 or len(daily_matrices[i]) >= expected_pairs:
            complete_indices.append(i)

    comparable_indices = complete_indices if len(complete_indices) >= 2 else list(range(n_days))
    today_idx = comparable_indices[-1]
    yesterday_idx = comparable_indices[-2]

    today = daily_snapshots[today_idx]
    yesterday = daily_snapshots[yesterday_idx]
    today_mat = daily_matrices[today_idx]
    yesterday_mat = daily_matrices[yesterday_idx]

    today_active = [p for p in today["participants"]
                    if not p.get("characteristics", {}).get("eliminated")]
    sentiment_today = {p["name"]: calc_sentiment(p) for p in today_active}
    yesterday_active = [p for p in yesterday["participants"]
                        if not p.get("characteristics", {}).get("eliminated")]
    sentiment_yesterday = {p["name"]: calc_sentiment(p) for p in yesterday_active}
    today_participants = {p["name"]: p for p in today_active if p.get("name")}

    def _score_profile(participant: dict) -> dict[str, Any]:
        hearts = 0
        negatives = 0
        impact_parts: list[tuple[float, str]] = []
        for rxn in participant.get("characteristics", {}).get("receivedReactions", []):
            label = _canonical_reaction_label(rxn.get("label"))
            amt_raw = rxn.get("amount", 0)
            try:
                amount = int(amt_raw)
            except Exception:
                continue
            if amount <= 0:
                continue
            if label in POSITIVE:
                hearts += amount
            else:
                negatives += amount
            weight = SENTIMENT_WEIGHTS.get(label, 0)
            impact = round(weight * amount, 1)
            emoji = REACTION_EMOJI.get(label, label or "•")
            impact_parts.append((abs(impact), f"{emoji} {amount}x ({impact:+.1f})"))

        impact_parts.sort(key=lambda x: x[0], reverse=True)
        top_impacts = " · ".join(part for _, part in impact_parts[:3])
        reason = f"Score = soma ponderada de reações recebidas. ❤️ {hearts} | negativas {negatives}."
        if top_impacts:
            reason += f" Maiores impactos: {top_impacts}."
        return {
            "hearts": hearts,
            "negative": negatives,
            "reason": reason,
        }

    score_profiles = {
        name: _score_profile(participant)
        for name, participant in today_participants.items()
    }

    # -- Ranking leader + podium + movers --
    if sentiment_today:
        sentiment_leader = max(sentiment_today, key=sentiment_today.get)
        leader_score = sentiment_today[sentiment_leader]
        streak = 1
        for i in range(len(daily_snapshots) - 2, -1, -1):
            snap = daily_snapshots[i]
            snap_active = [p for p in snap["participants"]
                           if not p.get("characteristics", {}).get("eliminated")]
            if not snap_active:
                break
            snap_sent = {p["name"]: calc_sentiment(p) for p in snap_active}
            if snap_sent and max(snap_sent, key=snap_sent.get) == sentiment_leader:
                streak += 1
            else:
                break

        def _rank_item(name: str, score: float) -> dict[str, Any]:
            profile = score_profiles.get(name, {})
            return {
                "name": name,
                "score": score,
                "hearts": profile.get("hearts", 0),
                "negative": profile.get("negative", 0),
                "reason": profile.get("reason", ""),
            }

        sorted_today = sorted(sentiment_today.items(), key=lambda x: x[1], reverse=True)
        podium_all = [_rank_item(n, s) for n, s in sorted_today]
        bottom_all = [_rank_item(n, s) for n, s in reversed(sorted_today)]
        podium = podium_all[:6]
        bottom3 = bottom_all[:6]

        def _build_delta_items(reference_scores: dict[str, float], reason_prefix: str) -> list[dict[str, Any]]:
            items: list[dict[str, Any]] = []
            for n, today_score in sentiment_today.items():
                if n not in reference_scores:
                    continue
                previous_score = reference_scores[n]
                delta = round(today_score - previous_score, 1)
                if delta == 0:
                    continue
                items.append({
                    "name": n,
                    "delta": delta,
                    "today_score": round(today_score, 1),
                    "yesterday_score": round(previous_score, 1),
                    "reason": (
                        f"{reason_prefix}: score de hoje ({today_score:+.1f}) "
                        f"− score de referência ({previous_score:+.1f}) = {delta:+.1f}."
                    ),
                })
            items.sort(key=lambda x: (abs(x["delta"]), x["delta"]), reverse=True)
            return items

        day_delta_all = _build_delta_items(sentiment_yesterday, "Variação vs ontem")
        week_reference = {}
        if len(daily_snapshots) >= 7:
            week_snapshot = daily_snapshots[-7]
            week_reference = {
                p["name"]: calc_sentiment(p)
                for p in week_snapshot.get("participants", [])
                if not p.get("characteristics", {}).get("eliminated") and p.get("name")
            }
        week_delta_all = _build_delta_items(week_reference, "Variação na semana") if week_reference else []

        delta_all = day_delta_all or week_delta_all
        movers_scope = "day" if day_delta_all else ("week" if week_delta_all else "none")
        movers_label = "📅 Variação vs ontem" if movers_scope == "day" else "📅 Variação na semana"
        movers_up = [item for item in delta_all if item["delta"] > 0.5][:3]
        movers_down = [item for item in delta_all if item["delta"] < -0.5][:3]
        movers_down.sort(key=lambda x: x["delta"])  # most negative first

        cards.append({
            "type": "ranking",
            "icon": "🏆", "title": "Ranking",
            "color": "#f1c40f", "link": "evolucao.html#sentimento",
            "leader": sentiment_leader,
            "leader_score": round(leader_score, 1),
            "streak": streak,
            "podium": podium,
            "bottom3": bottom3,
            "podium_all": podium_all,
            "bottom_all": bottom_all,
            "movers_up": movers_up,
            "movers_down": movers_down,
            "delta_all": delta_all,
            "movers_scope": movers_scope,
            "movers_label": movers_label if delta_all else "",
        })

        streak_text = f" pelo {streak}º dia consecutivo" if streak > 1 else ""
        pod_txt = " · ".join(f"{p['name']} ({p['score']:+.1f})" for p in podium)
        movers_parts = []
        for mu in movers_up:
            movers_parts.append(f"📈 {mu['name']} ({mu['delta']:+.1f})")
        for md in movers_down:
            movers_parts.append(f"📉 {md['name']} ({md['delta']:+.1f})")
        movers_txt = " | " + " · ".join(movers_parts) if movers_parts else ""
        highlights.append(
            f"🏆 **{sentiment_leader}** lidera o [ranking](evolucao.html#sentimento){streak_text} ({leader_score:+.1f})"
            f" — Top 3: {pod_txt}{movers_txt}"
        )

    # -- Reaction changes summary --
    common_pairs = today_mat.keys() & yesterday_mat.keys()
    changes = [(pair, yesterday_mat[pair], today_mat[pair])
               for pair in common_pairs if yesterday_mat[pair] != today_mat[pair]]
    n_changes = len(changes)
    if n_changes > 0:
        total_possible = len(common_pairs)
        pct_changed = round(n_changes / total_possible * 100, 0) if total_possible > 0 else 0

        n_improve = sum(1 for _, old, new in changes
                       if SENTIMENT_WEIGHTS.get(new, 0) > SENTIMENT_WEIGHTS.get(old, 0))
        n_worsen = sum(1 for _, old, new in changes
                      if SENTIMENT_WEIGHTS.get(new, 0) < SENTIMENT_WEIGHTS.get(old, 0))
        n_lateral = n_changes - n_improve - n_worsen

        hearts_gained = sum(1 for _, old, new in changes if new in POSITIVE and old not in POSITIVE)
        hearts_lost = sum(1 for _, old, new in changes if old in POSITIVE and new not in POSITIVE)

        current_change = {
            "total": n_changes,
            "reference_date": today.get("date"),
            "from_date": yesterday.get("date"),
            "to_date": today.get("date"),
            "pct": int(pct_changed),
            "total_possible": total_possible,
            "improve": n_improve,
            "worsen": n_worsen,
            "lateral": n_lateral,
            "net": (n_improve - n_worsen),
            "hearts_gained": hearts_gained,
            "hearts_lost": hearts_lost,
        }
        history_rows = list(daily_changes_history or [])
        matched_row = next((row for row in reversed(history_rows) if row.get("date") == today.get("date")), None)

        pair_changes_local = []
        transition_counts_local: dict[str, int] = defaultdict(int)
        giver_volatility_local: dict[str, dict[str, int]] = {}
        giver_melhora: dict[str, int] = defaultdict(int)
        giver_piora: dict[str, int] = defaultdict(int)
        giver_lateral: dict[str, int] = defaultdict(int)
        giver_changes: dict[str, int] = defaultdict(int)
        new_streak_breaks_local = []

        for pair, old_raw, new_raw in changes:
            giver, receiver = pair
            old_label = _canonical_reaction_label(old_raw)
            new_label = _canonical_reaction_label(new_raw)
            old_weight = SENTIMENT_WEIGHTS.get(old_label, 0)
            new_weight = SENTIMENT_WEIGHTS.get(new_label, 0)
            delta = round(new_weight - old_weight, 2)
            tipo = "Melhora" if delta > 0 else ("Piora" if delta < 0 else "Lateral")

            pair_changes_local.append({
                "giver": giver,
                "receiver": receiver,
                "prev_rxn": old_label,
                "curr_rxn": new_label,
                "delta": delta,
                "tipo": tipo,
            })
            transition_counts_local[f"{old_label}→{new_label}"] += 1
            giver_changes[giver] += 1
            if tipo == "Melhora":
                giver_melhora[giver] += 1
            elif tipo == "Piora":
                giver_piora[giver] += 1
            else:
                giver_lateral[giver] += 1

            prior_heart_days = _count_pair_streak_days(pair, old_label, daily_matrices, end_idx=yesterday_idx) if old_label in POSITIVE else 0
            if old_label in POSITIVE and new_label in (MILD_NEGATIVE | STRONG_NEGATIVE) and prior_heart_days >= 5:
                new_streak_breaks_local.append({
                    "giver": giver,
                    "receiver": receiver,
                    "previous_streak": prior_heart_days,
                    "new_emoji": new_label,
                    "severity": "strong" if new_label in STRONG_NEGATIVE else "mild",
                    "date": today.get("date"),
                })

        for giver, total in giver_changes.items():
            giver_volatility_local[giver] = {
                "total": total,
                "melhora": giver_melhora.get(giver, 0),
                "piora": giver_piora.get(giver, 0),
                "lateral": giver_lateral.get(giver, 0),
            }

        comparison_names = ({p.get("name") for p in today_active if p.get("name")} &
                            {p.get("name") for p in yesterday_active if p.get("name")})
        prev_mutual, _prev_blind = _classify_hostility_pairs(yesterday_mat, comparison_names)
        curr_mutual, _curr_blind = _classify_hostility_pairs(today_mat, comparison_names)
        new_mutual_hostilities_local = []
        for pair in sorted(curr_mutual - prev_mutual, key=lambda p: tuple(sorted(p))):
            a, b = sorted(pair)
            new_mutual_hostilities_local.append({
                "pair": [a, b],
                "reactions": {
                    "a_to_b": today_mat.get((a, b), ""),
                    "b_to_a": today_mat.get((b, a), ""),
                },
            })

        if matched_row:
            current_change.update(matched_row)
        current_change.setdefault("pair_changes", pair_changes_local)
        current_change.setdefault("transition_counts", dict(transition_counts_local))
        current_change.setdefault("giver_volatility", giver_volatility_local)
        current_change.setdefault("new_mutual_hostilities", new_mutual_hostilities_local)
        current_change.setdefault("new_streak_breaks", new_streak_breaks_local)
        pulso_card = _build_pulso_changes_card(
            current_change,
            history_rows or [current_change],
            active_set=active_set,
            current_cycle=current_cycle,
            latest_date=latest_date or today.get("date", ""),
            manual_events=manual_events,
            auto_events=auto_events,
            paredoes=paredoes,
        )

        direction = "🟢 mais melhorias" if n_improve > n_worsen else (
            "🔴 mais pioras" if n_worsen > n_improve else "⚖️ equilibrado")
        hearts_parts = []
        if hearts_gained:
            hearts_parts.append(f"+{hearts_gained} ❤️")
        if hearts_lost:
            hearts_parts.append(f"-{hearts_lost} ❤️")
        hearts_txt = f" ({' / '.join(hearts_parts)})" if hearts_parts else ""
        if pulso_card.get("mode") == "today":
            highlights.append(
                f"📊 **{n_changes} reações** [mudaram](evolucao.html#pulso) ontem ({pct_changed:.0f}% do total)"
                f" — {n_improve} melhorias, {n_worsen} pioras, {n_lateral} laterais"
                f" · {direction}{hearts_txt}"
            )
        else:
            hero = pulso_card.get("hero") or {}
            hero_bits = [hero.get("date_label") or _format_short_date(hero.get("date", ""))]
            if hero.get("value") and hero.get("value_label"):
                hero_bits.append(f"{hero['value']} {hero['value_label']}")
            hero_txt = " · ".join(bit for bit in hero_bits if bit)
            highlights.append(
                f"📊 [Pulso](evolucao.html#pulso): ontem mexeu {n_changes} reações ({pct_changed:.0f}%)"
                f" — arquivo em rotação: {hero_txt}"
            )

    viradas_card = _build_viradas_card(
        daily_snapshots=daily_snapshots,
        daily_matrices=daily_matrices,
        yesterday_idx=yesterday_idx,
        today_idx=today_idx,
        latest_snapshot_date=daily_snapshots[-1].get("date", ""),
    )
    if n_changes > 0:
        cards.append(pulso_card)
    if viradas_card:
        cards.append(viradas_card)
        counts = viradas_card.get("counts", {})
        hero = viradas_card.get("hero") or {}
        highlights.append(
            f"🔄 **{viradas_card.get('total', 0)} viradas** [de um dia para o outro](evolucao.html#pulso): "
            f"{counts.get('dramatic', 0)} dramáticas, "
            f"{counts.get('hostilities', 0)} hostilidades novas, "
            f"{counts.get('breaks', 0)} alianças rompidas"
            f" — destaque: {hero.get('giver', '').split()[0]} → {hero.get('receiver', '').split()[0]} "
            f"({hero.get('old_emoji', '')}→{hero.get('new_emoji', '')})"
        )

    return highlights, cards


def _resolve_sinc_week(sinc_data: dict, current_cycle: int) -> tuple[int, list[int]]:
    """Resolve which Sincerao week should be displayed.

    Rule: keep the current week only if it has Sincerao data; otherwise keep
    the most recent week with Sincerao data.
    """
    edge_weeks = [(e.get("cycle")) for e in sinc_data.get("edges", []) if isinstance((e.get("cycle")), int)] if sinc_data else []
    agg_weeks = [(a.get("cycle")) for a in sinc_data.get("aggregates", []) if a.get("scores")] if sinc_data else []
    agg_weeks = [w for w in agg_weeks if isinstance(w, int)]
    available_weeks = sorted(set(edge_weeks + agg_weeks))

    sinc_week_used = current_cycle
    if available_weeks and sinc_week_used not in available_weeks:
        sinc_week_used = max(available_weeks)
    return sinc_week_used, available_weeks


def _resolve_sinc_reference_date(sinc_data: dict, sinc_week_used: int) -> str | None:
    """Return canonical date for the selected Sincerao week, if available."""
    for w in sinc_data.get("weeks", []) if sinc_data else []:
        if (w.get("cycle")) == sinc_week_used and w.get("date"):
            return w.get("date")
    return None


def _resolve_matrix_for_date(
    target_date: str | None,
    daily_snapshots: list[dict],
    daily_matrices: list[dict],
    fallback_matrix: dict[tuple[str, str], str],
    fallback_date: str | None,
) -> tuple[dict[tuple[str, str], str], str | None]:
    """Pick the closest daily matrix to a target date (prefer <= target)."""
    if not daily_snapshots or not daily_matrices:
        return fallback_matrix, fallback_date

    n = min(len(daily_snapshots), len(daily_matrices))
    if n == 0:
        return fallback_matrix, fallback_date

    snaps = daily_snapshots[:n]
    mats = daily_matrices[:n]

    if not target_date:
        return mats[-1], snaps[-1].get("date")

    for i, snap in enumerate(snaps):
        if snap.get("date") == target_date:
            return mats[i], snap.get("date")

    prev_idx = None
    for i, snap in enumerate(snaps):
        d = snap.get("date")
        if d and d <= target_date:
            prev_idx = i
    if prev_idx is not None:
        return mats[prev_idx], snaps[prev_idx].get("date")

    return mats[0], snaps[0].get("date")


def _compute_sincerao_highlight(
    sinc_data: dict,
    current_cycle: int,
    latest_matrix: dict[tuple[str, str], str],
    active_set: set[str] | None = None,
) -> tuple[list[str], list[dict], list[dict], list[dict], list[dict], int, list[int], dict]:
    """Sincerão x Queridômetro contradictions, alignments, and radar.

    Returns (highlights, cards, pair_contradictions, pair_aligned_pos, pair_aligned_neg,
             sinc_week_used, available_weeks, radar).

    Historical Sincerão data still falls back to the latest available cycle so
    downstream relations/profile views keep working between live shows. The
    index highlight card, however, is only shown when the current cycle itself
    already has Sincerão data.
    """
    highlights = []
    cards = []

    sinc_week_used, available_weeks = _resolve_sinc_week(sinc_data, current_cycle)

    pair_contradictions = []
    pair_aligned_pos = []
    pair_aligned_neg = []
    for edge in sinc_data.get("edges", []) if sinc_data else []:
        if (edge.get("cycle")) != sinc_week_used:
            continue
        etype = edge.get("type")
        if etype not in ["elogio", "nao_ganha", "ataque"]:
            continue
        actor = edge.get("actor")
        target = edge.get("target")
        if not actor or not target:
            continue
        if active_set and (actor not in active_set or target not in active_set):
            continue
        rxn = latest_matrix.get((actor, target), "")
        if not rxn:
            continue
        rxn = _canonical_reaction_label(rxn)
        rxn_weight = SENTIMENT_WEIGHTS.get(rxn, 0)
        rxn_sign = "pos" if rxn_weight > 0 else ("neg" if rxn_weight < 0 else "neu")
        edge_sign = "pos" if etype == "elogio" else "neg"
        tipo_label = SINC_TYPE_META.get(etype, {}).get("label", etype)
        row = {
            "ator": actor, "alvo": target,
            "tipo": etype, "tipo_label": tipo_label,
            "tema": edge.get("tema"), "reacao": rxn,
            "emoji": REACTION_EMOJI.get(rxn, "?"),
        }
        if edge_sign == "neg" and rxn_sign == "pos":
            pair_contradictions.append(row)
        elif edge_sign == "pos" and rxn_sign == "pos":
            pair_aligned_pos.append(row)
        elif edge_sign == "neg" and rxn_sign == "neg":
            pair_aligned_neg.append(row)

    if pair_contradictions:
        lines = [f"{r['ator']}→{r['alvo']} ({r['tipo_label']}, mas dá {r['emoji']})" for r in pair_contradictions[:4]]
        extra = len(pair_contradictions) - 4
        highlights.append(
            f"⚡ **{len(pair_contradictions)} contradição(ões)** Sincerão×Queridômetro: "
            + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
        )
    if pair_aligned_pos:
        sample_txt = ", ".join([f"{r['ator']}→{r['alvo']}" for r in pair_aligned_pos[:3]])
        highlights.append(f"🤝 Alinhamentos positivos Sincerão×Queridômetro: {sample_txt}")

    # Compute radar for the week used
    week_edges_for_radar = [e for e in (sinc_data.get("edges", []) if sinc_data else [])
                            if (e.get("cycle")) == sinc_week_used]
    radar = _compute_sincerao_radar(week_edges_for_radar, sinc_week_used, latest_matrix, active_set=active_set)

    # Get week format name
    sinc_week_format = ""
    for w in sinc_data.get("weeks", []) if sinc_data else []:
        if (w.get("cycle")) == sinc_week_used:
            sinc_week_format = w.get("format", "")
            break

    # Unified Sincerão card: radar + contradictions merged
    show_current_cycle_card = current_cycle in available_weeks
    if show_current_cycle_card and (radar.get("neg_ranked") or radar.get("pos_ranked") or pair_contradictions):
        cards.append({
            "type": "sincerao",
            "icon": "🔥", "title": f"Sincerão S{sinc_week_used}",
            "color": "#e67e22", "link": "relacoes.html#sincerao-contradictions",
            "format": sinc_week_format,
            "radar": radar,
            "contradictions": pair_contradictions,
            "aligned_neg": pair_aligned_neg,
        })

    return (highlights, cards, pair_contradictions, pair_aligned_pos, pair_aligned_neg,
            sinc_week_used, available_weeks, radar)


def _compute_vulnerability_cards(latest: dict, active_names: list[str], active_set: set[str], received_impact: dict, relations_pairs: dict, relations_data: dict | list | None = None, *, latest_date: str | None = None) -> tuple[list[str], list[dict], list[str]]:
    """Mais Alvo, Mais Agressor, vulnerability, and active paredão cards.

    Returns (highlights, cards, paredao_names).
    """
    highlights = []
    cards = []

    # -- Active paredão --
    paredao_names = [p["name"] for p in latest["participants"]
                     if "Paredão" in parse_roles(p.get("characteristics", {}).get("roles", []))]
    if paredao_names:
        cards.append({
            "type": "paredao",
            "icon": "🗳️", "title": "Paredão Ativo",
            "color": "#e74c3c", "link": "paredao.html",
            "nominees": sorted(paredao_names),
        })
        highlights.append(f"🗳️ [**Paredão ativo**](paredao.html): {', '.join(sorted(paredao_names))}")

    # -- Old Mais Alvo (edge-based) removed: replaced by new Mais Alvo (event-based) in _compute_static_cards --
    # -- Mais Agressor — moved to _compute_static_cards (uses raw power_events from ctx) --

    # -- Most vulnerable (false friends) --
    if relations_pairs:
        vuln_items = []
        for name_v in active_names:
            ff_count = 0
            enemies = []
            enemy_details = []
            pairs_me = relations_pairs.get(name_v, {})
            for other in active_names:
                if other == name_v:
                    continue
                my_score = pairs_me.get(other, {}).get("score", 0)
                their_score = relations_pairs.get(other, {}).get(name_v, {}).get("score", 0)
                if my_score > 0 and their_score < 0:
                    ff_count += 1
                    enemies.append(other)
                    enemy_details.append({
                        "name": other,
                        "my_score": round(my_score, 1),
                        "their_score": round(their_score, 1),
                    })
            if ff_count >= 3:
                enemy_preview = " · ".join(
                    f"{d['name'].split()[0]} (você {d['my_score']:+.1f} / ele {d['their_score']:+.1f})"
                    for d in enemy_details[:3]
                )
                reason = (
                    "Vulnerabilidade = pessoas em que você confia (score > 0), "
                    "mas que têm score negativo contra você."
                )
                if enemy_preview:
                    reason += f" Casos principais: {enemy_preview}."
                vuln_items.append({
                    "name": name_v,
                    "count": ff_count,
                    "enemies": enemies[:5],
                    "enemy_details": enemy_details[:5],
                    "level": "critical" if ff_count >= 5 else "warning",
                    "reason": reason,
                })
        vuln_items.sort(key=lambda x: x["count"], reverse=True)
        if vuln_items:
            cards.append({
                "type": "vulnerability",
                "icon": "🔴", "title": "Vulnerabilidade",
                "color": "#e74c3c", "link": "#perfis",
                "total": len(vuln_items),
                "items": vuln_items[:5],
                "items_all": vuln_items,
            })
            lines = []
            for v in vuln_items[:3]:
                level = "🔴 muito vulnerável" if v["level"] == "critical" else "🟠 vulnerável"
                enemies_txt = ", ".join(e.split()[0] for e in v["enemies"][:3])
                lines.append(f"**{v['name']}** ({v['count']} falsos amigos: {enemies_txt}… — {level})")
            extra = len(vuln_items) - 3
            highlights.append(
                f"🔴 [Vulnerabilidade](#perfis): " + " · ".join(lines)
                + (f" (+{extra} mais com 3+)" if extra > 0 else "")
            )

    return highlights, cards, paredao_names


def _compute_breaks_and_context_cards(
    relations_data: dict | list,
    active_set: set[str],
    latest: dict,
    current_cycle: int,
    daily_snapshots: list[dict],
    reference_date: str | None = None,
) -> tuple[list[str], list[dict]]:
    """Streak breaks (alliance ruptures) and week context cards.

    Returns (highlights, cards).
    """
    highlights = []
    cards = []

    # -- Streak breaks (alliance ruptures) --
    streak_breaks_data = relations_data.get("streak_breaks", []) if isinstance(relations_data, dict) else []
    active_breaks = [b for b in streak_breaks_data if b.get("giver") in active_set and b.get("receiver") in active_set]
    if active_breaks:
        strong = [b for b in active_breaks if b.get("severity") == "strong"]
        active_breaks_sorted = sorted(
            active_breaks,
            key=lambda b: (b.get("date", ""), b.get("previous_streak", 0)),
            reverse=True,
        )
        break_items = []
        for b in active_breaks_sorted:
            break_items.append({
                "giver": b["giver"], "receiver": b["receiver"],
                "streak": b.get("previous_streak", 0),
                "new_emoji": REACTION_EMOJI.get(b.get("new_emoji", ""), "❓"),
                "severity": b.get("severity", "mild"),
                "date": b.get("date", ""),
            })
        cards.append({
            "type": "breaks",
            "icon": "💔", "title": "Alianças Rompidas",
            "color": "#8e44ad", "link": "relacoes.html#aliancas",
            "total": len(active_breaks),
            "strong_count": len(strong),
            "reference_date": reference_date or latest.get("date"),
            "display_limit": 4,
            "event_latest_date": break_items[0].get("date", "") if break_items else "",
            "items": break_items,
        })
        lines = [f"{b['giver']} → {b['receiver']} ({b['streak']}d ❤️ → {b['new_emoji']})"
                 + (" 🚨" if b["severity"] == "strong" else "") for b in break_items[:4]]
        extra = len(active_breaks) - 4
        severity_txt = f" — **{len(strong)} graves**" if strong else ""
        highlights.append(
            f"💔 **{len(active_breaks)} aliança(s) rompida(s)** [histórico ativo](relacoes.html#aliancas){severity_txt}: "
            + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
        )

    # -- Week context --
    context_cycle = current_cycle
    n_active = len([p for p in latest["participants"]
                    if not p.get("characteristics", {}).get("eliminated")])
    cards.append({
        "type": "context",
        "icon": "📅", "title": "Contexto",
        "color": "#2ecc71",
        "cycle": context_cycle,
        "days": len(daily_snapshots),
        "active": n_active,
    })
    highlights.append(
        f"📅 **Ciclo do Paredão {context_cycle}** — {len(daily_snapshots)} dias de dados, {n_active} participantes ativos"
    )

    return highlights, cards


def _build_context_card(
    *,
    latest: dict,
    current_cycle: int,
    daily_snapshots: list[dict],
) -> tuple[str, dict[str, Any]]:
    n_active = len([p for p in latest.get("participants", []) if not p.get("characteristics", {}).get("eliminated")])
    return (
        f"📅 **Ciclo do Paredão {current_cycle}** — {len(daily_snapshots)} dias de dados, {n_active} participantes ativos",
        {
            "type": "context",
            "icon": "📅",
            "title": "Contexto",
            "color": "#2ecc71",
            "cycle": current_cycle,
            "days": len(daily_snapshots),
            "active": n_active,
        },
    )


def _build_figurinha_stat_line(stats: dict) -> str:
    """Build one-line stat summary for figurinha_repetida card."""
    metrics = stats.get("metrics", {})
    parts = []
    ft = metrics.get("first_timer", {})
    if ft.get("rate") is not None:
        parts.append(f"{int(ft['rate'] * 100)}% eliminados na 1ª ida")
    bv = metrics.get("bv_losers_eliminated", {})
    if bv.get("rate") is not None and bv.get("total", 0) > 0:
        pct = int(bv["rate"] * 100)
        parts.append(f"Em {pct}% dos casos, o perdedor do BV foi eliminado (exclui falso)")
    return " · ".join(parts) if parts else ""


def _compute_static_cards(ctx: dict[str, Any]) -> tuple[list[str], list[dict], dict]:
    """Mais Blindados + exposure + VIP x Xepa cards (accumulated metrics).

    Returns (highlights, cards, exposure_stats).
    """
    highlights: list[str] = []
    cards: list[dict] = []
    active_set = ctx["active_set"]
    paredoes_data = ctx["paredoes"]
    paredoes_list = paredoes_data.get("paredoes", []) if paredoes_data else []
    participant_windows = build_participant_windows(
        ctx.get("participants_index"),
        active_names=active_set,
        manual_events=ctx.get("manual_events"),
    )
    exposure_by_name = compute_house_vote_exposure(
        paredoes_list,
        participant_windows,
        recent_window=VISADOS_RECENT_WINDOW,
    ) if paredoes_list else {}

    # ── Mais Blindados ──
    # Shared accumulators used by both blindados and Mais Alvo
    on_paredao: Counter[str] = Counter()
    bv_escape_count: Counter[str] = Counter()
    by_lider: Counter[str] = Counter()
    by_casa: Counter[str] = Counter()
    by_dynamic: Counter[str] = Counter()
    n_paredoes = 0
    display_limit = 4

    paredoes_with_votes = [p for p in paredoes_list if p.get("votos_casa")]
    if paredoes_with_votes:
        n_paredoes = len(paredoes_with_votes)
        bv_escape_detail: dict[str, list[int]] = defaultdict(list)  # BV-only paredão nums
        mdp_escape_detail: dict[str, list[int]] = defaultdict(list)  # MdP-only paredão nums
        fake_paredao_detail: dict[str, list[int]] = defaultdict(list)
        protection_detail: dict[str, list[tuple[int, str]]] = defaultdict(list)

        # Classify nomination method from como field
        for par in paredoes_with_votes:
            for ind in par.get("indicados_finais", []):
                nome = ind.get("nome", "") if isinstance(ind, dict) else ind
                como = (ind.get("como", "") if isinstance(ind, dict) else "").lower()
                if not nome or nome not in active_set:
                    continue
                if "líder" in como:
                    by_lider[nome] += 1
                elif "casa" in como or "mais votad" in como:
                    by_casa[nome] += 1
                else:
                    by_dynamic[nome] += 1

        for par in paredoes_with_votes:
            num = par.get("numero", 0)
            form = par.get("formacao", {})
            indicados = {(ind["nome"] if isinstance(ind, dict) else ind)
                         for ind in par.get("indicados_finais", [])}
            protected_names = compute_protected_names(form)
            if par.get("paredao_falso"):
                for indicado in indicados:
                    if indicado in active_set:
                        fake_paredao_detail[indicado].append(num)

            # Reason classification for display (Líder Nx / Imune Nx / Autoimune Nx)
            lider_names_set = set(resolve_leaders(form))
            imun_name = (form.get("imunizado") or {}).get("quem") if isinstance(form.get("imunizado"), dict) else None

            # Bug fix 2: BV escape counting (supports vencedores array)
            bv = form.get("bate_volta", {}) or {}
            bv_winners = bv.get("vencedores") or ([bv["vencedor"]] if bv.get("vencedor") else [])
            for bw in bv_winners:
                if bw and bw not in indicados:
                    bv_escape_count[bw] += 1
                    bv_escape_detail[bw].append(num)

            # Máquina do Poder saves count as escapes (emparedado then saved)
            mdp = form.get("maquina_do_poder", {}) or {}
            mdp_salvou = mdp.get("salvou", "")
            if mdp_salvou and mdp_salvou not in indicados:
                bv_escape_count[mdp_salvou] += 1
                mdp_escape_detail[mdp_salvou].append(num)

            for name in active_set:
                if name in indicados:
                    on_paredao[name] += 1
                if name in protected_names:
                    reason = "Líder" if name in lider_names_set else ("Imune" if name == imun_name else "Autoimune")
                    protection_detail[name].append((num, reason))

        blindados_items_all = []
        for name in active_set:
            n_par = on_paredao.get(name, 0)
            n_bv = bv_escape_count.get(name, 0)
            stats = exposure_by_name.get(name, {})
            n_prot = stats.get("protected", 0)
            n_avail = stats.get("available", 0)
            votes_total = stats.get("votes_total", 0)
            votes_available = stats.get("votes_available", 0)
            voted_paredoes = stats.get("voted_paredoes", 0)

            # Protection breakdown for display
            reason_counts = Counter(r for _, r in protection_detail.get(name, []))
            reason_numbers: dict[str, list[int]] = defaultdict(list)
            for par_num, reason in protection_detail.get(name, []):
                reason_numbers[reason].append(par_num)
            ordered_reasons = [r for r in BLINDADOS_REASON_ORDER if reason_counts.get(r)]
            prot_text = ", ".join(f"{r} {reason_counts[r]}x" for r in ordered_reasons) if ordered_reasons else ""
            protection_tags = [
                {
                    "label": reason,
                    "count": reason_counts[reason],
                    "nums": sorted(reason_numbers[reason]),
                    "text": f"{reason} {reason_counts[reason]}x ({', '.join(f'{n}º' for n in sorted(reason_numbers[reason]))})",
                }
                for reason in ordered_reasons
            ]

            # BV/MdP escape tags (separate tags for each type)
            bv_nums = bv_escape_detail.get(name, [])
            mdp_nums = mdp_escape_detail.get(name, [])
            escape_tags: list[dict] = []
            if bv_nums:
                bv_str = ", ".join(f"{n}º" for n in bv_nums)
                escape_tags.append({
                    "label": "Bate-Volta",
                    "count": len(bv_nums),
                    "nums": list(bv_nums),
                    "text": f"Bate-Volta {len(bv_nums)}x ({bv_str})",
                })
            if mdp_nums:
                mdp_str = ", ".join(f"{n}º" for n in mdp_nums)
                escape_tags.append({
                    "label": "Máq. do Poder",
                    "count": len(mdp_nums),
                    "nums": list(mdp_nums),
                    "text": f"Máq. do Poder {len(mdp_nums)}x ({mdp_str})",
                })
            bv_text = ", ".join(t["text"] for t in escape_tags) if escape_tags else ""

            # Nomination breakdown text
            nom_parts = []
            if by_lider.get(name, 0):
                nom_parts.append(f"Líder {by_lider[name]}x")
            if by_casa.get(name, 0):
                nom_parts.append(f"Casa {by_casa[name]}x")
            if by_dynamic.get(name, 0):
                nom_parts.append(f"Dinâmica {by_dynamic[name]}x")
            nom_text = ", ".join(nom_parts)

            blindados_items_all.append({
                "name": name,
                "paredao": n_par,
                "bv_escapes": n_bv,
                "exposure": n_par + n_bv,
                "protected": n_prot,
                "available": n_avail,
                "votes_total": votes_total,
                "votes_available": votes_available,
                "voted_paredoes": voted_paredoes,
                "by_lider": by_lider.get(name, 0),
                "by_casa": by_casa.get(name, 0),
                "by_dynamic": by_dynamic.get(name, 0),
                "nom_text": nom_text,
                "prot_text": prot_text,
                "protection_tags": protection_tags,
                "escape_tags": escape_tags,
                "bv_text": bv_text,
                "last_voted_paredao": stats.get("last_voted_paredao", 0),
                "total": n_paredoes,
                # Backward compat
                "votes": votes_total,
                "bv_escape": n_bv > 0,
            })
        # Sort: fewer exposure → more protected → fewer votes → name (deterministic)
        blindados_items_all.sort(key=lambda x: (x["exposure"], -x["protected"], x["votes_total"], x["name"]))
        blindados_items = blindados_items_all[:display_limit]

        cards.append({
            "type": "blindados",
            "icon": "\U0001f6e1\ufe0f", "title": "Mais Blindados",
            "color": "#3498db", "link": "paredoes.html",
            "total": len(blindados_items_all),
            "display_limit": display_limit,
            "items": blindados_items,
            "items_all": blindados_items_all,
            "n_paredoes": n_paredoes,
        })

    # ── Mais Alvo (target, per-event from power_events) ──
    power_events = ctx.get("power_events", [])
    participants_index = ctx.get("participants_index", {})
    all_participant_names = [p["name"] for p in participants_index.get("participants", []) if p.get("name")]
    current_cycle = ctx.get("current_cycle", 0)
    recent_week_cutoff = current_cycle - 3

    if power_events and all_participant_names:
        # Mais Alvo: count each power_event as 1 hit on the target
        target_hits: Counter[str] = Counter()
        target_hits_recent: Counter[str] = Counter()
        target_types: dict[str, Counter[str]] = defaultdict(Counter)
        target_detail: dict[str, list[dict]] = defaultdict(list)

        # Mais Agressor: per-individual actor counting (expand actors arrays)
        aggr_hits: Counter[str] = Counter()
        aggr_hits_recent: Counter[str] = Counter()
        aggr_types: dict[str, Counter[str]] = defaultdict(Counter)
        aggr_detail: dict[str, list[dict]] = defaultdict(list)

        for ev in power_events:
            if ev.get("type") not in POWER_TARGET_TYPES:
                continue
            if ev.get("impacto") != "negativo":
                continue
            target = (ev.get("target") or "").strip()
            if not target:
                continue
            week = ev.get("cycle", ev.get("week", 0))
            ev_type = ev["type"]

            # Mais Alvo: 1 hit per event on target
            target_hits[target] += 1
            target_types[target][ev_type] += 1
            target_detail[target].append({
                "type": ev_type, "actor": ev.get("actor", ""),
                "date": ev.get("date", ""), "cycle": week,
            })
            if week > recent_week_cutoff:
                target_hits_recent[target] += 1

            # Mais Agressor: 1 hit per individual actor
            actors = ev.get("actors") or [ev.get("actor", "")]
            for actor in actors:
                actor = (actor or "").strip()
                if not actor:
                    continue
                aggr_hits[actor] += 1
                aggr_types[actor][ev_type] += 1
                aggr_detail[actor].append({
                    "type": ev_type, "target": target,
                    "date": ev.get("date", ""), "cycle": week,
                })
                if week > recent_week_cutoff:
                    aggr_hits_recent[actor] += 1

        # ── Build Mais Alvo (visados) items ──
        visados_items_active: list[dict] = []
        visados_items_exited: list[dict] = []
        for name in all_participant_names:
            hits = target_hits.get(name, 0)
            hits_recent = target_hits_recent.get(name, 0)
            n_par = on_paredao.get(name, 0) if paredoes_with_votes else 0
            n_bv = bv_escape_count.get(name, 0) if paredoes_with_votes else 0
            ph = target_types.get(name, Counter())
            p_tags = [
                {"label": POWER_TAG_LABELS.get(t, t), "count": c,
                 "text": f"{POWER_TAG_LABELS.get(t, t)} {c}x"}
                for t, c in ph.most_common()
            ]
            detail = target_detail.get(name, [])
            is_active = name in active_set
            item = {
                "name": name,
                "paredao": n_par,
                "bv_escapes": n_bv,
                "power_hits": hits,
                "power_hits_recent": hits_recent,
                "power_tags": p_tags,
                "power_detail": detail,
                "nom_text": ", ".join(
                    f"{lbl} {cnt}x" for lbl, cnt in [
                        ("Líder", by_lider.get(name, 0)),
                        ("Casa", by_casa.get(name, 0)),
                        ("Dinâmica", by_dynamic.get(name, 0)),
                    ] if cnt
                ) if paredoes_with_votes else "",
                "active": is_active,
            }
            if is_active:
                visados_items_active.append(item)
            elif hits > 0:
                visados_items_exited.append(item)

        visados_items_active.sort(key=lambda x: (-x["power_hits"], -x["paredao"], -x["power_hits_recent"], x["name"]))
        visados_items_exited.sort(key=lambda x: (-x["power_hits"], -x["paredao"], -x["power_hits_recent"], x["name"]))
        visados_items = visados_items_active[:display_limit] if paredoes_with_votes else visados_items_active[:4]

        cards.append({
            "type": "visados",
            "icon": "🎯", "title": "Mais Alvo",
            "color": "#e67e22", "link": "paredoes.html",
            "total": len(visados_items_active),
            "display_limit": display_limit if paredoes_with_votes else 4,
            "items": visados_items,
            "items_all": visados_items_active,
            "items_exited": visados_items_exited,
            "n_paredoes": n_paredoes if paredoes_with_votes else 0,
        })

        # ── Build Mais Agressor items ──
        aggr_items_active: list[dict] = []
        aggr_items_exited: list[dict] = []
        for name in all_participant_names:
            hits = aggr_hits.get(name, 0)
            if hits == 0:
                continue
            hits_recent = aggr_hits_recent.get(name, 0)
            ah = aggr_types.get(name, Counter())
            a_tags = [
                {"label": POWER_TAG_LABELS.get(t, t), "count": c,
                 "text": f"{POWER_TAG_LABELS.get(t, t)} {c}x"}
                for t, c in ah.most_common()
            ]
            is_active = name in active_set
            item = {
                "name": name,
                "power_hits": hits,
                "power_hits_recent": hits_recent,
                "power_tags": a_tags,
                "power_detail": aggr_detail.get(name, []),
                "active": is_active,
            }
            if is_active:
                aggr_items_active.append(item)
            else:
                aggr_items_exited.append(item)

        aggr_items_active.sort(key=lambda x: (-x["power_hits"], -x["power_hits_recent"], x["name"]))
        aggr_items_exited.sort(key=lambda x: (-x["power_hits"], -x["power_hits_recent"], x["name"]))

        if aggr_items_active:
            cards.append({
                "type": "mais_agressor",
                "icon": "⚔️", "title": "Mais Agressor",
                "color": "#8e44ad", "link": "evolucao.html#impacto",
                "total": len(aggr_items_active),
                "items": aggr_items_active[:5],
                "items_all": aggr_items_active,
                "items_exited": aggr_items_exited,
            })
            lines = [f"**{d['name']}** ({d['power_hits']})" for d in aggr_items_active[:3]]
            extra = len(aggr_items_active) - 3
            highlights.append(
                f"⚔️ [Mais agressores](evolucao.html#impacto): "
                + " · ".join(lines) + (f" (+{extra} mais)" if extra > 0 else "")
            )

    # ── Nunca foi ao Paredão ──
    if paredoes_list:
        nunca_items, nunca_exited = build_nunca_paredao_items(
            ctx, paredoes_list, exposure_by_name,
        )
        paredoes_with_indicados = [p for p in paredoes_list if p.get("indicados_finais")]
        if nunca_items:
            cards.append({
                "type": "nunca_paredao",
                "icon": "✨",
                "title": "Nunca foi ao Paredão",
                "color": "#27ae60",
                "link": "paredoes.html#nunca-paredao",
                "n_paredoes": len(paredoes_with_indicados),
                "n_active": len(active_set),
                "context_line": f"{len(nunca_items)} de {len(active_set)} ativos nunca enfrentaram o público",
                "display_limit": 5,
                "items": nunca_items[:5],
                "items_all": nunca_items,
                "items_exited": nunca_exited,
            })

    # ── Figurinha Repetida ──
    exposure_stats = compute_paredao_exposure_stats(ctx) if paredoes_list else {"metrics": {}, "facts": {}}
    if paredoes_list:
        fig_items_all = build_figurinha_repetida_items(ctx, paredoes_list)
        fig_items = [i for i in fig_items_all if i["appearance_count"] >= 2]
        if fig_items:
            cards.append({
                "type": "figurinha_repetida",
                "icon": "🔁",
                "title": "Figurinha Repetida",
                "color": "#8e44ad",
                "link": "paredoes.html#figurinha-repetida",
                "n_paredoes": len([p for p in paredoes_list if p.get("indicados_finais")]),
                "display_limit": 5,
                "stats": exposure_stats,
                "stat_line": _build_figurinha_stat_line(exposure_stats),
                "items": fig_items[:5],
                "items_all": fig_items,  # only repeaters (count >= 2)
            })

    # ── VIP / Xepa (separate cards) ──
    vip_days = ctx.get("vip_days", {})
    xepa_days = ctx.get("xepa_days", {})
    total_days_map = ctx.get("total_days", {})

    if vip_days or xepa_days:
        vip_ranked = sorted(
            [{"name": n, "vip": vip_days.get(n, 0), "xepa": xepa_days.get(n, 0), "total": total_days_map.get(n, 0)}
             for n in active_set],
            key=lambda x: x["vip"], reverse=True,
        )
        xepa_ranked = sorted(
            [{"name": n, "xepa": xepa_days.get(n, 0), "vip": vip_days.get(n, 0), "total": total_days_map.get(n, 0)}
             for n in active_set],
            key=lambda x: x["xepa"], reverse=True,
        )
        cards.append({
            "type": "vip",
            "icon": "\U0001f451", "title": "Mais dias VIP",
            "color": "#f1c40f", "link": "relacoes.html#vip-xepa",
            "items": vip_ranked,
        })
        cards.append({
            "type": "xepa",
            "icon": "\U0001f373", "title": "Mais dias Xepa",
            "color": "#95a5a6", "link": "relacoes.html#vip-xepa",
            "items": xepa_ranked,
        })

    return highlights, cards, exposure_stats


def _build_highlights_and_cards(ctx: dict[str, Any]) -> dict[str, Any]:
    """Daily movers, dramatic changes, Sincerão contradictions, all highlight cards."""
    daily_snapshots = ctx["daily_snapshots"]
    daily_matrices = ctx["daily_matrices"]
    latest_matrix = ctx["latest_matrix"]
    active_names = ctx["active_names"]
    active_set = ctx["active_set"]
    relations_pairs = ctx["relations_pairs"]
    received_impact = ctx["received_impact"]
    relations_data = ctx["relations_data"]
    sinc_data = ctx["sinc_data"]
    current_cycle = ctx["current_cycle"]
    latest = ctx["latest"]
    latest_date = ctx["latest_date"]

    highlights = []
    cards = []

    # Daily movers, ranking, changes, dramatic, hostilities
    dm_hl, dm_cards = _compute_daily_movers_cards(
        daily_snapshots,
        daily_matrices,
        active_names,
        active_set=active_set,
        current_cycle=current_cycle,
        latest_date=latest_date,
        manual_events=ctx.get("manual_events"),
        auto_events=ctx.get("auto_events"),
        paredoes=ctx.get("paredoes"),
        daily_changes_history=(ctx.get("daily_metrics") or {}).get("daily_changes", []),
    )
    highlights.extend(dm_hl)
    cards.extend(dm_cards)

    # Resolve Sincerao week and lock reaction matrix to the Sincerao date
    # (avoid comparing Sincerão actions against "today" reactions days later).
    sinc_week_for_reactions, _ = _resolve_sinc_week(sinc_data, current_cycle)
    sinc_reference_day = _resolve_sinc_reference_date(sinc_data, sinc_week_for_reactions)
    sinc_reference_matrix, sinc_reference_date = _resolve_matrix_for_date(
        sinc_reference_day,
        daily_snapshots,
        daily_matrices,
        latest_matrix,
        latest_date,
    )

    # Sincerão x Queridômetro
    (sinc_hl, sinc_cards, pair_contradictions, pair_aligned_pos, pair_aligned_neg,
     sinc_week_used, available_weeks, sinc_radar) = _compute_sincerao_highlight(
        sinc_data, current_cycle, sinc_reference_matrix, active_set=active_set)
    for card in sinc_cards:
        if card.get("type") != "sincerao":
            continue
        card["cycle"] = sinc_week_used
        card["reaction_reference_date"] = sinc_reference_date
    highlights.extend(sinc_hl)
    cards.extend(sinc_cards)

    # Impact, vulnerability, paredão
    vuln_hl, vuln_cards, paredao_names = _compute_vulnerability_cards(
        latest, active_names, active_set, received_impact, relations_pairs, relations_data,
        latest_date=latest_date)
    highlights.extend(vuln_hl)
    cards.extend(vuln_cards)

    # Context only. Historical break rows stay available elsewhere, but the
    # index surface now routes latest-comparison pair changes through Viradas.
    context_hl, context_card = _build_context_card(
        latest=latest,
        current_cycle=current_cycle,
        daily_snapshots=daily_snapshots,
    )
    highlights.append(context_hl)
    cards.append(context_card)

    # Static cards: blindados, exposure, VIP x Xepa
    static_hl, static_cards, exposure_stats = _compute_static_cards(ctx)
    highlights.extend(static_hl)
    cards.extend(static_cards)

    return {
        "highlights": highlights,
        "cards": cards,
        "exposure_stats": exposure_stats,
        "pair_contradictions": pair_contradictions,
        "pair_aligned_pos": pair_aligned_pos,
        "pair_aligned_neg": pair_aligned_neg,
        "sinc_week_used": sinc_week_used,
        "available_weeks": available_weeks,
        "sinc_radar": sinc_radar,
        "sinc_reference_matrix": sinc_reference_matrix,
        "sinc_reference_date": sinc_reference_date,
        "paredao_names": paredao_names,
    }


def _build_overview_stats(ctx: dict[str, Any]) -> dict[str, Any]:
    """Group counts, hearts, hostility stats, watchlist."""
    active = ctx["active"]
    active_set = ctx["active_set"]
    latest_matrix = ctx["latest_matrix"]
    latest_date = ctx["latest_date"]
    member_of = ctx["member_of"]
    daily_snapshots = ctx["daily_snapshots"]

    groups = Counter(p.get("characteristics", {}).get("memberOf", "?") for p in active)
    total_hearts = 0
    total_negative = 0
    for p in active:
        for rxn in p.get("characteristics", {}).get("receivedReactions", []):
            amt = rxn.get("amount", 0)
            if rxn.get("label") == "Coração":
                total_hearts += amt
            else:
                total_negative += amt

    n_two_sided = 0
    n_one_sided = 0
    blind_spot_victims = set()
    attackers = set()
    checked_pairs = set()
    for (a, b), rxn_a_to_b in latest_matrix.items():
        if a not in active_set or b not in active_set:
            continue
        rxn_b_to_a = latest_matrix.get((b, a), "")
        a_dislikes_b = rxn_a_to_b not in POSITIVE and rxn_a_to_b != ""
        b_dislikes_a = rxn_b_to_a not in POSITIVE and rxn_b_to_a != ""
        b_likes_a = rxn_b_to_a in POSITIVE
        pair = frozenset([a, b])
        if a_dislikes_b and b_dislikes_a:
            if pair not in checked_pairs:
                n_two_sided += 1
                checked_pairs.add(pair)
        elif a_dislikes_b and b_likes_a:
            n_one_sided += 1
            attackers.add(a)
            blind_spot_victims.add(b)

    try:
        date_obj = datetime.strptime(latest_date, "%Y-%m-%d")
        date_display = date_obj.strftime("%d/%m")
    except ValueError:
        date_display = latest_date

    # Watchlist data
    loving_victim = Counter()
    hostile_giver = Counter()
    blind_spots = {}
    for (a, b), rxn_a_to_b in latest_matrix.items():
        if a not in active_set or b not in active_set:
            continue
        rxn_b_to_a = latest_matrix.get((b, a), "")
        a_dislikes_b = rxn_a_to_b not in POSITIVE and rxn_a_to_b != ""
        b_likes_a = rxn_b_to_a in POSITIVE
        if a_dislikes_b and b_likes_a:
            hostile_giver[a] += 1
            loving_victim[b] += 1
            blind_spots.setdefault(b, []).append(a)

    vulnerability_scores = []
    for name in loving_victim:
        hearts_to_enemies = loving_victim[name]
        attacks_on_friends = hostile_giver.get(name, 0)
        ratio = hearts_to_enemies / (attacks_on_friends + 1)
        if ratio >= 3:
            risk_label = "Alto Risco"
            risk_color = "#e74c3c"
        elif ratio >= 2:
            risk_label = "Risco Médio"
            risk_color = "#f39c12"
        else:
            risk_label = "Atenção"
            risk_color = "#f1c40f"
        vulnerability_scores.append({
            "name": name,
            "hearts_to_enemies": hearts_to_enemies,
            "attacks_on_friends": attacks_on_friends,
            "ratio": ratio,
            "grupo": member_of.get(name, "?"),
            "attackers": blind_spots.get(name, []),
            "risk_label": risk_label,
            "risk_color": risk_color,
        })

    top_vulnerable = sorted(
        vulnerability_scores, key=lambda x: (-x["ratio"], -x["hearts_to_enemies"])
    )[:5]

    return {
        "groups": groups,
        "total_hearts": total_hearts,
        "total_negative": total_negative,
        "n_two_sided": n_two_sided,
        "n_one_sided": n_one_sided,
        "blind_spot_victims": blind_spot_victims,
        "date_display": date_display,
        "top_vulnerable": top_vulnerable,
    }


def _build_ranking_tables(ctx: dict[str, Any]) -> dict[str, Any]:
    """Sentiment ranking, strategic ranking, timeline, changes."""
    latest = ctx["latest"]
    daily_snapshots = ctx["daily_snapshots"]
    daily_metrics = ctx["daily_metrics"]
    relations_pairs = ctx["relations_pairs"]
    relations_data = ctx["relations_data"]
    member_of = ctx["member_of"]
    avatars = ctx["avatars"]

    ranking_today = []
    for p in latest["participants"]:
        if p.get("characteristics", {}).get("eliminated"):
            continue
        name = p.get("name")
        if not name:
            continue
        hearts = sum(r.get("amount", 0) for r in p.get("characteristics", {}).get("receivedReactions", [])
                     if r.get("label") == "Coração")
        neg = sum(r.get("amount", 0) for r in p.get("characteristics", {}).get("receivedReactions", [])
                  if r.get("label") != "Coração")
        ranking_today.append({
            "name": name,
            "score": calc_sentiment(p),
            "hearts": hearts,
            "negative": neg,
            "group": p.get("characteristics", {}).get("memberOf", "?"),
            "avatar": avatars.get(name, ""),
        })

    yesterday_scores = {}
    week_ago_scores = {}
    yesterday_label = None
    week_ago_label = None
    if len(daily_snapshots) >= 2:
        yesterday = daily_snapshots[-2]
        yesterday_label = yesterday.get("label") or yesterday.get("date")
        for p in yesterday["participants"]:
            if not p.get("characteristics", {}).get("eliminated"):
                yesterday_scores[p["name"]] = calc_sentiment(p)
    if len(daily_snapshots) >= 7:
        week_ago = daily_snapshots[-7]
        week_ago_label = week_ago.get("label") or week_ago.get("date")
        for p in week_ago["participants"]:
            if not p.get("characteristics", {}).get("eliminated"):
                week_ago_scores[p["name"]] = calc_sentiment(p)

    def build_change_rows(today_list: list[dict], past_scores: dict[str, float]) -> list[dict]:
        rows = []
        if not past_scores:
            return rows
        today_map = {r["name"]: r for r in today_list}
        for name, past_score in past_scores.items():
            if name not in today_map:
                continue
            today_score = today_map[name]["score"]
            rows.append({
                "name": name,
                "group": today_map[name]["group"],
                "past": past_score,
                "today": today_score,
                "delta": today_score - past_score,
            })
        rows.sort(key=lambda x: -x["delta"])
        return rows

    change_yesterday = build_change_rows(ranking_today, yesterday_scores)
    change_week = build_change_rows(ranking_today, week_ago_scores)

    # Timeline data (queridômetro sentiment per day) — with precomputed rank
    timeline = []
    daily_metrics_map = {d.get("date"): d for d in daily_metrics.get("daily", [])}
    if daily_metrics_map:
        for date_str in sorted(daily_metrics_map.keys()):
            entry = daily_metrics_map[date_str]
            for name, score in entry.get("sentiment", {}).items():
                timeline.append({
                    "date": date_str,
                    "name": name,
                    "sentiment": score,
                    "group": member_of.get(name, "?"),
                })
    else:
        for snap in daily_snapshots:
            for p in snap["participants"]:
                if p.get("characteristics", {}).get("eliminated"):
                    continue
                name = p["name"]
                timeline.append({
                    "date": snap["date"],
                    "name": name,
                    "sentiment": calc_sentiment(p),
                    "group": p.get("characteristics", {}).get("memberOf", "?"),
                })

    # Add rank per date to timeline
    _tl_by_date = defaultdict(list)
    for row in timeline:
        _tl_by_date[row["date"]].append(row)
    for _date_rows in _tl_by_date.values():
        _sorted = sorted(_date_rows, key=lambda r: r["sentiment"], reverse=True)
        _prev_score, _prev_rank = None, 0
        for i, row in enumerate(_sorted):
            if row["sentiment"] != _prev_score:
                _prev_rank = i + 1
                _prev_score = row["sentiment"]
            row["rank"] = _prev_rank

    # Strategic timeline — per-day composite scores (queridômetro + accumulated events)
    strategic_timeline = []
    event_edges = relations_data.get("edges", []) if isinstance(relations_data, dict) else []
    if daily_snapshots and event_edges:
        for snap in daily_snapshots:
            date_str = snap["date"]
            snap_parts = [p for p in snap["participants"]
                          if not p.get("characteristics", {}).get("eliminated")]
            snap_names = {p["name"] for p in snap_parts}
            if len(snap_names) < 2:
                continue

            snap_matrix = build_reaction_matrix(snap_parts)
            pair_base = {}
            for (giver, receiver), label in snap_matrix.items():
                pair_base[(giver, receiver)] = SENTIMENT_WEIGHTS.get(label, 0)

            pair_events = defaultdict(float)
            for e in event_edges:
                if e.get("date", "") <= date_str:
                    pair_events[(e["actor"], e["target"])] += e.get("weight", 0)

            for name in snap_names:
                incoming = []
                for other in snap_names:
                    if other != name:
                        base = pair_base.get((other, name), 0)
                        evts = pair_events.get((other, name), 0)
                        incoming.append(base + evts)
                if incoming:
                    strategic_timeline.append({
                        "date": date_str,
                        "name": name,
                        "score": round(sum(incoming) / len(incoming), 3),
                        "group": member_of.get(name, "?"),
                    })

    # Add rank per date to strategic_timeline
    _stl_by_date = defaultdict(list)
    for row in strategic_timeline:
        _stl_by_date[row["date"]].append(row)
    for _date_rows in _stl_by_date.values():
        _sorted = sorted(_date_rows, key=lambda r: r["score"], reverse=True)
        _prev_score, _prev_rank = None, 0
        for i, row in enumerate(_sorted):
            if row["score"] != _prev_score:
                _prev_rank = i + 1
                _prev_score = row["score"]
            row["rank"] = _prev_rank

    return {
        "ranking_today": ranking_today,
        "yesterday_label": yesterday_label,
        "week_ago_label": week_ago_label,
        "change_yesterday": change_yesterday,
        "change_week": change_week,
        "timeline": timeline,
        "strategic_timeline": strategic_timeline,
    }


def _build_cross_table_and_summary(ctx: dict[str, Any]) -> dict[str, Any]:
    """Cross-reaction matrix, reaction summary table."""
    active_names = ctx["active_names"]
    active = ctx["active"]
    latest_matrix = ctx["latest_matrix"]

    cross_names = active_names
    cross_matrix = []
    for giver in cross_names:
        row = []
        for receiver in cross_names:
            if giver == receiver:
                row.append("")
            else:
                row.append(latest_matrix.get((giver, receiver), ""))
        cross_matrix.append(row)

    # Reaction summary table — built from latest_matrix (handles synthetic snapshots)
    summary_rows = []
    for name in active_names:
        rxn_counts: dict[str, int] = {}
        for giver in active_names:
            if giver == name:
                continue
            label = latest_matrix.get((giver, name), "")
            if label:
                emoji = REACTION_EMOJI.get(label, label)
                rxn_counts[emoji] = rxn_counts.get(emoji, 0) + 1
        hearts = rxn_counts.get("❤️", 0)
        neg_sum = sum(v for k, v in rxn_counts.items() if k != "❤️")
        score = hearts - neg_sum  # simplified sentiment from matrix
        summary_rows.append({
            "name": name,
            "hearts": hearts,
            "planta": rxn_counts.get("🌱", 0),
            "mala": rxn_counts.get("💼", 0),
            "biscoito": rxn_counts.get("🍪", 0),
            "cobra": rxn_counts.get("🐍", 0),
            "alvo": rxn_counts.get("🎯", 0),
            "vomito": rxn_counts.get("🤮", 0),
            "mentiroso": rxn_counts.get("🤥", 0),
            "coracao_partido": rxn_counts.get("💔", 0),
            "score": score,
        })
    summary_rows.sort(key=lambda r: r["score"], reverse=True)

    max_hearts = max((r["hearts"] for r in summary_rows), default=1)
    max_neg = max((r["cobra"] + r["alvo"] + r["vomito"] + r["mentiroso"] for r in summary_rows), default=1)

    return {
        "cross_names": cross_names,
        "cross_matrix": cross_matrix,
        "summary_rows": summary_rows,
        "max_hearts": max_hearts,
        "max_neg": max_neg,
    }


def _compute_vote_multipliers_for_paredao(
    par: dict[str, Any], power_events: list[dict[str, Any]], week: Any
) -> dict[str, int]:
    """Build {voter_name: multiplier} for a single paredao entry.

    Accounts for votos_anulados, impedidos_votar, voto_duplo, and voto_anulado
    power events. Returns a defaultdict with default value 1.
    """
    multiplier: dict[str, int] = defaultdict(lambda: 1)

    for voter in par.get("votos_anulados", []) or []:
        multiplier[voter] = 0
    for voter in par.get("impedidos_votar", []) or []:
        multiplier[voter] = 0

    for ev in power_events:
        ev_week = get_cycle_number(ev["date"]) if ev.get("date") else (ev.get("cycle") or ev.get("week", 0))
        if week and ev_week == week:
            if ev.get("type") == "voto_duplo":
                for a in normalize_actors(ev):
                    if a:
                        multiplier[a] = 2
            if ev.get("type") == "voto_anulado":
                target = ev.get("target")
                if target:
                    multiplier[target] = 0

    return multiplier


def _collect_bv_escapes(
    provas_list: list[dict[str, Any]], paredoes_data: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    """Detect Bate e Volta escape winners matched to their paredao.

    Returns {winner_name: [{numero, data}]} by matching BV losers to paredao
    nominees and picking the closest date.
    """
    bv_escapes: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for prova in provas_list:
        if prova.get("tipo") != "bate_volta":
            continue
        winners = prova.get("vencedores") or (
            [prova["vencedor"]] if prova.get("vencedor") else []
        )
        if not winners:
            continue
        prova_date = prova.get("date", "")
        bv_participants: set[str] = set()
        for fase in prova.get("fases", []):
            for entry in fase.get("classificacao", []):
                if "nome" in entry:
                    bv_participants.add(entry["nome"])
        bv_losers = bv_participants - set(winners)
        matched_par = None
        best_gap = 999
        for par in paredoes_data:
            par_names = {
                (ind.get("nome", "") if isinstance(ind, dict) else ind)
                for ind in par.get("indicados_finais", [])
            }
            if bv_losers & par_names:
                par_date = par.get("data", "")
                gap = (
                    abs(
                        (
                            datetime.strptime(par_date, "%Y-%m-%d")
                            - datetime.strptime(prova_date, "%Y-%m-%d")
                        ).days
                    )
                    if par_date and prova_date
                    else 999
                )
                if gap < best_gap:
                    best_gap = gap
                    matched_par = par
        if matched_par:
            for vencedor in winners:
                bv_escapes[vencedor].append(
                    {
                        "numero": matched_par.get("numero"),
                        "data": matched_par.get("data"),
                    }
                )

    # Máquina do Poder saves also count as paredão escapes
    for par in paredoes_data:
        form = par.get("formacao", {})
        if not isinstance(form, dict):
            continue
        mdp = form.get("maquina_do_poder", {}) or {}
        salvou = mdp.get("salvou", "")
        if salvou and salvou not in bv_escapes:
            bv_escapes[salvou].append(
                {
                    "numero": par.get("numero"),
                    "data": par.get("data"),
                }
            )

    return bv_escapes


def _build_curiosity_lookups(ctx: dict[str, Any]) -> dict[str, Any]:
    """Cartola, provas, streaks, vote history lookups for profiles."""
    paredoes = ctx["paredoes"]
    manual_events = ctx["manual_events"]
    power_events = ctx["power_events"]
    relations_pairs = ctx["relations_pairs"]
    relations_data = ctx["relations_data"]
    daily_metrics = ctx["daily_metrics"]
    cartola_data = ctx["cartola_data"]
    prova_data = ctx["prova_data"]
    provas_raw = ctx["provas_raw"]
    current_cycle = ctx["current_cycle"]
    leader_periods = ctx["leader_periods"]

    # Votes received (by week), with voto duplo/anulado
    votes_received_by_week = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    revealed_votes = defaultdict(set)

    for par in paredoes.get("paredoes", []) if paredoes else []:
        votos = par.get("votos_casa", {}) or {}
        if not votos:
            continue
        week = par.get("cycle")
        multiplier = _compute_vote_multipliers_for_paredao(par, power_events, week)

        for voter, target in votos.items():
            v = voter.strip()
            t = target.strip()
            mult = multiplier.get(v, 1)
            if mult <= 0:
                continue
            votes_received_by_week[week][t][v] += mult

    for wev in _iter_cycle_entries(manual_events) if manual_events else []:
        for key in ("dedo_duro", "voto_revelado"):
            dd = wev.get(key)
            if isinstance(dd, dict):
                voter = dd.get("votante")
                target = dd.get("alvo")
                if voter and target:
                    revealed_votes[target].add(voter)
            elif isinstance(dd, list):
                for item in dd:
                    voter = item.get("votante")
                    target = item.get("alvo")
                    if voter and target:
                        revealed_votes[target].add(voter)

    current_vote_week = current_cycle

    # Sincerao edges (current week) used for contradictions/insights
    sinc_data = ctx["sinc_data"]
    sinc_edges_week = [e for e in sinc_data.get("edges", []) if (e.get("cycle")) == current_cycle]
    sinc_weeks_meta = {}
    for w in sinc_data.get("weeks", []):
        wk = w.get("cycle")
        if wk is not None:
            sinc_weeks_meta[wk] = w.get("format", "")

    # Cartola: name -> {total, rank}
    cartola_lb = cartola_data.get("leaderboard", [])
    cartola_sorted = sorted(cartola_lb, key=lambda x: x.get("total", 0), reverse=True)
    cartola_by_name = {}
    for i, entry in enumerate(cartola_sorted):
        cartola_by_name[entry.get("name", "")] = {"total": entry.get("total", 0), "rank": i + 1}

    # Provas: name -> leaderboard entry
    prova_lb = prova_data.get("leaderboard", [])
    prova_by_name = {e["name"]: e for e in prova_lb if e.get("name")}

    # Sentiment history: name -> [(date, score)]
    sentiment_history = defaultdict(list)
    for day in daily_metrics.get("daily", []):
        date_str_d = day.get("date", "")
        for nm, sc in day.get("sentiment", {}).items():
            sentiment_history[nm].append((date_str_d, sc))

    # Streak breaks data
    streak_breaks_data = relations_data.get("streak_breaks", []) if isinstance(relations_data, dict) else []

    # Longest received heart streaks per participant + count of 10+ day streaks
    longest_streaks = {}
    long_alliance_counts = defaultdict(int)
    for pair_giver, targets in relations_pairs.items():
        if not isinstance(targets, dict):
            continue
        for pair_receiver, rel in targets.items():
            if not isinstance(rel, dict):
                continue
            slen = rel.get("streak_len", 0)
            if slen >= 10:
                long_alliance_counts[pair_receiver] += 1
            if slen > longest_streaks.get(pair_receiver, {}).get("len", 0):
                longest_streaks[pair_receiver] = {"len": slen, "partner": pair_giver}

    # Total house votes received per participant (all paredões)
    total_house_votes = Counter()
    for par in paredoes.get("paredoes", []):
        for voter, target in (par.get("votos_casa") or {}).items():
            total_house_votes[target.strip()] += 1

    # Ever nominated / survived paredão
    ever_nominated = set()
    survived_paredao = set()
    for par in paredoes.get("paredoes", []):
        resultado = par.get("resultado", {})
        eliminado = resultado.get("eliminado", "") if resultado else ""
        for ind in par.get("indicados_finais", []):
            nome = ind.get("nome", "") if isinstance(ind, dict) else ind
            if nome:
                ever_nominated.add(nome)
                if par.get("status") == "finalizado" and nome != eliminado:
                    survived_paredao.add(nome)

    # Bate e Volta escapes: winner escaped the paredão, match BV to paredão via losers + date
    provas_list = provas_raw.get("provas", [])
    paredoes_list = paredoes.get("paredoes", []) if paredoes else []
    bv_escapes = _collect_bv_escapes(provas_list, paredoes_list)
    for vencedor in bv_escapes:
        ever_nominated.add(vencedor)

    # Breaks given/received counts
    breaks_given_count = Counter(b["giver"] for b in streak_breaks_data)
    breaks_received_count = Counter(b["receiver"] for b in streak_breaks_data)

    # Total leader periods available
    n_leader_periods = len(leader_periods)

    # House vote eligibility per participant (all paredões with votos_casa)
    paredoes_with_votes = [p for p in paredoes_list if p.get("votos_casa")]
    n_paredoes_with_votes = len(paredoes_with_votes)
    house_vote_ineligible = defaultdict(list)  # name → [(num, reason)]
    for par in paredoes_with_votes:
        num = par.get("numero", 0)
        form = par.get("formacao", {})
        for l in resolve_leaders(form):
            house_vote_ineligible[l].append((num, "Líder"))
        for ind in par.get("indicados_finais", []):
            n = ind.get("nome", "") if isinstance(ind, dict) else ind
            if n:
                house_vote_ineligible[n].append((num, "no Paredão"))
        im = form.get("imunizado")
        if im and im.get("quem"):
            house_vote_ineligible[im["quem"]].append((num, "imune"))
        if form.get("anjo_autoimune") and form.get("anjo"):
            house_vote_ineligible[form["anjo"]].append((num, "imune"))

    return {
        "votes_received_by_week": votes_received_by_week,
        "revealed_votes": revealed_votes,
        "current_vote_week": current_vote_week,
        "sinc_edges_week": sinc_edges_week,
        "sinc_weeks_meta": sinc_weeks_meta,
        "cartola_by_name": cartola_by_name,
        "prova_by_name": prova_by_name,
        "sentiment_history": sentiment_history,
        "streak_breaks_data": streak_breaks_data,
        "longest_streaks": longest_streaks,
        "long_alliance_counts": long_alliance_counts,
        "total_house_votes": total_house_votes,
        "ever_nominated": ever_nominated,
        "survived_paredao": survived_paredao,
        "bv_escapes": bv_escapes,
        "breaks_given_count": breaks_given_count,
        "breaks_received_count": breaks_received_count,
        "n_leader_periods": n_leader_periods,
        "house_vote_ineligible": house_vote_ineligible,
        "n_paredoes_with_votes": n_paredoes_with_votes,
    }


def _build_profile_header(name: str, latest: dict, latest_matrix: dict[tuple[str, str], str], active_names: list[str], avatars: dict[str, str]) -> dict[str, Any]:
    """Participant data lookup, reaction summaries, given/received details.

    Returns a dict with p, roles, rxn_summary, given_summary, given_detail, received_detail.
    """
    p = next(pp for pp in latest["participants"] if pp.get("name") == name)
    roles = parse_roles(p.get("characteristics", {}).get("roles", []))

    rxn_summary = []
    for rxn in p.get("characteristics", {}).get("receivedReactions", []):
        emoji = REACTION_EMOJI.get(rxn["label"], rxn["label"])
        rxn_summary.append({"emoji": emoji, "count": rxn.get("amount", 0)})

    given = {}
    received_detail = []
    given_detail = []
    for other_name in active_names:
        if other_name == name:
            continue
        rxn = latest_matrix.get((name, other_name), "")
        if rxn:
            emoji = REACTION_EMOJI.get(rxn, rxn)
            given[emoji] = given.get(emoji, 0) + 1
            given_detail.append({"name": other_name, "emoji": emoji})
        rxn_from = latest_matrix.get((other_name, name), "")
        if rxn_from:
            received_detail.append({"name": other_name, "emoji": REACTION_EMOJI.get(rxn_from, rxn_from)})
    given_summary = [{"emoji": e, "count": c} for e, c in sorted(given.items(), key=lambda x: -x[1])]

    return {
        "p": p,
        "roles": roles,
        "rxn_summary": rxn_summary,
        "given_summary": given_summary,
        "given_detail": given_detail,
        "received_detail": received_detail,
        "score": calc_sentiment(p),
        "avatar": avatars.get(name, ""),
        "member_of": p.get("characteristics", {}).get("memberOf", "?"),
        "group": p.get("characteristics", {}).get("group", "?"),
        "balance": p.get("characteristics", {}).get("balance", 0),
    }


def _build_profile_stats_grid(name: str, latest_matrix: dict[tuple[str, str], str], active_names: list[str], relations_pairs: dict,
                               received_impact: dict, relations_data: dict | list, power_events: list[dict],
                               roles_current: dict[str, list[str]], current_cycle: int | None) -> dict[str, Any]:
    """Relations (allies/enemies/false_friends/blind_targets), risk level, impact, animosity, events.

    Returns a dict with relations, risk, impact, animosity, and event data.
    """
    def pair_sentiment(giver: str, receiver: str) -> float:
        rel = relations_pairs.get(giver, {}).get(receiver)
        if rel:
            return rel.get("score", 0)
        label = latest_matrix.get((giver, receiver), "")
        return SENTIMENT_WEIGHTS.get(label, 0)

    allies = []
    enemies = []
    false_friends = []
    blind_targets = []
    for other_name in active_names:
        if other_name == name:
            continue
        my_rxn = latest_matrix.get((name, other_name), "")
        their_rxn = latest_matrix.get((other_name, name), "")
        my_score = pair_sentiment(name, other_name)
        their_score = pair_sentiment(other_name, name)
        my_is_positive = my_score > 0
        their_is_positive = their_score > 0
        my_is_negative = my_score < 0
        their_is_negative = their_score < 0
        if my_is_positive and their_is_positive:
            allies.append({
                "name": other_name,
                "my_score": round(my_score, 2),
                "their_score": round(their_score, 2),
            })
        elif my_is_negative and their_is_negative:
            enemies.append({
                "name": other_name,
                "my_emoji": REACTION_EMOJI.get(my_rxn, "?"),
                "their_emoji": REACTION_EMOJI.get(their_rxn, "?"),
                "my_score": round(my_score, 2),
                "their_score": round(their_score, 2),
            })
        elif my_is_positive and their_is_negative:
            false_friends.append({
                "name": other_name,
                "their_emoji": REACTION_EMOJI.get(their_rxn, "?"),
                "my_score": round(my_score, 2),
                "their_score": round(their_score, 2),
            })
        elif my_is_negative and their_is_positive:
            blind_targets.append({
                "name": other_name,
                "my_emoji": REACTION_EMOJI.get(my_rxn, "?"),
                "my_score": round(my_score, 2),
                "their_score": round(their_score, 2),
            })

    n_false_friends = len(false_friends)
    if n_false_friends >= 5:
        risk_level = "🔴 MUITO VULNERÁVEL"
        risk_color = "#dc3545"
    elif n_false_friends >= 3:
        risk_level = "🟠 VULNERÁVEL"
        risk_color = "#fd7e14"
    elif n_false_friends >= 1:
        risk_level = "🟡 ATENÇÃO"
        risk_color = "#ffc107"
    else:
        risk_level = "🟢 PROTEGIDO"
        risk_color = "#28a745"

    target_events_all = [ev for ev in power_events if ev.get("target") == name]

    # Current events: role-based (leader/anjo/monstro/imune) + cycle-week events
    current_events = []
    historic_events = []
    for ev in target_events_all:
        ev_type = ev.get("type")
        ev_week = get_cycle_number(ev["date"]) if ev.get("date") else (ev.get("cycle") or ev.get("week", 0))
        if ev_type in ["lider", "anjo", "monstro", "imunidade"]:
            role_label = next((k for k, v in ROLE_TYPES.items() if v == ev_type), None)
            if role_label and name in roles_current.get(role_label, []):
                current_events.append(ev)
            else:
                historic_events.append(ev)
        elif ev_week == current_cycle:
            current_events.append(ev)
        else:
            historic_events.append(ev)

    pos_events = [ev for ev in current_events if ev.get("impacto") == "positivo"]
    neg_events = [ev for ev in current_events if ev.get("impacto") == "negativo"]
    pos_events_hist = [ev for ev in historic_events if ev.get("impacto") == "positivo"]
    neg_events_hist = [ev for ev in historic_events if ev.get("impacto") == "negativo"]

    # Impacto Recebido — power_event + vote received, no backlash/sincerao
    all_edges = relations_data.get("edges", []) if isinstance(relations_data, dict) else []
    external_score = 0.0
    external_positive = 0.0
    external_count = 0
    external_breakdown: dict[str, float] = defaultdict(float)
    for edge in all_edges:
        if edge.get("target") != name:
            continue
        w = edge.get("weight", 0)
        if edge.get("backlash"):
            continue
        if edge["type"] not in ("power_event", "vote"):
            continue
        if w < 0:
            external_score += w
            external_breakdown[edge.get("event_type") or edge["type"]] += w
            external_count += 1
        elif w > 0:
            external_positive += w

    if external_score <= -10:
        external_level = "🔴 ALTO"
        external_color = "#dc3545"
    elif external_score <= -5:
        external_level = "🟠 MÉDIO"
        external_color = "#fd7e14"
    elif external_score < 0:
        external_level = "🟡 BAIXO"
        external_color = "#ffc107"
    else:
        external_level = "🟢 NENHUM"
        external_color = "#28a745"

    # Agressividade — deliberate individual power events outgoing only
    animosity_score = 0.0
    animosity_breakdown: dict[str, float] = defaultdict(float)
    for edge in all_edges:
        if edge.get("actor") != name:
            continue
        w = edge.get("weight", 0)
        if w >= 0 or edge.get("backlash"):
            continue
        if edge["type"] != "power_event":
            continue
        if edge.get("event_type") not in DELIBERATE_POWER_TYPES:
            continue
        animosity_score += w
        animosity_breakdown[edge.get("event_type", "other")] += w

    if animosity_score <= -8:
        animosity_level = "🔴 ALTA"
        animosity_color = "#dc3545"
    elif animosity_score <= -4:
        animosity_level = "🟠 MÉDIA"
        animosity_color = "#fd7e14"
    elif animosity_score < 0:
        animosity_level = "🟡 BAIXA"
        animosity_color = "#ffc107"
    else:
        animosity_level = "🟢 NENHUMA"
        animosity_color = "#28a745"

    return {
        "allies": allies,
        "enemies": enemies,
        "false_friends": false_friends,
        "blind_targets": blind_targets,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "pos_events": pos_events,
        "neg_events": neg_events,
        "pos_events_hist": pos_events_hist,
        "neg_events_hist": neg_events_hist,
        "external_score": external_score,
        "external_positive": external_positive,
        "external_count": external_count,
        "external_breakdown": external_breakdown,
        "external_level": external_level,
        "external_color": external_color,
        "animosity_score": animosity_score,
        "animosity_breakdown": animosity_breakdown,
        "animosity_level": animosity_level,
        "animosity_color": animosity_color,
    }


def _build_profile_querido_section(name: str, latest_matrix: dict[tuple[str, str], str], sinc_data: dict, sinc_edges_week: list[dict],
                                    current_cycle: int, votes_received_by_week: dict, current_vote_week: int | None,
                                    revealed_votes: dict[str, set[str]], plant_scores: dict, plant_week: dict | None,
                                    sinc_weeks_meta: dict[int, str] | None = None) -> dict[str, Any]:
    """Queridômetro section: votes, plant index.

    Returns a dict with vote_list, aggregate_events, plant_info.
    Sincerao data is now built by _build_profile_sincerao() separately.
    """
    if sinc_weeks_meta is None:
        sinc_weeks_meta = {}
    vote_map = votes_received_by_week.get(current_vote_week, {}).get(name, {})

    def aggregate_events(events: list[dict]) -> list[dict]:
        grouped = defaultdict(lambda: {"count": 0, "actors": []})
        for ev in events:
            etype = ev.get("type")
            actors = normalize_actors(ev)
            key = (etype, tuple(actors))
            grouped[key]["count"] += 1
            grouped[key]["actors"] = actors
        items = []
        for (etype, actors), meta in grouped.items():
            items.append({
                "type": etype,
                "label": POWER_EVENT_LABELS.get(etype, etype),
                "emoji": POWER_EVENT_EMOJI.get(etype, "•"),
                "count": meta["count"],
                "actors": actors,
            })
        return items

    vote_list = []
    for voter, count in sorted(vote_map.items(), key=lambda x: (-x[1], x[0])):
        vote_list.append({
            "voter": voter,
            "count": count,
            "revealed": voter in revealed_votes.get(name, set()),
        })

    plant_info = plant_scores.get(name)
    if plant_info and plant_week:
        plant_info = dict(plant_info)
        plant_info["cycle"] = plant_week.get("cycle")
        plant_info["date_range"] = plant_week.get("date_range", {})

    return {
        "aggregate_events": aggregate_events,
        "vote_list": vote_list,
        "plant_info": plant_info,
    }


def _build_profile_footer(name: str, allies: list[dict], enemies: list[dict], given_summary: list[dict], active_set: set[str],
                           paredoes: dict, lookups: dict[str, Any], vip_days: dict[str, int], xepa_days: dict[str, int], total_days: dict[str, int],
                           vip_cycles_selected: dict[str, int], plant_scores: dict) -> dict[str, Any]:
    """Curiosities and game stats for the profile footer.

    Returns a dict with curiosities, paredao_history, bv_escape_list, house_votes_detail.
    """
    streak_breaks_data = lookups["streak_breaks_data"]
    longest_streaks = lookups["longest_streaks"]
    long_alliance_counts = lookups["long_alliance_counts"]
    total_house_votes = lookups["total_house_votes"]
    ever_nominated = lookups["ever_nominated"]
    survived_paredao = lookups["survived_paredao"]
    bv_escapes = lookups["bv_escapes"]
    breaks_given_count = lookups["breaks_given_count"]
    breaks_received_count = lookups["breaks_received_count"]
    n_leader_periods = lookups["n_leader_periods"]
    cartola_by_name = lookups["cartola_by_name"]
    prova_by_name = lookups["prova_by_name"]
    sentiment_history = lookups["sentiment_history"]
    votes_received_by_week = lookups["votes_received_by_week"]
    revealed_votes = lookups["revealed_votes"]
    house_vote_ineligible = lookups["house_vote_ineligible"]
    n_paredoes_with_votes = lookups["n_paredoes_with_votes"]
    current_vote_week = lookups["current_vote_week"]

    # -- Build curiosities --
    curiosities = []

    # 1. Streak break given (high drama)
    my_breaks_given = [b for b in streak_breaks_data if b.get("giver") == name]
    my_breaks_received = [b for b in streak_breaks_data if b.get("receiver") == name]
    if my_breaks_given:
        worst = max(my_breaks_given, key=lambda b: b.get("previous_streak", 0))
        curiosities.append({"icon": "💔", "text": f"Rompeu aliança de {worst.get('previous_streak', 0)}d com {worst['receiver']}", "priority": 9})

    # 2. Streak break received
    if my_breaks_received:
        worst = max(my_breaks_received, key=lambda b: b.get("previous_streak", 0))
        curiosities.append({"icon": "💔", "text": f"Perdeu aliança de {worst.get('previous_streak', 0)}d de {worst['giver']}", "priority": 8})

    # 3. Serial betrayer (multiple breaks given)
    n_breaks_given = breaks_given_count.get(name, 0)
    if n_breaks_given >= 2:
        curiosities.append({"icon": "🗡️", "text": f"Traidor em série: rompeu {n_breaks_given} alianças", "priority": 7})

    # 4. Competition wins
    prov = prova_by_name.get(name)
    if prov:
        wins = prov.get("wins", 0)
        if wins > 0:
            curiosities.append({"icon": "🥇", "text": f"{wins} vitória(s) em provas", "priority": 7})

    # 5. Most betrayed (multiple breaks received)
    n_breaks_received = breaks_received_count.get(name, 0)
    if n_breaks_received >= 2:
        curiosities.append({"icon": "😢", "text": f"Mais traído: perdeu {n_breaks_received} alianças", "priority": 6})

    # 6. Vote target (many house votes)
    n_house_votes = total_house_votes.get(name, 0)
    if n_house_votes >= 5:
        curiosities.append({"icon": "🎯", "text": f"Alvo da casa: {n_house_votes} votos recebidos", "priority": 6})

    # 7. Many alliances (10+ day streaks)
    n_long_alliances = long_alliance_counts.get(name, 0)
    ls = longest_streaks.get(name, {})
    if n_long_alliances >= 10:
        curiosities.append({"icon": "🤝", "text": f"{n_long_alliances} alianças de 10+ dias (recorde: {ls.get('len', 0)}d)", "priority": 6})
    elif ls.get("len", 0) >= 10:
        curiosities.append({"icon": "🤝", "text": f"Aliança mais longa: {ls['len']}d de ❤️ de {ls['partner']}", "priority": 5})

    # 8. Polarizer (many allies AND many enemies)
    n_allies = len(allies)
    n_enemies_count = len(enemies)
    if n_allies >= 5 and n_enemies_count >= 5:
        curiosities.append({"icon": "⚡", "text": f"Polarizador: {n_allies} aliados vs {n_enemies_count} inimigos", "priority": 5})

    # 9. Untouchable / Shielded from house votes
    inelig_list = house_vote_ineligible.get(name, [])
    n_eligible = n_paredoes_with_votes - len(inelig_list)
    if n_house_votes == 0 and n_eligible >= 2:
        curiosities.append({"icon": "🛡️", "text": "Intocável: nunca recebeu voto da casa", "priority": 5})
    if n_paredoes_with_votes >= 4 and n_eligible <= n_paredoes_with_votes * 0.5:
        # Eligible in less than half of paredões — structurally protected
        reasons = defaultdict(int)
        for _, reason in inelig_list:
            reasons[reason] += 1
        reason_parts = []
        if reasons.get("Líder"):
            reason_parts.append(f"{reasons['Líder']}x Líder")
        if reasons.get("imune"):
            reason_parts.append(f"{reasons['imune']}x imune")
        if reasons.get("no Paredão"):
            reason_parts.append(f"{reasons['no Paredão']}x no Paredão")
        reason_str = ", ".join(reason_parts) if reason_parts else ""
        curiosities.append({"icon": "🔒", "text": f"Blindado: elegível para voto da casa em apenas {n_eligible} de {n_paredoes_with_votes} paredões ({reason_str})", "priority": 4})

    # 10. Survived paredão
    if name in survived_paredao:
        curiosities.append({"icon": "🔥", "text": "Sobreviveu ao paredão", "priority": 5})

    # 11. Biggest single-day sentiment swing (threshold raised to ±5)
    hist = sentiment_history.get(name, [])
    if len(hist) >= 2:
        max_swing = 0.0
        swing_date = ""
        for j in range(1, len(hist)):
            delta = hist[j][1] - hist[j - 1][1]
            if abs(delta) > abs(max_swing):
                max_swing = delta
                swing_date = hist[j][0]
        if abs(max_swing) >= 5:
            direction = "📈" if max_swing > 0 else "📉"
            try:
                d = datetime.strptime(swing_date, "%Y-%m-%d").strftime("%d/%m")
            except Exception:
                d = swing_date
            curiosities.append({"icon": direction, "text": f"Maior variação: {max_swing:+.1f} em {d}", "priority": 5})

    # 12. VIP favorite (selected 2+ times by leaders)
    n_vip_sel = vip_cycles_selected.get(name, 0)
    if n_vip_sel >= 2 and n_leader_periods >= 2:
        curiosities.append({"icon": "✨", "text": f"VIP favorito: selecionado {n_vip_sel}× de {n_leader_periods} líderes", "priority": 5})

    # 13. Competition top-3 (no wins)
    if prov:
        top3 = prov.get("top3", 0)
        wins = prov.get("wins", 0)
        if top3 >= 2 and wins == 0:
            curiosities.append({"icon": "🎯", "text": f"{top3} top-3 em provas", "priority": 4})
        elif wins == 0 and prov.get("best_position"):
            curiosities.append({"icon": "🎯", "text": f"Melhor posição em provas: {prov['best_position']}º", "priority": 4})

    # 14. Never VIP (selected by leaders)
    if n_vip_sel == 0 and n_leader_periods >= 2:
        curiosities.append({"icon": "🍽️", "text": "Nunca selecionado para o VIP", "priority": 4})

    # 15. Favorite emoji given (most-given non-heart emoji to 5+ people)
    non_heart_given = [r for r in given_summary if r.get("emoji") != "❤️"]
    if non_heart_given and non_heart_given[0]["count"] >= 5:
        fav = non_heart_given[0]
        curiosities.append({"icon": "🎭", "text": f"Emoji favorito: dá {fav['emoji']} para {fav['count']} colegas", "priority": 3})

    # 16. Hearts-given ratio
    total_given_hearts = sum(r["count"] for r in given_summary if r.get("emoji") == "❤️")
    total_given = sum(r["count"] for r in given_summary)
    if total_given > 0:
        heart_pct = round(total_given_hearts / total_given * 100)
        if heart_pct >= 80:
            curiosities.append({"icon": "❤️", "text": f"Dá ❤️ para {heart_pct}% dos colegas", "priority": 3})
        elif heart_pct <= 40:
            curiosities.append({"icon": "🐍", "text": f"Só dá ❤️ para {heart_pct}% dos colegas", "priority": 3})

    # 17. Cartola ranking (demoted from 5 -> 3)
    cart = cartola_by_name.get(name)
    if cart:
        curiosities.append({"icon": "🏆", "text": f"Cartola BBB: {cart['total']} pts ({cart['rank']}º lugar)", "priority": 3})

    # 18. VIP/Xepa day stats
    _vip_d = vip_days.get(name, 0)
    _xepa_d = xepa_days.get(name, 0)
    _total_d = total_days.get(name, 0)
    if _total_d >= 5:
        vip_pct = round(_vip_d / _total_d * 100) if _total_d > 0 else 0
        if vip_pct >= 75:
            curiosities.append({"icon": "✨", "text": f"VIP em {vip_pct}% dos dias", "priority": 2})
        elif vip_pct <= 25 and _xepa_d > 0:
            curiosities.append({"icon": "🍽️", "text": f"Xepa em {100 - vip_pct}% dos dias", "priority": 2})

    # 19. Never nominated
    if name not in ever_nominated and name in active_set:
        curiosities.append({"icon": "🛡️", "text": "Nunca foi ao paredão", "priority": 2})

    # 20. Planta invisível (high plant index = very plant-like)
    _plant = plant_scores.get(name)
    if _plant and isinstance(_plant, dict):
        _plant_score = _plant.get("score", 0)
        if _plant_score >= 60:
            curiosities.append({"icon": "🌱", "text": f"Plantinha invisível: {_plant_score:.0f} no Plant Index", "priority": 4})

    # 21. Biggest rival (mutual enemy with worst combined score)
    if enemies:
        worst_enemy = min(enemies, key=lambda e: e.get("my_score", 0) + e.get("their_score", 0))
        combined = round(worst_enemy.get("my_score", 0) + worst_enemy.get("their_score", 0), 1)
        curiosities.append({"icon": "🔗", "text": f"Maior rival: {worst_enemy['name']} (score {combined:+.1f})", "priority": 4})

    # 22. Em queda: weekly score drop >= 8 points
    if len(hist) >= 5:
        recent_score = hist[-1][1]
        week_back_score = hist[-min(7, len(hist))][1]
        weekly_drop = recent_score - week_back_score
        if weekly_drop <= -8:
            curiosities.append({"icon": "📉", "text": f"Em queda: {weekly_drop:+.1f} pts na semana", "priority": 5})
        elif weekly_drop >= 8:
            curiosities.append({"icon": "📈", "text": f"Em alta: {weekly_drop:+.1f} pts na semana", "priority": 5})

    # 23. Secret vote target (unrevealed votes from many people)
    _vote_map = votes_received_by_week.get(current_vote_week, {}).get(name, {})
    _revealed = revealed_votes.get(name, set())
    _secret_voters = [v for v in _vote_map if v not in _revealed]
    if len(_secret_voters) >= 3:
        curiosities.append({"icon": "🤐", "text": f"Alvo oculto: {len(_secret_voters)} votos secretos", "priority": 5})

    # 24. Paredão target: nominated multiple times across paredões (excl. BV escapes)
    _n_nominations = 0
    for par in paredoes.get("paredoes", []):
        _bv = get_bv_winners(par)
        for ind in par.get("indicados_finais", []):
            _ind_name = ind.get("nome", "") if isinstance(ind, dict) else ind
            if _ind_name == name and _ind_name not in _bv:
                _n_nominations += 1
    if _n_nominations >= 2:
        curiosities.append({"icon": "⚠️", "text": f"Alvo frequente: {_n_nominations}× no paredão", "priority": 5})

    # Sort by priority, keep all (record-holder post-processing will trim)
    curiosities.sort(key=lambda x: x.get("priority", 0), reverse=True)
    curiosities = curiosities[:8]

    # -- Game stats for stat chips (excl. BV escapes) --
    paredao_history = []
    for par in paredoes.get("paredoes", []):
        _bv = get_bv_winners(par)
        for ind in par.get("indicados_finais", []):
            nome = ind.get("nome", "") if isinstance(ind, dict) else ind
            if nome != name or nome in _bv:
                continue  # Skip BV winners — they escaped
            como = ind.get("como", "?") if isinstance(ind, dict) else "?"
            resultado = par.get("resultado", {})
            eliminado = resultado.get("eliminado", "") if resultado else ""
            votos = resultado.get("votos", {}) if resultado else {}
            my_votes = votos.get(name, {})
            paredao_history.append({
                "numero": par.get("numero"),
                "data": par.get("data"),
                "como": como,
                "resultado": "Eliminado" if eliminado == name else "Sobreviveu" if par.get("status") == "finalizado" else "Em andamento",
                "voto_total": my_votes.get("voto_total") if my_votes else None,
            })
    # Bate e Volta escapes (separate from paredão history)
    bv_escape_list = []
    for bv in bv_escapes.get(name, []):
        bv_escape_list.append({
            "numero": bv["numero"],
            "data": bv["data"],
        })
    paredao_history.sort(key=lambda x: x.get("numero", 0))

    house_votes_detail = []
    for par in paredoes.get("paredoes", []):
        voters_for_me = [voter for voter, target in (par.get("votos_casa") or {}).items() if target.strip() == name]
        if voters_for_me:
            house_votes_detail.append({
                "numero": par.get("numero"),
                "data": par.get("data"),
                "voters": sorted(voters_for_me),
            })

    return {
        "curiosities": curiosities,
        "paredao_history": paredao_history,
        "bv_escape_list": bv_escape_list,
        "house_votes_detail": house_votes_detail,
    }


def _build_profile_entry(name: str, ctx: dict[str, Any], lookups: dict[str, Any]) -> dict[str, Any]:
    """Per-participant profile: allies, enemies, curiosities, game stats."""
    latest = ctx["latest"]
    latest_matrix = ctx["latest_matrix"]
    active_names = ctx["active_names"]
    active_set = ctx["active_set"]
    avatars = ctx["avatars"]
    relations_pairs = ctx["relations_pairs"]
    relations_data = ctx["relations_data"]
    received_impact = ctx["received_impact"]
    power_events = ctx["power_events"]
    sinc_data = ctx["sinc_data"]
    paredoes = ctx["paredoes"]
    roles_current = ctx["roles_current"]
    current_cycle = ctx["current_cycle"]
    sinc_week_used = ctx.get("sinc_week_used", current_cycle)
    sinc_reference_matrix = ctx.get("sinc_reference_matrix", latest_matrix)
    plant_scores = ctx["plant_scores"]
    plant_week = ctx["plant_week"]
    vip_days = ctx["vip_days"]
    xepa_days = ctx["xepa_days"]
    total_days = ctx["total_days"]
    vip_cycles_selected = ctx["vip_cycles_selected"]
    xepa_cycles = ctx["xepa_cycles"]

    # 1. Header: participant data, reactions, given/received details
    header = _build_profile_header(name, latest, latest_matrix, active_names, avatars)

    # 2. Stats grid: relations, risk, impact, animosity, events
    stats = _build_profile_stats_grid(
        name, latest_matrix, active_names, relations_pairs,
        received_impact, relations_data, power_events,
        roles_current, current_cycle)

    # 3. Queridômetro section: votes, plant index
    querido = _build_profile_querido_section(
        name, latest_matrix, sinc_data, lookups["sinc_edges_week"],
        current_cycle, lookups["votes_received_by_week"], lookups["current_vote_week"],
        lookups["revealed_votes"], plant_scores, plant_week,
        sinc_weeks_meta=lookups.get("sinc_weeks_meta"))

    # 3a. Sincerao model (received/given)
    sincerao_model = _build_profile_sincerao(
        name, sinc_data, sinc_week_used, sinc_reference_matrix,
        sinc_weeks_meta=lookups.get("sinc_weeks_meta", {}))

    # 4. Footer: curiosities, game stats
    footer = _build_profile_footer(
        name, stats["allies"], stats["enemies"], header["given_summary"],
        active_set, paredoes, lookups, vip_days, xepa_days, total_days,
        vip_cycles_selected, plant_scores)

    aggregate_events = querido["aggregate_events"]

    return {
        "name": name,
        "member_of": header["member_of"],
        "group": header["group"],
        "balance": header["balance"],
        "roles": header["roles"],
        "score": header["score"],
        "avatar": header["avatar"],
        "risk_level": stats["risk_level"],
        "risk_color": stats["risk_color"],
        "external_level": stats["external_level"],
        "external_color": stats["external_color"],
        "animosity_level": stats["animosity_level"],
        "animosity_color": stats["animosity_color"],
        "rxn_summary": header["rxn_summary"],
        "given_summary": header["given_summary"],
        "received_detail": sorted(header["received_detail"], key=lambda x: x["name"]),
        "given_detail": sorted(header["given_detail"], key=lambda x: x["name"]),
        "relations": {
            "allies": sorted(stats["allies"], key=lambda x: x["name"]),
            "enemies": sorted(stats["enemies"], key=lambda x: x["name"]),
            "false_friends": sorted(stats["false_friends"], key=lambda x: x["name"]),
            "blind_targets": sorted(stats["blind_targets"], key=lambda x: x["name"]),
        },
        "events": {
            "pos_week": aggregate_events(stats["pos_events"]),
            "neg_week": aggregate_events(stats["neg_events"]),
            "pos_hist": aggregate_events(stats["pos_events_hist"]),
            "neg_hist": aggregate_events(stats["neg_events_hist"]),
        },
        "votes_received": querido["vote_list"],
        "sincerao": sincerao_model,
        "vip_days": vip_days.get(name, 0),
        "xepa_days": xepa_days.get(name, 0),
        "days_total": total_days.get(name, 0),
        "vip_cycles": vip_cycles_selected.get(name, 0),
        "xepa_cycles": xepa_cycles.get(name, 0),
        "scores": {
            "external": stats["external_score"],
            "external_positive": stats["external_positive"],
            "external_count": stats["external_count"],
            "external_breakdown": {k: round(v, 2) for k, v in sorted(stats["external_breakdown"].items(), key=lambda x: x[1])},
            "animosity": stats["animosity_score"],
            "animosity_breakdown": {k: round(v, 2) for k, v in sorted(stats["animosity_breakdown"].items(), key=lambda x: x[1])},
        },
        "plant_index": querido["plant_info"],
        "game_stats": {
            "total_house_votes": lookups["total_house_votes"].get(name, 0),
            "house_votes_detail": footer["house_votes_detail"],
            "paredao_count": len(footer["paredao_history"]),
            "paredao_history": footer["paredao_history"],
            "bv_escapes": len(footer["bv_escape_list"]),
            "bv_escape_detail": footer["bv_escape_list"],
            "cartola_total": lookups["cartola_by_name"].get(name, {}).get("total", 0),
            "cartola_rank": lookups["cartola_by_name"].get(name, {}).get("rank"),
            "prova_wins": lookups["prova_by_name"].get(name, {}).get("wins", 0),
        },
        "curiosities": footer["curiosities"],
    }


def _build_record_holder_curiosities(profiles: list[dict], ctx: dict[str, Any]) -> None:
    """Post-processing: record-holder bullets injected into profiles."""
    active_set = ctx["active_set"]

    record_data = {}
    for prof in profiles:
        nm = prof["name"]
        if nm not in active_set:
            continue
        rel = prof.get("relations", {})
        record_data[nm] = {
            "allies": len(rel.get("allies", [])),
            "enemies": len(rel.get("enemies", [])),
            "false_friends": len(rel.get("false_friends", [])),
            "blind_targets": len(rel.get("blind_targets", [])),
        }
        gs = prof.get("given_summary", [])
        total_g = sum(r["count"] for r in gs)
        hearts_g = sum(r["count"] for r in gs if r.get("emoji") == "❤️")
        record_data[nm]["heart_pct"] = round(hearts_g / total_g * 100) if total_g > 0 else 0
        record_data[nm]["neg_pct"] = 100 - record_data[nm]["heart_pct"] if total_g > 0 else 0

    records_to_check = [
        ("allies", 3, "👑", "Mais aliados da casa ({v})", 6),
        ("enemies", 3, "⚔️", "Mais inimigos da casa ({v})", 6),
        ("false_friends", 2, "🎭", "Mais falsos amigos ({v})", 6),
        ("blind_targets", 2, "🙈", "Mais alvos cegos ({v})", 6),
        ("heart_pct", 70, "💝", "Mais generoso com ❤️ ({v}%)", 5),
        ("neg_pct", 50, "💀", "Mais hostil da casa ({v}% negativos)", 5),
    ]

    record_holders = {}
    for field, min_val, icon, template, priority in records_to_check:
        if not record_data:
            continue
        best_name = max(record_data, key=lambda n: record_data[n].get(field, 0))
        best_val = record_data[best_name].get(field, 0)
        if best_val < min_val:
            continue
        tied = [n for n in record_data if record_data[n].get(field, 0) == best_val]
        if len(tied) > 1:
            continue
        record_holders.setdefault(best_name, []).append({
            "icon": icon, "text": template.format(v=best_val), "priority": priority,
        })

    MAX_CURIOSITIES = 8
    for prof in profiles:
        nm = prof["name"]
        if nm in record_holders:
            combined = record_holders[nm] + prof.get("curiosities", [])
            combined.sort(key=lambda x: x.get("priority", 0), reverse=True)
            prof["curiosities"] = [{"icon": c["icon"], "text": c["text"]} for c in combined[:MAX_CURIOSITIES]]
        else:
            prof["curiosities"] = [{"icon": c["icon"], "text": c["text"]} for c in prof.get("curiosities", [])[:MAX_CURIOSITIES]]


def _build_saldo_card(profiles: list[dict], *, display_limit: int = 5) -> dict[str, Any] | None:
    """Build a reusable saldo de estalecas card payload from profile view-models."""
    if not profiles:
        return None

    saldo_profiles = sorted(
        profiles,
        key=lambda p: (-int(p.get("balance", 0) or 0), str(p.get("name", ""))),
    )
    if not saldo_profiles:
        return None

    max_bal = max(abs(int(p.get("balance", 0) or 0)) for p in saldo_profiles) or 1
    medals = ["🥇", "🥈", "🥉", "4º", "5º"]
    items_all = []
    for idx, prof in enumerate(saldo_profiles, start=1):
        balance = int(prof.get("balance", 0) or 0)
        grupo = prof.get("group", "")
        border_color = GROUP_COLORS.get(grupo, "#999")
        balance_color = (
            "#1a9850" if balance > 1000 else
            ("#66bd63" if balance > 0 else ("#888" if balance == 0 else "#e74c3c"))
        )
        items_all.append({
            "name": prof.get("name", ""),
            "first_name": (prof.get("name", "") or "").split()[0] if prof.get("name") else "?",
            "group": grupo,
            "rank": idx,
            "rank_label": medals[idx - 1] if idx <= len(medals) else f"{idx}º",
            "border_color": border_color,
            "balance": balance,
            "balance_color": balance_color,
            "bar_pct": min(100, abs(balance) / max_bal * 100) if max_bal > 0 else 0,
        })

    return {
        "type": "saldo",
        "icon": "💰",
        "title": "Saldo de Estalecas",
        "link": "evolucao.html#saldo",
        "source_tag": "📸 Dado do dia",
        "subtitle": "Ranking dos participantes com mais estalecas. Moeda do jogo usada em compras e dinâmicas de poder.",
        "display_limit": display_limit,
        "max_balance": max_bal,
        "total": len(items_all),
        "items": items_all[:display_limit],
        "items_all": items_all,
    }


def _build_eliminated_list(ctx: dict[str, Any]) -> list[dict]:
    """Eliminated/exited participant list."""
    manual_events = ctx["manual_events"]
    avatars = ctx["avatars"]
    member_of = ctx["member_of"]

    eliminated_list = []
    manual_participants = manual_events.get("participants", {})
    for exit_name, exit_info in manual_participants.items():
        if not isinstance(exit_info, dict):
            continue
        status = exit_info.get("status", "")
        status_labels = {
            "eliminada": "Eliminada",
            "eliminado": "Eliminado",
            "desistente": "Desistente",
            "desclassificado": "Desclassificado",
            "desclassificada": "Desclassificada",
        }
        label = status_labels.get(status, status.capitalize())
        eliminated_list.append({
            "name": exit_name,
            "status": status,
            "status_label": label,
            "exit_date": exit_info.get("exit_date", ""),
            "exit_reason": exit_info.get("exit_reason", ""),
            "paredao_numero": exit_info.get("paredao_numero"),
            "avatar": avatars.get(exit_name, ""),
            "member_of": member_of.get(exit_name, "?"),
        })
    eliminated_list.sort(key=lambda x: x.get("exit_date", ""))
    return eliminated_list


# ── Main orchestrator ─────────────────────────────────────────────────────


def build_index_data() -> dict | None:
    snapshots = get_all_snapshots()
    if not snapshots:
        print("No snapshots found. Skipping index data.")
        return None

    daily_snapshots = get_daily_snapshots(snapshots)
    daily_matrices = [build_reaction_matrix(s["participants"]) for s in daily_snapshots]

    # 1. Shared context (loads JSONs, computes member_of, avatars, roles, VIP, etc.)
    ctx = _build_shared_context(snapshots, daily_snapshots, daily_matrices)

    # 2. Highlights and cards
    hl = _build_highlights_and_cards(ctx)
    ctx["sinc_week_used"] = hl["sinc_week_used"]
    ctx["sinc_reference_matrix"] = hl.get("sinc_reference_matrix", ctx["latest_matrix"])

    # 3. Overview stats
    ov = _build_overview_stats(ctx)

    # 4. Ranking tables + timelines
    rk = _build_ranking_tables(ctx)

    # 5. Cross table and reaction summary
    ct = _build_cross_table_and_summary(ctx)

    # 6. Curiosity lookups
    lookups = _build_curiosity_lookups(ctx)

    # 7. Build profiles
    active = ctx["active"]
    profiles = []
    for p in sorted(active, key=lambda x: x["name"]):
        profiles.append(_build_profile_entry(p["name"], ctx, lookups))

    # 8. Record-holder curiosities (post-processing)
    _build_record_holder_curiosities(profiles, ctx)
    saldo_card = _build_saldo_card(profiles)

    # 9. Eliminated list
    eliminated_list = _build_eliminated_list(ctx)

    # Big Fone consensus analysis
    def pair_sentiment(giver: str, receiver: str) -> float:
        rel = ctx["relations_pairs"].get(giver, {}).get(receiver)
        if rel:
            return rel.get("score", 0)
        label = ctx["latest_matrix"].get((giver, receiver), "")
        return SENTIMENT_WEIGHTS.get(label, 0)

    big_fone_consensus = build_big_fone_consensus(
        ctx["manual_events"], ctx["current_cycle"], ctx["active_names"], ctx["active_set"],
        ctx["avatars"], ctx["member_of"], ctx["roles_current"], ctx["latest_matrix"], pair_sentiment,
    )

    latest_paredao = None
    paredao_card = None
    transformed_paredoes = load_paredoes_transformed(member_of=ctx["member_of"])
    if transformed_paredoes:
        latest_paredao = transformed_paredoes[-1]
        # If latest paredão has no nominees yet, show the last finalized result instead
        if not latest_paredao.get("participantes") and len(transformed_paredoes) >= 2:
            last_finalized = next(
                (p for p in reversed(transformed_paredoes[:-1]) if p.get("status") == "finalizado"),
                None,
            )
            if last_finalized:
                latest_paredao = last_finalized
        polls_data = load_votalhada_polls()
        current_poll = get_poll_for_paredao(polls_data, latest_paredao["numero"])
        history = build_paredao_history(ctx["paredoes"].get("paredoes", []), latest_paredao["numero"])
        paredao_card = build_paredao_card_payload(latest_paredao, current_poll, polls_data, history)

    paredao_names = [n["name"] for n in paredao_card.get("nominees", [])] if paredao_card else hl["paredao_names"]
    paredao_status = {
        "names": sorted(paredao_names),
        "status": (paredao_card or {}).get("status_label", "Em Votação" if paredao_names else "Aguardando formação"),
        "card": paredao_card,
    }

    for card in hl["cards"]:
        if card.get("type") == "context":
            card["cycle"] = ctx["current_cycle"]

    hl["cards"] = [c for c in hl["cards"] if c.get("type") != "paredao"]
    if paredao_card and paredao_card.get("state") != "empty":
        is_finalized_paredao = paredao_card.get("state") == "finalized"
        hl["cards"].append({
            "type": "paredao",
            "icon": "🗳️",
            "title": "Último Paredão" if is_finalized_paredao else "Paredão Ativo",
            "subtitle": (
                "Resumo do paredão encerrado; o card volta ao modo ativo quando o próximo for formado."
                if is_finalized_paredao
                else "Leitura atual do paredão; quando fechar, o card troca para o resultado oficial."
            ),
            "color": paredao_card.get("status_color", "#e74c3c"),
            "link": "paredao.html",
            "payload": paredao_card,
        })

    payload = {
        "_metadata": {"generated_at": datetime.now(timezone.utc).isoformat()},
        "latest": {
            "date": ctx["latest_date"],
            "label": ctx["latest_date"],
        },
        "current_cycle": ctx["current_cycle"],
        "active_names": ctx["active_names"],
        "member_of": ctx["member_of"],
        "avatars": ctx["avatars"],
        "highlights": {
            "date_display": ov["date_display"],
            "items": hl["highlights"],
            "cards": hl["cards"],
        },
        "contradictions": hl["pair_contradictions"],
        "overview": {
            "n_active": len(active),
            "groups": ov["groups"],
            "total_hearts": ov["total_hearts"],
            "total_negative": ov["total_negative"],
            "n_two_sided": ov["n_two_sided"],
            "n_one_sided": ov["n_one_sided"],
            "n_blind_spots": len(ov["blind_spot_victims"]),
            "n_daily": len(ctx["daily_snapshots"]),
            "date_display": ov["date_display"],
        },
        "paredao": paredao_status,
        "watchlist": ov["top_vulnerable"],
        "ranking": {
            "height": max(500, len(active) * 32),
            "today": rk["ranking_today"],
            "yesterday_label": rk["yesterday_label"],
            "week_label": rk["week_ago_label"],
            "change_yesterday": rk["change_yesterday"],
            "change_week": rk["change_week"],
        },
        "timeline": rk["timeline"],
        "strategic_timeline": rk["strategic_timeline"],
        "cross_table": {
            "names": ct["cross_names"],
            "matrix": ct["cross_matrix"],
        },
        "reaction_summary": {
            "rows": ct["summary_rows"],
            "max_hearts": ct["max_hearts"],
            "max_neg": ct["max_neg"],
        },
        "sincerao": {
            "current_cycle": hl["sinc_week_used"] if hl["available_weeks"] else None,
            "available_weeks": hl["available_weeks"],
            "reaction_reference_date": hl.get("sinc_reference_date"),
            "type_coverage": _compute_sinc_type_coverage(ctx["sinc_data"]),
            "radar": {
                **(hl["sinc_radar"] if isinstance(hl.get("sinc_radar"), dict) else {}),
                "scope": "active_only",
            },
            "pairs": {
                "aligned_positive": hl["pair_aligned_pos"],
                "aligned_negative": hl["pair_aligned_neg"],
                "contradictions": hl["pair_contradictions"],
            },
        },
        "vip": {
            "leader": ctx["house_leader"],
            "leaders": ctx["house_leaders"],
            "leader_start": ctx["leader_start_date"],
            "recipients": sorted(ctx["vip_recipients"]),
            "weight": 0.2,
        },
        "leader_periods": ctx["leader_periods"],
        "profiles": profiles,
        "saldo_card": saldo_card,
        "eliminated": eliminated_list,
        "big_fone_consensus": big_fone_consensus,
        "paredao_exposure": {
            "stats": hl["exposure_stats"],
        },
    }

    return payload


def write_index_data() -> None:
    payload = build_index_data()
    if payload is None:
        return
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DERIVED_DIR / "index_data.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    print(f"Index data written to {output_path}")


if __name__ == "__main__":
    write_index_data()
