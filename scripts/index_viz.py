"""Focused render helpers extracted from index.qmd."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import plotly.graph_objects as go

from data_utils import GROUP_COLORS, REACTION_EMOJI, SENTIMENT_WEIGHTS


def _escape_text(value) -> str:
    return escape("" if value is None else str(value))


def _escape_attr(value) -> str:
    return escape("" if value is None else str(value), quote=True)


def _profile_slug(name) -> str:
    return ("" if name is None else str(name)).lower().replace(" ", "-")


def _profile_href(name) -> str:
    return _escape_attr(f"#perfil-{_profile_slug(name)}")


def _coerce_float(value, default=0.0) -> float:
    if value in (None, ""):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value, default=0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _parse_datetime_like(value) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            raise ValueError("missing date")
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            dt = datetime.strptime(text, "%Y-%m-%d")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def fmt_date_br(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        return _parse_datetime_like(date_str).strftime("%d/%m")
    except Exception:
        return date_str


def card_header(icon, title, link=None, badge=None, source_tag=None, subtitle=None):
    """Card header with icon, title, optional link, badge, source tag, and subtitle."""
    meta_parts = []
    if badge:
        meta_parts.append(f'<span class="dashboard-card-badge fs-xs u-s187">{_escape_text(badge)}</span>')
    if source_tag:
        meta_parts.append(f'<span class="dashboard-card-source fs-2xs u-s253">{_escape_text(source_tag)}</span>')
    if link:
        meta_parts.append(f'<a href="{_escape_attr(link)}" class="dashboard-card-link fs-xs u-s254">ver mais ↗</a>')
    meta_html = f'<div class="dashboard-card-header-meta">{"".join(meta_parts)}</div>' if meta_parts else ""
    subtitle_html = f'<div class="dashboard-card-subtitle fs-sm u-s258">{_escape_text(subtitle)}</div>' if subtitle else ""
    return (
        f'<div class="u-s073 dashboard-card-header">'
        f'<div class="dashboard-card-header-main">'
        f'<span class="dashboard-card-icon fs-2xl">{icon}</span>'
        f'<span class="dashboard-card-title fs-base u-s392">{_escape_text(title)}</span>'
        f"</div>"
        f"{meta_html}"
        f"{subtitle_html}</div>"
    )


def stat_chip(value, label, color="#888"):
    """Small stat chip."""
    return (
        f'<span class="u-s373">'
        f'<span class="fs-xl" style="font-weight:700;color:{color};">{_escape_text(value)}</span>'
        f'<span class="fs-2xs u-s259">{_escape_text(label)}</span></span>'
    )


def progress_bar(value, max_val, color="#3498db", height=6):
    """Mini progress bar."""
    pct = min(100, value / max_val * 100) if max_val > 0 else 0
    radius = height // 2
    return (
        f'<div style="background:rgba(255,255,255,0.08);border-radius:{radius}px;height:{height}px;width:100%;overflow:hidden;">'
        f'<div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:{radius}px;"></div></div>'
    )


def render_pulse_row(label: str, value: int, color_row: str, *, total_delta: int) -> str:
    return (
        f'<div style="display:grid;grid-template-columns:90px 1fr auto;gap:8px;align-items:center;">'
        f'<span class="fs-2xs" style="color:#aaa;">{_escape_text(label)}</span>'
        f'{progress_bar(value, total_delta, color_row, height=6)}'
        f'<span class="fs-sm" style="color:{color_row};font-weight:700;">{value}</span>'
        f'</div>'
    )


def render_saldo_card(payload: dict, *, avatar_fn) -> str:
    if not payload:
        return ""

    items_all = list(payload.get("items_all") or payload.get("items") or [])
    if not items_all:
        return ""

    default_limit = len(items_all) or 5
    display_limit = _coerce_int(payload.get("display_limit"), default=default_limit)
    if display_limit <= 0:
        display_limit = default_limit
    inline_items = items_all[:display_limit]
    overflow_items = items_all[display_limit:]

    def _row(item: dict) -> str:
        name = item.get("name", "")
        balance = item.get("balance", 0)
        if isinstance(balance, (int, float)) and float(balance).is_integer():
            balance_text = f"{int(balance):,}"
        elif isinstance(balance, (int, float)):
            balance_text = f"{balance:,.1f}"
        else:
            balance_text = _escape_text(balance)
        bar_pct = max(0.0, min(100.0, _coerce_float(item.get("bar_pct", 0), default=0.0)))
        return (
            f'<div class="u-s056">'
            f'{avatar_fn(name, 42, item.get("border_color", "#999"))}'
            f'<div class="u-s066">'
            f'<div class="u-s059">'
            f'<span class="fs-md u-s068">{_escape_text(item.get("rank_label", ""))} {_escape_text(item.get("first_name") or _short_name(name))}</span>'
            f'<span class="fs-base" style="color:{item.get("balance_color", "#888")};font-weight:700;">{balance_text}</span>'
            f'</div>'
            f'<div class="u-s014">'
            f'<div style="width:{bar_pct:.0f}%;height:100%;background:{item.get("balance_color", "#888")};border-radius:3px;"></div>'
            f'</div>'
            f'</div></div>'
        )

    rows_html = '<div class="u-s355">'
    rows_html += "".join(_row(item) for item in inline_items)
    if overflow_items:
        rows_html += (
            f'<details class="sinc-more">'
            f'<summary>+{len(overflow_items)} restantes</summary>'
            f'<div class="u-s355">'
            f'{"".join(_row(item) for item in overflow_items)}'
            f'</div></details>'
        )
    rows_html += '</div>'

    return (
        f'<div class="info-panel u-s199">'
        f'{card_header(payload.get("icon", "💰"), payload.get("title", "Saldo de Estalecas"), payload.get("link"), source_tag=payload.get("source_tag"), subtitle=payload.get("subtitle"))}'
        f'{rows_html}'
        f'</div>'
    )


def plant_color(score):
    if score >= 80:
        return "#2f7d46"
    if score >= 60:
        return "#6c8a3c"
    if score >= 40:
        return "#b9772a"
    return "#a94442"


def render_status_chip(emoji, label, level, color, detail_html=""):
    """Tappable status indicator with optional breakdown."""
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    bg = f"rgba({r},{g},{b},0.12)"
    if detail_html:
        return (
            f'<details class="status-detail">'
            f'<summary style="background:{bg};border-left:3px solid {color};">'
            f'<span class="fs-lg">{emoji}</span>'
            f'<div><div class="fs-sm" style="font-weight:700;color:{color};">{_escape_text(level)}</div>'
            f'<div class="fs-2xs u-s061">{_escape_text(label)}</div></div>'
            f'</summary>'
            f'<div class="status-breakdown u-s001">{detail_html}</div>'
            f"</details>"
        )
    return (
        f'<div style="display:flex;align-items:center;gap:0.4rem;background:{bg};'
        f'padding:0.4rem 0.8rem;border-radius:8px;border-left:3px solid {color};flex:1;min-width:140px;">'
        f'<span class="fs-lg">{emoji}</span>'
        f'<div><div class="fs-sm" style="font-weight:700;color:{color};">{_escape_text(level)}</div>'
        f'<div class="fs-2xs u-s061">{_escape_text(label)}</div></div>'
        f"</div>"
    )


def _short_name(name):
    return (name or "?").split()[0]


def av(name, size=48, border_color="#555", *, avatars, avatar_html):
    """Avatar image tag, clickable to the participant's profile."""
    return avatar_html(
        name,
        avatars,
        size=size,
        show_name=False,
        link=_profile_href(name),
        border_color=border_color,
        fallback_initials=True,
    )


def av_group_border(name: str, *, member_of, group_colors=GROUP_COLORS) -> str:
    grp = member_of.get(name, "")
    return group_colors.get(grp, "#666")


def pair_story_card(
    giver: str,
    receiver: str,
    transition_html: str,
    meta_text: str,
    *,
    avatar_fn,
    group_border_fn,
    border_color: str,
    left_border: str | None = None,
    right_border: str | None = None,
):
    """Centered pair card used by dramatic changes, hostilities, and alliance breaks."""
    left_border = left_border or group_border_fn(giver)
    right_border = right_border or group_border_fn(receiver)
    return (
        f'<div class="pair-story-card" style="border-left:3px solid {border_color};">'
        f'<div class="pair-story-grid">'
        f'<div class="pair-story-side">'
        f'{avatar_fn(giver, 42, left_border)}'
        f'<span class="pair-story-name">{_escape_text(giver.split()[0])}</span>'
        f'</div>'
        f'<div class="pair-story-center">'
        f'<div class="pair-story-transition">{transition_html}</div>'
        f'<div class="pair-story-meta">{_escape_text(meta_text)}</div>'
        f'</div>'
        f'<div class="pair-story-side">'
        f'{avatar_fn(receiver, 42, right_border)}'
        f'<span class="pair-story-name">{_escape_text(receiver.split()[0])}</span>'
        f'</div>'
        f'</div>'
        f'</div>'
    )


def render_overflow_toggle(count: int) -> str:
    safe_count = max(0, _coerce_int(count, default=0))
    return (
        f'<details class="sinc-more" style="margin-top:4px;">'
        f'<summary style="list-style:none;cursor:pointer;text-align:center;'
        f'padding:4px 0;color:#666;font-size:var(--fs-xs);">'
        f'<span style="background:rgba(255,255,255,0.08);padding:2px 14px;'
        f'border-radius:10px;">⋯ {safe_count}</span></summary>'
    )


def render_dramatic_event_row(
    item: dict,
    *,
    ref_date,
    is_hostile: bool,
    fmt_date_fn,
    days_ago_fn,
    pair_story_card_fn,
) -> str:
    giver = item["giver"]
    receiver = item["receiver"]
    date_str = item.get("date", "")
    when = fmt_date_fn(date_str)
    age_txt = days_ago_fn(date_str, ref_date)
    when_txt = f"{when} ({age_txt})" if when and age_txt else (when or age_txt)

    old_emoji = item.get("old_emoji", "?")
    new_emoji = item.get("new_emoji", item.get("emoji", "?") if is_hostile else "?")
    if not is_hostile:
        new_emoji = item.get("new_emoji", "?")

    transition_html = (
        f'<span class="pair-story-origin">{_escape_text(old_emoji)}</span>'
        f'<span class="pair-story-arrow">→</span>'
        f'<span class="pair-story-destination">{_escape_text(new_emoji)}</span>'
    )

    if is_hostile:
        meta_txt = f"Hostilidade unilateral · {when_txt}"
        row_border = "#f39c12"
    else:
        severity = _coerce_float(item.get("severity", 0))
        severity_text = "alta" if severity >= 1.5 else ("média" if severity >= 1.0 else "leve")
        meta_txt = f"Mudança {severity_text} · {when_txt}"
        row_border = "#e74c3c" if severity >= 1.5 else "#8e44ad"

    return pair_story_card_fn(
        giver,
        receiver,
        transition_html,
        meta_txt,
        border_color=row_border,
    )


def render_rank_chip(
    entry: dict,
    lane_type: str,
    is_top: bool,
    *,
    avatar_html_fn,
    avatars: dict | None = None,
    avatar_size: int = 30,
    force_count: int | None = None,
) -> str:
    name = entry.get("name", "")
    first = _short_name(name)
    count = force_count if force_count is not None else _coerce_int(entry.get("count", 0), default=0)
    lane_colors = {
        "attack": "#e67e22",
        "praise": "#27ae60",
        "safe": "#3498db",
    }
    border_color = lane_colors.get(lane_type, "#666")
    if avatars is None:
        avatar = avatar_html_fn(name, border_color)
    else:
        avatar = avatar_html_fn(
            name,
            avatars,
            size=avatar_size,
            show_name=False,
            border_color=border_color,
            fallback_initials=True,
        )
    top_cls = " top" if is_top else ""
    return (
        f'<a href="{_profile_href(name)}" class="sinc-person-chip {lane_type}{top_cls}">'
        f'<span class="sinc-person-avatar">{avatar}</span>'
        f'<span class="sinc-person-meta">'
        f'<span class="sinc-person-name">{_escape_text(first)}</span>'
        f'<span class="sinc-count-badge {lane_type}">{count}x</span>'
        f'</span>'
        f'</a>'
    )


def render_ranked_lane(
    title: str,
    icon: str,
    ranked: list[dict],
    empty_text: str,
    lane_type: str,
    *,
    inline_max: int,
    render_rank_chip_fn=None,
    avatar_html_fn=None,
    avatars: dict | None = None,
    avatar_size: int = 30,
    highlight_top: bool = True,
    force_count: int | None = None,
) -> str:
    lane = [f'<div class="sinc-lane"><div class="sinc-lane-head">{icon} {title}</div>']
    if not ranked:
        lane.append(f'<div class="sinc-empty">{_escape_text(empty_text)}</div></div>')
        return "".join(lane)

    top_count = ranked[0].get("count", 0)
    inline_items = ranked[:inline_max]
    overflow_items = ranked[inline_max:]
    if render_rank_chip_fn is None:
        if avatar_html_fn is None:
            raise ValueError("render_ranked_lane requires render_rank_chip_fn or avatar_html_fn")

        def render_rank_chip_fn(entry_item, entry_lane_type, entry_is_top, force_count=None):
            return render_rank_chip(
                entry_item,
                entry_lane_type,
                entry_is_top,
                avatar_html_fn=avatar_html_fn,
                avatars=avatars,
                avatar_size=avatar_size,
                force_count=force_count,
            )

    lane.append('<div class="sinc-people-grid">')
    lane.extend(
        render_rank_chip_fn(
            item,
            lane_type,
            highlight_top and item.get("count", 0) == top_count,
            force_count=force_count,
        )
        for item in inline_items
    )
    lane.append('</div>')
    if overflow_items:
        lane.append(
            f'<details class="sinc-more"><summary>+{len(overflow_items)} restantes</summary>'
            f'<div class="sinc-more-list"><div class="sinc-people-grid">'
        )
        lane.extend(
            render_rank_chip_fn(item, lane_type, False, force_count=force_count)
            for item in overflow_items
        )
        lane.append('</div></div></details>')
    lane.append('</div>')
    return "".join(lane)


def render_pair_lane(
    title: str,
    icon: str,
    pairs: list[dict],
    mode: str,
    *,
    inline_max: int,
    render_pair_chip_fn,
    show_header: bool = True,
) -> str:
    lane = ['<div class="sinc-lane">']
    if show_header:
        lane.append(f'<div class="sinc-lane-head">{icon} {title}</div>')
    if not pairs:
        lane.append('<div class="sinc-empty">Sem casos nesta semana.</div></div>')
        return "".join(lane)

    inline_items = pairs[:inline_max]
    overflow_items = pairs[inline_max:]
    lane.append('<div class="sinc-chip-wrap">')
    lane.extend(render_pair_chip_fn(item, mode=mode) for item in inline_items)
    lane.append('</div>')
    if overflow_items:
        lane.append(
            f'<details class="sinc-more"><summary>+{len(overflow_items)} restantes</summary>'
            f'<div class="sinc-more-list">'
        )
        lane.extend(render_pair_chip_fn(item, mode=mode) for item in overflow_items)
        lane.append('</div></details>')
    lane.append('</div>')
    return "".join(lane)


def render_toggle_pair_lane(
    title: str,
    icon: str,
    pairs: list[dict],
    mode: str,
    *,
    inline_max: int,
    render_pair_chip_fn,
) -> str:
    count = len(pairs)
    body = render_pair_lane(
        title,
        icon,
        pairs,
        mode,
        inline_max=inline_max,
        render_pair_chip_fn=render_pair_chip_fn,
        show_header=False,
    )
    return (
        f'<details class="sinc-toggle">'
        f'<summary>{icon} {title} <span class="sinc-toggle-count">({count})</span></summary>'
        f'{body}'
        f'</details>'
    )


def render_alvo_rows(items, rid, *, avatar_fn) -> str:
    worst = abs(_coerce_float(items[0]["score"], default=0.0)) if items else 1
    worst = worst or 1
    html = f'<div id="{_escape_attr(rid)}" class="u-s058">'
    inline_items = items[:5]
    overflow_items = items[5:]
    for item in inline_items:
        name = item["name"]
        score = _coerce_float(item.get("score", 0.0))
        bar_pct = min(100.0, abs(score) / worst * 100.0) if worst > 0 else 0.0
        html += (
            f'<div class="u-s056">'
            f'<a href="{_profile_href(name)}" style="text-decoration:none">{avatar_fn(name, 42, "#c0392b")}</a>'
            f'<div class="u-s066">'
            f'<div class="u-s059">'
            f'<a href="{_profile_href(name)}" class="fs-md u-s068" style="text-decoration:none;color:inherit">{_escape_text(_short_name(name))}</a>'
            f'<span class="fs-sm" style="color:#c0392b;font-weight:700">{score:.1f}</span>'
            f'</div>'
            f'<div class="u-s014">'
            f'<div style="width:{bar_pct:.0f}%;height:100%;background:#c0392b;border-radius:3px;"></div>'
            f'</div>'
            f'</div></div>'
        )
    if overflow_items:
        html += (
            f'<details class="sinc-more">'
            f'<summary>+{len(overflow_items)} restantes</summary>'
            f'<div class="u-s058">'
        )
        for item in overflow_items:
            name = item["name"]
            score = _coerce_float(item.get("score", 0.0))
            bar_pct = min(100.0, abs(score) / worst * 100.0) if worst > 0 else 0.0
            html += (
                f'<div class="u-s056">'
                f'<a href="{_profile_href(name)}" style="text-decoration:none">{avatar_fn(name, 42, "#c0392b")}</a>'
                f'<div class="u-s066">'
                f'<div class="u-s059">'
                f'<a href="{_profile_href(name)}" class="fs-md u-s068" style="text-decoration:none;color:inherit">{_escape_text(_short_name(name))}</a>'
                f'<span class="fs-sm" style="color:#c0392b;font-weight:700">{score:.1f}</span>'
                f'</div>'
                f'<div class="u-s014">'
                f'<div style="width:{bar_pct:.0f}%;height:100%;background:#c0392b;border-radius:3px;"></div>'
                f'</div>'
                f'</div></div>'
            )
        html += '</div></details>'
    html += '</div>'
    return html


def render_break_row(
    item: dict,
    *,
    break_ref_date,
    fmt_date_fn,
    days_ago_fn,
    pair_story_card_fn,
) -> str:
    giver = item["giver"]
    receiver = item["receiver"]
    streak = _coerce_int(item.get("streak", 0), default=0)
    new_emoji = item.get("new_emoji", "?")
    severity = item.get("severity", "mild")
    date_str = item.get("date", "")
    date_fmt = fmt_date_fn(date_str)
    age_txt = days_ago_fn(date_str, break_ref_date)
    when_txt = f"{date_fmt} ({age_txt})" if date_fmt and age_txt else (date_fmt or age_txt)
    severity_border = "#e74c3c" if severity == "strong" else "#8e44ad"
    meta_txt = f"Rompimento{' grave' if severity == 'strong' else ''}"
    if when_txt:
        meta_txt += f" · {when_txt}"
    transition_html = (
        f'<span class="pair-story-origin">{streak}d ❤️</span>'
        f'<span class="pair-story-arrow">→</span>'
        f'<span class="pair-story-destination">{_escape_text(new_emoji)}</span>'
    )
    return pair_story_card_fn(
        giver,
        receiver,
        transition_html,
        meta_txt,
        border_color=severity_border,
    )


def render_blindado_row(item: dict, *, n_par: int, avatar_fn) -> str:
    name = item["name"]
    paredao_count = _coerce_int(item.get("paredao", 0), default=0)
    protected = _coerce_int(item.get("protected", 0), default=0)
    available = _coerce_int(item.get("available", 0), default=0)
    votes = _coerce_int(item.get("votes", 0), default=0)
    has_bv = bool(item.get("bv_escape", False))
    bv_text = item.get("bv_text", "")
    protection_tags = item.get("protection_tags") or []

    border = "#3498db" if protected >= 3 else ("#27ae60" if paredao_count == 0 else "#f39c12")
    par_color = "#27ae60" if paredao_count == 0 else ("#f39c12" if paredao_count == 1 else "#e74c3c")
    par_label = f"{paredao_count} paredão" if paredao_count == 1 else f"{paredao_count} paredões"
    bar_pct = min(100.0, protected / n_par * 100.0) if n_par > 0 else 0.0
    badges = []
    if has_bv and bv_text:
        badges.append(
            f"<span class='fs-2xs' style='padding:1px 6px;border-radius:999px;background:#1b3f5c;color:#9dd3ff;white-space:nowrap;display:inline-flex;align-items:center;flex:0 0 auto;'>{_escape_text(bv_text)}</span>"
        )
    for tag in protection_tags:
        if not isinstance(tag, dict):
            continue
        label = tag.get("label")
        tone_style = "background:#2d1b3f;color:#d9b3ff;" if label == "Líder" else "background:#123b2a;color:#8fe3b8;"
        badges.append(
            f"<span class='fs-2xs' style='padding:1px 6px;border-radius:999px;{tone_style}white-space:nowrap;display:inline-flex;align-items:center;flex:0 0 auto;'>{_escape_text(tag.get('text', ''))}</span>"
        )
    badges_html = "".join(badges)
    extra_badges = (
        f"<div style='margin-top:3px;display:flex;flex-direction:column;align-items:flex-start;gap:4px;'>{badges_html}</div>"
        if badges_html else ""
    )
    eligible_label = "elegível" if available == 1 else "elegíveis"
    votes_label = "voto" if votes == 1 else "votos"

    return (
        f'<div class="u-s056" style="align-items:flex-start;">'
        f'<a href="{_profile_href(name)}" style="text-decoration:none">{avatar_fn(name, 42, border)}</a>'
        f'<div class="u-s066">'
        f'<div class="u-s059">'
        f'<a href="{_profile_href(name)}" class="fs-md u-s068" style="text-decoration:none;color:inherit">{_escape_text(_short_name(name))}</a>'
        f'<span class="fs-sm" style="color:{par_color};font-weight:700;">{par_label}</span>'
        f'</div>'
        f'<div class="u-s014">'
        f'<div style="width:{bar_pct:.0f}%;height:100%;background:#3498db;border-radius:3px;"></div>'
        f'</div>'
        f'<div class="fs-2xs" style="color:#888;">{votes} {votes_label} em {available} {eligible_label} · protegido {protected}x</div>'
        f'{extra_badges}'
        f'</div></div>'
    )


def render_visado_row(item: dict, *, max_votes: int, recent_window: int, avatar_fn) -> str:
    name = item["name"]
    paredao_count = _coerce_int(item.get("paredao", 0), default=0)
    votes_total = _coerce_int(item.get("votes_total", 0), default=0)
    votes_recent = _coerce_int(item.get("votes_recent", 0), default=0)
    intensity = _coerce_float(item.get("intensity_prevote", 0.0))
    bv_count = _coerce_int(item.get("bv_escapes", 0), default=0)
    fake_count = _coerce_int(item.get("fake_paredao_count", 0), default=0)
    fake_nums_raw = item.get("fake_paredao_nums")
    if fake_nums_raw in (None, ""):
        fake_nums = []
    elif isinstance(fake_nums_raw, (list, tuple)):
        fake_nums = [num for num in fake_nums_raw if num not in (None, "")]
    else:
        fake_nums = [fake_nums_raw]
    by_lider = _coerce_int(item.get("by_lider", 0), default=0)
    by_casa = _coerce_int(item.get("by_casa", 0), default=0)
    by_dynamic = _coerce_int(item.get("by_dynamic", 0), default=0)

    border = "#c0392b" if paredao_count >= 2 else ("#d35400" if votes_total >= 2 else "#8e44ad")
    par_color = "#c0392b" if paredao_count >= 2 else ("#e67e22" if paredao_count == 1 else "#7f8c8d")
    par_label = f"{paredao_count} paredão" if paredao_count == 1 else f"{paredao_count} paredões"
    bar_pct = min(100.0, votes_total / max_votes * 100.0) if max_votes > 0 else 0.0
    intensity_pct = round(intensity * 100)

    badges = []
    if bv_count:
        badges.append(
            f"<span class='fs-2xs' style='padding:1px 6px;border-radius:999px;background:#1b3f5c;color:#9dd3ff;white-space:nowrap;display:inline-flex;align-items:center;flex:0 0 auto;'>Escapou Bate-Volta {bv_count}x</span>"
        )
    if fake_count:
        fake_txt = ", ".join(f"{num}º" for num in fake_nums)
        fake_suffix = f" ({_escape_text(fake_txt)})" if fake_txt else ""
        badges.append(
            f"<span class='fs-2xs' style='padding:1px 6px;border-radius:999px;background:#123b2a;color:#8fe3b8;white-space:nowrap;display:inline-flex;align-items:center;flex:0 0 auto;'>Paredão falso {fake_count}x{fake_suffix}</span>"
        )
    if by_lider:
        badges.append(
            f"<span class='fs-2xs' style='padding:1px 6px;border-radius:999px;background:#2d1b3f;color:#d9b3ff;white-space:nowrap;display:inline-flex;align-items:center;flex:0 0 auto;'>Líder {by_lider}x</span>"
        )
    if by_casa:
        badges.append(
            f"<span class='fs-2xs' style='padding:1px 6px;border-radius:999px;background:#123b2a;color:#8fe3b8;white-space:nowrap;display:inline-flex;align-items:center;flex:0 0 auto;'>Casa {by_casa}x</span>"
        )
    if by_dynamic:
        badges.append(
            f"<span class='fs-2xs' style='padding:1px 6px;border-radius:999px;background:#123b2a;color:#8fe3b8;white-space:nowrap;display:inline-flex;align-items:center;flex:0 0 auto;'>Dinâmica {by_dynamic}x</span>"
        )
    badges_html = "".join(badges)
    extra_badges = (
        f"<div style='margin-top:3px;display:flex;flex-direction:column;align-items:flex-start;gap:4px;'>{badges_html}</div>"
        if badges_html else ""
    )
    votes_total_label = "voto" if votes_total == 1 else "votos"
    recent_label = "recente" if votes_recent == 1 else "recentes"

    return (
        f'<div class="u-s056" style="align-items:flex-start;">'
        f'<a href="{_profile_href(name)}" style="text-decoration:none">{avatar_fn(name, 42, border)}</a>'
        f'<div class="u-s066">'
        f'<div class="u-s059">'
        f'<a href="{_profile_href(name)}" class="fs-md u-s068" style="text-decoration:none;color:inherit">{_escape_text(_short_name(name))}</a>'
        f'<span class="fs-sm" style="color:{par_color};font-weight:700;">{par_label}</span>'
        f'</div>'
        f'<div class="u-s014">'
        f'<div style="width:{bar_pct:.0f}%;height:100%;background:#e67e22;border-radius:3px;"></div>'
        f'</div>'
        f'<div class="fs-2xs" style="color:#888;">{votes_total} {votes_total_label} total · {votes_recent} {recent_label} ({recent_window} ciclos) · intensidade {intensity_pct}%</div>'
        f'{extra_badges}'
        f'</div></div>'
    )


def render_vx_row(item: dict, *, day_key: str, accent: str, max_days: int, avatar_fn) -> str:
    name = item["name"]
    days = _coerce_int(item.get(day_key, 0), default=0)
    total = _coerce_int(item.get("total", 0), default=0)
    pct = round(days / total * 100) if total > 0 else 0
    bar_pct = min(100.0, days / max_days * 100.0) if max_days > 0 else 0.0
    return (
        f'<div class="u-s056">'
        f'<a href="{_profile_href(name)}" style="text-decoration:none">{avatar_fn(name, 38, accent)}</a>'
        f'<div class="u-s066">'
        f'<div class="u-s059">'
        f'<a href="{_profile_href(name)}" class="fs-sm u-s068" style="text-decoration:none;color:inherit">{_escape_text(_short_name(name))}</a>'
        f'<span class="fs-sm" style="color:{accent};font-weight:700;">{days}d ({pct}%)</span>'
        f'</div>'
        f'<div class="u-s014">'
        f'<div style="width:{bar_pct:.0f}%;height:100%;background:{accent};border-radius:3px;"></div>'
        f'</div>'
        f'</div></div>'
    )


def render_pair_chip(item: dict, *, mode: str) -> str:
    a_name = item.get("ator", "")
    b_name = item.get("alvo", "")
    a_first = a_name.split()[0] if a_name else "?"
    b_first = b_name.split()[0] if b_name else "?"
    tipo = item.get("tipo_label", "?")
    emoji = item.get("emoji", "?")
    if mode == "contra":
        detail = f"{tipo} mas dá {emoji}"
    else:
        detail = f"{tipo} + {emoji}"
    return (
        f'<span class="sinc-chip-muted">'
        f'<a href="{_profile_href(a_name)}" class="sinc-chip">{_escape_text(a_first)}</a>'
        f' → <a href="{_profile_href(b_name)}" class="sinc-chip">{_escape_text(b_first)}</a> '
        f'<span class="sinc-chip-muted">({_escape_text(detail)})</span>'
        f'</span>'
    )


def render_actor_avatars(
    actors,
    border_color="#666",
    color_lookup=None,
    size=24,
    skip_icons=None,
    *,
    avatars,
    source_icons,
):
    if not actors:
        return ""
    parts = []
    for actor in actors:
        color = border_color
        if color_lookup and actor in color_lookup:
            color = color_lookup[actor]
        if actor in avatars and avatars[actor]:
            parts.append(
                f'<img src="{_escape_attr(avatars[actor])}" style="width:{size}px;height:{size}px;border-radius:50%;'
                f'border:1.5px solid {color};object-fit:cover;margin-right:-3px;">'
            )
            continue
        lower = actor.lower() if isinstance(actor, str) else ""
        if "dinâmica da casa" in lower:
            continue
        icon = None
        for key, value in source_icons.items():
            if key in lower:
                icon = value
                break
        if icon and skip_icons and icon in skip_icons:
            continue
        parts.append(f'<span class="fs-base">{icon or "🎬"}</span>')
    return "".join(parts)


def make_event_chips(events, border_color, color_lookup=None, *, render_actor_avatars_fn):
    if not events:
        return "<span class='u-s058'>—</span>"
    chips = []
    for event in events:
        emoji = event.get("emoji", "•")
        label = event.get("label", event.get("type"))
        count = event.get("count", 1)
        actors = event.get("actors", [])
        count_prefix = f"{count}x " if count > 1 else ""
        chip_border = border_color
        actor_html = render_actor_avatars_fn(
            actors,
            chip_border,
            color_lookup=color_lookup,
            size=20,
            skip_icons={emoji} if emoji else None,
        )
        actor_label = " + ".join(actors) if actors else ""
        title = f"{label} — {actor_label}" if actor_label else label
        chips.append(
            f"<span style='display:inline-flex; align-items:center; gap:0.25rem; background:#2f2f2f; "
            f"border:1px solid {chip_border}; color:#ddd; border-radius:8px; padding:0.2rem 0.5rem; "
            f"margin:0.1rem; line-height:1.4;' title=\"{_escape_attr(title)}\" class=\"fs-md\">"
            f"{count_prefix}{emoji} {_escape_text(label)} {actor_html}</span>"
        )
    return " ".join(chips)


def render_avatar_row(items, border_color, max_show=999, *, avatar_fn):
    """Row of avatars with name + score under each. Shows ALL by default."""
    if not items:
        return '<span class="fs-md u-s058">—</span>'
    limit = _coerce_int(max_show, default=len(items))
    if limit <= 0:
        return '<span class="fs-md u-s058">—</span>'
    visible_items = items[:limit]
    html = '<div class="avatar-row">'
    for item in visible_items:
        if isinstance(item, str):
            name = item
            score_html = ""
        else:
            name = item.get("name", "")
            their_score = item.get("their_score")
            my_score = item.get("my_score")
            if their_score is not None:
                score_color = "#28a745" if their_score >= 0 else "#dc3545"
                score_html = f'<div class="fs-2xs" style="color:{score_color};font-weight:600;">{their_score:+.1f}</div>'
            elif my_score is not None:
                score_color = "#28a745" if my_score >= 0 else "#dc3545"
                score_html = f'<div class="fs-2xs" style="color:{score_color};font-weight:600;">{my_score:+.1f}</div>'
            else:
                score_html = ""
        first_name = _escape_text(name.split()[0] if name else "")
        html += (
            f'<div class="u-s352">'
            f'{avatar_fn(name, 48, border_color)}'
            f'<div class="fs-2xs u-s266">{first_name}</div>'
            f"{score_html}"
            f"</div>"
        )
    html += "</div>"
    return html


def render_profile_sinc_chip(ix: dict, who_key: str) -> str:
    emoji = ix.get("emoji", "")
    who_first = ix.get(who_key, "").split()[0] if ix.get(who_key) else ""
    label = ix.get("label", "")
    valence_cls = "pos" if ix.get("valence", "neg") == "pos" else "neg"
    return (
        f"<span class='profile-sinc-chip {valence_cls}'>"
        f"{emoji} {_escape_text(who_first)} <span class='profile-sinc-chip-text'>{_escape_text(label)}</span></span>"
    )


def render_profile_sinc_row(
    row_label: str,
    interactions: list[dict],
    who_key: str,
    inline_max: int,
    week_prefix: str = "",
) -> str:
    if not interactions:
        return ""
    inline = interactions[:inline_max]
    overflow = interactions[inline_max:]
    chips = "".join(render_profile_sinc_chip(ix, who_key) for ix in inline)
    row_html = (
        f"<div class='profile-sinc-row'>"
        f"{week_prefix}"
        f"<span class='profile-sinc-label'>{_escape_text(row_label)}</span>"
        f"<div class='profile-sinc-chip-wrap'>{chips}</div>"
        f"</div>"
    )
    if overflow:
        overflow_chips = "".join(render_profile_sinc_chip(ix, who_key) for ix in overflow)
        row_html += (
            f"<details class='profile-sinc-more'>"
            f"<summary>+{len(overflow)} desta semana</summary>"
            f"<div class='profile-sinc-chip-wrap profile-sinc-overflow'>{overflow_chips}</div>"
            f"</details>"
        )
    return row_html


def build_rxn_detail_html(detail_list, *, avatar_fn) -> str:
    if not detail_list:
        return ""
    groups = {}
    for detail in detail_list:
        emoji = detail.get("emoji", "?")
        groups.setdefault(emoji, []).append(detail["name"])
    rows = []
    for emoji, names_list in groups.items():
        avatars_html = "".join(
            f'<div class="u-s351">'
            f'{avatar_fn(name, 36, "#555")}'
            f'<div class="fs-2xs u-s265">{_escape_text(name.split()[0])}</div>'
            f'</div>'
            for name in names_list
        )
        rows.append(
            f'<div class="u-s037">'
            f'<div class="fs-md u-s405">{_escape_text(emoji)} ({len(names_list)})</div>'
            f'<div class="u-s359">{avatars_html}</div>'
            f'</div>'
        )
    return "".join(rows)


def days_ago_str(date_str: str, ref_date: str | None = None, *, anchor_brt):
    if not date_str:
        return ""
    try:
        d0 = _parse_datetime_like(date_str).date()
    except Exception:
        return ""
    anchor = anchor_brt
    if ref_date:
        try:
            anchor = _parse_datetime_like(ref_date).date()
        except Exception:
            anchor = anchor_brt

    delta = (anchor - d0).days
    if delta < 0:
        return ""
    if delta == 0:
        return "hoje"
    if delta == 1:
        return "há 1 dia"
    return f"há {delta} dias"


def make_cross_table_heatmap(participants, matrix, title_suffix=""):
    """Return the reaction cross-table heatmap."""
    active_names = sorted(
        [
            participant["name"]
            for participant in participants
            if not participant.get("characteristics", {}).get("eliminated")
        ]
    )

    heat_data = [[0.0 for _ in active_names] for _ in active_names]
    rxn_labels = []
    for i, giver in enumerate(active_names):
        row_labels = []
        for j, receiver in enumerate(active_names):
            if giver == receiver:
                heat_data[i][j] = float("nan")
                row_labels.append("—")
            else:
                rxn = matrix.get((giver, receiver), "")
                heat_data[i][j] = SENTIMENT_WEIGHTS.get(rxn, 0)
                row_labels.append(REACTION_EMOJI.get(rxn, "?"))
        rxn_labels.append(row_labels)

    short_names = [name.split()[0] if len(name) > 12 else name for name in active_names]

    fig = go.Figure(
        data=go.Heatmap(
            z=heat_data,
            x=short_names,
            y=short_names,
            colorscale=[
                [0, "#d73027"],
                [0.25, "#fc8d59"],
                [0.5, "#ffffbf"],
                [1.0, "#1a9850"],
            ],
            zmin=-1,
            zmax=1,
            text=[[rxn_labels[i][j] for j in range(len(active_names))] for i in range(len(active_names))],
            texttemplate="%{text}",
            textfont=dict(size=14),
            hovertemplate="%{y} → %{x}: %{text}<extra></extra>",
            colorbar=dict(
                title="Sentimento",
                tickvals=[-1, -0.5, 0, 1],
                ticktext=["Forte Neg", "Leve Neg", "Neutro", "Positivo"],
            ),
        )
    )

    title = "Mapa de Reações"
    if title_suffix:
        title += f" — {title_suffix}"

    fig.update_layout(
        title=title,
        xaxis_title="Receptor ←",
        yaxis_title="Emissor →",
        height=750,
        xaxis=dict(tickangle=45, side="bottom"),
        yaxis=dict(autorange="reversed"),
    )

    return fig


def _get_cross_table_cell_style(rxn):
    if not rxn:
        return "background: #444; color: #888;"

    weight = SENTIMENT_WEIGHTS.get(rxn, 0)
    if weight == 1:
        return "background: #1a9850; color: #fff;"
    if weight == -0.5:
        return "background: #fc8d59; color: #000;"
    if weight == -1:
        return "background: #d73027; color: #fff;"
    return "background: #ffffbf; color: #000;"


def make_cross_table_html(cross_data, title_suffix=""):
    """Return HTML for the sticky reaction cross-table."""
    active_names = cross_data.get("names", [])
    matrix = cross_data.get("matrix", [])
    short_names = [name.split()[0] if len(name) > 10 else name for name in active_names]

    html = []
    html.append(
        """
<div class="index-cross-table scroll-x">
<table class="index-cross-table__table">
<thead>
<tr>
<th class="u-s001">→ deu / ↓ recebeu</th>
"""
    )

    for short_name in short_names:
        html.append(f"<th>{_escape_text(short_name)}</th>")
    html.append("</tr></thead><tbody>")

    for i, giver in enumerate(active_names):
        html.append(f"<tr><th>{_escape_text(short_names[i])}</th>")
        for j, receiver in enumerate(active_names):
            if giver == receiver:
                html.append('<td class="u-s117">—</td>')
            else:
                rxn = matrix[i][j] if i < len(matrix) and j < len(matrix[i]) else ""
                emoji = REACTION_EMOJI.get(rxn, "?") if rxn else "?"
                style = _get_cross_table_cell_style(rxn)
                tooltip = f"{giver} → {receiver}: {rxn or 'N/A'}"
                html.append(f'<td style="{style}" title="{_escape_attr(tooltip)}">{emoji}</td>')
        html.append("</tr>")

    html.append("</tbody></table></div>")
    return "\n".join(html)


def make_reaction_summary_html(summary_data, collapsed_rows=5):
    """Return HTML for the received-reactions summary table."""
    summary_rows = summary_data.get("rows", [])
    max_hearts = summary_data.get("max_hearts", 1) or 1
    n_total = len(summary_rows)

    def heart_color(val):
        if val == 0:
            return "color: #666;"
        intensity = min(val / max_hearts, 1)
        if intensity > 0.7:
            return "background: #1a9850; color: #fff; font-weight: bold;"
        if intensity > 0.4:
            return "background: #91cf60; color: #000;"
        return "color: #a6d96a;"

    def neg_color(val):
        if val == 0:
            return "color: #666;"
        if val >= 3:
            return "background: #d73027; color: #fff; font-weight: bold;"
        if val >= 2:
            return "background: #fc8d59; color: #000;"
        return "color: #fdae61;"

    def score_color(val):
        if val >= 10:
            return "background: #1a9850; color: #fff; font-weight: bold;"
        if val >= 5:
            return "color: #66bd63;"
        if val >= 0:
            return "color: #a6d96a;"
        if val >= -5:
            return "color: #fdae61;"
        if val >= -10:
            return "color: #f46d43;"
        return "background: #d73027; color: #fff; font-weight: bold;"

    html = []
    html.append(
        """
<div class="index-reaction-summary">
<div class="scroll-x">
<table class="index-reaction-summary__table">
<thead>
<tr>
<th>Participante</th>
<th>❤️</th>
<th>🌱</th>
<th>💼</th>
<th>🍪</th>
<th>🐍</th>
<th>🎯</th>
<th>🤮</th>
<th>🤥</th>
<th>💔</th>
<th>Score</th>
</tr>
</thead>
<tbody>
"""
    )

    for i, row in enumerate(summary_rows):
        row_class = "index-reaction-summary__row--collapsed" if i >= collapsed_rows else ""
        html.append(f'<tr class="{row_class}">')
        html.append(f'<td>{_escape_text(row["name"])}</td>')
        html.append(f'<td style="{heart_color(row["hearts"])}">{row["hearts"]}</td>')
        html.append(f'<td style="{neg_color(row["planta"])}">{row["planta"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["mala"])}">{row["mala"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["biscoito"])}">{row["biscoito"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["cobra"])}">{row["cobra"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["alvo"])}">{row["alvo"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["vomito"])}">{row["vomito"] or "·"}</td>')
        html.append(f'<td style="{neg_color(row["mentiroso"])}">{row["mentiroso"] or "·"}</td>')
        html.append(
            f'<td style="{neg_color(row["coracao_partido"])}">{row["coracao_partido"] or "·"}</td>'
        )
        html.append(f'<td style="{score_color(row["score"])}">{row["score"]:+.1f}</td>')
        html.append("</tr>")

    html.append("</tbody></table></div>")

    if n_total > collapsed_rows:
        html.append(
            f"""
<button type="button" class="index-reaction-summary__toggle" onclick="
    var wrapper = this.closest('.index-reaction-summary');
    var rows = wrapper ? wrapper.querySelectorAll('.index-reaction-summary__row--collapsed') : [];
    var btn = this;
    if (btn.dataset.expanded === 'true') {{
        rows.forEach(r => r.style.display = 'none');
        btn.innerHTML = '▼ Ver todos os {n_total} participantes';
        btn.dataset.expanded = 'false';
    }} else {{
        rows.forEach(r => r.style.display = 'table-row');
        btn.innerHTML = '▲ Mostrar menos';
        btn.dataset.expanded = 'true';
    }}
" data-expanded="false">▼ Ver todos os {n_total} participantes</button>
"""
        )

    html.append("</div>")

    return "\n".join(html)
