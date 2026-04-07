"""Focused render helpers extracted from index.qmd."""

from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import plotly.graph_objects as go

from data_utils import GROUP_COLORS, REACTION_EMOJI, SENTIMENT_WEIGHTS

# ── Profile-card render constants (L-3 / L-4) ──

SOURCE_ICONS: dict[str, str] = {
    'big fone': '\U0001f4de',
    'caixas-surpresa': '\U0001f381',
    'prova do líder': '\U0001f451',
    'prova do anjo': '\U0001f607',
    'castigo do monstro': '\U0001f479',
    'dinâmica da casa': '\U0001f3ac',
}

COMP_LABELS: dict[str, str] = {
    "power_event": "Eventos de poder",
    "sincerao": "Sincerão",
    "vote": "Votos",
    "vip": "VIP",
    "anjo": "Anjo",
    "visibility": "Visibilidade",
}


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


def value_color(val: float, scheme: str = "signed") -> str:
    """Return a color for a numeric value based on its scheme.

    Schemes:
      signed  — positive green → gray 0 → negative red (balance, scores, deltas)
      danger  — low green → mid orange → high red (paredão count, votes received, hits)
      pct     — 0% gray → 50% yellow → 100% red (intensity, elimination %)
    """
    if scheme == "signed":
        if val > 1000:
            return "#1a9850"    # dark green (strong positive)
        if val > 100:
            return "#27ae60"    # medium green
        if val > 0:
            return "#66bd63"    # light green
        if val == 0:
            return "#888"       # gray (neutral)
        if val > -100:
            return "#e67e22"    # orange (mild negative)
        return "#e74c3c"        # red (strong negative)
    if scheme == "danger":
        if val <= 0:
            return "#888"       # gray (none)
        if val <= 1:
            return "#66bd63"    # green (low)
        if val <= 2:
            return "#f39c12"    # orange (medium)
        if val <= 3:
            return "#e67e22"    # dark orange
        return "#e74c3c"        # red (high)
    if scheme == "pct":
        if val <= 10:
            return "#66bd63"    # green (low %)
        if val <= 30:
            return "#f1c40f"    # yellow
        if val <= 60:
            return "#e67e22"    # orange
        return "#e74c3c"        # red (high %)
    return "#888"


def render_pulse_row(label: str, value: int, color_row: str, *, total_delta: int) -> str:
    return (
        f'<div style="display:grid;grid-template-columns:90px 1fr auto;gap:8px;align-items:center;">'
        f'<span class="fs-2xs" style="color:#aaa;">{_escape_text(label)}</span>'
        f'{progress_bar(value, total_delta, color_row, height=6)}'
        f'<span class="fs-sm" style="color:{color_row};font-weight:700;">{value}</span>'
        f'</div>'
    )


def _render_pulso_chip(label: str) -> str:
    return f'<span class="pulso-chip">{_escape_text(label)}</span>'


def _render_pulso_participants(participants: list[dict], *, avatar_fn) -> str:
    if not participants:
        return ""

    items = []
    for item in participants:
        name = item.get("name", "")
        status = item.get("status", "active")
        border_color = "#4f7cff" if status == "active" else "#7a7f87"
        aria_label = name if status == "active" else f"{name} (eliminado)"
        items.append(
            f'<span class="pulso-person-chip {"is-eliminated" if status != "active" else ""}" aria-label="{_escape_attr(aria_label)}">'
            f'{avatar_fn(name, 34, border_color)}'
            f'<span class="pulso-person-name">{_escape_text(_short_name(name))}</span>'
            f'</span>'
        )
    return f'<div class="pulso-participants">{"".join(items)}</div>'


def _render_pulso_timeline(timeline: list[dict]) -> str:
    if not timeline:
        return ""

    items = []
    for entry in timeline:
        if not isinstance(entry, dict):
            continue
        date_label = fmt_date_br(entry.get("date", ""))
        summary = entry.get("summary") or entry.get("text") or entry.get("support") or ""
        items.append(
            f'<div class="pulso-timeline-item">'
            f'<span class="pulso-timeline-date">{_escape_text(date_label)}</span>'
            f'<span class="pulso-timeline-summary">{_escape_text(summary)}</span>'
            f'</div>'
        )

    if not items:
        return ""
    return (
        f'<div class="pulso-context-section">'
        f'<div class="pulso-context-label">Linha do tempo</div>'
        f'<div class="pulso-timeline">{"".join(items)}</div>'
        f'</div>'
    )


def _render_pulso_support(support: str) -> str:
    if not support:
        return ""

    parts = [part.strip() for part in support.split(",") if part.strip()]
    if len(parts) > 1:
        items = "".join(
            f'<span class="pulso-fact-breakdown-item">{_escape_text(part)}</span>'
            for part in parts
        )
        return f'<div class="pulso-fact-breakdown pulso-fact-breakdown--tokens">{items}</div>'

    return f'<div class="pulso-fact-breakdown">{_escape_text(support)}</div>'


def _render_pulso_fact(fact: dict, *, avatar_fn, hero: bool = False) -> str:
    if not fact:
        return ""

    context = fact.get("context") or {}
    chips = list(context.get("chips") or [])
    timeline = list(context.get("timeline") or [])
    participants = list(fact.get("participants") or [])
    date_label = fact.get("date_label") or fmt_date_br(fact.get("date", ""))
    moment = context.get("moment", "")
    support = fact.get("support", "")
    summary = fact.get("summary", "")
    drill_html = ""
    if chips or timeline or participants:
        chips_html = ""
        if chips:
            chips_html = (
                f'<div class="pulso-context-section">'
                f'<div class="pulso-context-label">Contexto do momento</div>'
                f'<div class="pulso-chip-row">{"".join(_render_pulso_chip(chip) for chip in chips)}</div>'
                f'</div>'
            )
        timeline_html = _render_pulso_timeline(timeline)
        participants_html = ""
        if participants:
            participants_html = (
                f'<div class="pulso-context-section">'
                f'<div class="pulso-context-label">Quem aparece nessa história</div>'
                f'{_render_pulso_participants(participants, avatar_fn=avatar_fn)}'
                f'</div>'
            )
        drill_html = (
            f'<details class="pulso-context-drill">'
            f'<summary><span class="pulso-toggle-icon">▾</span><span class="pulso-toggle-text">contexto</span></summary>'
            f'<div class="pulso-context-body">'
            f'{chips_html}'
            f'{timeline_html}'
            f'{participants_html}'
            f'</div></details>'
        )

    fact_cls = "pulso-fact pulso-fact--hero" if hero else "pulso-fact"
    support_html = _render_pulso_support(support)
    return (
        f'<section class="{fact_cls}">'
        f'<div class="pulso-fact-kicker">'
        f'<span class="pulso-kicker-date">{_escape_text(date_label)}</span>'
        f'<span class="pulso-kicker-moment">{_escape_text(moment)}</span>'
        f'</div>'
        f'<div class="pulso-fact-head">'
        f'<div class="pulso-fact-copy">'
        f'<div class="pulso-fact-title">{_escape_text(fact.get("title", ""))}</div>'
        f'<div class="pulso-fact-summary">{_escape_text(summary)}</div>'
        f'</div>'
        f'<div class="pulso-fact-stat">'
        f'<span class="pulso-fact-value">{_escape_text(fact.get("value", ""))}</span>'
        f'<span class="pulso-fact-value-label">{_escape_text(fact.get("value_label", ""))}</span>'
        f'</div>'
        f'</div>'
        f'{support_html}'
        f'{drill_html}'
        f'</section>'
    )


def render_pulso_card(payload: dict, *, avatar_fn) -> str:
    if not payload:
        return ""

    mode = payload.get("mode", "history")
    today = payload.get("today") or {}
    facts = list(payload.get("facts") or [])
    hero = payload.get("hero") or (facts[0] if facts else {})
    extra_facts = facts[1:3] if mode == "history" and facts else facts[:2]

    def _metric(label: str, value, accent: str, note: str = "") -> str:
        note_html = f'<span class="pulso-metric-note">{_escape_text(note)}</span>' if note else ""
        return (
            f'<div class="pulso-metric">'
            f'<span class="pulso-metric-value" style="color:{accent};">{_escape_text(value)}</span>'
            f'<span class="pulso-metric-label">{_escape_text(label)}</span>'
            f'{note_html}</div>'
        )

    total = _coerce_int(today.get("total"))
    pct = _coerce_int(today.get("pct"))
    improve = _coerce_int(today.get("improve"))
    worsen = _coerce_int(today.get("worsen"))
    lateral = _coerce_int(today.get("lateral"))
    hearts_gained = _coerce_int(today.get("hearts_gained"))
    hearts_lost = _coerce_int(today.get("hearts_lost"))
    net = _coerce_int(today.get("net"), default=improve - worsen)
    date_label = today.get("date_label") or today.get("date") or ""
    today_chips = list(today.get("chips") or [])
    collapsed_chips = today_chips[:3]
    if len(today_chips) > 3:
        collapsed_chips.append(f"+{len(today_chips) - 3} sinais")

    today_strip = (
        f'<section class="pulso-today-strip">'
        f'<div class="pulso-today-head">'
        f'<div class="pulso-today-title">Última comparação</div>'
        f'<div class="pulso-today-date">{_escape_text(date_label)}</div>'
        f'<div class="pulso-today-subtitle">{total} mudanças de um dia para o outro ({pct}%)</div>'
        f'</div>'
        f'<div class="pulso-metrics-grid">'
        f'{_metric("Melhoras", improve, "#2ecc71")}'
        f'{_metric("Pioras", worsen, "#ff7262")}'
        f'{_metric("Laterais", lateral, "#b4bcc8")}'
        f'{_metric("Saldo", f"{net:+d}", "#7ec8ff", note=f"❤️ +{hearts_gained} / -{hearts_lost}")}'
        f'</div>'
        f'<div class="pulso-chip-row">{"".join(_render_pulso_chip(chip) for chip in collapsed_chips)}</div>'
        f'</section>'
    )

    facts_html = ""
    if extra_facts:
        extra_label = f"mais {len(extra_facts)} fatos do arquivo"
        facts_html = (
            f'<details class="pulso-rail-toggle">'
            f'<summary><span class="pulso-toggle-icon">▾</span><span class="pulso-toggle-text">{_escape_text(extra_label)}</span></summary>'
            f'<div class="pulso-rail">'
            f'{"".join(_render_pulso_fact(fact, avatar_fn=avatar_fn) for fact in extra_facts)}'
            f'</div>'
            f'</details>'
        )

    return (
        f'<div class="info-panel pulso-panel">'
        f'{card_header(payload.get("icon", "📊"), payload.get("title", "Arquivo do Queridômetro"), payload.get("link"), source_tag=payload.get("source_tag"), subtitle=payload.get("subtitle"))}'
        f'<div class="pulso-card pulso-card--{_escape_attr(mode)}">'
        f'{_render_pulso_fact(hero, avatar_fn=avatar_fn, hero=True)}'
        f'{today_strip}'
        f'{facts_html}'
        f'</div></div>'
    )


def _render_viradas_chip(chip: dict) -> str:
    tone = chip.get("tone", "neutral")
    return f'<span class="viradas-chip viradas-chip--{_escape_attr(tone)}">{_escape_text(chip.get("text", ""))}</span>'


def _render_viradas_summary_item(item: dict) -> str:
    return (
        f'<div class="viradas-summary-item viradas-summary-item--{_escape_attr(item.get("kind", ""))}">'
        f'<span class="viradas-summary-count">{_escape_text(item.get("count", 0))}</span>'
        f'<span class="viradas-summary-title">{_escape_text(item.get("title", ""))}</span>'
        f'<span class="viradas-summary-note">{_escape_text(item.get("note", ""))}</span>'
        f'</div>'
    )


def _render_viradas_group_row(item: dict, *, avatar_fn) -> str:
    kind = item.get("kind", "")
    border_color = {
        "dramatic": "#e74c3c",
        "hostilities": "#f39c12",
        "breaks": "#8e44ad",
    }.get(kind, "#4f7cff")
    transition_html = (
        f'<span class="pair-story-origin">{_escape_text(item.get("old_emoji", ""))}</span>'
        f'<span class="pair-story-arrow">→</span>'
        f'<span class="pair-story-destination">{_escape_text(item.get("new_emoji", ""))}</span>'
    )
    return pair_story_card(
        item.get("giver", ""),
        item.get("receiver", ""),
        transition_html,
        item.get("meta_line", ""),
        avatar_fn=avatar_fn,
        group_border_fn=lambda _name: "#4f7cff",
        border_color=border_color,
    )


def render_viradas_card(payload: dict, *, avatar_fn) -> str:
    if not payload:
        return ""

    hero = payload.get("hero") or {}
    summary = list(payload.get("summary") or [])
    groups = [group for group in (payload.get("groups") or []) if group.get("items")]
    total = _coerce_int(payload.get("total"), default=sum(_coerce_int(item.get("count"), default=0) for item in summary))

    hero_chips = "".join(_render_viradas_chip(chip) for chip in hero.get("chips", []))
    hero_kicker = hero.get("kicker", "")
    hero_date = fmt_date_br(hero.get("date", ""))
    hero_left = avatar_fn(hero.get("giver", ""), 46, "#4f7cff")
    hero_right = avatar_fn(hero.get("receiver", ""), 46, "#4f7cff")
    drill_html = ""
    if groups:
        drill_html = (
            f'<details class="viradas-drill">'
            f'<summary><span class="viradas-toggle-icon">▾</span><span class="viradas-toggle-text">mais {total} viradas do dia</span></summary>'
            f'<div class="viradas-groups">'
            + "".join(
                f'<section class="viradas-group viradas-group--{_escape_attr(group.get("kind", ""))}">'
                f'<div class="viradas-group-title">{_escape_text(group.get("title", ""))}</div>'
                f'<div class="viradas-group-rows">'
                f'{"".join(_render_viradas_group_row(item, avatar_fn=avatar_fn) for item in group.get("items", []))}'
                f'</div></section>'
                for group in groups
            )
            + '</div></details>'
        )

    return (
        f'<div class="info-panel viradas-panel">'
        f'{card_header(payload.get("icon", "🔄"), payload.get("title", "Viradas"), payload.get("link"), source_tag=payload.get("source_tag"), subtitle=payload.get("subtitle"))}'
        f'<div class="viradas-card viradas-card--{_escape_attr(payload.get("state", "partial"))}">'
        f'<section class="viradas-hero">'
        f'<div class="viradas-hero-kicker">'
        f'<span class="viradas-kicker-label">{_escape_text(hero_kicker)}</span>'
        f'<span class="viradas-kicker-date">{_escape_text(hero_date)}</span>'
        f'</div>'
        f'<div class="viradas-hero-head">'
        f'<div class="viradas-hero-pair">'
        f'<div class="viradas-side">{hero_left}<span class="viradas-side-name">{_escape_text(_short_name(hero.get("giver", "")))}</span></div>'
        f'<div class="viradas-center">'
        f'<div class="viradas-transition"><span class="viradas-transition-old">{_escape_text(hero.get("old_emoji", ""))}</span><span class="viradas-transition-arrow">→</span><span class="viradas-transition-new">{_escape_text(hero.get("new_emoji", ""))}</span></div>'
        f'</div>'
        f'<div class="viradas-side">{hero_right}<span class="viradas-side-name">{_escape_text(_short_name(hero.get("receiver", "")))}</span></div>'
        f'</div>'
        f'<div class="viradas-hero-copy">'
        f'<div class="viradas-hero-main">'
        f'<div class="viradas-copy-block">'
        f'<div class="viradas-hero-title">{_escape_text(hero.get("title", ""))}</div>'
        f'<div class="viradas-hero-body">{_escape_text(hero.get("body", ""))}</div>'
        f'</div>'
        f'<div class="viradas-hero-stat">'
        f'<span class="viradas-stat-value">{_escape_text(hero.get("stat_value", ""))}</span>'
        f'<span class="viradas-stat-label">{_escape_text(hero.get("stat_label", ""))}</span>'
        f'</div>'
        f'</div>'
        f'<div class="viradas-chip-row">{hero_chips}</div>'
        f'</div>'
        f'</div>'
        f'</section>'
        f'<section class="viradas-summary-strip">{"".join(_render_viradas_summary_item(item) for item in summary)}</section>'
        f'{drill_html}'
        f'</div></div>'
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
    chooser_names = entry.get("actors") or []
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
    avatar_html = f'<span class="sinc-person-avatar">{avatar}</span>'
    meta_html = (
        f'<span class="sinc-person-meta">'
        f'<span class="sinc-person-name">{_escape_text(first)}</span>'
        f'<span class="sinc-count-badge {lane_type}">{count}x</span>'
        f'</span>'
    )
    chip_html = (
        f'<a href="{_profile_href(name)}" class="sinc-person-chip {lane_type}{top_cls}">'
        f'{avatar_html}'
        f'{meta_html}'
        f'</a>'
    )
    if not chooser_names:
        return chip_html

    chooser_html = "".join(
        f'<span class="sinc-chip-drill-actor">{_escape_text(_short_name(actor_name))}</span>'
        for actor_name in chooser_names
    )
    return (
        f'<div class="sinc-person-card sinc-person-chip {lane_type}{top_cls}">'
        f'<a href="{_profile_href(name)}" class="sinc-person-avatar-link">{avatar_html}</a>'
        f'<details class="sinc-person-chip-toggle" data-sinc-sync-toggle="chooser">'
        f'<summary class="sinc-person-chip-summary">{meta_html}</summary>'
        f'<div class="sinc-chip-drill-list">{chooser_html}</div>'
        f'</details>'
        f'</div>'
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
    if render_rank_chip_fn is not None:
        chip_fn = render_rank_chip_fn
    else:
        if avatar_html_fn is None:
            raise ValueError("render_ranked_lane requires render_rank_chip_fn or avatar_html_fn")

        def chip_fn(entry_item, entry_lane_type, entry_is_top, force_count=None):
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
        chip_fn(
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
            chip_fn(item, lane_type, False, force_count=force_count)
            for item in overflow_items
        )
        lane.append('</div></div></details>')
    lane.append('</div>')
    return "".join(lane)


def render_podiums_lane(
    podiums: list[dict],
    *,
    avatar_html_fn,
    avatars: dict | None = None,
    avatar_size: int = 30,
) -> str:
    """Render an expandable podium grid for 'pódio + quem não ganha' format.

    Each entry in podiums: {name, slot_2, slot_3, nao_ganha}.
    """
    lane = ['<div class="sinc-lane"><div class="sinc-lane-head">🏆 Pódios</div>']
    if not podiums:
        lane.append('<div class="sinc-empty">Sem dados de pódio.</div></div>')
        return "".join(lane)

    lane.append('<div class="sinc-podiums-grid">')
    for pod in podiums:
        name = pod.get("name", "")
        first = _short_name(name)
        slot_2 = pod.get("slot_2") or "—"
        slot_3 = pod.get("slot_3") or "—"
        nao_ganha = pod.get("nao_ganha") or "—"
        if avatars is None:
            avatar = avatar_html_fn(name, "#e67e22")
        else:
            avatar = avatar_html_fn(
                name, avatars, size=avatar_size, show_name=False,
                border_color="#e67e22", fallback_initials=True,
            )
        slot_2_short = _short_name(slot_2) if slot_2 != "—" else "—"
        slot_3_short = _short_name(slot_3) if slot_3 != "—" else "—"
        ng_short = _short_name(nao_ganha) if nao_ganha != "—" else "—"
        lane.append(
            f'<details class="sinc-podium-entry" data-sinc-sync-toggle="chooser">'
            f'<summary class="sinc-podium-summary">'
            f'<span class="sinc-person-avatar">{avatar}</span>'
            f'<span class="sinc-podium-name">{_escape_text(first)}</span>'
            f'</summary>'
            f'<div class="sinc-podium-detail">'
            f'<span class="sinc-podium-slot gold">🥈 {_escape_text(slot_2_short)}</span>'
            f'<span class="sinc-podium-slot silver">🥉 {_escape_text(slot_3_short)}</span>'
            f'<span class="sinc-podium-nao-ganha">🚫 {_escape_text(ng_short)}</span>'
            f'</div>'
            f'</details>'
        )
    lane.append('</div></div>')
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
            f'<span class="fs-sm" style="color:{value_color(score, "signed")};font-weight:700">{score:.1f}</span>'
            f'</div>'
            f'<div class="u-s014">'
            f'<div style="width:{bar_pct:.0f}%;height:100%;background:{value_color(score, "signed")};border-radius:3px;"></div>'
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
                f'<span class="fs-sm" style="color:{value_color(score, "signed")};font-weight:700">{score:.1f}</span>'
                f'</div>'
                f'<div class="u-s014">'
                f'<div style="width:{bar_pct:.0f}%;height:100%;background:{value_color(score, "signed")};border-radius:3px;"></div>'
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
    voted_paredoes = _coerce_int(item.get("voted_paredoes", 0), default=0)
    escape_tags = item.get("escape_tags") or []
    protection_tags = item.get("protection_tags") or []

    border = "#3498db" if protected >= 3 else ("#27ae60" if paredao_count == 0 else "#f39c12")
    par_color = "#27ae60" if paredao_count == 0 else ("#f39c12" if paredao_count == 1 else "#e74c3c")
    par_label = f"{paredao_count} paredão" if paredao_count == 1 else f"{paredao_count} paredões"
    bar_pct = min(100.0, protected / n_par * 100.0) if n_par > 0 else 0.0
    badges = []
    for etag in escape_tags:
        if not isinstance(etag, dict):
            continue
        badges.append(
            f"<span class='fs-2xs' style='padding:1px 6px;border-radius:999px;background:#1b3f5c;color:#9dd3ff;white-space:nowrap;display:inline-flex;align-items:center;flex:0 0 auto;'>{_escape_text(etag.get('text', ''))}</span>"
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
    voted_paredoes_label = "paredão" if voted_paredoes == 1 else "paredões"

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
        f'<div class="fs-2xs" style="color:#888;">{votes} {votes_label} em {available} {eligible_label} · votado em {voted_paredoes} {voted_paredoes_label} · protegido {protected}x</div>'
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
        f'<div style="width:{bar_pct:.0f}%;height:100%;background:{value_color(paredao_count, "danger")};border-radius:3px;"></div>'
        f'</div>'
        f'<div class="fs-2xs" style="color:#888;">{votes_total} {votes_total_label} total · {votes_recent} {recent_label} ({recent_window} ciclos) · intensidade <span style="color:{value_color(intensity_pct, "pct")};font-weight:600;">{intensity_pct}%</span></div>'
        f'{extra_badges}'
        f'</div></div>'
    )


def _power_tag_badge(tag: dict, bg: str, fg: str) -> str:
    """Render a single power tag badge."""
    text = _escape_text(tag.get("text", ""))
    return (
        f"<span class='fs-2xs' style='padding:1px 6px;border-radius:999px;"
        f"background:{bg};color:{fg};white-space:nowrap;"
        f"display:inline-flex;align-items:center;flex:0 0 auto;'>{text}</span>"
    )


def _power_detail_html(detail: list[dict], mode: str, tag_labels: dict[str, str] | None = None) -> str:
    """Render expandable drill-down for power events."""
    if not detail:
        return ""
    labels = tag_labels or {}
    lines = []
    for d in detail:
        ev_type = d.get("type", "")
        label = labels.get(ev_type, ev_type.replace("_", " ").title())
        week = d.get("cycle", "")
        week_str = f" ({week}º)" if week else ""
        if mode == "target":
            actor = _escape_text(d.get("actor", ""))
            lines.append(f"<div class='fs-2xs' style='color:#999;padding:1px 0;'>{label} por {actor}{week_str}</div>")
        else:
            target = _escape_text(d.get("target", ""))
            lines.append(f"<div class='fs-2xs' style='color:#999;padding:1px 0;'>{label} → {target}{week_str}</div>")
    content = "".join(lines)
    return (
        f"<details style='margin-top:4px;'>"
        f"<summary class='fs-2xs' style='color:#777;cursor:pointer;'>Detalhes ({len(detail)})</summary>"
        f"<div style='margin-top:2px;padding-left:8px;border-left:2px solid #333;'>{content}</div>"
        f"</details>"
    )


def render_na_mira_row(item: dict, *, max_hits: int, avatar_fn, tag_labels: dict[str, str] | None = None) -> str:
    """Render a Mais Alvo (target) row with power tags and drill-down."""
    name = item["name"]
    hits = _coerce_int(item.get("power_hits", 0))
    hits_recent = _coerce_int(item.get("power_hits_recent", 0))
    paredao_count = _coerce_int(item.get("paredao", 0))
    power_tags = item.get("power_tags") or []
    detail = item.get("power_detail") or []
    nom_text = item.get("nom_text", "")

    border = "#c0392b" if hits >= 4 else ("#e67e22" if hits >= 2 else "#7f8c8d")
    bar_pct = min(100.0, hits / max_hits * 100.0) if max_hits > 0 else 0.0
    hit_label = "ação contra" if hits == 1 else "ações contra"

    # Status line
    par_label = f"{paredao_count} paredão" if paredao_count == 1 else f"{paredao_count} paredões"
    recent_label = f" · {hits_recent} recentes (3 sem.)" if hits_recent else ""
    status_line = f"{par_label}{recent_label}"

    # Power tags
    tag_html = "".join(_power_tag_badge(t, "#3f1b1b", "#ff9d9d") for t in power_tags)
    tags_block = (
        f"<div style='margin-top:3px;display:flex;flex-wrap:wrap;gap:4px;'>{tag_html}</div>"
        if tag_html else ""
    )

    # Drill-down
    detail_block = _power_detail_html(detail, "target", tag_labels)

    return (
        f'<div class="u-s056" style="align-items:flex-start;">'
        f'<a href="{_profile_href(name)}" style="text-decoration:none">{avatar_fn(name, 42, border)}</a>'
        f'<div class="u-s066">'
        f'<div class="u-s059">'
        f'<a href="{_profile_href(name)}" class="fs-md u-s068" style="text-decoration:none;color:inherit">{_escape_text(_short_name(name))}</a>'
        f'<span class="fs-sm" style="color:{value_color(hits, "danger")};font-weight:700;">{hits} {hit_label}</span>'
        f'</div>'
        f'<div class="u-s014">'
        f'<div style="width:{bar_pct:.0f}%;height:100%;background:{value_color(hits, "danger")};border-radius:3px;"></div>'
        f'</div>'
        f'<div class="fs-2xs" style="color:#888;">{_escape_text(status_line)}</div>'
        f'{tags_block}'
        f'{detail_block}'
        f'</div></div>'
    )


def render_agressor_row(item: dict, *, max_hits: int, avatar_fn, tag_labels: dict[str, str] | None = None) -> str:
    """Render a Mais Agressor row with power tags and drill-down."""
    name = item["name"]
    hits = _coerce_int(item.get("power_hits", 0))
    hits_recent = _coerce_int(item.get("power_hits_recent", 0))
    power_tags = item.get("power_tags") or []
    detail = item.get("power_detail") or []

    border = "#8e44ad" if hits >= 4 else ("#6f42c1" if hits >= 2 else "#7f8c8d")
    bar_pct = min(100.0, hits / max_hits * 100.0) if max_hits > 0 else 0.0
    hit_label = "ação" if hits == 1 else "ações"

    recent_label = f" · {hits_recent} recentes (3 sem.)" if hits_recent else ""
    status_line = f"{hits} {hit_label} deliberada{'s' if hits != 1 else ''}{recent_label}"

    tag_html = "".join(_power_tag_badge(t, "#2d1b3f", "#d9b3ff") for t in power_tags)
    tags_block = (
        f"<div style='margin-top:3px;display:flex;flex-wrap:wrap;gap:4px;'>{tag_html}</div>"
        if tag_html else ""
    )
    detail_block = _power_detail_html(detail, "aggressor", tag_labels)

    return (
        f'<div class="u-s056" style="align-items:flex-start;">'
        f'<a href="{_profile_href(name)}" style="text-decoration:none">{avatar_fn(name, 42, border)}</a>'
        f'<div class="u-s066">'
        f'<div class="u-s059">'
        f'<a href="{_profile_href(name)}" class="fs-md u-s068" style="text-decoration:none;color:inherit">{_escape_text(_short_name(name))}</a>'
        f'<span class="fs-sm" style="color:{value_color(hits, "danger")};font-weight:700;">{hits} {hit_label}</span>'
        f'</div>'
        f'<div class="u-s014">'
        f'<div style="width:{bar_pct:.0f}%;height:100%;background:{value_color(hits, "danger")};border-radius:3px;"></div>'
        f'</div>'
        f'<div class="fs-2xs" style="color:#888;">{_escape_text(status_line)}</div>'
        f'{tags_block}'
        f'{detail_block}'
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
    tipo = item.get("tema") or item.get("tipo_label") or item.get("tipo") or "?"
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
    caption = f"<caption>{_escape_text(title_suffix)}</caption>" if title_suffix else ""
    html.append(
        f"""
<div class="index-cross-table scroll-x">
<table class="index-cross-table__table">
{caption}
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


# ═══════════════════════════════════════════════════════════════════════
# Profile-card rendering  (L-1 extraction from index.qmd)
# ═══════════════════════════════════════════════════════════════════════

def _render_profile_hero(
    p: dict,
    *,
    avatars: dict,
    group_colors: dict,
) -> tuple[str, str, str]:
    """Return (avatar_img, group_pill + role_pill, stat_chips) HTML fragments."""
    name = p.get("name")
    member_of = p.get("member_of", "?")
    group = p.get("group", "?")
    balance = p.get("balance", 0)
    roles = p.get("roles", [])
    score = p.get("score", 0)

    avatar_url = avatars.get(name, "")
    cor_grupo = group_colors.get(member_of, "#666")
    role_text = ", ".join(roles) if roles else ""
    score_color = "#28a745" if score >= 0 else "#dc3545"

    avatar_img = (
        f'<img src="{avatar_url}" alt="{name}" '
        f'style="width:88px;height:88px;border-radius:50%;object-fit:cover;'
        f'border:3px solid {cor_grupo};flex-shrink:0;">'
    ) if avatar_url else ""

    group_pill = (
        f'<span style="display:inline-block;background:{cor_grupo};color:#fff;'
        f'padding:2px 8px;border-radius:10px;font-weight:600;" class="fs-xs">{member_of}</span>'
    )
    role_pill = (
        f' <span class="fs-xs u-s372">{role_text}</span>'
    ) if role_text else ""

    vip_w = p.get("vip_cycles", 0)
    xepa_w = p.get("xepa_cycles", 0)
    current_group = group
    group_label = "VIP" if current_group.lower() == "vip" else "Xepa"
    group_chip_color = "#f1c40f" if current_group.lower() == "vip" else "#888"

    # ── Game stats from precomputed data ──
    gs = p.get("game_stats", {})
    n_votes = gs.get("total_house_votes", 0)
    n_paredoes = gs.get("paredao_count", 0)
    cartola_pts = gs.get("cartola_total", 0)
    cartola_rank = gs.get("cartola_rank")
    prova_wins = gs.get("prova_wins", 0)

    # Votos chip (expandable if has detail)
    votes_detail_rows = ""
    for vd in gs.get("house_votes_detail", []):
        voters_str = ", ".join(vd.get("voters", []))
        votes_detail_rows += (
            f"<div class='u-s072'>"
            f"<b>{vd.get('numero', '?')}º Paredão</b> ({vd.get('data', '')})<br>"
            f"<span class='u-s001'>Votaram: {voters_str}</span></div>"
        )
    if votes_detail_rows:
        votos_chip = (
            f'<details class="u-s061">'
            f'<summary class="rxn-chip u-s208">'
            f'🗳️ <b>{n_votes}</b> {"voto" if n_votes == 1 else "votos"}</summary>'
            f'<div class="u-s472">'
            f'{votes_detail_rows}</div></details>'
        )
    else:
        votos_chip = (
            f'<span class="rxn-chip u-s019">'
            f'🗳️ <b>{n_votes}</b> votos</span>'
        )

    # Paredões chip (expandable if has history)
    paredao_detail_rows = ""
    for ph in gs.get("paredao_history", []):
        res = ph.get("resultado", "?")
        res_color = "#e74c3c" if res == "Eliminado" else "#2ecc71" if res == "Sobreviveu" else "#f1c40f"
        vt = ph.get("voto_total")
        vt_str = f" — {vt:.2f}%" if vt is not None else ""
        paredao_detail_rows += (
            f"<div class='u-s072'>"
            f"<b>{ph.get('numero', '?')}º Paredão</b> ({ph.get('data', '')})<br>"
            f"<span class='u-s001'>Como: {ph.get('como', '?')}</span> · "
            f"<span style='color:{res_color};'>{res}{vt_str}</span></div>"
        )
    if n_paredoes > 0 and paredao_detail_rows:
        paredoes_chip = (
            f'<details class="u-s061">'
            f'<summary class="rxn-chip u-s207">'
            f'🏛️ <b>{n_paredoes}</b> {"paredão" if n_paredoes == 1 else "paredões"}</summary>'
            f'<div class="u-s473">'
            f'{paredao_detail_rows}</div></details>'
        )
    else:
        paredoes_chip = (
            f'<span class="rxn-chip u-s019">'
            f'🏛️ <b>0</b> paredões</span>'
        )

    # Cartola chip
    rank_str = f" ({cartola_rank}º)" if cartola_rank else ""
    cartola_chip = (
        f'<span class="rxn-chip u-s206">'
        f'🏆 <b>{cartola_pts}</b> pts{rank_str}</span>'
    )

    # Prova chip (only if wins > 0)
    prova_chip = ""
    if prova_wins > 0:
        prova_chip = (
            f'<span class="rxn-chip u-s203">'
            f'🥇 <b>{prova_wins}</b> {"vitória" if prova_wins == 1 else "vitórias"}</span>'
        )

    # Bate e Volta chip (only if escapes > 0)
    n_bv = gs.get("bv_escapes", 0)
    bv_chip = ""
    if n_bv > 0:
        bv_chip = (
            f'<span class="rxn-chip u-s204">'
            f'🔄 <b>{n_bv}</b> Bate e Volta</span>'
        )

    stat_chips = (
        f'<div class="stat-row">'
        f'<span class="rxn-chip" style="border:1px solid {score_color};">'
        f'<span style="font-weight:700;color:{score_color};">{score:+.1f}</span> Sentimento</span>'
        f'<span class="rxn-chip u-s205">'
        f'{balance:,} Saldo</span>'
        f'<span class="rxn-chip" style="border:1px solid {group_chip_color};">'
        f'<span style="font-weight:700;color:{group_chip_color};">{group_label}</span>'
        f' VIP {vip_w}× · Xepa {xepa_w}×</span>'
        f'{votos_chip}{paredoes_chip}{bv_chip}{cartola_chip}{prova_chip}'
        f'</div>'
    )

    pills_html = f'{group_pill}{role_pill}'
    return avatar_img, pills_html, stat_chips


def _render_profile_status_strip(
    p: dict,
    *,
    allies: list,
    enemies: list,
    false_friends: list,
    blind_targets: list,
) -> str:
    """Return the status-strip HTML (vulnerability, impact, hostility, plant, contradiction)."""
    n_allies = len(allies)
    n_enemies = len(enemies)
    n_false_friends = len(false_friends)

    risk_level = p.get("risk_level")
    risk_color = p.get("risk_color")
    external_level = p.get("external_level")
    external_color = p.get("external_color")
    animosity_level = p.get("animosity_level")
    animosity_color = p.get("animosity_color")
    scores_data = p.get("scores", {})

    ff_names_list = [f["name"] for f in false_friends[:5]]
    ff_names_str = ", ".join(ff_names_list)
    if len(false_friends) > 5:
        ff_names_str += f" +{len(false_friends) - 5}"
    vuln_detail = (
        f"<div class='sb-row'><span>Falsos amigos</span><span>{n_false_friends}</span></div>"
        f"<div class='sb-row'><span>Aliados</span><span>{n_allies}</span></div>"
        f"<div class='sb-row'><span>Inimigos</span><span>{n_enemies}</span></div>"
        f"<div class='sb-row'><span>Alvos ocultos</span><span>{len(blind_targets)}</span></div>"
    )
    if ff_names_list:
        vuln_detail += f"<div class='sb-muted'>Pontos cegos: {ff_names_str}</div>"
    vuln_chip = render_status_chip("🎯", "Vulnerabilidade", risk_level, risk_color, vuln_detail)

    ext_score = scores_data.get("external", 0)
    ext_pos = scores_data.get("external_positive", 0)
    ext_count = scores_data.get("external_count", 0)
    ext_bd = scores_data.get("external_breakdown", {})
    ext_detail = "".join(
        f"<div class='sb-row'><span>{COMP_LABELS.get(k, k)}</span><span>{v:+.1f}</span></div>"
        for k, v in sorted(ext_bd.items(), key=lambda x: x[1])
    ) if ext_bd else "<div class='sb-muted'>Nenhum evento negativo recebido.</div>"
    ext_detail += f"<div class='sb-muted'>Total: {ext_score:.1f} | Positivos: +{ext_pos:.1f} | Eventos: {ext_count}</div>"
    impact_chip = render_status_chip("🎯", "Impacto Recebido", external_level, external_color, ext_detail)

    anim_score = scores_data.get("animosity", 0)
    anim_bd = scores_data.get("animosity_breakdown", {})
    anim_detail = "".join(
        f"<div class='sb-row'><span>{COMP_LABELS.get(k, k)}</span><span>{v:+.1f}</span></div>"
        for k, v in sorted(anim_bd.items(), key=lambda x: x[1])
    ) if anim_bd else "<div class='sb-muted'>Nenhum evento negativo causado.</div>"
    anim_detail += f"<div class='sb-muted'>Total: {anim_score:.1f}</div>"
    hostility_chip = render_status_chip("⚔️", "Agressividade", animosity_level, animosity_color, anim_detail)

    plant_info = p.get("plant_index") or {}
    plant_chip_html = ""
    if plant_info and plant_info.get("score") is not None:
        score_roll = plant_info.get("rolling", plant_info.get("score", 0))
        score_val = int(round(score_roll))
        plant_week_num = plant_info.get("cycle")
        plant_color_hex = plant_color(score_val)
        bd_rows = []
        for item in plant_info.get("breakdown", []):
            pts = item.get("points", 0)
            if pts > 0:
                bd_rows.append(f"<div class='sb-row'><span>{item.get('label', '')}</span><span>+{pts}</span></div>")
        plant_detail = "".join(bd_rows) if bd_rows else "<div class='sb-muted'>Sem sinais fortes.</div>"
        plant_detail += f"<div class='sb-muted'>Semana {plant_week_num} | Rolling {score_roll:.1f}</div>"
        plant_chip_html = render_status_chip("🌱", "Planta Index", f"{score_val}/100", plant_color_hex, plant_detail)

    sinc = p.get("sincerao", {})
    sinc_summary = sinc.get("summary", {})
    sinc_contra_count = sinc_summary.get("contradiction_count", 0)
    sinc_contra_targets = sinc_summary.get("contradiction_targets", [])
    contra_chip = ""
    if sinc_contra_count:
        targets_txt = ", ".join(sinc_contra_targets)
        contra_detail = f"<div class='sb-muted'>Diz que não gosta no Sincerão, mas dá ❤️ para: {targets_txt}</div>"
        contra_chip = render_status_chip("⚡", "Contradição", f"{sinc_contra_count}x", "#6f42c1", contra_detail)

    status_chips = vuln_chip + impact_chip + hostility_chip
    if plant_chip_html:
        status_chips += plant_chip_html
    if contra_chip:
        status_chips += contra_chip
    return status_chips


def _render_profile_reactions(
    p: dict,
    *,
    avatar_fn,
) -> str:
    """Return the reactions-grid HTML (received + given)."""
    rxn_received_chips = " ".join(
        f'<span class="rxn-chip">{r["emoji"]}×{r["count"]}</span>'
        for r in p.get("rxn_summary", [])
    )
    rxn_given_chips = " ".join(
        f'<span class="rxn-chip">{r["emoji"]}×{r["count"]}</span>'
        for r in p.get("given_summary", [])
    )

    received_detail = p.get("received_detail", [])
    given_detail = p.get("given_detail", [])
    received_detail_html = build_rxn_detail_html(received_detail, avatar_fn=avatar_fn)
    given_detail_html = build_rxn_detail_html(given_detail, avatar_fn=avatar_fn)

    return (
        f'<div class="profile-reactions-grid">'
        f'<div>'
        f'<details class="rxn-detail">'
        f'<summary class="u-s046">'
        f'<div class="fs-sm u-s068">RECEBEU <span class="rxn-hint fs-2xs u-s065">▶ clique p/ detalhes</span></div>'
        f'{rxn_received_chips}'
        f'</summary>'
        f'<div class="u-s103">{received_detail_html}</div>'
        f'</details>'
        f'</div>'
        f'<div>'
        f'<details class="rxn-detail">'
        f'<summary class="u-s046">'
        f'<div class="fs-sm u-s068">DEU <span class="rxn-hint fs-2xs u-s065">▶ clique p/ detalhes</span></div>'
        f'{rxn_given_chips}'
        f'</summary>'
        f'<div class="u-s103">{given_detail_html}</div>'
        f'</details>'
        f'</div>'
        f'</div>'
    )


def _render_profile_relations(
    *,
    allies: list,
    enemies: list,
    false_friends: list,
    blind_targets: list,
    render_avatar_row_fn,
) -> str:
    """Return the relations-grid HTML."""
    n_allies = len(allies)
    n_enemies = len(enemies)
    n_false_friends = len(false_friends)

    relations_html = (
        '<div class="fs-xs u-s244">'
        'Score = queridômetro + eventos acumulados (votos, poder, Sincerão). '
        'Positivo = relação boa · Negativo = hostilidade.'
        '</div>'
    )
    if allies:
        relations_html += (
            f'<div class="relation-section u-s188">'
            f'<div class="relation-label u-s055">✅ Aliados ({n_allies})</div>'
            f'{render_avatar_row_fn(allies, "#28a745")}'
            f'<div class="fs-sm u-s245">Score positivo mútuo. Votos seguros.</div>'
            f'</div>'
        )
    if enemies:
        enemy_emoji_text = ", ".join(
            f'{e["name"].split()[0]} ({e.get("my_emoji","?")}↔{e.get("their_emoji","?")})'
            for e in enemies[:6]
        )
        relations_html += (
            f'<div class="relation-section u-s169">'
            f'<div class="relation-label u-s062">⚔️ Inimigos ({n_enemies})</div>'
            f'{render_avatar_row_fn(enemies, "#dc3545")}'
            f'<div class="fs-sm u-s252">{enemy_emoji_text}</div>'
            f'<div class="fs-sm u-s057">Score negativo mútuo. Votos contra esperados.</div>'
            f'</div>'
        )
    if false_friends:
        ff_emoji_text = ", ".join(
            f'<span class="u-s062">{f["name"].split()[0]} ({f.get("their_emoji","?")})</span>'
            for f in false_friends[:6]
        )
        relations_html += (
            f'<div class="relation-section u-s184">'
            f'<div class="relation-label u-s293">⚠️ Falsos Amigos ({n_false_friends}) — PERIGO</div>'
            f'{render_avatar_row_fn(false_friends, "#ffc107")}'
            f'<div class="fs-sm u-s079">{ff_emoji_text}</div>'
            f'<div class="fs-sm u-s057">Seu score é positivo, o deles negativo. Votam contra 2-3×.</div>'
            f'</div>'
        )
    if blind_targets:
        bt_emoji_text = ", ".join(
            f'<span class="u-s028">{b["name"].split()[0]} ({b.get("my_emoji","?")})</span>'
            for b in blind_targets[:6]
        )
        relations_html += (
            f'<div class="relation-section u-s165">'
            f'<div class="relation-label u-s028">🗡️ Alvos Ocultos ({len(blind_targets)})</div>'
            f'{render_avatar_row_fn(blind_targets, "#6f42c1")}'
            f'<div class="fs-sm u-s079">{bt_emoji_text}</div>'
            f'<div class="fs-sm u-s057">Seu score é negativo, o deles positivo. Não sabem.</div>'
            f'</div>'
        )
    return relations_html


def _render_profile_sincerao(p: dict) -> str:
    """Return the Sincerão section HTML for a profile card."""
    sinc = p.get("sincerao", {})
    sinc_summary = sinc.get("summary", {})
    sinc_current = sinc.get("current", {})
    sinc_season = sinc.get("season", {})
    sinc_total = sinc_summary.get("received_total", 0) + sinc_summary.get("given_total", 0)

    sincerao_html = ""
    if sinc_total > 0:
        CURRENT_INLINE_MAX = 8
        HISTORY_INLINE_MAX = 10
        sinc_parts: list[str] = []

        # -- Current week (Recebeu / Fez) --
        current_rows: list[str] = []
        current_received = sinc_current.get("received", [])
        if current_received:
            current_rows.append(render_profile_sinc_row("Recebeu", current_received, "actor", CURRENT_INLINE_MAX))

        current_given = sinc_current.get("given", [])
        if current_given:
            current_rows.append(render_profile_sinc_row("Fez", current_given, "target", CURRENT_INLINE_MAX))

        if current_rows:
            sinc_parts.append(f"<div class='profile-sinc-current'>{''.join(current_rows)}</div>")

        # -- Season history (collapsed): both received AND given per past week --
        received_by_week = sinc_season.get("received_by_week", [])
        given_by_week = sinc_season.get("given_by_week", [])
        current_wk = sinc.get("current_cycle")

        past_weeks_set: set = set()
        for w in received_by_week:
            _wk = w.get("cycle")
            if _wk != current_wk:
                past_weeks_set.add(_wk)
        for w in given_by_week:
            _wk = w.get("cycle")
            if _wk != current_wk:
                past_weeks_set.add(_wk)

        if past_weeks_set:
            recv_lookup = {w.get("cycle"): w["interactions"] for w in received_by_week}
            given_lookup = {w.get("cycle"): w["interactions"] for w in given_by_week}
            history_rows: list[str] = []
            for wk in sorted(past_weeks_set, reverse=True):
                week_parts: list[str] = []
                week_badge = f"<span class='profile-sinc-week'>S{wk}</span>"
                week_badge_ghost = "<span class='profile-sinc-week ghost'></span>"

                recv_ints = recv_lookup.get(wk, [])
                if recv_ints:
                    week_parts.append(
                        render_profile_sinc_row(
                            "Recebeu",
                            recv_ints,
                            "actor",
                            HISTORY_INLINE_MAX,
                            week_prefix=week_badge,
                        )
                    )

                given_ints = given_lookup.get(wk, [])
                if given_ints:
                    week_parts.append(
                        render_profile_sinc_row(
                            "Fez",
                            given_ints,
                            "target",
                            HISTORY_INLINE_MAX,
                            week_prefix=(week_badge_ghost if recv_ints else week_badge),
                        )
                    )

                if week_parts:
                    history_rows.append(f"<div class='profile-sinc-week-block'>{''.join(week_parts)}</div>")

            if history_rows:
                n_past = len(past_weeks_set)
                sinc_parts.append(
                    f"<details class='profile-sinc-history'>"
                    f"<summary>+ {n_past} semana{'s' if n_past > 1 else ''} anterior{'es' if n_past > 1 else ''}</summary>"
                    f"<div class='profile-sinc-history-body'>{''.join(history_rows)}</div>"
                    f"</details>"
                )

        sincerao_html = "".join(sinc_parts)
    return sincerao_html


def _render_profile_dynamics(
    p: dict,
    *,
    relation_colors: dict,
    avatars: dict,
    avatar_fn,
    make_event_chips_fn,
    sincerao_html: str,
) -> str:
    """Return the game-dynamics section HTML."""
    events = p.get("events", {})

    pos_html = make_event_chips_fn(events.get("pos_week", []), "#28a745", relation_colors)
    neg_html = make_event_chips_fn(events.get("neg_week", []), "#dc3545", relation_colors)
    pos_hist_html = make_event_chips_fn(events.get("pos_hist", []), "#2ecc71", relation_colors) if events.get("pos_hist") else ""
    neg_hist_html = make_event_chips_fn(events.get("neg_hist", []), "#e74c3c", relation_colors) if events.get("neg_hist") else ""
    hist_html = ""
    if events.get("pos_hist"):
        hist_html += f"<span class='u-s055'>{pos_hist_html}</span>"
    if events.get("neg_hist"):
        hist_html += f"<span class='u-s271'>{neg_hist_html}</span>"

    votes = p.get("votes_received", [])
    votes_html = ""
    if votes:
        vote_rows: list[str] = []
        for v in votes:
            voter = v.get("voter")
            count = v.get("count", 1)
            is_revealed = v.get("revealed", False)
            count_badge = f'<span class="fs-2xs u-s148">{count}×</span>' if count > 1 else ""
            border = relation_colors.get(voter, "#666")
            reveal_badge = ' <span class="fs-sm u-s025">👁️</span>' if is_revealed else ""
            voter_avatar = avatar_fn(voter, 36, border) if voter in avatars else ""
            voter_first = voter.split()[0] if voter else ""
            vote_rows.append(
                f"<div class='u-s334'>"
                f"{voter_avatar}"
                f"<span class='fs-base u-s272'>{voter_first}</span>"
                f"{count_badge}{reveal_badge}</div>"
            )
        votes_html = "".join(vote_rows)

    sinc = p.get("sincerao", {})
    sinc_summary = sinc.get("summary", {})
    sinc_total = sinc_summary.get("received_total", 0) + sinc_summary.get("given_total", 0)

    has_dynamics = (events.get("pos_week") or events.get("neg_week") or votes or sincerao_html
                    or events.get("pos_hist") or events.get("neg_hist"))
    dynamics_html = ""
    if has_dynamics:
        dynamics_inner = ""
        if events.get("pos_week"):
            dynamics_inner += (
                f"<div class='u-s338'>"
                f"<strong class='fs-base u-s055'>+ Benefícios</strong> {pos_html}</div>"
            )
        if events.get("neg_week"):
            dynamics_inner += (
                f"<div class='u-s337'>"
                f"<strong class='fs-base u-s062'>− Prejuízos</strong> {neg_html}</div>"
            )
        if votes:
            dynamics_inner += (
                f"<div class='u-s037'>"
                f"<strong class='fs-base u-s294'>🗳️ Votos recebidos</strong>"
                f"<div class='u-s353'>{votes_html}</div></div>"
            )
        if sincerao_html:
            sinc_count_label = f" ({sinc_total})" if sinc_total else ""
            dynamics_inner += (
                f"<div style='display:flex;flex-direction:column;gap:2px'>"
                f"<strong class='fs-base u-s025'>🔥 Sincerão{sinc_count_label}</strong>{sincerao_html}</div>"
            )
        if events.get("pos_hist") or events.get("neg_hist"):
            dynamics_inner += (
                f"<div class='u-s335'>"
                f"<strong class='fs-base u-s061'>📜 Histórico</strong> {hist_html}</div>"
            )
        dynamics_html = (
            f'<div class="u-s465">'
            f'<div class="fs-base u-s390">⚡ Dinâmicas do Jogo</div>'
            f'<div class="fs-base">{dynamics_inner}</div>'
            f'</div>'
        )
    return dynamics_html


def _render_profile_curiosities(p: dict) -> str:
    """Return the curiosities section HTML."""
    curiosities = p.get("curiosities", [])
    if not curiosities:
        return ""
    items_html = "".join(
        f'<div class="curiosity-item">'
        f'<span class="curiosity-icon">{c["icon"]}</span>'
        f'<span>{c["text"]}</span></div>'
        for c in curiosities
    )
    return (
        f'<div class="u-s464">'
        f'<div class="fs-base u-s391">💡 Curiosidades</div>'
        f'{items_html}</div>'
    )


def render_profile_card(
    p: dict,
    *,
    avatars: dict,
    group_colors: dict,
    avatar_fn,
    make_event_chips_fn,
    render_avatar_row_fn,
) -> str:
    """Render the full HTML for one participant profile card.

    Parameters
    ----------
    p : dict
        Participant profile dict from ``index_data["profiles"]``.
    avatars : dict
        Mapping of participant name -> avatar URL.
    group_colors : dict
        ``GROUP_COLORS`` mapping.
    avatar_fn : callable
        Partially-applied ``av()`` helper (``avatar_fn(name, size, border)``).
    make_event_chips_fn : callable
        Partially-applied ``make_event_chips()`` helper.
    render_avatar_row_fn : callable
        Partially-applied ``render_avatar_row()`` helper.
    """
    name = p.get("name", "")
    member_of = p.get("member_of", "?")
    cor_grupo = group_colors.get(member_of, "#666")
    name_slug = name.lower().replace(" ", "-")

    rel = p.get("relations", {})
    allies = rel.get("allies", [])
    enemies = rel.get("enemies", [])
    false_friends = rel.get("false_friends", [])
    blind_targets = rel.get("blind_targets", [])

    ally_names = {a["name"] for a in allies}
    enemy_names = {n["name"] for n in enemies}
    false_friend_names = {n["name"] for n in false_friends}
    blind_names = {n["name"] for n in blind_targets}

    relation_colors: dict[str, str] = {}
    relation_colors.update({n: "#28a745" for n in ally_names})
    relation_colors.update({n: "#dc3545" for n in enemy_names})
    relation_colors.update({n: "#ffc107" for n in false_friend_names})
    relation_colors.update({n: "#6f42c1" for n in blind_names})

    # [1] HERO
    avatar_img, pills_html, stat_chips = _render_profile_hero(
        p,
        avatars=avatars,
        group_colors=group_colors,
    )

    # [2] STATUS STRIP
    status_chips = _render_profile_status_strip(
        p,
        allies=allies,
        enemies=enemies,
        false_friends=false_friends,
        blind_targets=blind_targets,
    )

    # [3] REACTIONS
    reactions_html = _render_profile_reactions(p, avatar_fn=avatar_fn)

    # [4] RELATIONS
    relations_html = _render_profile_relations(
        allies=allies,
        enemies=enemies,
        false_friends=false_friends,
        blind_targets=blind_targets,
        render_avatar_row_fn=render_avatar_row_fn,
    )
    relations_content = relations_html if relations_html else '<div class="fs-base u-s058">Sem relações classificadas.</div>'

    # [5] SINCERAO (needed by dynamics)
    sincerao_html = _render_profile_sincerao(p)

    # [6] DYNAMICS
    dynamics_html = _render_profile_dynamics(
        p,
        relation_colors=relation_colors,
        avatars=avatars,
        avatar_fn=avatar_fn,
        make_event_chips_fn=make_event_chips_fn,
        sincerao_html=sincerao_html,
    )

    # [7] CURIOSITIES
    curiosities_html = _render_profile_curiosities(p)

    # ═══ ASSEMBLE CARD ═══
    return (
        f'<div id="perfil-{name_slug}" class="profile-card u-s039">'
        f'<div style="background:linear-gradient(90deg,rgba(48,48,48,0.9),rgba(48,48,48,0.3));border-left:5px solid {cor_grupo};">'
        f'<div class="profile-hero-inner">'
        f'{avatar_img}'
        f'<div>'
        f'<h3 class="fs-2xl u-s434">{name}</h3>'
        f'<div class="u-s356">'
        f'{pills_html}'
        f'</div>'
        f'{stat_chips}'
        f'</div>'
        f'</div>'
        f'</div>'
        f'<div class="profile-status-strip">'
        f'{status_chips}'
        f'</div>'
        f'{reactions_html}'
        f'{dynamics_html}'
        f'<div class="profile-relations">'
        f'{relations_content}'
        f'</div>'
        f'{curiosities_html}'
        f'</div>'
    )
