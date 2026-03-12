"""Shared helpers for the Votacao page."""

from __future__ import annotations

from html import escape


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def build_retro_vote_summary(paredoes_finalizados: list[dict]) -> dict:
    rows: list[dict] = []
    n_changed = 0
    winner_deltas: list[float] = []

    for paredao in paredoes_finalizados:
        participants: list[dict] = []
        for part in paredao.get("participantes", []):
            if part.get("voto_unico") is None or part.get("voto_torcida") is None:
                continue
            vu = _to_float(part.get("voto_unico"))
            vt = _to_float(part.get("voto_torcida"))
            v7030 = _to_float(part.get("voto_total"), (vu * 0.7) + (vt * 0.3))
            v5050 = (vu * 0.5) + (vt * 0.5)
            participants.append(
                {
                    "nome": part.get("nome", ""),
                    "vu": vu,
                    "vt": vt,
                    "v7030": v7030,
                    "v5050": v5050,
                    "delta": v7030 - v5050,
                }
            )

        if not participants:
            continue

        winner_7030 = max(participants, key=lambda item: item["v7030"])
        winner_5050 = max(participants, key=lambda item: item["v5050"])
        mudou = winner_7030["nome"] != winner_5050["nome"]
        if mudou:
            n_changed += 1

        winner_deltas.append(abs(winner_7030["v7030"] - winner_7030["v5050"]))
        rows.append(
            {
                "paredao": paredao.get("numero"),
                "is_falso": bool(paredao.get("paredao_falso", False)),
                "participants": sorted(
                    participants,
                    key=lambda item: item["v7030"],
                    reverse=True,
                ),
                "winner_7030": winner_7030,
                "winner_5050": winner_5050,
                "mudou": mudou,
            }
        )

    avg_delta = sum(winner_deltas) / len(winner_deltas) if winner_deltas else 0.0
    return {
        "rows": rows,
        "n_changed": n_changed,
        "avg_delta": avg_delta,
    }


def build_voting_health_summary(paredoes_fin: list[dict]) -> dict:
    rows: list[dict] = []

    for paredao in paredoes_fin:
        participants = paredao.get("participantes", [])
        if not participants or participants[0].get("voto_unico") is None:
            continue

        by_vu = sorted(participants, key=lambda item: _to_float(item.get("voto_unico")), reverse=True)
        if len(by_vu) < 2:
            continue

        top_choice = by_vu[0]
        second_choice = by_vu[1]
        actual_winner = max(participants, key=lambda item: _to_float(item.get("voto_total")))
        by_vt = sorted(participants, key=lambda item: _to_float(item.get("voto_torcida")), reverse=True)
        vt_top = by_vt[0]

        surv_vu = _to_float(second_choice.get("voto_unico"))
        surv_vt = _to_float(second_choice.get("voto_torcida"))
        elim_vu = _to_float(top_choice.get("voto_unico"))
        elim_vt = _to_float(top_choice.get("voto_torcida"))
        surv_inflation = surv_vt - surv_vu
        elim_gap = elim_vt - elim_vu
        danger = max(max(0.0, surv_inflation), max(0.0, -elim_gap))

        rows.append(
            {
                "num": paredao.get("numero", "?"),
                "is_falso": bool(paredao.get("paredao_falso", False)),
                "surv_nome": second_choice.get("nome", ""),
                "surv_vu": surv_vu,
                "surv_vt": surv_vt,
                "surv_inflation": surv_inflation,
                "elim_nome": top_choice.get("nome", ""),
                "elim_vu": elim_vu,
                "elim_vt": elim_vt,
                "elim_gap": elim_gap,
                "danger": danger,
                "povo_decidiu": top_choice.get("nome") == actual_winner.get("nome"),
                "ranking_invertido": top_choice.get("nome") != vt_top.get("nome"),
                "vt_top_nome": vt_top.get("nome", ""),
                "vt_top_pct": _to_float(vt_top.get("voto_torcida")),
                "vt_top_vu": _to_float(vt_top.get("voto_unico")),
            }
        )

    max_danger_row = max(rows, key=lambda item: item["danger"], default=None)
    max_danger = max_danger_row["danger"] if max_danger_row else 0.0
    max_danger_num = max_danger_row["num"] if max_danger_row else "?"
    return {
        "rows": rows,
        "max_danger": max_danger,
        "max_danger_num": max_danger_num,
        "n_above_3": sum(1 for item in rows if item["danger"] >= 3),
        "n_above_5": sum(1 for item in rows if item["danger"] >= 5),
        "n_above_7": sum(1 for item in rows if item["danger"] >= 7),
        "n_healthy": sum(1 for item in rows if item["danger"] < 3),
        "max_flip_7030": (max_danger / (70 / 30)) if max_danger else 0.0,
    }


def render_votacao_badge(text: str, tone: str) -> str:
    return f'<span class="votacao-badge votacao-badge--{escape(tone)}">{escape(text)}</span>'


def render_votacao_status_chip(text: str, tone: str) -> str:
    return f'<span class="votacao-status-chip votacao-status-chip--{escape(tone)}">{escape(text)}</span>'


def _render_retro_card(row: dict) -> str:
    label = f'{row["paredao"]}o Paredão Falso' if row.get("is_falso") else f'{row["paredao"]}o Paredão'
    badge = render_votacao_badge("resultado muda", "change") if row.get("mudou") else render_votacao_badge("mesmo resultado", "same")

    lines = ['<article class="votacao-retro-card">']
    lines.append('<div class="votacao-retro-card-header">')
    lines.append(f'<div class="votacao-retro-card-title">{escape(label)}</div>')
    lines.append(badge)
    lines.append("</div>")

    winner_7030 = row["winner_7030"]["nome"]
    winner_5050 = row["winner_5050"]["nome"]
    top_label = "SALVO" if row.get("is_falso") else "ELIM"
    winner_tone = "saved" if row.get("is_falso") else "elim"
    alt_tone = winner_tone if winner_7030 == winner_5050 else "alt"

    lines.append('<div class="votacao-retro-card-verdict">')
    lines.append(
        f'<div class="votacao-retro-card-verdict-line">{render_votacao_status_chip(f"{top_label} 70/30", winner_tone)} '
        f'<strong>{escape(winner_7030)}</strong></div>'
    )
    lines.append(
        f'<div class="votacao-retro-card-verdict-line">{render_votacao_status_chip(f"{top_label} 50/50", alt_tone)} '
        f'<strong>{escape(winner_5050)}</strong></div>'
    )
    lines.append("</div>")

    lines.append('<div class="votacao-retro-card-rows">')
    for part in row["participants"]:
        lines.append('<div class="votacao-retro-card-row">')
        lines.append(f'<div class="votacao-retro-card-name">{escape(part["nome"])}</div>')
        lines.append(
            '<div class="votacao-retro-card-metrics">'
            f'<span>VU {part["vu"]:.2f}%</span>'
            f'<span>VT {part["vt"]:.2f}%</span>'
            f'<span>70/30 {part["v7030"]:.2f}%</span>'
            f'<span>50/50 {part["v5050"]:.2f}%</span>'
            f'<span>Δ {part["delta"]:+.2f}</span>'
            '</div>'
        )
        lines.append("</div>")
    lines.append("</div>")
    lines.append("</article>")
    return "".join(lines)


def render_votacao_retro_section(summary: dict) -> str:
    rows = summary.get("rows", [])
    if not rows:
        return '<section class="votacao-retro"></section>'

    lines = ['<section class="votacao-section votacao-retro">']
    lines.append(
        '<div class="votacao-retro-summary">'
        f'<strong>{summary.get("n_changed", 0)}/{len(rows)}</strong> paredões mudariam de resultado com 50/50'
        f'<span>Diferença média no percentual do mais votado: {summary.get("avg_delta", 0.0):.2f} p.p.</span>'
        '</div>'
    )

    lines.append('<div class="votacao-retro-cards votacao-mobile-only">')
    for row in rows:
        lines.append(_render_retro_card(row))
    lines.append("</div>")

    lines.append('<div class="votacao-retro-table-wrap votacao-desktop-only">')
    lines.append('<table class="votacao-compare-table votacao-retro-table">')
    lines.append('<caption>Comparação entre os resultados 70/30 e 50/50 em cada paredão finalizado.</caption>')
    lines.append("<thead><tr>")
    for label in ("Nome", "Voto Único", "Voto Torcida", "70/30", "50/50", "Δ", "Status"):
        lines.append(f'<th scope="col">{escape(label)}</th>')
    lines.append("</tr></thead><tbody>")

    for row in rows:
        label = f'{row["paredao"]}o Paredão Falso' if row.get("is_falso") else f'{row["paredao"]}o Paredão'
        group_badge = render_votacao_badge("resultado muda", "change") if row.get("mudou") else render_votacao_badge("mesmo resultado", "same")
        lines.append(
            f'<tr class="votacao-group-row votacao-retro-group-row"><th scope="colgroup" colspan="7">{escape(label)} {group_badge}</th></tr>'
        )

        top_label = "SALVO" if row.get("is_falso") else "ELIM"
        winner_tone = "saved" if row.get("is_falso") else "elim"

        for part in row["participants"]:
            chips: list[str] = []
            if part["nome"] == row["winner_7030"]["nome"]:
                chips.append(render_votacao_status_chip(f"{top_label} 70/30", winner_tone))
            if part["nome"] == row["winner_5050"]["nome"] and part["nome"] != row["winner_7030"]["nome"]:
                chips.append(render_votacao_status_chip(f"{top_label} 50/50", "alt"))
            if not chips:
                fallback = "não salvo" if row.get("is_falso") else "salvo"
                fallback_tone = "quiet" if row.get("is_falso") else "saved"
                chips.append(render_votacao_status_chip(fallback, fallback_tone))

            delta = part["delta"]
            delta_color = "#ff9b93" if delta > 0 else "#88efb2" if delta < 0 else "#aab9cb"

            lines.append("<tr>")
            lines.append(f'<th scope="row">{escape(part["nome"])}</th>')
            lines.append(f'<td class="votacao-number">{part["vu"]:.2f}%</td>')
            lines.append(f'<td class="votacao-number">{part["vt"]:.2f}%</td>')
            lines.append(f'<td class="votacao-number">{part["v7030"]:.2f}%</td>')
            lines.append(f'<td class="votacao-number">{part["v5050"]:.2f}%</td>')
            lines.append(f'<td class="votacao-number" style="color:{delta_color};">{delta:+.2f}</td>')
            lines.append(f'<td>{" ".join(chips)}</td>')
            lines.append("</tr>")

    lines.append("</tbody></table></div></section>")
    return "".join(lines)
