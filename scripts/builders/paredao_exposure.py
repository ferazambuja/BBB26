"""Paredão exposure analytics — stats, route metrics, and BV analysis.

Computes aggregate metrics from paredão data for exposure cards and docs.
All stats are computed once inside build_index_data() via compute_paredao_exposure_stats().
The pipeline only extracts from the builder payload — no recomputation.
"""
from __future__ import annotations

import unicodedata
from collections import Counter
from typing import Any

from data_utils import normalize_route_label, compute_protected_names, BBB26_PREMIERE
from builders.vote_prediction import extract_paredao_eligibility

ACTIVE_LAST_SEEN = "9999-12-31"


# ── Paredão predicates ────────────────────────────────────────────────────


def _is_finalized(p: dict) -> bool:
    return (p.get("status") or "").lower() == "finalizado"


def _is_fake(p: dict) -> bool:
    return bool(p.get("paredao_falso"))


def _has_indicados(p: dict) -> bool:
    return bool(p.get("indicados_finais"))


def _get_eliminated(p: dict) -> str | None:
    resultado = p.get("resultado") or {}
    return resultado.get("eliminado") or None


def _find_paredao(paredoes: list[dict], numero: int) -> dict | None:
    for p in paredoes:
        if p.get("numero") == numero:
            return p
    return None


def _get_vote_pct(p: dict, name: str) -> float | None:
    resultado = p.get("resultado") or {}
    votos = resultado.get("votos") or {}
    return (votos.get(name) or {}).get("voto_total")


def _metric(n: int, total: int, scope: str) -> dict:
    """Build a strict metric dict {rate, n, total, scope}."""
    return {
        "rate": round(n / total, 4) if total > 0 else None,
        "n": n,
        "total": total,
        "scope": scope,
    }


def _get_bv_info(p: dict) -> dict | None:
    """Extract Bate-e-Volta info from a paredão. Returns None if no BV."""
    form = p.get("formacao") or {}
    bv = form.get("bate_volta") or {}
    participants = bv.get("participantes") or []
    if not participants:
        return None
    winners = bv.get("vencedores") or ([bv["vencedor"]] if bv.get("vencedor") else [])
    return {
        "participants": participants,
        "winners": [w for w in winners if w],
        "losers": [pp for pp in participants if pp not in winners],
    }


# ── Scope partitioning ───────────────────────────────────────────────────


def _partition_scopes(paredoes_list: list[dict]) -> dict[str, list[dict]]:
    """Split paredões into scope partitions."""
    with_indicados = [p for p in paredoes_list if _has_indicados(p)]
    all_finalized = [p for p in with_indicados if _is_finalized(p)]
    real_only = [p for p in all_finalized if not _is_fake(p)]
    return {
        "with_indicados": with_indicados,
        "all_finalized": all_finalized,
        "real_only": real_only,
    }


# ── Shared nominee history (reused by stats + figurinha) ─────────────────


def _build_nominee_history(paredoes: list[dict]) -> dict[str, list[dict]]:
    """Build per-participant nomination history from paredões with indicados.

    Returns {name: [entry_dict, ...]} sorted chronologically within each name.
    Each entry has: numero, como, como_short, resultado, voto_total, falso.
    """
    history: dict[str, list[dict]] = {}
    for p in sorted(paredoes, key=lambda x: x.get("numero", 0)):
        num = p.get("numero", 0)
        eliminated = _get_eliminated(p)
        is_fake = _is_fake(p)
        resultado_data = p.get("resultado") or {}
        votos = resultado_data.get("votos") or {}
        for ind in p.get("indicados_finais", []):
            nome = ind["nome"] if isinstance(ind, dict) else ind
            como_raw = ind.get("como", "") if isinstance(ind, dict) else ""
            result = "eliminado" if nome == eliminated else "sobreviveu"
            if is_fake and nome == eliminated:
                result = "quarto_secreto"
            voto_total = (votos.get(nome) or {}).get("voto_total")
            if nome not in history:
                history[nome] = []
            history[nome].append({
                "numero": num,
                "como": como_raw,
                "como_short": normalize_route_label(como_raw),
                "resultado": result,
                "voto_total": voto_total,
                "falso": is_fake,
            })
    return history


# ── Metric sub-computations ──────────────────────────────────────────────


def _compute_first_timer_metric(real_only: list[dict]) -> dict:
    """First-timer elimination rate (real_only scope)."""
    seen: set[str] = set()
    first_timers = 0
    total_elims = 0
    for p in sorted(real_only, key=lambda x: x.get("numero", 0)):
        indicados = [
            (ind["nome"] if isinstance(ind, dict) else ind)
            for ind in p.get("indicados_finais", [])
        ]
        eliminated = _get_eliminated(p)
        if eliminated:
            total_elims += 1
            if eliminated not in seen:
                first_timers += 1
        seen.update(indicados)
    return _metric(first_timers, total_elims, "real_only")


def _compute_route_metrics(real_only: list[dict]) -> tuple[dict, dict[str, str], list[dict], list[str]]:
    """Route effectiveness metrics (real_only scope).

    Returns (route_metrics_dict, route_key_labels, single_sample_routes, unknown_routes).
    route_key_labels maps metric keys (e.g. 'route_lider') to canonical labels (e.g. 'Líder').
    """
    canonical_labels = {
        "Líder", "Contragolpe", "Consenso Anjo+Monstro", "Duelo de Risco",
        "Casa", "Big Fone", "Bloco do Paredão", "Exilado", "Caixas-Surpresa",
        "Aguardando origem",
    }
    route_counts: Counter[str] = Counter()
    route_elims: Counter[str] = Counter()
    for p in real_only:
        eliminated = _get_eliminated(p)
        for ind in p.get("indicados_finais", []):
            nome = ind["nome"] if isinstance(ind, dict) else ind
            como = ind.get("como", "") if isinstance(ind, dict) else ""
            route = normalize_route_label(como)
            route_counts[route] += 1
            if nome == eliminated:
                route_elims[route] += 1

    metrics: dict[str, dict] = {}
    key_labels: dict[str, str] = {}
    singles: list[dict] = []
    for label in sorted(route_counts):
        total = route_counts[label]
        n_elim = route_elims.get(label, 0)
        slug = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode()
        key = f"route_{slug.lower().replace(' ', '_').replace('+', '_')}"
        if total == 1:
            singles.append({"route": label, "n": n_elim, "total": total, "eliminated": n_elim > 0})
        else:
            metrics[key] = _metric(n_elim, total, "real_only")
            key_labels[key] = label

    unknown = [r for r in route_counts if r not in canonical_labels]
    return metrics, key_labels, singles, unknown


def _compute_bv_metrics(real_only: list[dict]) -> tuple[dict, int]:
    """Bate-e-Volta metrics (real_only scope).

    Returns (metrics_dict, total_participants_count).
    """
    paredoes_count = 0
    total_participants = 0
    winners_total = winners_ok = 0
    losers_total = losers_survived = losers_eliminated = 0

    for p in real_only:
        bv = _get_bv_info(p)
        if not bv:
            continue
        paredoes_count += 1
        eliminated = _get_eliminated(p)
        total_participants += len(bv["participants"])
        for w in bv["winners"]:
            winners_total += 1
            if w != eliminated:
                winners_ok += 1
        for loser in bv["losers"]:
            losers_total += 1
            if loser == eliminated:
                losers_eliminated += 1
            else:
                losers_survived += 1

    metrics = {
        "bv_presence_by_paredao": _metric(paredoes_count, len(real_only), "real_only"),
        "bv_winners_escaped": _metric(winners_ok, winners_total, "real_only"),
        "bv_losers_survived": _metric(losers_survived, losers_total, "real_only"),
        "bv_losers_eliminated": _metric(losers_eliminated, losers_total, "real_only"),
    }
    return metrics, total_participants


def _compute_exposure_facts(
    nominee_history: dict[str, list[dict]],
    with_indicados: list[dict],
    real_only: list[dict],
) -> dict[str, Any]:
    """Compute free-form exposure facts from shared nominee history."""
    facts: dict[str, Any] = {}

    # Biggest vote swing between consecutive real paredões
    biggest_swing = None
    for name, history in nominee_history.items():
        real_entries = [h for h in history if not h["falso"]]
        for i in range(1, len(real_entries)):
            prev_p = _find_paredao(real_only, real_entries[i - 1]["numero"])
            curr_p = _find_paredao(real_only, real_entries[i]["numero"])
            if prev_p and curr_p:
                prev_pct = _get_vote_pct(prev_p, name)
                curr_pct = _get_vote_pct(curr_p, name)
                if prev_pct is not None and curr_pct is not None:
                    swing = abs(curr_pct - prev_pct)
                    if biggest_swing is None or swing > biggest_swing["swing_pp"]:
                        biggest_swing = {
                            "name": name, "from_pct": prev_pct, "to_pct": curr_pct,
                            "swing_pp": round(swing, 2),
                            "from_paredao": real_entries[i - 1]["numero"],
                            "to_paredao": real_entries[i]["numero"],
                        }
    if biggest_swing:
        facts["biggest_swing"] = biggest_swing

    # BV queen/king (most BV participations)
    bv_counts: Counter[str] = Counter()
    for p in with_indicados:
        bv = _get_bv_info(p)
        if bv:
            for participant in bv["participants"]:
                bv_counts[participant] += 1
    if bv_counts:
        top_name, top_count = bv_counts.most_common(1)[0]
        facts["bv_queen"] = {"name": top_name, "count": top_count}

    # Líder favorite target
    target_counts: Counter[str] = Counter()
    for p in with_indicados:
        indicado = (p.get("formacao") or {}).get("indicado_lider")
        if indicado:
            target_counts[indicado] += 1
    if target_counts:
        top_name, top_count = target_counts.most_common(1)[0]
        if top_count >= 2:
            facts["lider_favorite_target"] = {"name": top_name, "count": top_count}

    return facts


# ── Public API ───────────────────────────────────────────────────────────


def build_participant_windows(
    participants_index: dict | list | None,
    *,
    active_names: set[str] | None = None,
    manual_events: dict | None = None,
) -> dict[str, dict[str, str]]:
    """Build {name: {first_seen, last_seen}} windows for exposure checks."""
    windows: dict[str, dict[str, str]] = {}

    entries = (
        participants_index.get("participants", [])
        if isinstance(participants_index, dict)
        else (participants_index or [])
    )
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name")
        if not name:
            continue
        windows[name] = {
            "first_seen": entry.get("first_seen", BBB26_PREMIERE),
            "last_seen": entry.get("last_seen", ACTIVE_LAST_SEEN),
        }

    for name in active_names or set():
        windows.setdefault(name, {
            "first_seen": BBB26_PREMIERE,
            "last_seen": ACTIVE_LAST_SEEN,
        })

    # Clamp stale derived windows with manual exits and fill gaps for participants
    # missing from participants_index entirely.
    # min() ensures exit_date overrides a stale ACTIVE_LAST_SEEN from participants_index.
    for name, info in (manual_events or {}).get("participants", {}).items():
        if not isinstance(info, dict):
            continue
        exit_date = info.get("exit_date")
        if not exit_date:
            continue
        windows.setdefault(name, {"first_seen": BBB26_PREMIERE, "last_seen": exit_date})
        existing_last_seen = windows[name].get("last_seen") or exit_date
        windows[name]["last_seen"] = min(existing_last_seen, exit_date)

    return windows


def compute_house_vote_exposure(
    paredoes_list: list[dict],
    participant_windows: dict[str, dict[str, str]],
    *,
    recent_window: int = 3,
) -> dict[str, dict[str, int]]:
    """Canonical presence-aware house-vote exposure for all known participants."""
    exposure = {
        name: {
            "votes_total": 0,
            "votes_recent": 0,
            "votes_available": 0,
            "available": 0,
            "protected": 0,
            "last_voted_paredao": 0,
        }
        for name in participant_windows
    }
    if not participant_windows:
        return exposure

    paredoes_with_votes = [p for p in paredoes_list if _has_indicados(p) and (p.get("votos_casa") or {})]
    recent_cycle_nums = {
        par.get("numero", 0)
        for par in sorted(paredoes_with_votes, key=lambda p: p.get("numero", 0))[-recent_window:]
    }

    for par in paredoes_with_votes:
        num = par.get("numero", 0)
        data_formacao = par.get("data_formacao") or par.get("data", "")
        if not data_formacao:
            continue

        cant_be_voted = extract_paredao_eligibility(par)["cant_be_voted"]
        protected_names = compute_protected_names(par.get("formacao") or {})
        vote_targets = Counter(
            target.strip()
            for target in (par.get("votos_casa") or {}).values()
            if isinstance(target, str)
        )

        for name, window in participant_windows.items():
            first_seen = window.get("first_seen", BBB26_PREMIERE)
            last_seen = window.get("last_seen", ACTIVE_LAST_SEEN)
            if not first_seen or not last_seen or not (first_seen <= data_formacao <= last_seen):
                continue
            if name in protected_names:
                exposure[name]["protected"] += 1
            if name not in cant_be_voted:
                exposure[name]["available"] += 1
                exposure[name]["votes_available"] += vote_targets.get(name, 0)

        for target_name, count in vote_targets.items():
            window = participant_windows.get(target_name)
            if not window:
                continue
            first_seen = window.get("first_seen", BBB26_PREMIERE)
            last_seen = window.get("last_seen", ACTIVE_LAST_SEEN)
            if not first_seen or not last_seen or not (first_seen <= data_formacao <= last_seen):
                continue
            exposure[target_name]["votes_total"] += count
            exposure[target_name]["last_voted_paredao"] = max(
                exposure[target_name]["last_voted_paredao"],
                num,
            )
            if num in recent_cycle_nums:
                exposure[target_name]["votes_recent"] += count

    return exposure


def compute_paredao_exposure_stats(ctx: dict[str, Any]) -> dict:
    """Compute all paredão exposure stats from builder context.

    Returns dict with 'metrics' (strict schema) and 'facts' (free-form).
    """
    paredoes_data = ctx.get("paredoes") or {}
    paredoes_list = paredoes_data.get("paredoes", []) if isinstance(paredoes_data, dict) else []

    scopes = _partition_scopes(paredoes_list)
    with_indicados = scopes["with_indicados"]
    real_only = scopes["real_only"]

    nominee_history = _build_nominee_history(with_indicados)
    route_metrics, route_key_labels, single_samples, unknown_routes = _compute_route_metrics(real_only)
    bv_metrics, bv_total_participants = _compute_bv_metrics(real_only)

    metrics = {
        "first_timer": _compute_first_timer_metric(real_only),
        **route_metrics,
        **bv_metrics,
    }

    facts: dict[str, Any] = {
        "bv_total_participants": bv_total_participants,
        "route_key_labels": route_key_labels,
        "single_sample_routes": single_samples,
        "unknown_routes": unknown_routes,
        "scope_sizes": {k: len(v) for k, v in scopes.items()},
        "appearance_counter": {
            name: len(entries) for name, entries in
            sorted(nominee_history.items(), key=lambda x: -len(x[1]))
        },
        **_compute_exposure_facts(nominee_history, with_indicados, real_only),
    }

    return {"metrics": metrics, "facts": facts}


def build_nunca_paredao_items(
    ctx: dict[str, Any],
    paredoes_list: list[dict],
    exposure_by_name: dict[str, dict[str, int]],
) -> tuple[list[dict], list[dict]]:
    """Build items and items_exited for nunca_paredao card.

    Returns (items, items_exited).
    """
    active_set = ctx["active_set"]
    manual_events = ctx.get("manual_events") or {}

    all_nominees = _collect_all_nominees(paredoes_list)
    n_paredoes = len([p for p in paredoes_list if _has_indicados(p)])

    items = []
    for name in active_set:
        if name in all_nominees:
            continue
        stats = exposure_by_name.get(name, {})
        items.append({
            "name": name,
            "votes_total": stats.get("votes_total", 0),
            "votes_recent": stats.get("votes_recent", 0),
            "votes_available": stats.get("votes_available", 0),
            "available": stats.get("available", 0),
            "protected": stats.get("protected", 0),
            "last_voted_paredao": stats.get("last_voted_paredao", 0),
            "n_paredoes": n_paredoes,
            "n_paredoes_scope": "with_indicados",
            "vote_counts_scope": "paredoes_with_votes",
            "status": "active",
        })
    items.sort(key=lambda x: (-x["votes_recent"], -x["votes_total"], x["name"]))

    items_exited = _build_exited_untouchables(
        manual_events, all_nominees, n_paredoes,
        exposure_by_name=exposure_by_name,
    )
    return items, items_exited


def build_figurinha_repetida_items(
    ctx: dict[str, Any],
    paredoes_list: list[dict],
) -> list[dict]:
    """Build items for figurinha_repetida card.

    Returns all participants who appeared in indicados_finais at least once,
    sorted by appearance_count DESC, latest_paredao DESC, name ASC.
    """
    active_set = ctx["active_set"]
    participants_index = ctx.get("participants_index") or {}
    with_indicados = [p for p in paredoes_list if _has_indicados(p)]
    nominee_history = _build_nominee_history(with_indicados)

    items = []
    for name, history in nominee_history.items():
        route_summary: Counter[str] = Counter()
        for h in history:
            route_summary[h["como_short"]] += 1

        is_active = name in active_set
        items.append({
            "name": name,
            "appearance_count": len(history),
            "route_summary": dict(route_summary),
            "latest_paredao": max(h["numero"] for h in history),
            "fake_paredao_count": sum(1 for h in history if h["falso"]),
            "fake_paredao_nums": [h["numero"] for h in history if h["falso"]],
            "was_eliminated": any(h["resultado"] == "eliminado" for h in history),
            "returned": _detect_return(name, history, active_set, participants_index, with_indicados),
            "survived_count": sum(1 for h in history if h["resultado"] == "sobreviveu"),
            "history": history,
            "active": is_active,
            "use_grayscale": not is_active,
        })

    items.sort(key=lambda x: (-x["appearance_count"], -x["latest_paredao"], x["name"]))
    return items


# ── Private helpers for card builders ────────────────────────────────────


def _collect_all_nominees(paredoes_list: list[dict]) -> set[str]:
    """Collect all names that ever appeared in indicados_finais."""
    nominees: set[str] = set()
    for p in paredoes_list:
        for ind in p.get("indicados_finais", []):
            nominees.add(ind["nome"] if isinstance(ind, dict) else ind)
    return nominees


def _build_exited_untouchables(
    manual_events: dict, all_nominees: set[str], n_paredoes: int,
    exposure_by_name: dict[str, dict[str, int]] | None = None,
) -> list[dict]:
    """Build items_exited: non-eliminado exited participants never nominated."""
    status_labels = {
        "desistente": "Desistente",
        "desclassificado": "Desclassificado",
        "desclassificada": "Desclassificada",
    }
    items = []
    for name, info in (manual_events.get("participants") or {}).items():
        if not isinstance(info, dict):
            continue
        status = info.get("status", "")
        if "eliminad" in status or name in all_nominees:
            continue

        exit_date = info.get("exit_date", "")
        vstats = (exposure_by_name or {}).get(name, {})

        context_note = ""
        if vstats.get("available", 0) == 0 and n_paredoes > 0:
            context_note = "Saiu antes do 1º Paredão"

        items.append({
            "name": name,
            "votes_total": vstats.get("votes_total", 0),
            "votes_recent": vstats.get("votes_recent", 0),
            "votes_available": vstats.get("votes_available", 0),
            "available": vstats.get("available", 0),
            "protected": vstats.get("protected", 0),
            "last_voted_paredao": vstats.get("last_voted_paredao", 0),
            "context_note": context_note,
            "n_paredoes": n_paredoes,
            "n_paredoes_scope": "with_indicados",
            "vote_counts_scope": "paredoes_with_votes",
            "status": status,
            "status_label": status_labels.get(status, status.capitalize()),
            "exit_date": exit_date,
            "use_grayscale": True,
        })
    items.sort(key=lambda x: (x.get("exit_date", ""), x["name"]))
    return items


def _detect_return(
    name: str,
    history: list[dict],
    active_set: set[str],
    participants_index: dict,
    paredoes: list[dict],
) -> bool:
    """Detect if participant returned after a fake-paredão elimination.

    Three signals: (1) later paredão appearance, (2) currently active,
    (3) participants_index.last_seen is after the fake paredão date.
    """
    fake_elims = [h for h in history if h["resultado"] == "quarto_secreto"]
    if not fake_elims:
        return False
    fake_num = max(h["numero"] for h in fake_elims)
    if any(h["numero"] > fake_num for h in history) or name in active_set:
        return True
    if participants_index:
        fake_par = _find_paredao(paredoes, fake_num)
        fake_date = (fake_par or {}).get("data", "")
        pi_entries = participants_index.get("participants", [])
        pi_entry = next((p for p in pi_entries if p.get("name") == name), None)
        last_seen = (pi_entry or {}).get("last_seen", "")
        if fake_date and last_seen and last_seen > fake_date:
            return True
    return False
