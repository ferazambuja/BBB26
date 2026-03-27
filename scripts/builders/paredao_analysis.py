"""Paredão analysis: vote classification, relationship history, badges."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from data_utils import (
    POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE,
    REACTION_EMOJI,
    build_reaction_matrix, calc_sentiment, patch_missing_raio_x, resolve_leaders,
)

DERIVED_DIR = Path(__file__).parent.parent.parent / "data" / "derived"
SPOTLIGHT_TARGET = "Milena"
SPOTLIGHT_ACTORS = ("Alberto Cowboy", "Jonas Sulzbach")
SPOTLIGHT_TRIO = frozenset((SPOTLIGHT_TARGET, *SPOTLIGHT_ACTORS))
NEGATIVE_SINC_TYPES = frozenset({"nao_ganha", "ataque", "paredao_perfeito", "regua_fora"})
POWER_TIMELINE_TYPES = frozenset({"mira_do_lider", "indicacao", "monstro", "barrado_baile", "veto_bate_volta"})
EVENT_TYPE_LABELS = {
    "mira_do_lider": "Na Mira do Líder",
    "indicacao": "Indicação",
    "monstro": "Monstro",
    "barrado_baile": "Barrado no Baile",
    "ataque": "Ataque no Sincerão",
    "nao_ganha": "Não Ganha",
    "paredao_perfeito": "Paredão Perfeito",
    "regua_fora": "Fora da Régua",
}
POWER_DECISION_TYPES = frozenset({"mira_do_lider", "indicacao", "barrado_baile", "veto_bate_volta", "monstro"})
SPOTLIGHT_ALLY = "Ana Paula Renault"
SECRET_SIGNAL_NOTE = (
    "O queridômetro é um sinal privado de sentimento: ajuda a mostrar o clima da relação, "
    "mas pesa menos que ações públicas como indicação, barrado, Monstro e Sincerão."
)


def _story_event_label(event_type: str) -> str:
    return EVENT_TYPE_LABELS.get(event_type, event_type.replace("_", " ").title())


def _is_spotlight_pair(actor: str | None, target: str | None) -> bool:
    return bool(actor and target and actor != target and actor in SPOTLIGHT_TRIO and target in SPOTLIGHT_TRIO)


def _normalize_story_event(
    *,
    actor: str,
    target: str,
    event_type: str,
    date: str,
    week: int | None,
    detail: str = "",
    source_kind: str = "",
) -> dict:
    return {
        "actor": actor,
        "target": target,
        "event_type": event_type,
        "label": _story_event_label(event_type),
        "date": date,
        "cycle": week,
        "detail": detail or _story_event_label(event_type),
        "source_kind": source_kind,
    }


def _group_power_decisions(
    par: dict,
    manual_events: dict | None,
    auto_events: list[dict] | None,
) -> list[dict]:
    grouped: dict[tuple[str, str, str], dict] = {}

    def _register(actor: str, event: dict, source_kind: str) -> None:
        if actor not in SPOTLIGHT_ACTORS:
            return
        if event.get("impacto") != "negativo":
            return
        event_type = event.get("type", "")
        if event_type not in POWER_DECISION_TYPES:
            return
        detail = (event.get("detail") or "").lower()
        # Consensus box dynamics are public mechanics, not discretionary leader-style power use.
        if event_type == "indicacao" and "dinâmica das caixas" in detail:
            return
        key = (actor, event.get("date", ""), event_type)
        entry = grouped.setdefault(key, {
            "actor": actor,
            "date": event.get("date", ""),
            "cycle": event.get("cycle"),
            "event_type": event_type,
            "label": _story_event_label(event_type),
            "targets": [],
            "details": [],
            "source_kinds": set(),
        })
        target = event.get("target")
        if target and target not in entry["targets"]:
            entry["targets"].append(target)
        raw_detail = event.get("detail", "")
        if raw_detail and raw_detail not in entry["details"]:
            entry["details"].append(raw_detail)
        entry["source_kinds"].add(source_kind)

    for event in (manual_events or {}).get("power_events", []):
        actors = event.get("actors") or [event.get("actor")]
        for actor in actors:
            if actor:
                _register(actor, event, "manual")

    for event in auto_events or []:
        actor = event.get("actor")
        if actor:
            _register(actor, event, "auto")

    formacao = par.get("formacao", {})
    if par.get("numero") == 8 and formacao.get("indicado_lider") == SPOTLIGHT_TARGET:
        detail = formacao.get("motivo_indicacao") or formacao.get("motivo_lider") or "Indicação em consenso ao paredão"
        for actor in resolve_leaders(formacao):
            if actor not in SPOTLIGHT_ACTORS:
                continue
            key = (actor, par.get("data_formacao") or par.get("data", ""), "indicacao")
            entry = grouped.setdefault(key, {
                "actor": actor,
                "date": par.get("data_formacao") or par.get("data", ""),
                "cycle": par.get("cycle"),
                "event_type": "indicacao",
                "label": _story_event_label("indicacao"),
                "targets": [],
                "details": [],
                "source_kinds": set(),
            })
            if SPOTLIGHT_TARGET not in entry["targets"]:
                entry["targets"].append(SPOTLIGHT_TARGET)
            if detail and detail not in entry["details"]:
                entry["details"].append(detail)
            entry["source_kinds"].add("paredao")

    rows = []
    for entry in grouped.values():
        rows.append({
            **entry,
            "source_kinds": sorted(entry["source_kinds"]),
        })
    rows.sort(key=lambda item: (item["actor"], item["date"], item["event_type"]))
    return rows


def _build_power_usage_story(
    par: dict,
    manual_events: dict | None,
    auto_events: list[dict] | None,
) -> dict:
    decisions = _group_power_decisions(par, manual_events, auto_events)
    by_actor: dict[str, dict] = {}

    for actor in SPOTLIGHT_ACTORS:
        actor_rows = [row for row in decisions if row["actor"] == actor]
        toward_target = sum(1 for row in actor_rows if SPOTLIGHT_TARGET in row["targets"])
        toward_target_or_ally = sum(1 for row in actor_rows if any(target in (SPOTLIGHT_TARGET, SPOTLIGHT_ALLY) for target in row["targets"]))
        total = len(actor_rows)
        by_actor[actor] = {
            "total": total,
            "toward_target": toward_target,
            "toward_target_pct": round((toward_target / total * 100), 1) if total else 0.0,
            "toward_target_or_ally": toward_target_or_ally,
            "toward_target_or_ally_pct": round((toward_target_or_ally / total * 100), 1) if total else 0.0,
        }

    total = len(decisions)
    toward_target = sum(1 for row in decisions if SPOTLIGHT_TARGET in row["targets"])
    toward_target_or_ally = sum(1 for row in decisions if any(target in (SPOTLIGHT_TARGET, SPOTLIGHT_ALLY) for target in row["targets"]))
    proxy_evidence = []
    for row in decisions:
        if SPOTLIGHT_ALLY not in row["targets"]:
            continue
        detail = " ".join(row["details"]).strip()
        proxy_evidence.append({
            "actor": row["actor"],
            "target": SPOTLIGHT_ALLY,
            "date": row["date"],
            "cycle": row.get("cycle"),
            "event_type": row["event_type"],
            "label": row["label"],
            "detail": detail,
        })

    return {
        "by_actor": by_actor,
        "combined": {
            "total": total,
            "toward_target": toward_target,
            "toward_target_pct": round((toward_target / total * 100), 1) if total else 0.0,
            "toward_target_or_ally": toward_target_or_ally,
            "toward_target_or_ally_pct": round((toward_target_or_ally / total * 100), 1) if total else 0.0,
        },
        "decisions": decisions,
        "proxy_evidence": proxy_evidence,
    }


def _collect_spotlight_timeline(
    par: dict,
    manual_events: dict | None,
    auto_events: list[dict] | None,
    sincerao_edges: dict | None,
) -> list[dict]:
    timeline: list[dict] = []

    for event in (manual_events or {}).get("power_events", []):
        actor = event.get("actor")
        target = event.get("target")
        if not _is_spotlight_pair(actor, target):
            continue
        if event.get("impacto") != "negativo":
            continue
        timeline.append(_normalize_story_event(
            actor=actor,
            target=target,
            event_type=event.get("type", ""),
            date=event.get("date", ""),
            week=event.get("cycle"),
            detail=event.get("detail", ""),
            source_kind="manual",
        ))

    for event in auto_events or []:
        actor = event.get("actor")
        target = event.get("target")
        if not _is_spotlight_pair(actor, target):
            continue
        if event.get("impacto") != "negativo":
            continue
        timeline.append(_normalize_story_event(
            actor=actor,
            target=target,
            event_type=event.get("type", ""),
            date=event.get("date", ""),
            week=event.get("cycle"),
            detail=event.get("detail", ""),
            source_kind="auto",
        ))

    for event in (sincerao_edges or {}).get("edges", []):
        actor = event.get("actor")
        target = event.get("target")
        event_type = event.get("type", "")
        if not _is_spotlight_pair(actor, target):
            continue
        if event_type not in NEGATIVE_SINC_TYPES:
            continue
        detail = event.get("tema", "") or event.get("detail", "") or _story_event_label(event_type)
        timeline.append(_normalize_story_event(
            actor=actor,
            target=target,
            event_type=event_type,
            date=event.get("date", ""),
            week=event.get("cycle"),
            detail=detail,
            source_kind="sincerao",
        ))

    formacao = par.get("formacao", {})
    if par.get("numero") == 8 and formacao.get("indicado_lider") == SPOTLIGHT_TARGET:
        reason = formacao.get("motivo_indicacao") or formacao.get("motivo_lider") or "Indicação em consenso ao paredão"
        for leader in resolve_leaders(formacao):
            if leader not in SPOTLIGHT_ACTORS:
                continue
            timeline.append(_normalize_story_event(
                actor=leader,
                target=SPOTLIGHT_TARGET,
                event_type="indicacao",
                date=par.get("data_formacao") or par.get("data", ""),
                week=par.get("cycle"),
                detail=f"Indicação em consenso. {reason}",
                source_kind="paredao",
            ))

    timeline.sort(key=lambda item: (
        item.get("date", ""),
        item.get("cycle") or 0,
        item.get("actor", ""),
        item.get("target", ""),
        item.get("event_type", ""),
    ))
    return timeline


def _build_spotlight_past_indications(
    paredoes_list: list[dict],
    actors: tuple[str, ...] = SPOTLIGHT_ACTORS,
    target: str = SPOTLIGHT_TARGET,
) -> list[dict]:
    past: list[dict] = []
    for paredao in paredoes_list:
        if paredao.get("status") != "finalizado":
            continue
        formacao = paredao.get("formacao", {})
        leaders = [leader for leader in resolve_leaders(formacao) if leader in actors]
        if not leaders or formacao.get("indicado_lider") != target:
            continue
        resultado = paredao.get("resultado") or {}
        votos = resultado.get("votos") or {}
        eliminated = resultado.get("eliminado")
        if not eliminated:
            continue
        milena_votes = votos.get(target) or {}
        eliminated_votes = votos.get(eliminated) or {}
        if not milena_votes or not eliminated_votes:
            continue
        past.append({
            "paredao_num": paredao.get("numero"),
            "leaders": leaders,
            "reason": formacao.get("motivo_lider") or formacao.get("motivo_indicacao") or "",
            "milena_voto_unico": milena_votes.get("voto_unico"),
            "eliminated": eliminated,
            "eliminated_voto_unico": eliminated_votes.get("voto_unico"),
            "milena_survived": eliminated != target,
        })
    return past


def _resolve_matrix_at_or_before(
    target_date: str,
    daily_snapshots: list[dict],
    daily_matrices: list[dict],
) -> tuple[str, dict[tuple[str, str], str] | None]:
    if not daily_snapshots or not daily_matrices:
        return "", None

    chosen_idx = 0
    for idx, snap in enumerate(daily_snapshots):
        if snap["date"] <= target_date:
            chosen_idx = idx

    return daily_snapshots[chosen_idx]["date"], daily_matrices[chosen_idx]


def _collect_pair_secret_history(
    actor: str,
    target: str,
    daily_snapshots: list[dict],
    daily_matrices: list[dict],
    cutoff_date: str,
) -> list[dict]:
    history: list[dict] = []
    for snap, matrix in zip(daily_snapshots, daily_matrices):
        snap_date = snap["date"]
        if snap_date > cutoff_date:
            break
        label = matrix.get((actor, target), "")
        if not label:
            continue
        reverse_label = matrix.get((target, actor), "")
        history.append({
            "date": snap_date,
            "label": label,
            "emoji": REACTION_EMOJI.get(label, label),
            "reverse_label": reverse_label,
            "reverse_emoji": REACTION_EMOJI.get(reverse_label, reverse_label) if reverse_label else "",
        })
    return history


def _summarize_pair_secret_history(history: list[dict]) -> dict:
    if not history:
        return {
            "days_with_data": 0,
            "ever_sent_heart": False,
            "heart_days": 0,
            "mutual_heart_days": 0,
            "first_non_heart_date": None,
            "last_positive_date": None,
            "days_since_last_positive": None,
            "last_mutual_positive_date": None,
            "days_since_last_mutual_positive": None,
            "latest_label": "",
            "latest_emoji": "",
            "most_frequent_label": "",
            "most_frequent_emoji": "",
            "most_frequent_count": 0,
            "longest_streak": {},
            "current_streak": {},
        }

    counts = Counter(item["label"] for item in history)
    most_frequent_label, most_frequent_count = counts.most_common(1)[0]
    first_non_heart_date = next((item["date"] for item in history if item["label"] != "Coração"), None)
    latest = history[-1]
    cutoff_date = latest["date"]
    last_positive_date = next((item["date"] for item in reversed(history) if item["label"] in POSITIVE), None)
    last_mutual_positive_date = next(
        (
            item["date"]
            for item in reversed(history)
            if item["label"] in POSITIVE and item["reverse_label"] in POSITIVE
        ),
        None,
    )
    mutual_heart_days = sum(
        1
        for item in history
        if item["label"] == "Coração" and item["reverse_label"] == "Coração"
    )

    best_streak = {"label": "", "emoji": "", "length": 0, "start_date": None, "end_date": None}
    current_label = ""
    current_start = None
    current_length = 0
    prev_date = None

    for item in history:
        label = item["label"]
        if label == current_label:
            current_length += 1
        else:
            if current_label and current_length > best_streak["length"]:
                best_streak = {
                    "label": current_label,
                    "emoji": REACTION_EMOJI.get(current_label, current_label),
                    "length": current_length,
                    "start_date": current_start,
                    "end_date": prev_date,
                }
            current_label = label
            current_start = item["date"]
            current_length = 1
        prev_date = item["date"]

    if current_label and current_length > best_streak["length"]:
        best_streak = {
            "label": current_label,
            "emoji": REACTION_EMOJI.get(current_label, current_label),
            "length": current_length,
            "start_date": current_start,
            "end_date": prev_date,
        }

    current_streak_length = 0
    current_streak_start = latest["date"]
    for item in reversed(history):
        if item["label"] != latest["label"]:
            break
        current_streak_length += 1
        current_streak_start = item["date"]

    def _days_since(date_str: str | None) -> int | None:
        if not date_str:
            return None
        return (date.fromisoformat(cutoff_date) - date.fromisoformat(date_str)).days

    return {
        "days_with_data": len(history),
        "ever_sent_heart": "Coração" in counts,
        "heart_days": counts.get("Coração", 0),
        "mutual_heart_days": mutual_heart_days,
        "first_non_heart_date": first_non_heart_date,
        "last_positive_date": last_positive_date,
        "days_since_last_positive": _days_since(last_positive_date),
        "last_mutual_positive_date": last_mutual_positive_date,
        "days_since_last_mutual_positive": _days_since(last_mutual_positive_date),
        "latest_label": latest["label"],
        "latest_emoji": latest["emoji"],
        "most_frequent_label": most_frequent_label,
        "most_frequent_emoji": REACTION_EMOJI.get(most_frequent_label, most_frequent_label),
        "most_frequent_count": most_frequent_count,
        "longest_streak": best_streak,
        "current_streak": {
            "label": latest["label"],
            "emoji": latest["emoji"],
            "length": current_streak_length,
            "start_date": current_streak_start,
            "end_date": latest["date"],
        },
    }


def _build_secret_queridometro_story(
    daily_snapshots: list[dict],
    daily_matrices: list[dict],
    cutoff_date: str,
    formation_day_reactions: dict[str, dict[str, str]],
) -> dict:
    pairs: dict[str, dict] = {}
    for actor in SPOTLIGHT_ACTORS:
        pairs[actor] = {
            "to_target": _summarize_pair_secret_history(
                _collect_pair_secret_history(actor, SPOTLIGHT_TARGET, daily_snapshots, daily_matrices, cutoff_date)
            ),
            "from_target": _summarize_pair_secret_history(
                _collect_pair_secret_history(SPOTLIGHT_TARGET, actor, daily_snapshots, daily_matrices, cutoff_date)
            ),
        }

    alberto = pairs["Alberto Cowboy"]
    jonas = pairs["Jonas Sulzbach"]
    facts = []

    if alberto["to_target"]["ever_sent_heart"] and alberto["to_target"]["mutual_heart_days"] == 0:
        facts.append(
            "Alberto até mandou ❤️ para Milena no começo, mas os dois nunca ficaram em ❤️ mútuo no mesmo dia."
        )

    if jonas["to_target"]["mutual_heart_days"] > 0:
        facts.append(
            f"Jonas e Milena tiveram {jonas['to_target']['mutual_heart_days']} dia(s) de ❤️ mútuo antes de a relação azedar."
        )

    facts.append(
        "No domingo da formação, o retrato secreto já era "
        f"Alberto {REACTION_EMOJI.get(formation_day_reactions['Alberto Cowboy']['to_target'], formation_day_reactions['Alberto Cowboy']['to_target'])} "
        f"Milena e Milena {REACTION_EMOJI.get(formation_day_reactions['Alberto Cowboy']['from_target'], formation_day_reactions['Alberto Cowboy']['from_target'])} Alberto; "
        f"Jonas {REACTION_EMOJI.get(formation_day_reactions['Jonas Sulzbach']['to_target'], formation_day_reactions['Jonas Sulzbach']['to_target'])} "
        f"Milena e Milena {REACTION_EMOJI.get(formation_day_reactions['Jonas Sulzbach']['from_target'], formation_day_reactions['Jonas Sulzbach']['from_target'])} Jonas."
    )
    facts.append(
        "No fechamento desse recorte, Alberto termina em "
        f"{alberto['to_target']['latest_emoji']} contra Milena; "
        f"Milena responde com {alberto['from_target']['latest_emoji']} para Alberto; "
        f"Jonas fecha em {jonas['to_target']['latest_emoji']} e Milena em {jonas['from_target']['latest_emoji']}."
    )

    return {
        "private_signal_note": SECRET_SIGNAL_NOTE,
        "pairs": pairs,
        "facts": facts,
    }


def _build_week8_featured_story(
    par: dict,
    paredoes_list: list[dict],
    matrix_p: dict[tuple[str, str], str] | None,
    daily_snapshots: list[dict],
    daily_matrices: list[dict],
    manual_events: dict | None,
    auto_events: list[dict] | None,
    sincerao_edges: dict | None,
) -> dict | None:
    if par.get("numero") != 8:
        return None

    formacao = par.get("formacao", {})
    leaders = [leader for leader in resolve_leaders(formacao) if leader in SPOTLIGHT_ACTORS]
    if formacao.get("indicado_lider") != SPOTLIGHT_TARGET or set(leaders) != set(SPOTLIGHT_ACTORS):
        return None

    formation_day_date, formation_matrix = _resolve_matrix_at_or_before(
        par.get("data_formacao") or par.get("data", ""),
        daily_snapshots,
        daily_matrices,
    )
    if formation_matrix is None:
        formation_day_date = par.get("data_formacao") or par.get("data", "")
        formation_matrix = matrix_p or {}

    timeline = _collect_spotlight_timeline(par, manual_events, auto_events, sincerao_edges)
    if not timeline:
        return None

    summary_counts = {
        f"{leader}->{SPOTLIGHT_TARGET}": sum(
            1 for item in timeline if item["actor"] == leader and item["target"] == SPOTLIGHT_TARGET
        )
        for leader in SPOTLIGHT_ACTORS
    }
    for leader in SPOTLIGHT_ACTORS:
        summary_counts[f"{SPOTLIGHT_TARGET}->{leader}"] = sum(
            1 for item in timeline if item["actor"] == SPOTLIGHT_TARGET and item["target"] == leader
        )
    summary_counts["leaders_to_target_total"] = sum(
        summary_counts[f"{leader}->{SPOTLIGHT_TARGET}"] for leader in SPOTLIGHT_ACTORS
    )
    summary_counts["target_back_total"] = sum(
        summary_counts[f"{SPOTLIGHT_TARGET}->{leader}"] for leader in SPOTLIGHT_ACTORS
    )

    formation_day_reactions = {}
    for leader in SPOTLIGHT_ACTORS:
        formation_day_reactions[leader] = {
            "to_target": formation_matrix.get((leader, SPOTLIGHT_TARGET), "") if formation_matrix else "",
            "from_target": formation_matrix.get((SPOTLIGHT_TARGET, leader), "") if formation_matrix else "",
        }

    return {
        "kind": "milena_targeted_by_dual_leaders",
        "title": "Milena no alvo de Alberto e Jonas",
        "target": SPOTLIGHT_TARGET,
        "actors": list(SPOTLIGHT_ACTORS),
        "summary_counts": summary_counts,
        "formation_day_date": formation_day_date,
        "formation_day_reactions": formation_day_reactions,
        "timeline": timeline,
        "past_leader_indications": _build_spotlight_past_indications(paredoes_list),
        "power_usage": _build_power_usage_story(par, manual_events, auto_events),
        "secret_queridometro": _build_secret_queridometro_story(
            daily_snapshots,
            daily_matrices,
            formation_day_date,
            formation_day_reactions,
        ),
        "thesis": "Alberto e Jonas acumularam um histórico bem mais longo de ataques diretos contra Milena do que ela construiu de volta.",
        "caveat": "Milena também devolveu menos e mais tarde, sobretudo a partir da semana 6.",
    }


def _compute_pair_relationship_history(
    actor: str,
    target: str,
    daily_matrices: list[dict],
    daily_snapshots: list[dict],
    is_finalizado: bool,
    analysis_date: str,
) -> dict:
    """Compute relationship history between actor→target from daily matrices.

    Returns a dict with pattern, days_as_friends/enemies, change_date, narrative.
    """
    all_neg = MILD_NEGATIVE | STRONG_NEGATIVE
    history = []
    days_positive = 0
    days_negative = 0
    days_mutual_positive = 0
    change_date = None
    prev_was_positive = None

    for i, mat in enumerate(daily_matrices):
        snap_date = daily_snapshots[i]["date"]
        if is_finalizado and snap_date > analysis_date:
            break
        rxn_v = mat.get((actor, target), "")
        if not rxn_v:
            continue
        rxn_a = mat.get((target, actor), "")
        v_pos = rxn_v in POSITIVE
        v_neg = rxn_v in all_neg
        history.append((snap_date, rxn_v, rxn_a))
        if v_pos:
            days_positive += 1
            if prev_was_positive is False:
                change_date = snap_date
        elif v_neg:
            days_negative += 1
            if prev_was_positive is True:
                change_date = snap_date
        if v_pos and rxn_a in POSITIVE:
            days_mutual_positive += 1
        prev_was_positive = v_pos

    total_hist_days = len(history)
    if total_hist_days == 0:
        return {"pattern": "sem_dados", "days_as_friends": 0, "days_as_enemies": 0,
                "days_mutual_friends": 0, "change_date": None,
                "narrative": "Sem dados", "total_days": 0}

    current_positive = history[-1][1] in POSITIVE
    if days_positive == total_hist_days:
        pattern, narrative = "sempre_amigos", f"Sempre deu ❤️ ({days_positive} dias)."
    elif days_negative == total_hist_days:
        pattern, narrative = "sempre_inimigos", f"Inimigos desde o início ({days_negative} dias)."
    elif days_positive > 0 and not current_positive and change_date:
        days_since = sum(1 for d, _, _ in history if d >= change_date)
        if days_since <= 2:
            pattern, narrative = "recem_inimigos", f"Eram amigos por {days_positive} dias, mudou há {days_since} dia(s)!"
        else:
            pattern, narrative = "ex_amigos", f"Foram amigos por {days_positive} dias, romperam em {change_date}."
    elif days_negative > 0 and current_positive and change_date:
        pattern, narrative = "reconciliados", f"Reconciliaram em {change_date}."
    else:
        pattern, narrative = "instavel", f"Instável: {days_positive}d ❤️, {days_negative}d negativo."

    return {"pattern": pattern, "days_as_friends": days_positive,
            "days_as_enemies": days_negative,
            "days_mutual_friends": days_mutual_positive,
            "change_date": change_date,
            "narrative": narrative, "total_days": total_hist_days}


def _build_paredao_vote_analysis(
    votos: dict[str, str],
    relationship_history: dict[str, dict],
    matrix_p: dict[tuple[str, str], str] | None,
) -> tuple[list[dict], Counter]:
    """Classify each house vote by relationship type (voter→target reaction patterns).

    Returns (vote_analysis list, relationship_counts Counter).
    """
    vote_analysis: list[dict] = []
    relationship_counts: Counter = Counter()
    for votante, alvo in votos.items():
        if not votante or not alvo or matrix_p is None:
            continue
        rxn_v = matrix_p.get((votante, alvo), "")
        rxn_a = matrix_p.get((alvo, votante), "")
        v_pos = rxn_v in POSITIVE
        a_pos = rxn_a in POSITIVE
        v_neg = rxn_v in (MILD_NEGATIVE | STRONG_NEGATIVE)
        a_neg = rxn_a in (MILD_NEGATIVE | STRONG_NEGATIVE)
        v_strong = rxn_v in STRONG_NEGATIVE

        if v_pos and a_pos:
            rel_type, rel_label, rel_color = "aliados_mutuos", "💔 Traição de Aliado", "#9b59b6"
        elif v_pos and not a_pos:
            rel_type, rel_label, rel_color = "falso_amigo", "🎭 Falso Amigo", "#E6194B"
        elif v_neg and a_neg:
            rel_type, rel_label, rel_color = "inimigos_declarados", "⚔️ Hostilidade Mútua", "#3CB44B"
        elif v_neg and a_pos:
            rel_type, rel_label, rel_color = "ponto_cego", "🎯 Ponto Cego do Alvo", "#f39c12"
        elif v_strong:
            rel_type, rel_label, rel_color = "hostilidade_forte", "🐍 Hostilidade Forte", "#3CB44B"
        elif v_neg:
            rel_type, rel_label, rel_color = "hostilidade_leve", "🌱 Hostilidade Leve", "#FF9800"
        else:
            rel_type, rel_label, rel_color = "neutro", "❓ Neutro", "#999"

        rh_key = f"{votante}→{alvo}"
        hist = relationship_history.get(rh_key, {})
        vote_analysis.append({
            "votante": votante,
            "alvo": alvo,
            "tipo": rel_type,
            "label": rel_label,
            "cor": rel_color,
            "emoji_dado": REACTION_EMOJI.get(rxn_v, "?"),
            "emoji_recebido": REACTION_EMOJI.get(rxn_a, "?"),
            "hist_pattern": hist.get("pattern", "sem_dados"),
            "hist_narrative": hist.get("narrative", "Sem dados"),
            "days_as_friends": hist.get("days_as_friends", 0),
            "days_as_enemies": hist.get("days_as_enemies", 0),
            "days_mutual_friends": hist.get("days_mutual_friends", 0),
            "change_date": hist.get("change_date"),
            "total_days": hist.get("total_days", 0),
        })
        relationship_counts[rel_type] += 1

    return vote_analysis, relationship_counts


def _build_paredao_summary_stats(
    par: dict,
    indicados: list[str],
    votos: dict[str, str],
    vote_analysis: list[dict],
    relationship_counts: Counter,
    relationship_history: dict[str, dict],
    matrix_p: dict[tuple[str, str], str] | None,
    daily_matrices: list[dict],
    daily_snapshots: list[dict],
    is_finalizado: bool,
    analysis_date: str,
) -> dict:
    """Compute aggregate vote stats, per-nominee breakdowns, and indicator pair analysis.

    Returns dict with vote_aggregates, per_nominee, indicator_pairs, indicator_reactions.
    """
    # Aggregate stats
    vote_counts_agg = Counter(votos.values())
    mais_votado, n_votos_mais = vote_counts_agg.most_common(1)[0] if vote_counts_agg else ("", 0)
    n_traicoes = sum(1 for v in vote_analysis if v["tipo"] in ("falso_amigo", "aliados_mutuos"))
    n_pontos_cegos = sum(1 for v in vote_analysis if v["tipo"] == "ponto_cego")
    n_esperados = sum(relationship_counts.get(t, 0) for t in ("inimigos_declarados", "hostilidade_forte", "hostilidade_leve"))

    # ── Per-nominee aggregates (vote breakdown per target) ──
    per_nominee: dict[str, dict] = {}
    for nome in indicados:
        votes_for = [v for v in vote_analysis if v["alvo"] == nome]
        per_nominee[nome] = {
            "n_votes": len(votes_for),
            "from_enemies": sum(1 for v in votes_for if v["tipo"] in ("inimigos_declarados", "hostilidade_forte", "hostilidade_leve")),
            "from_traitors": sum(1 for v in votes_for if v["tipo"] in ("falso_amigo", "aliados_mutuos")),
            "from_blind": sum(1 for v in votes_for if v["tipo"] == "ponto_cego"),
            "from_neutral": sum(1 for v in votes_for if v["tipo"] == "neutro"),
            "voters": [v["votante"] for v in votes_for],
        }

    # ── Indicator relationship pairs (Líder→indicado, Contragolpe, Dinâmica actors) ──
    formacao = par.get("formacao", {})
    indicator_pairs: list[dict] = []

    indicado_lider = formacao.get("indicado_lider")
    if indicado_lider:
        for lider in resolve_leaders(formacao):
            indicator_pairs.append({"actor": lider, "target": indicado_lider, "type": "lider"})

    contragolpe = formacao.get("contragolpe")
    if contragolpe and contragolpe.get("de") and contragolpe.get("para"):
        indicator_pairs.append({"actor": contragolpe["de"], "target": contragolpe["para"], "type": "contragolpe"})

    big_fone = formacao.get("big_fone")
    if big_fone and big_fone.get("atendeu") and big_fone.get("indicou"):
        indicator_pairs.append({"actor": big_fone["atendeu"], "target": big_fone["indicou"], "type": "big_fone"})

    dinamica = formacao.get("dinamica")
    if dinamica and dinamica.get("indicaram") and dinamica.get("indicado"):
        for actor in dinamica["indicaram"]:
            indicator_pairs.append({"actor": actor, "target": dinamica["indicado"], "type": "dinamica"})

    # Build relationship history for indicator pairs not already in votos_casa
    for pair in indicator_pairs:
        actor, target = pair["actor"], pair["target"]
        key = f"{actor}→{target}"
        if key not in relationship_history and matrix_p:
            relationship_history[key] = _compute_pair_relationship_history(
                actor, target, daily_matrices, daily_snapshots, is_finalizado, analysis_date)

        # Also add reverse direction (target→actor)
        rev_key = f"{target}→{actor}"
        if rev_key not in relationship_history and matrix_p:
            relationship_history[rev_key] = _compute_pair_relationship_history(
                target, actor, daily_matrices, daily_snapshots, is_finalizado, analysis_date)

    # Add indicator reaction snapshots at analysis date
    indicator_reactions: list[dict] = []
    for pair in indicator_pairs:
        actor, target = pair["actor"], pair["target"]
        if matrix_p:
            rxn_at = matrix_p.get((actor, target), "")
            rxn_ta = matrix_p.get((target, actor), "")
        else:
            rxn_at, rxn_ta = "", ""
        indicator_reactions.append({
            "actor": actor,
            "target": target,
            "type": pair["type"],
            "actor_to_target": REACTION_EMOJI.get(rxn_at, "?"),
            "target_to_actor": REACTION_EMOJI.get(rxn_ta, "?"),
            "actor_to_target_raw": rxn_at,
            "target_to_actor_raw": rxn_ta,
        })

    return {
        "vote_aggregates": {
            "relationship_counts": dict(relationship_counts),
            "vote_counts": dict(vote_counts_agg),
            "mais_votado": mais_votado,
            "n_votos_mais": n_votos_mais,
            "n_traicoes": n_traicoes,
            "n_pontos_cegos": n_pontos_cegos,
            "n_esperados": n_esperados,
            "total_votes": len(votos),
        },
        "per_nominee": per_nominee,
        "indicator_pairs": indicator_pairs,
        "indicator_reactions": indicator_reactions,
    }


def _analyze_single_paredao(
    par: dict,
    daily_snapshots: list[dict],
    daily_matrices: list[dict],
    paredoes_list: list[dict],
    manual_events: dict | None = None,
    auto_events: list[dict] | None = None,
    sincerao_edges: dict | None = None,
) -> dict | None:
    """Analyze a single paredão: nominee stats, relationship history, vote analysis.

    Returns a dict with the full analysis for this paredão, or None if skipped.
    """
    numero = par.get("numero")
    if not numero:
        return None
    data_formacao = par.get("data_formacao") or par.get("data", "")
    status = par.get("status", "")
    indicados = par.get("indicados_finais", par.get("participantes", []))
    if isinstance(indicados, list):
        indicados = [p.get("nome", p) if isinstance(p, dict) else p for p in indicados]

    is_finalizado = status == "finalizado"
    analysis_date = data_formacao

    # Find snapshot for analysis
    snap_for_analysis = None
    if is_finalizado:
        for snap in reversed(daily_snapshots):
            if snap["date"] <= analysis_date:
                snap_for_analysis = snap
                break
        if snap_for_analysis is None and daily_snapshots:
            snap_for_analysis = daily_snapshots[0]
    else:
        snap_for_analysis = daily_snapshots[-1] if daily_snapshots else None

    if not snap_for_analysis:
        return None

    if not is_finalizado:
        analysis_date = snap_for_analysis["date"]

    # Sentiment in analysis snapshot
    sent_paredao: dict[str, float] = {}
    neg_paredao: dict[str, int] = {}
    for p in snap_for_analysis["participants"]:
        if p.get("characteristics", {}).get("eliminated"):
            continue
        name = p["name"]
        sent_paredao[name] = calc_sentiment(p)
        neg_paredao[name] = sum(
            r["amount"] for r in p.get("characteristics", {}).get("receivedReactions", [])
            if r["label"] != "Coração"
        )

    # Ranking
    ranking_paredao = sorted(sent_paredao.items(), key=lambda x: x[1], reverse=True)
    rank_map = {name: i + 1 for i, (name, _) in enumerate(ranking_paredao)}

    # Historical daily series (up to analysis_date for finalizado)
    daily_sent: list[tuple[str, dict[str, float]]] = []
    for snap in daily_snapshots:
        date = snap["date"]
        if is_finalizado and date > analysis_date:
            continue
        day_scores: dict[str, float] = {}
        for p in snap["participants"]:
            if p.get("characteristics", {}).get("eliminated"):
                continue
            day_scores[p["name"]] = calc_sentiment(p)
        daily_sent.append((date, day_scores))

    # Top5/Bottom5 counts
    top5_counts: Counter = Counter()
    bottom5_counts: Counter = Counter()
    for _date, scores in daily_sent:
        sorted_names = sorted(scores.keys(), key=lambda n: scores[n], reverse=True)
        for n in sorted_names[:5]:
            top5_counts[n] += 1
        for n in sorted_names[-5:]:
            bottom5_counts[n] += 1

    # Build per-indicado stats
    indicados_stats = _analyze_nominees(indicados, daily_sent, sent_paredao, rank_map,
                                        top5_counts, bottom5_counts, neg_paredao)

    # Historical series for indicados
    historical_series: list[dict] = []
    for date, scores in daily_sent:
        for nome in indicados:
            if nome in scores:
                historical_series.append({
                    "date": date,
                    "name": nome,
                    "sentiment": round(scores[nome], 2),
                })

    # Relationship history for each voter→target pair
    votos = par.get("votos_casa", {}) or {}
    relationship_history: dict[str, dict] = {}
    for votante, alvo in votos.items():
        if not votante or not alvo:
            continue
        key = f"{votante}→{alvo}"
        relationship_history[key] = _compute_pair_relationship_history(
            votante, alvo, daily_matrices, daily_snapshots, is_finalizado, analysis_date)

    # Find the matrix at the analysis date
    matrix_p = None
    for idx_snap in range(len(daily_snapshots) - 1, -1, -1):
        if daily_snapshots[idx_snap]["date"] <= analysis_date:
            matrix_p = daily_matrices[idx_snap]
            break
    if matrix_p is None and daily_matrices:
        matrix_p = daily_matrices[0]

    # Vote classification
    vote_analysis, relationship_counts = _build_paredao_vote_analysis(
        votos, relationship_history, matrix_p)

    # Summary stats (aggregates, per-nominee, indicator pairs)
    summary = _build_paredao_summary_stats(
        par, indicados, votos, vote_analysis, relationship_counts,
        relationship_history, matrix_p, daily_matrices, daily_snapshots,
        is_finalizado, analysis_date)

    return {
        "numero": numero,
        "status": status,
        "data_formacao": data_formacao,
        "indicados": indicados,
        "quick_insights": {
            "analysis_date": analysis_date,
            "indicados_stats": indicados_stats,
            "historical_series": historical_series,
            "negs_recebidas": {nome: neg_paredao.get(nome, 0) for nome in indicados},
        },
        "relationship_history": relationship_history,
        "vote_analysis": vote_analysis,
        "featured_story": _build_week8_featured_story(
            par,
            paredoes_list,
            matrix_p,
            daily_snapshots,
            daily_matrices,
            manual_events,
            auto_events,
            sincerao_edges,
        ),
        **summary,
    }


def _analyze_nominees(
    indicados: list[str],
    daily_sent: list[tuple[str, dict[str, float]]],
    sent_paredao: dict[str, float],
    rank_map: dict[str, int],
    top5_counts: Counter,
    bottom5_counts: Counter,
    neg_paredao: dict[str, int],
) -> list[dict]:
    """Build per-nominee stats (sentiment, trend, top5/bottom5 counts)."""
    def _trend_3d(name):
        series = [scores.get(name) for _, scores in daily_sent if name in scores]
        if len(series) < 2:
            return None
        last = series[-1]
        if len(series) >= 4:
            prev = sum(series[-4:-1]) / 3
        else:
            prev = sum(series[:-1]) / (len(series) - 1)
        return last - prev

    indicados_stats = []
    for nome in indicados:
        series = [scores.get(nome) for _, scores in daily_sent if nome in scores]
        total_days = len(series)
        neg_days = sum(1 for v in series if v is not None and v < 0)
        pct_neg = (neg_days / total_days * 100) if total_days else 0

        delta = _trend_3d(nome)
        if delta is None:
            delta_str = "—"
        elif delta >= 0.8:
            delta_str = f"▲ +{delta:.1f}"
        elif delta <= -0.8:
            delta_str = f"▼ {delta:.1f}"
        else:
            delta_str = f"≈ {delta:+.1f}"

        indicados_stats.append({
            "nome": nome,
            "sentimento": round(sent_paredao.get(nome, 0), 1),
            "rank": rank_map.get(nome, 0),
            "delta_3d": delta_str,
            "dias_top5": top5_counts.get(nome, 0),
            "dias_bottom5": bottom5_counts.get(nome, 0),
            "dias_negativos": f"{neg_days}/{total_days} ({pct_neg:.0f}%)",
            "negs_recebidas": neg_paredao.get(nome, 0),
        })
    return indicados_stats


def build_paredao_analysis(
    daily_snapshots: list[dict],
    paredoes_data: dict | None,
    manual_events: dict | None = None,
    auto_events: list[dict] | None = None,
    sincerao_edges: dict | None = None,
    relations_scores: dict | None = None,
) -> dict:
    """Build quick insights and relationship history for each paredão.

    Returns a dict keyed by paredão number with stats for each nominee
    and relationship history for each voter→target pair.
    """
    by_paredao = {}
    paredoes_list = paredoes_data.get("paredoes", []) if paredoes_data else []

    # Build daily matrices once (with missing Raio-X patching)
    daily_matrices = []
    prev_matrix = {}
    for snap in daily_snapshots:
        active = [p for p in snap["participants"]
                  if not p.get("characteristics", {}).get("eliminated")]
        matrix = build_reaction_matrix(active)
        matrix, _carried = patch_missing_raio_x(matrix, snap["participants"], prev_matrix)
        daily_matrices.append(matrix)
        prev_matrix = matrix

    _ = relations_scores
    for par in paredoes_list:
        result = _analyze_single_paredao(
            par,
            daily_snapshots,
            daily_matrices,
            paredoes_list,
            manual_events=manual_events,
            auto_events=auto_events,
            sincerao_edges=sincerao_edges,
        )
        if result is not None:
            by_paredao[str(result["numero"])] = result

    return {"by_paredao": by_paredao}


def build_paredao_badges(daily_snapshots: list[dict], paredoes_data: dict | None) -> dict:
    """Build badge-vs-reality analysis for each paredão.

    Computes per-participant vulnerability, impact, and vote counts
    at each paredão formation date.
    """
    paredoes_list = paredoes_data.get("paredoes", []) if paredoes_data else []
    relations_file = DERIVED_DIR / "relations_scores.json"
    relations_data = {}
    if relations_file.exists():
        with open(relations_file, encoding="utf-8") as f:
            relations_data = json.load(f)
    received_impact = relations_data.get("received_impact", {})

    # Precompute votes received by week
    votes_received_by_week = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    for par in paredoes_list:
        votos = par.get("votos_casa", {}) or {}
        if not votos:
            continue
        week = par.get("cycle")
        for voter, target in votos.items():
            votes_received_by_week[week][target][voter] += 1

    by_paredao = {}
    for par in paredoes_list:
        data_form = par.get("data_formacao") or par.get("data")
        week = par.get("cycle")
        numero = par.get("numero")
        if not data_form or not week or not numero:
            continue

        # Find snapshot on or before formation date
        snap_found = None
        for snap in reversed(daily_snapshots):
            if snap["date"] <= data_form:
                snap_found = snap
                break
        if not snap_found:
            continue

        active = [p for p in snap_found["participants"]
                  if not p.get("characteristics", {}).get("eliminated")]
        active_names = [p["name"] for p in active]
        matrix = build_reaction_matrix(active)

        # Ineligible from paredão formation
        ineligible = set()
        indicacoes = defaultdict(int)
        form = par.get("formacao", {}) if isinstance(par.get("formacao"), dict) else {}
        indicado_lider = form.get("indicado_lider")
        if indicado_lider:
            ineligible.add(indicado_lider)
            indicacoes[indicado_lider] += 1
        bf = form.get("big_fone") or {}
        if isinstance(bf, dict) and bf.get("indicou"):
            ineligible.add(bf.get("indicou"))
            indicacoes[bf.get("indicou")] += 1
        cg = form.get("contragolpe") or {}
        if isinstance(cg, dict) and cg.get("para"):
            ineligible.add(cg.get("para"))
            indicacoes[cg.get("para")] += 1
        din = form.get("dinamica") or {}
        alvo = din.get("indicado")
        if alvo:
            ineligible.add(alvo)
            indicacoes[alvo] += 1
        im = form.get("imunizado") or {}
        if isinstance(im, dict) and im.get("quem"):
            ineligible.add(im.get("quem"))

        badges = []
        for p in active:
            name = p["name"]
            # False friends (vulnerability)
            ff = 0
            for b in active_names:
                if b == name:
                    continue
                my = matrix.get((name, b))
                their = matrix.get((b, name))
                if my in POSITIVE and their and their not in POSITIVE:
                    ff += 1
            if ff >= 5:
                vuln = "🔴 MUITO VULNERÁVEL"
            elif ff >= 3:
                vuln = "🟠 VULNERÁVEL"
            elif ff >= 1:
                vuln = "🟡 ATENÇÃO"
            else:
                vuln = "🟢 PROTEGIDO"

            votes_count = sum(votes_received_by_week.get(week, {}).get(name, {}).values())
            indic_count = indicacoes.get(name, 0)

            impact = received_impact.get(name, {})
            external_score = impact.get("negative", 0)
            if external_score <= -10:
                external_level = "🔴 ALTO"
            elif external_score <= -5:
                external_level = "🟠 MÉDIO"
            elif external_score < 0:
                external_level = "🟡 BAIXO"
            else:
                external_level = "🟢 NENHUM"

            badges.append({
                "participante": name,
                "votos_casa": votes_count,
                "indicacoes": indic_count,
                "elegivel_voto": name not in ineligible,
                "vulnerabilidade": vuln,
                "impacto_negativo": external_level,
                "impact_score": round(external_score, 2),
                "falsos_amigos": ff,
            })

        by_paredao[str(numero)] = {
            "numero": numero,
            "data_formacao": data_form,
            "badges": badges,
        }

    return {"by_paredao": by_paredao}
