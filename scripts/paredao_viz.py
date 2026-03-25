"""Paredão page visualization helpers — extracted from paredao.qmd."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
import re

from data_utils import (
    GROUP_COLORS,
    POWER_EVENT_EMOJI,
    POWER_EVENT_LABELS,
    REACTION_EMOJI,
    SENTIMENT_WEIGHTS,
    POSITIVE,
    MILD_NEGATIVE,
    STRONG_NEGATIVE,
    VOTALHADA_HOME,
    avatar_html,
    avatar_img,
    artigo,
    backtest_precision_model,
    calculate_precision_weights,
    calculate_votalhada_estimate_3070,
    genero,
    get_latest_votalhada_displayed_values,
    get_votalhada_source_url,
    has_votalhada_formula_change,
    normalize_route_label,
    parse_votalhada_hora,
    poll_has_weighted_latest_overlay,
    predict_precision_weighted,
    render_votalhada_logo,
    safe_html,
)

# ---------------------------------------------------------------------------
# Module-level constants for Líder prediction rendering
# ---------------------------------------------------------------------------

_COMP_META: dict[str, tuple[str, str, str]] = {
    "queridometro": ("🐍", "#e74c3c", "#2ecc71"),
    "power_event": ("⚔️", "#e74c3c", "#2ecc71"),
    "sincerao":    ("📢", "#e67e22", "#3498db"),
    "vote":        ("🗳️", "#e74c3c", "#2ecc71"),
    "vip":         ("🏠", "#3498db", "#3498db"),
    "anjo":        ("😇", "#3498db", "#3498db"),
}

_EDGE_DISPLAY: dict[str, tuple[str, str]] = {
    "power_event": ("⚔️", "Power Event"),
    "sincerao": ("📢", "Sincerão"),
    "vote": ("🗳️", "Voto"),
    "vip": ("🏠", "VIP"),
    "anjo": ("😇", "Anjo"),
}

_EMOJI_MAP = REACTION_EMOJI
_SPOTLIGHT_POWER_TYPES = {"mira_do_lider", "indicacao", "monstro", "barrado_baile", "veto_bate_volta"}
_SPOTLIGHT_SUMMARY_META: dict[str, tuple[str, str]] = {
    "mira_do_lider": (POWER_EVENT_EMOJI.get("mira_do_lider", "🔭"), POWER_EVENT_LABELS.get("mira_do_lider", "Mira do Líder")),
    "indicacao": (POWER_EVENT_EMOJI.get("indicacao", "🎯"), POWER_EVENT_LABELS.get("indicacao", "Indicação")),
    "monstro": (POWER_EVENT_EMOJI.get("monstro", "👹"), POWER_EVENT_LABELS.get("monstro", "Monstro")),
    "barrado_baile": (POWER_EVENT_EMOJI.get("barrado_baile", "🚫"), POWER_EVENT_LABELS.get("barrado_baile", "Barrado no Baile")),
    "veto_bate_volta": ("🌀", "Veto no Bate-Volta"),
    "ataque": ("💣", "Ataque"),
    "nao_ganha": ("🚫", "Não ganha"),
    "paredao_perfeito": ("🧱", "Paredão Perfeito"),
    "regua_fora": ("📏", "Fora da Régua"),
}
_SPOTLIGHT_EVENT_ORDER = {
    "mira_do_lider": 1,
    "indicacao": 2,
    "monstro": 3,
    "barrado_baile": 4,
    "veto_bate_volta": 5,
    "ataque": 6,
    "nao_ganha": 7,
    "paredao_perfeito": 8,
    "regua_fora": 9,
}


def build_paredao_history(
    all_paredoes: list[dict],
    current_numero: int,
) -> dict[str, list[dict]]:
    """Build per-participant paredão history from all paredões before the current one.

    Excludes Bate e Volta winners (they escaped and were not on the final paredão).
    """
    from data_utils import get_bv_winners

    history: dict[str, list[dict]] = {}
    for p in all_paredoes:
        num = p.get('numero', 0)
        if num >= current_numero:
            continue  # Only past paredões
        falso = p.get('paredao_falso', False)
        resultado = p.get('resultado', {})
        eliminado = resultado.get('eliminado', '')
        votos = resultado.get('votos', {})
        bv_winners = get_bv_winners(p)
        for ind in p.get('indicados_finais', []):
            nome = ind['nome']
            if nome in bv_winners:
                continue  # BV winners escaped — not counted as paredão appearance
            como = ind.get('como', '?')
            entry: dict = {'paredao': num, 'como': como, 'falso': falso}
            if votos and nome in votos:
                v = votos[nome]
                entry['voto_total'] = v.get('voto_total', 0)
                entry['eliminado'] = (nome == eliminado)
            history.setdefault(nome, []).append(entry)
    return history


EMPATE_THRESHOLD_PP = 2.0  # p.p. — gap below this = "empate técnico"


def is_empate_tecnico(gap_pp: float | None) -> bool:
    """Return True if the top-2 gap is below the empate técnico threshold."""
    return gap_pp is not None and gap_pp < EMPATE_THRESHOLD_PP


_PAREDAO_ROLE_COLORS: dict[str, str] = {
    "danger": "#e74c3c",
    "warning": "#f39c12",
    "safe": "#2ecc71",
    "neutral": "#95a5a6",
}


def _rich_text(text: str | None) -> str:
    """Escape user text and render simple **bold** emphasis."""
    if not text:
        return ""
    escaped = safe_html(text)
    rendered = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    return rendered.replace("\n", "<br>")


def _is_finalized_paredao(entry: dict | None) -> bool:
    if not entry:
        return False
    if entry.get("status") == "finalizado":
        return True
    return any(p.get("resultado") for p in entry.get("participantes", []))


def _format_collection_label(data_coleta: str | None) -> str | None:
    if not data_coleta:
        return None
    try:
        dt = datetime.fromisoformat(data_coleta.replace("Z", "+00:00"))
        return f"Coleta {dt.strftime('%d/%m')} · {dt.strftime('%H:%M')}"
    except Exception:
        return None






def _result_is_selected(result: str | None) -> bool:
    normalized = (result or "").upper()
    return normalized.startswith("ELIMINAD") or normalized == "QUARTO_SECRETO"


def _build_trust_badge(polls_data: dict | None) -> dict:
    backtest = backtest_precision_model(polls_data or {"paredoes": []}) if polls_data else None
    aggregate = (backtest or {}).get("aggregate") or {}
    n_paredoes = aggregate.get("n_paredoes", 0)
    model_mae = aggregate.get("model_mae")
    consolidado_mae = aggregate.get("consolidado_mae")
    visible = bool(
        n_paredoes >= 3
        and model_mae is not None
        and consolidado_mae is not None
        and model_mae < consolidado_mae
    )
    if not visible:
        return {"visible": False, "text": "", "short_text": "", "href": "", "aggregate": aggregate}

    model_correct = aggregate.get("model_correct", 0)
    consolidado_correct = aggregate.get("consolidado_correct", 0)
    votalhada_wrong = max(0, n_paredoes - consolidado_correct)
    if model_correct == n_paredoes:
        text = (
            f"No retrospectivo, nosso modelo acertou todos os paredões ({model_correct}/{n_paredoes}). "
            f"O Votalhada errou {votalhada_wrong} ({consolidado_correct}/{n_paredoes}). "
            f"Erro médio: {model_mae:.1f} p.p. vs {consolidado_mae:.1f} p.p."
        )
        short_text = (
            f"Acertamos {model_correct}/{n_paredoes}; Votalhada {consolidado_correct}/{n_paredoes} "
            f"(errou {votalhada_wrong})."
        )
    else:
        text = (
            f"No retrospectivo: nosso modelo {model_correct}/{n_paredoes} (erro {model_mae:.1f} p.p.) "
            f"vs Votalhada {consolidado_correct}/{n_paredoes} (erro {consolidado_mae:.1f} p.p.)."
        )
        short_text = (
            f"Retrospectivo: modelo {model_correct}/{n_paredoes} vs Votalhada {consolidado_correct}/{n_paredoes}."
        )
    return {
        "visible": True,
        "text": text,
        "short_text": short_text,
        "href": "paredoes.html#nosso-modelo-back-test",
        "aggregate": aggregate,
    }


def _route_fact_priority(route_short: str) -> int:
    lower = route_short.lower()
    if lower == "líder":
        return 0
    if "contragolpe" in lower:
        return 1
    if "consenso" in lower:
        return 2
    if "duelo" in lower:
        return 3
    return 4


def _build_active_fact_lines(nominees: list[dict], vote_mode: str) -> list[str]:
    facts: list[str] = []
    with_model = [n for n in nominees if n.get("model_pct") is not None]
    if len(with_model) >= 2:
        lead, runner = with_model[0], with_model[1]
        gap = abs((lead.get("model_pct") or 0.0) - (runner.get("model_pct") or 0.0))
        if is_empate_tecnico(gap):
            facts.append(
                f"Empate técnico no Nosso Modelo: {lead['first_name']} {lead['model_pct']:.2f}% "
                f"vs {runner['first_name']} {runner['model_pct']:.2f}%."
            )
        elif vote_mode == "save":
            facts.append(
                f"{lead['first_name']} lidera o Nosso Modelo por {gap:.1f} p.p. "
                f"sobre {runner['first_name']}."
            )
        else:
            facts.append(
                f"{lead['first_name']} abre {gap:.1f} p.p. sobre {runner['first_name']} "
                f"no Nosso Modelo."
            )

    repeat_nominees = [n for n in nominees if n.get("appearance_count", 1) > 1]
    if repeat_nominees:
        repeat_nominees.sort(key=lambda n: (-n["appearance_count"], n["name"]))
        repeated = repeat_nominees[0]
        facts.append(
            f"{repeated['first_name']} chega ao {repeated['appearance_count']}º paredão."
        )
    elif vote_mode == "save":
        facts.append("Neste paredão falso, a maior porcentagem indica quem segue no jogo.")
    else:
        routes = sorted(
            [n for n in nominees if n.get("route_short") and n.get("route_short") != "Aguardando origem"],
            key=lambda n: (_route_fact_priority(n["route_short"]), n["name"]),
        )
        if routes:
            chosen = routes[0]
            facts.append(f"{chosen['first_name']} caiu via {chosen['route_short']}.")

    return facts[:2]


def _build_card_curiosity_line(
    poll: dict | None,
    model_prediction: dict | None,
    vote_mode: str,
) -> tuple[str | None, list[dict]]:
    """Build a single dynamic curiosity line for active paredão/index cards."""
    if not poll:
        return None, []

    participantes = poll.get("participantes", [])
    consolidado = poll.get("consolidado", {})
    if len(participantes) < 2:
        return None, []

    v_rank = sorted(
        [(nome, float(consolidado.get(nome, 0) or 0)) for nome in participantes],
        key=lambda x: (-x[1], x[0]),
    )

    model_values = (model_prediction or {}).get("prediction", {}) if model_prediction else {}

    # Priority 1: momentum from the latest windows.
    serie = poll.get("serie_temporal", [])
    if len(serie) >= 3 and len(v_rank) >= 2:
        lead, runner = v_rank[0][0], v_rank[1][0]
        gap_now = max(0.0, v_rank[0][1] - v_rank[1][1])
        k = min(3, len(serie) - 1)
        past = serie[-(k + 1)]
        last = serie[-1]
        lead_delta = float(last.get(lead, 0) or 0) - float(past.get(lead, 0) or 0)
        runner_delta = float(last.get(runner, 0) or 0) - float(past.get(runner, 0) or 0)
        closing = runner_delta - lead_delta

        leader_swaps = 0
        try:
            leaders = [max(participantes, key=lambda n: float(pt.get(n, 0) or 0)) for pt in serie]
            leader_swaps = sum(1 for i in range(1, len(leaders)) if leaders[i] != leaders[i - 1])
        except Exception:
            leader_swaps = 0

        # Always freeze turnaround messaging once the configured closing time has passed,
        # regardless of momentum threshold.
        try:
            coleta_raw = str(poll.get("data_coleta", "")).replace("Z", "+00:00")
            coleta_dt = datetime.fromisoformat(coleta_raw) if coleta_raw else None

            close_raw = poll.get("fechamento_votacao")
            if close_raw:
                close_dt = datetime.fromisoformat(str(close_raw).replace("Z", "+00:00"))
            else:
                close_date = str(poll.get("data_paredao", ""))
                close_dt = datetime.fromisoformat(f"{close_date}T22:45:00-03:00") if close_date else None

            if coleta_dt and close_dt:
                if coleta_dt.tzinfo is None:
                    coleta_dt = coleta_dt.replace(tzinfo=timezone.utc)
                else:
                    coleta_dt = coleta_dt.astimezone(timezone.utc)
                if close_dt.tzinfo is None:
                    close_dt = close_dt.replace(tzinfo=timezone.utc)
                else:
                    close_dt = close_dt.astimezone(timezone.utc)

                now_utc = datetime.now(timezone.utc)
                now_ref = now_utc.replace(
                    minute=(now_utc.minute // 15) * 15,
                    second=0,
                    microsecond=0,
                )
                effective_start = max(coleta_dt, now_ref)
                hours_left = (close_dt - effective_start).total_seconds() / 3600.0
                if hours_left <= 0.05:
                    closing_rate_h = 0.0
                    try:
                        year_ref = int(str(poll.get("data_paredao", "2026")).split("-")[0])
                        t0 = parse_votalhada_hora(str(past.get("hora", "")), year=year_ref)
                        t1 = parse_votalhada_hora(str(last.get("hora", "")), year=year_ref)
                        if t0.tzinfo is None:
                            t0 = t0.replace(tzinfo=timezone.utc)
                        else:
                            t0 = t0.astimezone(timezone.utc)
                        if t1.tzinfo is None:
                            t1 = t1.replace(tzinfo=timezone.utc)
                        else:
                            t1 = t1.astimezone(timezone.utc)
                        span_hours = max(0.01, (t1 - t0).total_seconds() / 3600.0)
                        closing_rate_h = closing / span_hours
                    except Exception:
                        pass

                    m_gap = None
                    m_rank = None
                    if model_values:
                        m_rank = sorted(
                            [(nome, float(model_values.get(nome, 0) or 0)) for nome in participantes],
                            key=lambda x: (-x[1], x[0]),
                        )
                        if len(m_rank) >= 2:
                            m_gap = abs(m_rank[0][1] - m_rank[1][1])
                    if m_gap is not None and m_rank:
                        model_lead = m_rank[0][0].split()[0]
                        model_runner = m_rank[1][0].split()[0]
                        chips = [
                            {"label": "Diferença no fechamento", "value": f"{m_gap:.1f} p.p."},
                            {"label": f"Ritmo final ({model_runner})", "value": f"{closing_rate_h:+.2f} p.p./h"},
                        ]
                        return (
                            f"**Encerramento da votação atingido**. A leitura de virada foi congelada no fechamento.\n"
                            f"Última fotografia do modelo: **{model_lead}** à frente de **{model_runner}**. "
                            f"Agora o painel aguarda nova coleta final do Votalhada e o resultado oficial.",
                            chips,
                        )
                    return (
                        "**Encerramento da votação atingido**. O painel agora aguarda atualização final do Votalhada e resultado oficial.",
                        [],
                    )
        except Exception:
            pass

        if closing > 0.25 and gap_now > 0:
            # Friendly time-to-close language; avoid over-technical wording.
            try:
                year_ref = int(str(poll.get("data_paredao", "2026")).split("-")[0])
                t0 = parse_votalhada_hora(str(past.get("hora", "")), year=year_ref)
                t1 = parse_votalhada_hora(str(last.get("hora", "")), year=year_ref)
                if t0.tzinfo is None:
                    t0 = t0.replace(tzinfo=timezone.utc)
                else:
                    t0 = t0.astimezone(timezone.utc)
                if t1.tzinfo is None:
                    t1 = t1.replace(tzinfo=timezone.utc)
                else:
                    t1 = t1.astimezone(timezone.utc)
                span_hours = max(0.01, (t1 - t0).total_seconds() / 3600.0)
                closing_rate_h = closing / span_hours

                coleta_raw = str(poll.get("data_coleta", "")).replace("Z", "+00:00")
                coleta_dt = datetime.fromisoformat(coleta_raw) if coleta_raw else None

                close_raw = poll.get("fechamento_votacao")
                if close_raw:
                    close_dt = datetime.fromisoformat(str(close_raw).replace("Z", "+00:00"))
                else:
                    close_date = str(poll.get("data_paredao", ""))
                    close_dt = datetime.fromisoformat(f"{close_date}T22:45:00-03:00") if close_date else None

                if coleta_dt and close_dt:
                    # Standardize in UTC so countdown stays consistent across environments.
                    if coleta_dt.tzinfo is None:
                        coleta_dt = coleta_dt.replace(tzinfo=timezone.utc)
                    else:
                        coleta_dt = coleta_dt.astimezone(timezone.utc)
                    if close_dt.tzinfo is None:
                        close_dt = close_dt.replace(tzinfo=timezone.utc)
                    else:
                        close_dt = close_dt.astimezone(timezone.utc)

                    _now_utc = datetime.now(timezone.utc)
                    now_ref = _now_utc.replace(
                        minute=(_now_utc.minute // 15) * 15,
                        second=0,
                        microsecond=0,
                    )
                    effective_start = max(coleta_dt, now_ref)
                    hours_left = (close_dt - effective_start).total_seconds() / 3600.0
                    m_gap = None
                    m_rank = None
                    if model_values:
                        m_rank = sorted(
                            [(nome, float(model_values.get(nome, 0) or 0)) for nome in participantes],
                            key=lambda x: (-x[1], x[0]),
                        )
                        if len(m_rank) >= 2:
                            m_gap = abs(m_rank[0][1] - m_rank[1][1])
                    if hours_left > 0.05:

                        if m_gap is not None and m_gap >= 12.0 and m_rank:
                            model_lead = m_rank[0][0].split()[0]
                            model_runner = m_rank[1][0].split()[0]
                            eta_txt = "1 hora" if hours_left < 1.5 else f"{hours_left:.1f} horas"
                            required_rate_h = m_gap / max(hours_left, 0.01)
                            chips = [
                                {"label": "Diferença para virar", "value": f"{m_gap:.1f} p.p."},
                            ]
                            if closing_rate_h > 0.01:
                                pace_ratio = required_rate_h / closing_rate_h
                                chips.extend(
                                    [
                                        {"label": f"Ritmo atual ({model_runner})", "value": f"{closing_rate_h:.2f} p.p./h"},
                                        {"label": "Ritmo necessário", "value": f"{required_rate_h:.2f} p.p./h ({pace_ratio:.1f}x)"},
                                    ]
                                )
                                pace_txt = (
                                    f"No ritmo recente, **{model_runner}** está aproximando, mas ainda muito abaixo do necessário "
                                    f"para virar a tempo."
                                )
                            else:
                                chips.extend(
                                    [
                                        {"label": f"Ritmo atual ({model_runner})", "value": "≈ 0.00 p.p./h"},
                                        {"label": "Ritmo necessário", "value": f"{required_rate_h:.2f} p.p./h"},
                                    ]
                                )
                                pace_txt = (
                                    f"Nas últimas atualizações, **{model_runner}** praticamente não reduziu a diferença."
                                )
                            if vote_mode == "save":
                                objective_txt = (
                                    f"Para **{model_runner}** tomar a liderança e ir para o **Quarto Secreto** "
                                    f"no lugar de **{model_lead}** até o **encerramento da votação**"
                                )
                            else:
                                objective_txt = (
                                    f"Para **{model_runner}** ultrapassar **{model_lead}** e virar o mais votado para sair "
                                    f"até o **encerramento da votação**"
                                )
                            return (
                                f"**Cenário hoje está bem definido** no **Nosso Modelo**.\n"
                                f"{objective_txt} (em cerca de **{eta_txt}**), precisa tirar **{m_gap:.1f} pontos percentuais** de diferença.\n"
                                f"{pace_txt} **Veja os indicadores abaixo** para o ritmo atual vs necessário.",
                                chips,
                            )

                        required_rate_h = gap_now / hours_left
                        projected_gain = closing_rate_h * hours_left
                        if projected_gain >= gap_now:
                            swap_txt = f" A liderança já trocou {leader_swaps}x." if leader_swaps > 0 else ""
                            return (
                                f"Disputa aberta: no ritmo atual, {runner.split()[0]} pode encostar até o encerramento da votação."
                                f"{swap_txt}",
                                [],
                            )
                        else:
                            missing = max(0.0, gap_now - projected_gain)
                            swap_txt = f" A liderança já trocou {leader_swaps}x." if leader_swaps > 0 else ""
                            return (
                                f"Ritmo atual ajuda {runner.split()[0]}, mas ainda faltariam cerca de "
                                f"{missing:.1f} p.p. para virar até o encerramento da votação.{swap_txt}",
                                [],
                            )
                    else:
                        if m_gap is not None and m_rank:
                            model_lead = m_rank[0][0].split()[0]
                            model_runner = m_rank[1][0].split()[0]
                            chips = [
                                {"label": "Diferença no fechamento", "value": f"{m_gap:.1f} p.p."},
                                {"label": f"Ritmo final ({model_runner})", "value": f"{closing_rate_h:+.2f} p.p./h"},
                            ]
                            return (
                                f"**Encerramento da votação atingido**. A leitura de virada foi congelada no fechamento.\n"
                                f"Última fotografia do modelo: **{model_lead}** à frente de **{model_runner}**. "
                                f"Agora o painel aguarda nova coleta final do Votalhada e o resultado oficial.",
                                chips,
                            )
                        return (
                            "**Encerramento da votação atingido**. O painel agora aguarda atualização final do Votalhada e resultado oficial.",
                            [],
                        )
            except Exception:
                pass
            return (
                f"Ritmo: {runner.split()[0]} está reduzindo {closing:.2f} p.p. na disputa mais recente.",
                [],
            )
        if closing < -0.25:
            return f"Ritmo: {lead.split()[0]} só aumentou a vantagem nas últimas {k} atualizações.", []
        if is_empate_tecnico(gap_now):
            swap_txt = f" A liderança já trocou {leader_swaps}x." if leader_swaps > 0 else ""
            return (
                f"Disputa aberta: diferença de {gap_now:.2f} p.p. entre "
                f"{lead.split()[0]} e {runner.split()[0]}.{swap_txt}",
                [],
            )

    # Priority 2: model vs Votalhada confidence/agreement.
    if model_values:
        m_rank = sorted(
            [(nome, float(model_values.get(nome, 0) or 0)) for nome in participantes],
            key=lambda x: (-x[1], x[0]),
        )
        if m_rank and v_rank:
            m_gap = abs(m_rank[0][1] - m_rank[1][1]) if len(m_rank) >= 2 else None
            v_gap = abs(v_rank[0][1] - v_rank[1][1]) if len(v_rank) >= 2 else None
            target = "seguir no jogo" if vote_mode == "save" else "sair"
            if m_rank[0][0] == v_rank[0][0]:
                if m_gap is not None and v_gap is not None:
                    return (
                        f"Nosso Modelo e Votalhada (Ponderada) concordam em {m_rank[0][0].split()[0]} para {target}; "
                        f"confiança {m_gap:.1f} vs {v_gap:.1f} p.p.",
                        [],
                    )
                return f"Nosso Modelo e Votalhada (Ponderada) concordam em {m_rank[0][0].split()[0]} para {target}.", []
            return (
                f"Divergência: Votalhada (Ponderada) aponta {v_rank[0][0].split()[0]} ({v_rank[0][1]:.2f}%) "
                f"e Nosso Modelo aponta {m_rank[0][0].split()[0]} ({m_rank[0][1]:.2f}%).",
                [],
            )

    return None, []


def _build_memory_line(payload_nominees: list[dict], model_prediction: dict | None, vote_mode: str) -> str | None:
    if not model_prediction:
        return None
    selected = model_prediction.get("predicao_eliminado", "")
    prediction = model_prediction.get("prediction", {})
    if not selected or selected not in prediction:
        return None
    pct = prediction[selected]
    if vote_mode == "save":
        return f"Antes do resultado oficial, Nosso Modelo apontava {selected.split()[0]} com {pct:.2f}% para seguir no jogo."
    return f"Antes do resultado oficial, Nosso Modelo apontava {selected.split()[0]} com {pct:.2f}%."


def build_paredao_card_payload(
    paredao_entry: dict | None,
    poll: dict | None,
    polls_data: dict | None,
    paredao_history: dict[str, list[dict]] | None = None,
) -> dict:
    """Build the shared active/finalized paredao card payload for live and index pages."""
    if not paredao_entry:
        return {
            "state": "empty",
            "headline": "Paredão",
            "status_label": "Aguardando formação",
            "status_color": _PAREDAO_ROLE_COLORS["neutral"],
            "primary_source": "Nosso Modelo",
            "vote_mode": "eliminate",
            "collection_label": None,
            "nominees": [],
            "trust_badge": {"visible": False, "text": "", "short_text": "", "aggregate": {}},
            "fact_lines": [],
            "curiosity_line": None,
            "memory_line": None,
            "link_href": "paredao.html",
        }

    state = "finalized" if _is_finalized_paredao(paredao_entry) else "active"
    history_map = paredao_history or {}
    trust_badge = _build_trust_badge(polls_data)
    vote_mode = "save" if ((poll or {}).get("tipo_voto") == "salvar" or paredao_entry.get("paredao_falso")) else "eliminate"

    precision = calculate_precision_weights(polls_data or {"paredoes": []}) if polls_data else {"sufficient": False}
    model_prediction = predict_precision_weighted(poll, precision) if poll and precision.get("sufficient") else None
    model_values = (model_prediction or {}).get("prediction", {})

    nominees: list[dict] = []
    for participant in paredao_entry.get("participantes", []):
        name = participant.get("nome", "")
        if not name:
            continue
        route_raw = participant.get("como", "")
        route_short = normalize_route_label(route_raw)
        appearance_count = len(history_map.get(name, [])) + 1
        result = participant.get("resultado", "")
        nominee = {
            "name": name,
            "first_name": name.split()[0],
            "route_to_paredao": route_raw or route_short,
            "route_short": route_short,
            "appearance_count": appearance_count,
            "history_label": f"{appearance_count}º paredão" if appearance_count > 1 else None,
            "model_pct": model_values.get(name),
            "official_pct": participant.get("voto_total"),
            "display_pct": model_values.get(name) if state == "active" else participant.get("voto_total"),
            "is_eliminated": _result_is_selected(result),
            "use_grayscale": state == "finalized" and _result_is_selected(result),
            "result_label": result or "Em andamento",
            "color_role": "neutral",
            "accent_color": _PAREDAO_ROLE_COLORS["neutral"],
        }
        nominees.append(nominee)

    if state == "active" and model_values:
        nominees.sort(key=lambda n: (n.get("model_pct") is None, -(n.get("model_pct") or 0.0), n["name"]))
    elif state == "finalized":
        nominees.sort(key=lambda n: (-(n.get("display_pct") or 0.0), n["name"]))

    if state == "active" and model_values and nominees:
        last_idx = len(nominees) - 1
        for idx, nominee in enumerate(nominees):
            if vote_mode == "save":
                role = "safe" if idx == 0 else "danger" if idx == last_idx else "warning"
            else:
                role = "danger" if idx == 0 else "safe" if idx == last_idx else "warning"
            nominee["color_role"] = role
            nominee["accent_color"] = _PAREDAO_ROLE_COLORS[role]
    elif state == "finalized":
        for nominee in nominees:
            role = "danger" if nominee["is_eliminated"] else "safe"
            nominee["color_role"] = role
            nominee["accent_color"] = _PAREDAO_ROLE_COLORS[role]

    fact_lines = _build_active_fact_lines(nominees, vote_mode) if state == "active" else []
    curiosity_line = None
    curiosity_chips: list[dict] = []
    if state == "active":
        curiosity_line, curiosity_chips = _build_card_curiosity_line(poll, model_prediction, vote_mode)
    memory_line = _build_memory_line(nominees, model_prediction, vote_mode) if state == "finalized" else None

    numero = paredao_entry.get("numero")
    headline = f"{numero}º Paredão" if numero else "Paredão"
    if paredao_entry.get("paredao_falso"):
        headline += " Falso"
    status_label = "Em votação" if state == "active" else "Resultado oficial" if state == "finalized" else "Aguardando formação"
    status_color = "#f39c12" if state == "active" else "#e74c3c" if state == "finalized" else _PAREDAO_ROLE_COLORS["neutral"]

    return {
        "state": state,
        "headline": headline,
        "status_label": status_label,
        "status_color": status_color,
        "primary_source": "Nosso Modelo",
        "vote_mode": vote_mode,
        "collection_label": _format_collection_label((poll or {}).get("data_coleta")),
        "nominees": nominees,
        "trust_badge": trust_badge,
        "fact_lines": fact_lines,
        "curiosity_line": curiosity_line,
        "curiosity_chips": curiosity_chips,
        "memory_line": memory_line,
        "link_href": "paredao.html",
    }


def _render_curiosity_chips(chips: list[dict] | None, *, compact: bool = False) -> str:
    if not chips:
        return ""
    chip_items = "".join(
        (
            '<div class="paredao-curiosity-chip">'
            f'<div class="paredao-curiosity-chip-label">{safe_html(str(c.get("label", "")))}</div>'
            f'<div class="paredao-curiosity-chip-value">{safe_html(str(c.get("value", "")))}</div>'
            "</div>"
        )
        for c in chips[:3]
    )
    modifier = " is-compact" if compact else ""
    legend = '<div class="paredao-curiosity-legend">p.p./h = pontos percentuais por hora</div>'
    return f'<div class="paredao-curiosity-chips{modifier}">{chip_items}</div>{legend}'


def _format_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}%"


def _format_delta_pp(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.2f} p.p."


def _top2_gap(entries: list[tuple[str, float]]) -> float | None:
    if len(entries) < 2:
        return None
    return abs(entries[0][1] - entries[1][1])


def build_poll_comparison_payload(poll: dict | None, model_prediction: dict | None) -> dict | None:
    """Build payload for the merged Votalhada vs Nosso Modelo comparison card."""
    if not poll:
        return None

    participantes = poll.get("participantes", [])
    consolidado = poll.get("consolidado", {})
    if not participantes:
        return None

    vote_mode = "save" if poll.get("tipo_voto") == "salvar" else "eliminate"
    votalhada_rank = sorted(
        [(nome, float(consolidado.get(nome, 0) or 0)) for nome in participantes],
        key=lambda x: (-x[1], x[0]),
    )
    if not votalhada_rank:
        return None

    model_values = (model_prediction or {}).get("prediction", {}) if model_prediction else {}
    model_rank = sorted(
        [(nome, float(model_values.get(nome, 0) or 0)) for nome in participantes],
        key=lambda x: (-x[1], x[0]),
    ) if model_values else []

    votalhada_name, votalhada_pct = votalhada_rank[0]
    model_name, model_pct = model_rank[0] if model_rank else ("—", None)

    agreement = bool(model_rank and model_name == votalhada_name)
    winner_name = model_name if model_rank else votalhada_name
    winner_delta_pp = None
    if winner_name != "—" and winner_name in model_values:
        winner_delta_pp = float(model_values.get(winner_name, 0) or 0) - float(consolidado.get(winner_name, 0) or 0)

    rows = []
    for nome in participantes:
        v_pct = float(consolidado.get(nome, 0) or 0)
        m_pct = float(model_values.get(nome, 0) or 0) if model_rank else None
        delta = (m_pct - v_pct) if m_pct is not None else None
        rows.append(
            {
                "name": nome,
                "votalhada_pct": v_pct,
                "model_pct": m_pct,
                "delta_pp": delta,
            }
        )

    # Surface model order when available, fallback to votalhada order.
    if model_rank:
        order = {nome: idx for idx, (nome, _) in enumerate(model_rank)}
        rows.sort(key=lambda r: (order.get(r["name"], 999), r["name"]))
    else:
        order = {nome: idx for idx, (nome, _) in enumerate(votalhada_rank)}
        rows.sort(key=lambda r: (order.get(r["name"], 999), r["name"]))

    # Mirror the displayed 0.3 × 0.7 formula only for post-change polls.
    plataformas = poll.get("plataformas", {})
    mirror_3070: dict[str, float] = {}
    if has_votalhada_formula_change(poll):
        mirror_3070 = get_latest_votalhada_displayed_values(poll) or calculate_votalhada_estimate_3070(plataformas, participantes)

    mirror_rank = sorted(
        [(nome, mirror_3070.get(nome, 0)) for nome in participantes],
        key=lambda x: (-x[1], x[0]),
    ) if mirror_3070 else []
    mirror_name = mirror_rank[0][0] if mirror_rank else None
    mirror_pct = mirror_rank[0][1] if mirror_rank else None

    votalhada_gap = _top2_gap(votalhada_rank)
    model_gap = _top2_gap(model_rank) if model_rank else None
    mirror_gap = _top2_gap(mirror_rank) if mirror_rank else None

    return {
        "vote_mode": vote_mode,
        "agreement": agreement,
        "source_url": get_votalhada_source_url(poll),
        "votalhada": {
            "name": votalhada_name,
            "pct": votalhada_pct,
            "top2_gap_pp": votalhada_gap,
            "empate": is_empate_tecnico(votalhada_gap),
        },
        "mirror_3070": {
            "name": mirror_name,
            "pct": mirror_pct,
            "values": mirror_3070,
            "available": bool(mirror_3070),
            "top2_gap_pp": mirror_gap,
            "empate": is_empate_tecnico(mirror_gap),
        },
        "model": {
            "name": model_name,
            "pct": model_pct,
            "available": bool(model_rank),
            "top2_gap_pp": model_gap,
            "empate": is_empate_tecnico(model_gap),
        },
        "votalhada_top2_gap_pp": votalhada_gap,
        "model_top2_gap_pp": model_gap,
        "winner_delta_pp": winner_delta_pp,
        "rows": rows,
    }


def _votalhada_blurb(payload: dict) -> str:
    """Return the Votalhada panel description."""
    _link = f'<a href="{VOTALHADA_HOME}" target="_blank" rel="noopener">Votalhada</a>'
    mirror = payload.get("mirror_3070", {})
    if mirror.get("available"):
        return f"{_link} (Ponderada): cada plataforma pesa pelo volume de votos."
    return "Média por volume de votos das fontes."


def _mirror_3070_line(payload: dict) -> str:
    """Show the displayed 0.3 × 0.7 analysis as secondary when available."""
    mirror = payload.get("mirror_3070", {})
    if not mirror.get("available"):
        return ""
    mirror_pct = mirror.get("pct")
    mirror_name = mirror.get("name")
    legacy_name = payload.get("votalhada", {}).get("name")
    if mirror_pct is None:
        return ""
    if mirror_name and mirror_name != legacy_name:
        text = f'Votalhada 70%/30%: {safe_html(mirror_name.split()[0])} com {_format_pct(mirror_pct)}'
    else:
        text = f'Votalhada 70%/30%: {_format_pct(mirror_pct)}'
    empate_tag = ' <span class="poll-compare-empate-inline">⚖️</span>' if mirror.get("empate") else ""
    return (
        f'<div class="poll-compare-pct poll-compare-pct--secondary">'
        f'{text}{empate_tag}'
        f'</div>'
    )


def render_poll_timeseries_key(poll: dict | None, *, model_available: bool) -> str:
    """Render a compact model legend outside the Plotly figure."""
    if not poll or not poll.get("serie_temporal"):
        return ""

    primary_label = "Votalhada 70%/30%" if has_votalhada_formula_change(poll) else "Votalhada"
    items = [
        (
            "is-v7030",
            primary_label,
            "linha cheia do histórico exibido no card",
        ),
    ]
    if model_available:
        items.append(
            (
                "is-model",
                "Nosso Modelo",
                "linha pontilhada, ponderada por histórico de acerto",
            )
        )
    if poll_has_weighted_latest_overlay(poll):
        items.append(
            (
                "is-weighted",
                "Votalhada (Ponderada)",
                "quadrado vazado na última coleta",
            )
        )

    cards = "".join(
        (
            f'<div class="poll-timeseries-key-item">'
            f'<span class="poll-timeseries-swatch {klass}" aria-hidden="true"></span>'
            f'<div class="poll-timeseries-key-copy"><strong>{safe_html(title)}</strong>'
            f'<span>{safe_html(copy)}</span></div>'
            f'</div>'
        )
        for klass, title, copy in items
    )
    return (
        '<section class="poll-timeseries-key">'
        '<div class="poll-timeseries-key-title">Leituras do gráfico</div>'
        f'<div class="poll-timeseries-key-grid">{cards}</div>'
        '<div class="poll-timeseries-key-note">As cores continuam identificando cada participante.</div>'
        '</section>'
    )


def _votalhada_primary_block(
    payload: dict, v_avatar: str, v_panel: dict, mirror: dict, avatars: dict[str, str],
) -> str:
    """Render the Votalhada winner block — 70/30 as primary when available, weighted as secondary."""
    if mirror.get("available") and mirror.get("pct") is not None:
        # 70/30 is primary (big)
        m_name = mirror.get("name", "—")
        m_pct = mirror.get("pct")
        m_avatar = avatar_img(m_name, avatars, 58, border_color="#9b59b6") if m_name != "—" else v_avatar
        # Weighted is secondary (small)
        v_name = v_panel.get("name", "—")
        v_pct = v_panel.get("pct")
        secondary = (
            f'<div class="poll-compare-pct poll-compare-pct--secondary">'
            f'Modelo antigo (ponderada): {_format_pct(v_pct)}'
            f'{" ⚖️" if v_panel.get("empate") else ""}'
            f'</div>'
        )
        return (
            f'{m_avatar}<div>'
            f'<div class="poll-compare-name">{safe_html(m_name)}</div>'
            f'<div class="poll-compare-pct">com {_format_pct(m_pct)}</div>'
            f'{_empate_badge(mirror)}'
            f'{secondary}'
            f'</div>'
        )
    else:
        # No 70/30 — weighted is primary (old behavior)
        v_name = v_panel.get("name", "—")
        v_pct = v_panel.get("pct")
        return (
            f'{v_avatar}<div>'
            f'<div class="poll-compare-name">{safe_html(v_name)}</div>'
            f'<div class="poll-compare-pct">com {_format_pct(v_pct)}</div>'
            f'{_empate_badge(v_panel)}'
            f'</div>'
        )


def _empate_badge(panel: dict) -> str:
    """Return an empate técnico badge HTML if the panel's gap is below threshold."""
    if not panel.get("empate"):
        return ""
    gap = panel.get("top2_gap_pp")
    if gap is None:
        return ""
    return (
        f'<div class="poll-compare-empate">'
        f'⚖️ empate técnico (Δ {gap:.1f} p.p.)'
        f'</div>'
    )


def render_poll_comparison_card(payload: dict | None, avatars: dict[str, str]) -> str:
    """Render a merged comparison card for Votalhada vs Nosso Modelo."""
    if not payload:
        return ""

    v = payload.get("votalhada", {})
    m = payload.get("model", {})
    mirror = payload.get("mirror_3070", {})
    v_name = v.get("name", "—")
    m_name = m.get("name", "—")
    v_pct = v.get("pct")
    m_pct = m.get("pct")

    agreement = payload.get("agreement")
    agree_class = "is-agree" if agreement else "is-disagree"
    agree_label = "🤝 Concordam" if agreement else "🔀 Discordam"
    vote_mode = payload.get("vote_mode", "eliminate")
    if vote_mode == "save":
        decision_hint = "quem segue no jogo"
    else:
        decision_hint = "quem deve sair"

    model_gap = payload.get("model_top2_gap_pp")
    votalhada_gap = payload.get("votalhada_top2_gap_pp")
    if model_gap is not None and votalhada_gap is not None:
        confidence_line = (
            f"Confiança: Nosso Modelo Δtop2 {model_gap:.1f} p.p. "
            f"vs Votalhada (Ponderada) {votalhada_gap:.1f} p.p."
        )
    elif model_gap is not None:
        confidence_line = f"Confiança: Nosso Modelo Δtop2 {model_gap:.1f} p.p."
    else:
        confidence_line = "Confiança: aguardando histórico suficiente para o Nosso Modelo."

    winner_delta_pp = payload.get("winner_delta_pp")
    delta_line = f"Diferença no líder: {_format_delta_pp(winner_delta_pp)}"

    # Formula comparison line (old vs new Votalhada)
    formula_line = ""
    mirror_name = mirror.get("name")
    mirror_pct = mirror.get("pct")
    if mirror.get("available") and mirror_pct is not None and v_pct is not None:
        if mirror_name and mirror_name != v_name:
            formula_line = (
                f"No Votalhada 70%/30%, {mirror_name.split()[0]} lidera com {mirror_pct:.2f}% "
                f"(vs {v_name.split()[0]} {v_pct:.2f}% no Votalhada ponderado)."
            )
        else:
            diff = mirror_pct - v_pct
            if abs(diff) >= 0.1:
                formula_line = (
                    f"Votalhada 70%/30%: {mirror_pct:.2f}% vs Votalhada ponderado: {v_pct:.2f}% "
                    f"({diff:+.1f} p.p.)."
                )

    if agreement:
        lead_line = f"Ambos apontam {safe_html(m_name.split()[0])} ao comparar {decision_hint}."
    else:
        lead_line = (
            f"Votalhada (Ponderada) aponta {safe_html(v_name.split()[0])} e "
            f"Nosso Modelo aponta {safe_html(m_name.split()[0])} para {decision_hint}."
        )

    v_avatar = avatar_img(v_name, avatars, 58, border_color="#9b59b6") if v_name != "—" else ""
    m_avatar = avatar_img(m_name, avatars, 58, border_color="#00bc8c") if m_name != "—" else ""
    votalhada_line = (
        '<a class="poll-compare-trust is-votalhada" href="paredoes.html#precisão-das-enquetes-votalhada">'
        'Ver precisão histórica →</a>'
    )
    trust_line = (
        '<a class="poll-compare-trust" href="paredoes.html#nosso-modelo-back-test">'
        'Ver teste retrospectivo →</a>'
        if m.get("available")
        else '<div class="poll-compare-trust">Aguardando histórico suficiente.</div>'
    )

    rows_html = []
    for row in payload.get("rows", []):
        nome = row.get("name", "")
        avatar = avatar_img(nome, avatars, 26, border_color="#666")
        delta_pp = row.get("delta_pp")
        if delta_pp is None:
            delta_class = "is-close"
        elif abs(delta_pp) <= 1.0:
            delta_class = "is-close"
        elif delta_pp > 1.0:
            delta_class = "is-positive"
        else:
            delta_class = "is-negative"

        if row.get("model_pct") is None:
            model_cell = '<span class="poll-compare-val is-m">M —</span>'
        else:
            model_cell = f'<span class="poll-compare-val is-m">M {row.get("model_pct", 0):.2f}%</span>'
        rows_html.append(
            '<div class="poll-compare-chip">'
            f'<div class="poll-compare-chip-name">{avatar}<span>{safe_html(nome.split()[0])}</span></div>'
            f'<div class="poll-compare-chip-metrics">'
            f'<span class="poll-compare-val is-v">V {row.get("votalhada_pct", 0):.2f}%</span>'
            f"{model_cell}"
            f'<span class="poll-compare-val is-delta {delta_class}">Δ {_format_delta_pp(delta_pp)}</span>'
            f'</div>'
            '</div>'
        )
    rows_compact = "".join(rows_html)

    return (
        f'<section class="poll-compare-card {agree_class}">'
        f'<div class="poll-compare-bridge">'
        f'<div class="poll-compare-bridge-pill">{agree_label}</div>'
        f'<div class="poll-compare-bridge-target">{lead_line}</div>'
        f'<div class="poll-compare-bridge-metric">{safe_html(confidence_line)}</div>'
        f'<div class="poll-compare-bridge-metric">{safe_html(delta_line)}</div>'
        f'{f"""<div class="poll-compare-bridge-metric">{safe_html(formula_line)}</div>""" if formula_line else ""}'
        f'</div>'
        f'<div class="poll-compare-panels">'
        f'<div class="poll-compare-side is-model">'
        f'<div class="poll-compare-brand">📊 NOSSO MODELO</div>'
        f'<div class="poll-compare-blurb">Mesmas fontes, ponderadas por histórico de acerto.</div>'
        f'{trust_line}'
        f'<div class="poll-compare-winner">{m_avatar}<div>'
        f'<div class="poll-compare-name">{safe_html(m_name)}</div>'
        f'<div class="poll-compare-pct">com {_format_pct(m_pct)}</div>'
        f'{_empate_badge(m)}'
        f'</div></div></div>'
        f'<div class="poll-compare-side is-votalhada">'
        f'<div class="poll-compare-brand">{render_votalhada_logo(href=payload.get("source_url", VOTALHADA_HOME))}</div>'
        f'<div class="poll-compare-blurb">{_votalhada_blurb(payload)}</div>'
        f'{votalhada_line}'
        f'<div class="poll-compare-winner">{_votalhada_primary_block(payload, v_avatar, v, mirror, avatars)}'
        f'</div></div>'
        f'</div>'
        f'<div class="poll-compare-strip">{rows_compact}</div>'
        f'</section>'
    )


def _render_paredao_nominee_card(nominee: dict, avatars: dict[str, str], *, compact: bool = False) -> str:
    modifier = "paredao-index-nominee" if compact else "paredao-live-nominee"
    avatar_size = 52 if compact else 72
    pct = nominee.get("display_pct")
    pct_html = (
        f'<div class="paredao-card-pct">{pct:.2f}%</div>'
        if pct is not None else '<div class="paredao-card-pct paredao-card-pct--empty">—</div>'
    )
    width = max(0.0, min(100.0, pct if pct is not None else 0.0))
    bar_html = (
        f'<div class="paredao-card-bar-track"><div class="paredao-card-bar-fill" '
        f'style="width:{width:.2f}%; background:{nominee["accent_color"]};"></div></div>'
        if pct is not None else ""
    )
    appearance_count = int(nominee.get("appearance_count", 1) or 1)
    appearance_badge_html = ""
    if appearance_count > 1:
        appearance_badge_html = (
            f'<span class="paredao-card-appearance-badge" '
            f'title="{appearance_count}º paredão">{appearance_count}x</span>'
        )
    avatar = avatar_img(
        nominee["name"],
        avatars,
        avatar_size,
        border_color=nominee["accent_color"],
        grayscale=nominee.get("use_grayscale", False),
    )
    return (
        f'<div class="{modifier} is-{nominee["color_role"]}">'
        f'{appearance_badge_html}'
        f'<div class="paredao-card-avatar">{avatar}</div>'
        f'<div class="paredao-card-main">'
        f'<div class="paredao-card-name">{safe_html(nominee["first_name"])}</div>'
        f'{pct_html}'
        f'{bar_html}'
        f'<div class="paredao-card-route">{safe_html(nominee["route_short"])}</div>'
        f'</div>'
        f'</div>'
    )


def _render_trust_badge(badge: dict, *, compact: bool = False) -> str:
    if not badge.get("visible"):
        return ""
    text = badge.get("short_text") if compact else badge.get("text")
    href = badge.get("href")
    if href:
        return (
            f'<a class="paredao-card-trust" href="{safe_html(href)}" '
            f'title="Ver explicação do teste retrospectivo">📊 {safe_html(text)}</a>'
        )
    return f'<div class="paredao-card-trust">📊 {safe_html(text)}</div>'


def render_paredao_live_card(payload: dict | None, avatars: dict[str, str]) -> str:
    """Render the full live-page paredao card."""
    if not payload:
        return ""
    if payload.get("state") == "empty":
        return (
            '<div class="paredao-live-card is-empty">'
            '<div class="paredao-live-card-header">'
            '<div><div class="paredao-card-kicker">🗳️ Paredão</div>'
            '<div class="paredao-live-title">Aguardando formação</div></div>'
            '</div></div>'
        )

    nominees_html = "".join(_render_paredao_nominee_card(n, avatars) for n in payload.get("nominees", []))
    facts = payload.get("fact_lines", [])
    facts_html = "".join(f"<li>{_rich_text(fact)}</li>" for fact in facts)
    curiosity_line = payload.get("curiosity_line")
    curiosity_chips = payload.get("curiosity_chips") or []
    curiosity_html = (
        f'<div class="paredao-card-curiosity">💡 {_rich_text(curiosity_line)}</div>'
        if curiosity_line else ""
    )
    curiosity_chips_html = _render_curiosity_chips(curiosity_chips)
    memory_line = payload.get("memory_line")
    collection = payload.get("collection_label")
    collection_html = f'<div class="paredao-card-collection">{safe_html(collection)}</div>' if collection else ""
    facts_list_html = f'<ul class="paredao-card-facts">{facts_html}</ul>' if facts else ""
    memory_html = f'<div class="paredao-card-memory">{_rich_text(memory_line)}</div>' if memory_line else ""

    return (
        f'<div class="paredao-live-card is-{payload.get("state")}">'
        f'<div class="paredao-live-card-header">'
        f'<div class="paredao-live-card-title-block">'
        f'<div class="paredao-card-kicker">📊 {safe_html(payload.get("primary_source", "Nosso Modelo"))}</div>'
        f'<div class="paredao-live-title-row">'
        f'<h3 class="paredao-live-title">{safe_html(payload.get("headline", "Paredão"))}</h3>'
        f'<span class="paredao-card-status">{safe_html(payload.get("status_label", ""))}</span>'
        f'</div>'
        f'{collection_html}'
        f'</div>'
        f'{_render_trust_badge(payload.get("trust_badge", {}))}'
        f'</div>'
        f'<div class="paredao-live-grid">{nominees_html}</div>'
        f'{curiosity_html}'
        f'{curiosity_chips_html}'
        f'{facts_list_html}'
        f'{memory_html}'
        f'</div>'
    )


def render_paredao_index_card(payload: dict | None, avatars: dict[str, str]) -> str:
    """Render the compact homepage mirror for the current/latest paredao."""
    if not payload or payload.get("state") == "empty":
        return '<div class="paredao-index-card is-empty"><div class="paredao-index-empty">Nenhum paredão ativo no momento.</div></div>'

    nominees_html = "".join(_render_paredao_nominee_card(n, avatars, compact=True) for n in payload.get("nominees", []))
    curiosity_line = payload.get("curiosity_line")
    curiosity_chips = payload.get("curiosity_chips") or []
    fact = payload.get("memory_line") or (payload.get("fact_lines") or [None])[0]
    trust_badge = payload.get("trust_badge", {})
    notes: list[str] = []
    if trust_badge.get("visible"):
        notes.append(
            f'<a class="paredao-index-note is-link" href="{safe_html(trust_badge.get("href", "paredoes.html#nosso-modelo-back-test"))}">'
            f'📊 {safe_html(trust_badge.get("text", ""))}'
            f'</a>'
        )
    if curiosity_line:
        notes.append(f'<div class="paredao-index-curiosity">💡 {_rich_text(curiosity_line)}</div>')
        notes.append(_render_curiosity_chips(curiosity_chips, compact=True))
    elif fact:
        notes.append(f'<div class="paredao-index-note">{_rich_text(fact)}</div>')
    notes_html = f'<div class="paredao-index-notes">{"".join(notes)}</div>' if notes else ""
    return (
        f'<div class="paredao-index-card is-{payload.get("state")}">'
        f'<div class="paredao-index-grid">{nominees_html}</div>'
        f'{notes_html}'
        f'</div>'
    )


def render_nominee_cards_em_andamento(
    participantes: list[dict],
    esperado_indicados: int,
    avatars: dict[str, str],
    member_of: dict[str, str],
    *,
    poll_predictions: dict[str, float] | None = None,
    is_save_poll: bool = False,
    paredao_history: dict[str, list[dict]] | None = None,
    is_paredao_falso: bool = False,
) -> str:
    """Render nominee cards for an in-progress paredão.

    Args:
        poll_predictions: {name: pct} from our model (or consolidado).
        is_save_poll: True if vote-to-save (Paredão Falso).
        paredao_history: {name: [past entries]} for repeat nominees.
        is_paredao_falso: True if current paredão is fake.
    """
    lines: list[str] = []
    lines.append('<div style="display:flex; flex-wrap:wrap; justify-content:center; gap:1rem; margin:1.5rem 0;">')

    # Sort by prediction if available (highest first)
    sorted_parts = list(participantes)
    if poll_predictions:
        sorted_parts.sort(key=lambda p: poll_predictions.get(p['nome'], 0), reverse=True)

    for p in sorted_parts:
        nome = p['nome']
        avatar_url = avatars.get(nome, '')
        como_indicado = p.get('como', '')
        is_auto = como_indicado == 'API'
        esc_nome = safe_html(nome)
        first_name = nome.split()[0]

        # Determine card accent color from prediction
        pct = poll_predictions.get(nome, 0) if poll_predictions else 0
        if poll_predictions and len(poll_predictions) >= 2:
            max_pct = max(poll_predictions.values())
            min_pct = min(poll_predictions.values())
            if pct == max_pct:
                accent = '#2ecc71' if is_save_poll else '#e74c3c'
            elif pct == min_pct:
                accent = '#e74c3c' if is_save_poll else '#2ecc71'
            else:
                accent = '#f39c12'
        else:
            accent = '#f39c12'

        border_style = f"2px dashed {accent}" if is_auto else f"2px solid {accent}"
        opacity = "0.85" if is_auto else "1"

        # History count
        past = (paredao_history or {}).get(nome, [])
        n_past = len(past)
        hist_badge = ''
        if n_past > 0:
            hist_badge = f'<div class="fs-xs" style="position:absolute; top:-6px; right:-6px; background:#e74c3c; color:#fff; width:22px; height:22px; border-radius:50%; font-weight:bold; display:flex; align-items:center; justify-content:center; border:2px solid #1a1a2e;">{n_past + 1}x</div>'

        lines.append(f'<div style="border:{border_style}; border-radius:14px; padding:0.8rem; background:rgba(255,255,255,0.03); opacity:{opacity}; width:140px; text-align:center; position:relative;">')
        lines.append(hist_badge)
        if avatar_url:
            lines.append(f'<img src="{avatar_url}" alt="{esc_nome}" style="width:80px; height:80px; border-radius:50%; object-fit:cover; border:3px solid {accent}; margin-bottom:0.4rem;">')
        lines.append(f'<div class="fs-base" style="font-weight:bold; color:#fff; margin-bottom:0.2rem;">{first_name}</div>')

        # Prediction percentage + bar
        if poll_predictions and pct > 0:
            bar_color = accent
            lines.append(f'<div class="fs-2xl" style="font-weight:bold; color:{accent}; margin:0.2rem 0;">{pct:.2f}%</div>')
            lines.append(f'<div style="background:rgba(255,255,255,0.1); border-radius:4px; height:6px; width:100%; margin:0.2rem 0;">')
            lines.append(f'<div style="background:{bar_color}; height:100%; border-radius:4px; width:{min(pct, 100):.0f}%;"></div>')
            lines.append(f'</div>')

        # How they got nominated
        if como_indicado and not is_auto:
            lines.append(f'<div class="fs-xs" style="color:#aaa; margin-top:0.3rem;">via {safe_html(como_indicado)}</div>')
        elif is_auto:
            lines.append(f'<div class="fs-xs" style="color:#f39c12; margin-top:0.3rem;">⏳ aguardando</div>')

        lines.append('</div>')

    # Placeholder cards for missing nominees
    n_indicados = len(participantes)
    for _ in range(esperado_indicados - n_indicados):
        lines.append(f'<div style="border:2px dashed #444; border-radius:14px; padding:0.8rem; background:rgba(255,255,255,0.02); width:140px; text-align:center;">')
        lines.append(f'<div class="fs-4xl" style="width:80px; height:80px; border-radius:50%; background:#333; margin:0 auto 0.4rem auto; display:flex; align-items:center; justify-content:center; color:#555;">?</div>')
        lines.append(f'<div class="fs-base" style="color:#666;">Aguardando...</div>')
        lines.append('</div>')

    lines.append('</div>')
    return '\n'.join(lines)


def render_nominee_cards_finalized(
    df_rows: list[dict],
    avatars: dict[str, str],
    member_of: dict[str, str],
    *,
    is_paredao_falso: bool = False,
    paredao_history: dict[str, list[dict]] | None = None,
) -> str:
    """Render result cards for a finalized paredão.

    Each row dict must have keys: nome, grupo, resultado, voto_total.
    """
    lines: list[str] = []
    lines.append('<div style="display:flex; flex-wrap:wrap; justify-content:center; gap:1rem; margin:1.5rem 0 2rem 0;">')
    for row in df_rows:
        nome = row['nome']
        resultado = row.get('resultado', '')
        voto_total = row.get('voto_total', 0)
        avatar_url = avatars.get(nome, '')
        esc_nome = safe_html(nome)
        first_name = nome.split()[0]

        if resultado == 'ELIMINADA':
            border_color = '#E6194B'
            badge_bg = '#E6194B'
            if is_paredao_falso:
                badge_text = '🔮 QUARTO SECRETO'
            else:
                suf = 'A' if genero(nome) == 'f' else 'O'
                badge_text = f'ELIMINAD{suf}'
            img_filter = 'grayscale(100%)'
        else:
            border_color = '#3CB44B'
            badge_bg = '#3CB44B'
            suf = 'A' if genero(nome) == 'f' else 'O'
            badge_text = f'SALV{suf}'
            img_filter = 'none'

        # History count
        past = (paredao_history or {}).get(nome, [])
        n_past = len(past)
        hist_badge = ''
        if n_past > 0:
            hist_badge = f'<div class="fs-xs" style="position:absolute; top:-6px; right:-6px; background:#e74c3c; color:#fff; width:22px; height:22px; border-radius:50%; font-weight:bold; display:flex; align-items:center; justify-content:center; border:2px solid #1a1a2e;">{n_past + 1}x</div>'

        lines.append(f'<div style="width:150px; border:3px solid {border_color}; border-radius:14px; padding:0.8rem; background:rgba(255,255,255,0.03); text-align:center; position:relative;">')
        lines.append(hist_badge)
        if avatar_url:
            lines.append(f'<img src="{avatar_url}" alt="{esc_nome}" style="width:80px; height:80px; border-radius:50%; object-fit:cover; border:3px solid {border_color}; margin-bottom:0.4rem; filter:{img_filter};">')
        lines.append(f'<div class="fs-base" style="font-weight:bold; color:#fff; margin-bottom:0.3rem;">{first_name}</div>')
        lines.append(f'<span class="fs-2xs" style="display:inline-block; padding:0.2rem 0.5rem; background:{badge_bg}; color:#fff; border-radius:8px; font-weight:bold;">{badge_text}</span>')
        lines.append(f'<div class="fs-2xl" style="color:#fff; font-weight:bold; margin-top:0.3rem;">{voto_total:.2f}%</div>')
        lines.append('</div>')
    lines.append('</div>')
    return '\n'.join(lines)


def render_voting_blocs(
    votos_casa: dict[str, str],
    avatars: dict[str, str],
    member_of: dict[str, str],
) -> str:
    """Render side-by-side voting bloc boxes with narrative header."""
    contagem = Counter(votos_casa.values())
    ranking = contagem.most_common()
    if len(ranking) < 2:
        return ''

    lines: list[str] = []
    blocs = []
    for alvo, n_votos in ranking:
        votantes = sorted([v for v, a in votos_casa.items() if a == alvo])
        blocs.append({'alvo': alvo, 'n': n_votos, 'votantes': votantes})

    if len(ranking) == 2:
        lines.append(f'A casa se dividiu em dois blocos claros: **{blocs[0]["n"]}** votaram em **{safe_html(blocs[0]["alvo"])}**, **{blocs[1]["n"]}** votaram em **{safe_html(blocs[1]["alvo"])}**.\n')
    else:
        parts_bloc = [f'{b["n"]} em {safe_html(b["alvo"])}' for b in blocs]
        lines.append(f'Divisão da casa: {", ".join(parts_bloc)}.\n')

    lines.append('<div style="display:flex; flex-wrap:wrap; gap:1.5rem; justify-content:center; margin:1rem 0;">')
    for bloc in blocs:
        alvo = bloc['alvo']
        n_bl = bloc['n']
        votantes = bloc['votantes']
        cor_alvo = GROUP_COLORS.get(member_of.get(alvo, '?'), '#888')
        lines.append(f'<div style="background:linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02)); border:2px solid {cor_alvo}; border-radius:12px; padding:1rem; min-width:200px; flex:1; max-width:400px;">')
        lines.append(f'<div class="tc" style="margin-bottom:0.8rem;">')
        lines.append(f'{avatar_img(alvo, avatars, 48)}')
        lines.append(f'<div class="fs-lg" style="color:#fff; font-weight:bold; margin-top:0.3rem;">{safe_html(alvo)}</div>')
        lines.append(f'<div class="fs-2xl" style="color:{cor_alvo}; font-weight:bold;">{n_bl} votos</div>')
        lines.append(f'</div>')
        lines.append(f'<div style="display:flex; flex-wrap:wrap; gap:0.4rem; justify-content:center;">')
        for vot in votantes:
            vot_grupo = member_of.get(vot, '?')
            vot_cor = GROUP_COLORS.get(vot_grupo, '#888')
            lines.append(f'<div class="tc">')
            av_url = avatars.get(vot, '')
            esc_vot = safe_html(vot)
            if av_url:
                lines.append(f'<img src="{av_url}" style="width:36px; height:36px; border-radius:50%; border:2px solid {vot_cor};" alt="{esc_vot}" title="{esc_vot}">')
            else:
                lines.append(f'<div class="fs-xs" style="width:36px; height:36px; border-radius:50%; background:{vot_cor}; display:flex; align-items:center; justify-content:center; color:#fff;">{esc_vot[:2]}</div>')
            lines.append(f'<div class="fs-2xs" style="color:#aaa; max-width:50px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">{safe_html(vot.split()[0])}</div>')
            lines.append(f'</div>')
        lines.append(f'</div>')
        lines.append(f'</div>')
    lines.append('</div>')
    return '\n'.join(lines)


def _spotlight_reaction_emoji(label: str | None) -> str:
    if not label:
        return "—"
    return REACTION_EMOJI.get(label, label)


def _format_short_date(date_str: str | None) -> str:
    if not date_str:
        return "—"
    return f"{date_str[8:10]}/{date_str[5:7]}"


def _format_pct_number(value: float | int | None) -> str:
    if value is None:
        return "0,0"
    return f"{float(value):.2f}".replace(".", ",")


def _next_day_short(date_str: str | None) -> str:
    if not date_str:
        return "—"
    return (date.fromisoformat(date_str) + timedelta(days=1)).strftime("%d/%m")


def _spotlight_summary_rows(entries: list[tuple[str, int, str | None]]) -> str:
    if not entries:
        return '<div class="paredao-spotlight-note">Sem registro direto neste recorte.</div>'

    lines = ['<div class="paredao-spotlight-summary-list">']
    for event_type, count, target in entries:
        emoji, label = _SPOTLIGHT_SUMMARY_META.get(event_type, ("•", event_type.replace("_", " ").title()))
        target_suffix = f' em {safe_html(target)}' if target else ""
        lines.append(
            '<div class="paredao-spotlight-summary-item">'
            f'<span>{safe_html(emoji)} <strong>{count}x</strong> {safe_html(label)}{target_suffix}</span>'
            '</div>'
        )
    lines.append('</div>')
    return "\n".join(lines)


def _render_summary_card(title: str, rows: list[tuple[str, int, str | None]], note: str, tone_class: str, extra_note: str = "") -> str:
    lines = [f'<div class="paredao-spotlight-section-card {tone_class}">']
    lines.append(f'<h6 class="paredao-spotlight-subtitle">{safe_html(title)}</h6>')
    lines.append(_spotlight_summary_rows(rows))
    lines.append(f'<div class="paredao-spotlight-note">{note}</div>')
    if extra_note:
        lines.append(f'<div class="paredao-spotlight-note">{extra_note}</div>')
    lines.append('</div>')
    return "\n".join(lines)


def _build_power_rows(decisions: list[dict], actor: str) -> tuple[list[tuple[str, int, str | None]], bool]:
    counts: Counter[tuple[str, str]] = Counter()
    has_consensus_indication = False
    for row in decisions:
        if row.get("actor") != actor:
            continue
        relevant_targets = [target for target in row.get("targets", []) if target in ("Milena", "Ana Paula Renault")]
        for target in relevant_targets:
            counts[(row.get("event_type", ""), target)] += 1
        if (
            row.get("event_type") == "indicacao"
            and "Milena" in relevant_targets
            and any("consenso" in detail.lower() for detail in row.get("details", []))
        ):
            has_consensus_indication = True

    return (
        sorted(
            [(event_type, count, target) for (event_type, target), count in counts.items()],
            key=lambda item: (0 if item[2] == "Milena" else 1, _SPOTLIGHT_EVENT_ORDER.get(item[0], 99), item[2] or ""),
        ),
        has_consensus_indication,
    )


def _build_timeline_rows(items: list[dict], actor: str, target: str | None = None) -> list[tuple[str, int, str | None]]:
    counts: Counter[tuple[str, str | None]] = Counter()
    for item in items:
        if item.get("actor") != actor:
            continue
        if target and item.get("target") != target:
            continue
        counts[(item.get("event_type", ""), target)] += 1
    return sorted(
        [(event_type, count, row_target) for (event_type, row_target), count in counts.items()],
        key=lambda item: (_SPOTLIGHT_EVENT_ORDER.get(item[0], 99), item[2] or ""),
    )


def _pick_secret_streak(side: dict) -> dict:
    current = side.get("current_streak") or {}
    if current.get("length", 0) >= 5:
        return current
    return side.get("longest_streak") or current


def _render_secret_pair_card(actor: str, pair_data: dict) -> str:
    to_target = pair_data.get("to_target", {})
    from_target = pair_data.get("from_target", {})
    actor_first = actor.split()[0]
    to_streak = _pick_secret_streak(to_target)
    from_streak = _pick_secret_streak(from_target)
    lines = ['<div class="paredao-spotlight-card paredao-spotlight-card-secret">']
    lines.append(f'<div class="paredao-spotlight-card-title">{safe_html(actor)} x Milena</div>')
    if not to_target.get("last_mutual_positive_date"):
        lines.append(
            f'<div class="paredao-spotlight-note">{safe_html(actor_first)} até passou '
            f'<strong>{to_target.get("heart_days", 0)} dias</strong> mandando ❤️. '
            f'<strong>Nunca teve um dia de emojis positivos dos dois lados</strong>.</div>'
        )
        lines.append(
            f'<div class="paredao-spotlight-note">O último emoji positivo de {safe_html(actor_first)} para Milena foi em '
            f'<strong>{_format_short_date(to_target.get("last_positive_date"))}</strong>; '
            f'o último dela para {safe_html(actor_first)} foi em '
            f'<strong>{_format_short_date(from_target.get("last_positive_date"))}</strong>.</div>'
        )
    else:
        lines.append(
            f'<div class="paredao-spotlight-note">{safe_html(actor_first)} e Milena tiveram '
            f'<strong>{to_target.get("mutual_heart_days", 0)} dias</strong> de ❤️ mútuo no começo.</div>'
        )
        lines.append(
            f'<div class="paredao-spotlight-note">A última troca positiva dos dois foi em '
            f'<strong>{_format_short_date(to_target.get("last_mutual_positive_date"))}</strong>. '
            f'Desde <strong>{_next_day_short(to_target.get("last_mutual_positive_date"))}</strong>, '
            f'pelo menos um dos dois sai do verde em todos os dias do recorte.</div>'
        )
    lines.append(
        f'<div class="paredao-spotlight-note">No trecho mais duro, {safe_html(actor_first)} ficou '
        f'<strong>{to_streak.get("length", 0)} dias</strong> seguidos em {safe_html(to_streak.get("emoji", "—"))}; '
        f'Milena passou <strong>{from_streak.get("length", 0)} dias</strong> em '
        f'{safe_html(from_streak.get("emoji", "—"))} contra {safe_html(actor_first)}.</div>'
    )
    lines.append('</div>')
    return "\n".join(lines)


def render_featured_story(story: dict | None) -> str:
    """Render the week-8 spotlight shared by paredao.qmd and paredoes.qmd."""
    if not story:
        return ""

    target = story.get("target", "Milena")
    actors = story.get("actors", [])
    counts = story.get("summary_counts", {})
    formation_day_date = story.get("formation_day_date", "")
    formation_story = story.get("formation_day_reactions", {})
    timeline = story.get("timeline", [])
    prior_plate = story.get("past_leader_indications", [])
    power_usage = story.get("power_usage", {})
    secret = story.get("secret_queridometro", {})
    total_hits = counts.get("leaders_to_target_total", 0)
    total_back = counts.get("target_back_total", 0)

    attack_timeline = [item for item in timeline if item.get("actor") != target and item.get("event_type") not in _SPOTLIGHT_POWER_TYPES]
    response_timeline = [item for item in timeline if item.get("actor") == target]

    lines = ['<div class="paredao-spotlight">']
    lines.append('<div class="paredao-spotlight-kicker">Recorte especial da semana</div>')
    lines.append(f'<h4 class="paredao-spotlight-title">{safe_html(story.get("title", "Milena no alvo dos líderes"))}</h4>')
    lines.append(
        f'<p class="paredao-spotlight-thesis">{safe_html(story.get("thesis", ""))}</p>'
    )
    lines.append('<div class="paredao-spotlight-grid">')

    for actor in actors:
        reactions = formation_story.get(actor, {})
        to_target = _spotlight_reaction_emoji(reactions.get("to_target"))
        from_target = _spotlight_reaction_emoji(reactions.get("from_target"))
        hits = counts.get(f"{actor}->{target}", 0)
        back_hits = counts.get(f"{target}->{actor}", 0)
        lines.append('<div class="paredao-spotlight-card">')
        lines.append(f'<div class="paredao-spotlight-card-title">{safe_html(actor)} → {safe_html(target)}</div>')
        lines.append(f'<div class="paredao-spotlight-metric">{hits}</div>')
        lines.append(
            f'<div class="paredao-spotlight-note">{safe_html(actor)} já mirou {safe_html(target)} em {hits} momento(s) diretos; '
            f'ela devolveu {back_hits} vez(es).</div>'
        )
        _pill_date = f" ({safe_html(formation_day_date[5:])})" if formation_day_date else ""
        lines.append(
            '<div class="paredao-spotlight-pill">'
            f'<span class="paredao-spotlight-pill-label">Queridômetro no domingo da formação{_pill_date}</span>'
            f'<span class="paredao-spotlight-pill-value">'
            f'{safe_html(actor.split()[0])} {safe_html(to_target)} {safe_html(target)} · '
            f'{safe_html(target)} {safe_html(from_target)} {safe_html(actor.split()[0])}'
            '</span>'
            '</div>'
        )
        lines.append('</div>')

    lines.append('<div class="paredao-spotlight-card paredao-spotlight-card-accent">')
    lines.append('<div class="paredao-spotlight-card-title">Assimetria do recorte</div>')
    lines.append(f'<div class="paredao-spotlight-metric">{total_hits} x {total_back}</div>')
    lines.append(
        f'<div class="paredao-spotlight-note">Nos eventos diretos entre os três, Alberto e Jonas somam {total_hits} ataques contra '
        f'{safe_html(target)}. Ela soma {total_back} devoluções.</div>'
    )
    lines.append('</div>')
    lines.append('</div>')

    if power_usage:
        combined_power = power_usage.get("combined", {})
        by_actor_power = power_usage.get("by_actor", {})
        proxy_evidence = power_usage.get("proxy_evidence", [])
        decisions = power_usage.get("decisions", [])
        lines.append('<div class="paredao-spotlight-section">')
        lines.append('<h5 class="paredao-spotlight-section-title">Quando o poder caiu na mão deles</h5>')
        lines.append('<div class="paredao-spotlight-grid">')
        lines.append('<div class="paredao-spotlight-card">')
        lines.append('<div class="paredao-spotlight-card-title">Milena como alvo direto</div>')
        lines.append(f'<div class="paredao-spotlight-metric">{combined_power.get("toward_target_pct", 0):.2f}%</div>')
        lines.append(
            f'<div class="paredao-spotlight-note">{combined_power.get("toward_target", 0)} de '
            f'{combined_power.get("total", 0)} decisões negativas de Alberto e Jonas miraram diretamente em Milena.</div>'
        )
        lines.append('</div>')
        lines.append('<div class="paredao-spotlight-card">')
        lines.append('<div class="paredao-spotlight-card-title">Milena ou Ana Paula</div>')
        lines.append(f'<div class="paredao-spotlight-metric">{combined_power.get("toward_target_or_ally_pct", 0):.2f}%</div>')
        lines.append(
            f'<div class="paredao-spotlight-note">{combined_power.get("toward_target_or_ally", 0)} de '
            f'{combined_power.get("total", 0)} decisões negativas foram contra Milena ou Ana Paula, o eixo mais próximo dela no jogo.</div>'
        )
        lines.append('</div>')
        lines.append('</div>')
        for actor in actors:
            actor_power = by_actor_power.get(actor, {})
            rows, has_consensus = _build_power_rows(decisions, actor)
            extra_note = ""
            if has_consensus:
                extra_note = (
                    f'Inclui a indicação em consenso da liderança dupla com '
                    f'{"Jonas" if actor == "Alberto Cowboy" else "Alberto"} na semana 8.'
                )
            if actor == "Jonas Sulzbach" and any(
                entry.get("actor") == actor and "combo" in entry.get("detail", "").lower()
                for entry in proxy_evidence
            ):
                extra_note = (
                    f'{extra_note} ' if extra_note else ''
                ) + 'Com Ana Paula, Jonas ainda verbalizou o proxy: <strong>“combo, em dobro”</strong>.'
            lines.append(
                _render_summary_card(
                    f'👑 {actor.split()[0]}',
                    rows,
                    (
                        f'Direto em Milena ou Ana Paula: <strong>{actor_power.get("toward_target_or_ally", 0)} de '
                        f'{actor_power.get("total", 0)}</strong> decisões negativas '
                        f'(<strong>{_format_pct_number(actor_power.get("toward_target_or_ally_pct", 0))}%</strong>).'
                    ),
                    "tone-power",
                    extra_note,
                )
            )
        lines.append('</div>')

    lines.append('<div class="paredao-spotlight-section">')
    lines.append('<h5 class="paredao-spotlight-section-title">🎯 No Sincerão e nos ataques diretos</h5>')
    lines.append('<div class="paredao-spotlight-grid">')
    for actor in actors:
        actor_rows = _build_timeline_rows(attack_timeline, actor, target)
        actor_total = sum(count for _, count, _ in actor_rows)
        lines.append(
            _render_summary_card(
                actor.split()[0],
                actor_rows,
                f'Fora do poder, {safe_html(actor.split()[0])} ainda somou <strong>{actor_total}</strong> ataques públicos diretos contra Milena.',
                "tone-attack",
            )
        )
    lines.append('</div>')
    lines.append('</div>')

    lines.append('<div class="paredao-spotlight-section">')
    lines.append('<h5 class="paredao-spotlight-section-title">↩️ Quando Milena devolveu</h5>')
    lines.append('<div class="paredao-spotlight-grid">')
    for actor in actors:
        response_rows = _build_timeline_rows(response_timeline, target, actor)
        response_total = sum(count for _, count, _ in response_rows)
        lines.append(
            _render_summary_card(
                f'Milena → {actor.split()[0]}',
                response_rows,
                f'Milena respondeu publicamente {response_total} vez(es) a {safe_html(actor.split()[0])}.',
                "tone-response",
            )
        )
    lines.append('</div>')
    lines.append('</div>')

    if secret:
        lines.append('<div class="paredao-spotlight-section">')
        lines.append('<h5 class="paredao-spotlight-section-title">🔒 Queridômetro secreto</h5>')
        lines.append(f'<p class="paredao-spotlight-note">{safe_html(secret.get("private_signal_note", ""))}</p>')
        lines.append('<div class="paredao-spotlight-grid">')
        for actor in actors:
            pair_data = secret.get("pairs", {}).get(actor)
            if pair_data:
                lines.append(_render_secret_pair_card(actor, pair_data))
        lines.append('</div>')
        lines.append('</div>')

    if prior_plate:
        lines.append('<div class="paredao-spotlight-section">')
        lines.append('<h5 class="paredao-spotlight-section-title">Voto Único e resposta do público</h5>')
        lines.append('<div class="paredao-spotlight-grid">')
        for item in prior_plate:
            leaders_label = " + ".join(item.get("leaders", []))
            milena_vote = item.get("milena_voto_unico") or 0
            eliminated_vote = item.get("eliminated_voto_unico") or 0
            lines.append('<div class="paredao-spotlight-card">')
            lines.append(f'<div class="paredao-spotlight-card-title">{item.get("paredao_num")}º Paredão · {safe_html(leaders_label)}</div>')
            lines.append(
                f'<div class="paredao-spotlight-proof">Milena ficou com {milena_vote:.2f}% no Voto Único; '
                f'{safe_html(item.get("eliminated", ""))} saiu com {eliminated_vote:.2f}%.</div>'
            )
            lines.append('</div>')
        lines.append('</div>')
        lines.append('<p class="paredao-spotlight-note">Nas duas indicações já concluídas, o público não comprou a leitura dos líderes a ponto de eliminar Milena.</p>')
        lines.append('</div>')

    lines.append(f'<p class="paredao-spotlight-caveat">{safe_html(story.get("caveat", ""))}</p>')
    lines.append('</div>')
    return "\n".join(lines)


def render_votos_casa_table(
    votos_casa: dict[str, str],
    avatars: dict[str, str],
) -> str:
    """Render the house votes table (used in both em_andamento and finalized)."""
    contagem = Counter(votos_casa.values())
    ranking = contagem.most_common()
    lines: list[str] = []
    lines.append(f"**Mais votado:** **{safe_html(ranking[0][0])}** ({ranking[0][1]} votos)\n")
    lines.append('<table class="table table-striped fs-lg">')
    lines.append('<thead><tr><th>Alvo</th><th class="tc">Votos</th><th>Votantes</th></tr></thead>')
    lines.append('<tbody>')
    for alvo, n in ranking:
        votantes = sorted([v for v, a in votos_casa.items() if a == alvo])
        votantes_html = ' '.join([avatar_img(v, avatars, 42) for v in votantes])
        lines.append(f'<tr><td>{avatar_html(alvo, avatars, 42)}</td><td class="tc fs-xl" style="font-weight:bold;">{n}</td><td>{votantes_html}</td></tr>')
    lines.append('</tbody></table>\n')
    return '\n'.join(lines)


def render_duelo_result_card(
    sorteado: str,
    oponente: str,
    consenso_target: str,
    avatars: dict[str, str],
    resultado_detail: str = '',
) -> str:
    """Render the visual card for the Duelo de Risco result."""
    _av_s = avatars.get(sorteado, '')
    _av_o = avatars.get(oponente, '')
    _av_t = avatars.get(consenso_target, '')
    lines: list[str] = []
    lines.append('<div style="display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:1.2rem; margin:1.5rem 0; padding:1.5rem; background:linear-gradient(145deg,#1a1a2e,#16213e); border-radius:16px; border:1px solid rgba(155,89,182,0.4);">')
    esc_sorteado = safe_html(sorteado)
    esc_oponente = safe_html(oponente)
    esc_target = safe_html(consenso_target)
    # Sorteado
    lines.append(f'<div class="tc">')
    if _av_s:
        lines.append(f'<img src="{_av_s}" style="width:72px; height:72px; border-radius:50%; border:3px solid #9b59b6;" alt="{esc_sorteado}">')
    lines.append(f'<div style="color:#fff; font-weight:bold; margin-top:0.4rem;">{esc_sorteado}</div>')
    lines.append(f'<div class="fs-sm" style="background:#9b59b6; color:#fff; padding:0.15rem 0.6rem; border-radius:8px; margin-top:0.2rem;">🎲 Sorteada</div>')
    lines.append('</div>')
    # Arrow + decision
    lines.append(f'<div class="tc fs-3xl" style="color:#9b59b6; padding:0 0.5rem;">')
    lines.append(f'<div>🤝</div>')
    lines.append(f'<div class="fs-2xs" style="color:#ccc;">Nós indicamos</div>')
    lines.append(f'</div>')
    # Oponente
    lines.append(f'<div class="tc">')
    if _av_o:
        lines.append(f'<img src="{_av_o}" style="width:72px; height:72px; border-radius:50%; border:3px solid #e67e22;" alt="{esc_oponente}">')
    lines.append(f'<div style="color:#fff; font-weight:bold; margin-top:0.4rem;">{esc_oponente}</div>')
    lines.append(f'<div class="fs-sm" style="background:#e67e22; color:#fff; padding:0.15rem 0.6rem; border-radius:8px; margin-top:0.2rem;">⚔️ Oponente</div>')
    lines.append('</div>')
    # Arrow to target
    lines.append(f'<div class="tc fs-3xl" style="color:#e74c3c; padding:0 0.5rem;">→</div>')
    # Target
    lines.append(f'<div class="tc">')
    if _av_t:
        lines.append(f'<img src="{_av_t}" style="width:72px; height:72px; border-radius:50%; border:3px solid #e74c3c;" alt="{esc_target}">')
    lines.append(f'<div style="color:#fff; font-weight:bold; margin-top:0.4rem;">{esc_target}</div>')
    lines.append(f'<div class="fs-sm" style="background:#e74c3c; color:#fff; padding:0.15rem 0.6rem; border-radius:8px; margin-top:0.2rem;">📌 Emparedada</div>')
    lines.append('</div>')
    lines.append('</div>')
    if resultado_detail:
        lines.append(f'<p class="tc fs-base" style="color:#aaa; margin-top:0.5rem;">{safe_html(resultado_detail)}</p>\n')
    return '\n'.join(lines)


def render_overlap_box(
    title: str,
    color: str,
    rgba_bg: str,
    items: list[dict],
    emoji: str,
    consenso_target: str,
    avatars: dict[str, str],
) -> str:
    """Render a single hostility overlap classification box."""
    if not items:
        return ''
    lines: list[str] = []
    lines.append(f'<div style="background:{rgba_bg}; border:1px solid {color}; border-radius:10px; padding:0.8rem; margin:0.6rem 0;">')
    lines.append(f'<h5 style="color:{color}; margin-top:0;">{emoji} {safe_html(title)} ({len(items)})</h5>')
    lines.append('<div style="display:flex; flex-wrap:wrap; gap:0.5rem;">')
    for it in items:
        _av_it = avatars.get(it["name"], '')
        _img_it = f'<img src="{_av_it}" style="width:28px; height:28px; border-radius:50%; vertical-align:middle; margin-right:3px; border:2px solid {color};">' if _av_it else ''
        _mark = ' ⭐' if it["name"] == consenso_target else ''
        esc_it_name = safe_html(it["name"])
        lines.append(f'<span class="fs-base" style="background:rgba(0,0,0,0.3); padding:0.3rem 0.6rem; border-radius:8px;">{_img_it}<strong>{esc_it_name}</strong>{_mark} <span style="color:#888;">({it["bottleneck"]:+.2f})</span></span>')
    lines.append('</div></div>')
    return '\n'.join(lines)


def render_sincerinho_bar_chart(
    received: dict[str, int],
    not_nominated: list[str],
    avatars: dict[str, str],
) -> str:
    """Render the Sincerinho Paredão Perfeito received-nominations bar chart."""
    sorted_names = sorted(received.keys(), key=lambda x: -received[x])
    max_count = max(received.values()) if received else 1

    lines: list[str] = []
    lines.append('<h4 style="margin-top:1.2rem;">📊 Indicações Recebidas</h4>\n')
    lines.append('<div style="max-width:700px;">\n')
    for name in sorted_names:
        count = received[name]
        pct = (count / max_count) * 100
        color = "#E6194B" if count >= 6 else "#FF8C00" if count >= 3 else "#3CB44B"
        av = avatar_img(name, avatars, 32)
        lines.append(f'<div style="display:flex; align-items:center; margin-bottom:4px;">')
        lines.append(f'<div style="width:180px; display:flex; align-items:center; gap:6px;">{av} <span class="fs-base">{safe_html(name)}</span></div>')
        lines.append(f'<div style="flex:1; background:#333; border-radius:4px; height:22px; position:relative;">')
        lines.append(f'<div style="width:{pct}%; background:{color}; height:100%; border-radius:4px; display:flex; align-items:center; justify-content:flex-end; padding-right:6px;">')
        lines.append(f'<span class="fs-md" style="color:#fff; font-weight:bold;">{count}×</span>')
        lines.append('</div></div></div>\n')
    if not_nominated:
        not_html = " ".join([f'{avatar_img(n, avatars, 32)} {safe_html(n)}' for n in not_nominated])
        lines.append(f'<div class="fs-base" style="margin-top:8px; padding:6px 10px; background:#1a3a1a; border:1px solid #3CB44B; border-radius:6px;">')
        lines.append(f'🛡️ <strong>Não indicados:</strong> {not_html}</div>\n')
    lines.append('</div>\n')
    return '\n'.join(lines)


def _render_lider_summary_box(
    lider_name: str,
    display_week: str,
    ranked_top3: list[tuple[str, dict]],
    vip_list: list[str],
    anjo_name: str | None,
    imunizado_nome: str | None,
    avatars: dict[str, str],
) -> str:
    """Render the gradient header card with Líder identity, top-3 cards, and Anjo note."""
    _art = artigo(lider_name)
    esc_lider = safe_html(lider_name)
    html = ""

    html += '<div style="background:linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); '
    html += 'border:2px solid #e74c3c; border-radius:12px; padding:1.2rem 1.5rem; margin:1rem 0;">'
    html += f'<div class="fs-xl" style="margin-bottom:0.8rem;">'
    html += f'🎯 <strong style="color:#e74c3c;">Previsão de Indicação d{_art} Líder</strong></div>'

    html += f'<div style="display:flex; align-items:center; gap:0.8rem; margin-bottom:1rem;">'
    html += f'{avatar_img(lider_name, avatars, size=40)}'
    html += f'<span class="fs-xl" style="color:#eee;"><strong>{esc_lider}</strong> '
    html += f'<span class="text-muted">— Líder da Semana {display_week}</span></span></div>'

    # Top 3 summary cards
    html += '<div style="display:flex; gap:0.8rem; flex-wrap:wrap; margin-bottom:0.8rem;">'
    for _i, (_tname, _tentry) in enumerate(ranked_top3):
        _sc = _tentry.get("score", 0)
        _color = "#e74c3c" if _sc < -2 else "#e67e22" if _sc < 0 else "#2ecc71"
        _vip_tag = ' <span class="fs-sm" style="color:#3498db;">VIP</span>' if _tname in vip_list else ""
        html += f'<div style="background:#111; border:1px solid {_color}; border-radius:8px; '
        html += f'padding:0.6rem 0.8rem; min-width:140px; flex:1;">'
        html += f'<div class="text-muted fs-sm">#{_i+1} mais provável</div>'
        html += f'<div style="display:flex; align-items:center; gap:0.4rem; margin:0.3rem 0;">'
        html += f'{avatar_img(_tname, avatars, size=24)} '
        html += f'<strong style="color:#eee;">{safe_html(_tname)}</strong>{_vip_tag}</div>'
        html += f'<div class="fs-xl" style="color:{_color}; font-weight:bold;">{_sc:+.2f}</div>'
        html += '</div>'
    html += '</div>'

    # Anjo note
    if anjo_name:
        html += f'<div class="fs-base" style="color:#3498db;">😇 Anjo: <strong>{safe_html(anjo_name)}</strong>'
        if imunizado_nome:
            html += f' — imunizou <strong>{safe_html(imunizado_nome)}</strong> (bloqueado como alvo)'
        html += '</div>'
    else:
        html += '<div class="text-muted fs-base">😇 Anjo ainda não definido esta semana</div>'

    html += '</div>'
    return html


def _render_ranking_row(
    rank: int,
    tname: str,
    tentry: dict,
    lider_name: str,
    pairs_daily: dict,
    vip_list: list[str],
    imunizado_nome: str | None,
    max_abs_score: float,
    avatars: dict[str, str],
) -> str:
    """Render one <tr> for the ranking table per participant."""
    _sc = tentry.get("score", 0)
    _comps = tentry.get("components", {})
    _streak_len = tentry.get("streak_len", 0)
    _has_break = tentry.get("break", False)

    _sc_color = "#e74c3c" if _sc < -2 else "#e67e22" if _sc < 0 else "#2ecc71"
    _row_bg = "background:rgba(231,76,60,0.08);" if rank <= 3 else ""

    _is_immune = (tname == imunizado_nome)
    _immune_tag = ' <span class="fs-xs" style="background:#3498db; color:#fff; padding:1px 4px; border-radius:3px;">IMUNE</span>' if _is_immune else ""

    html = ""
    html += f'<tr class="sep-bottom" style="{_row_bg}">'
    html += f'<td class="cell-compact tc text-muted">{rank}</td>'
    html += f'<td class="cell-compact" style="white-space:nowrap;">{avatar_img(tname, avatars, size=22)}'
    html += f'<strong style="color:#eee;">{safe_html(tname)}</strong>{_immune_tag}</td>'
    html += f'<td class="cell-compact tabnum" style="color:{_sc_color}; font-weight:bold;">{_sc:+.2f}</td>'

    # Score bar
    _bar_pct = min(abs(_sc) / max_abs_score * 100, 100)
    _bar_color = "#e74c3c" if _sc < 0 else "#2ecc71"
    _bar_dir = "right" if _sc < 0 else "left"
    html += f'<td class="cell-compact" style="min-width:80px;">'
    html += f'<div style="width:100%; background:#222; border-radius:3px; height:12px; position:relative;">'
    html += f'<div style="width:{_bar_pct:.0f}%; background:{_bar_color}; height:100%; border-radius:3px; '
    html += f'float:{_bar_dir};"></div></div></td>'

    # Components
    html += f'<td class="cell-compact">'
    _chips = []
    for _ck, (_ce, _cneg, _cpos) in _COMP_META.items():
        _cv = _comps.get(_ck, 0.0)
        if abs(_cv) < 0.01:
            continue
        _cc = _cneg if _cv < 0 else _cpos
        _chips.append(
            f'<span class="fs-sm" style="background:{_cc}22; color:{_cc}; border:1px solid {_cc}44; '
            f'border-radius:3px; padding:0px 4px; white-space:nowrap;">'
            f'{_ce} {_cv:+.2f}</span>'
        )
    html += " ".join(_chips) if _chips else '<span style="color:#555;">—</span>'
    html += '</td>'

    # Reciprocity
    _recip_entry = pairs_daily.get(tname, {}).get(lider_name, {})
    _recip_score = _recip_entry.get("score", 0) if _recip_entry else 0

    if _sc < 0 and _recip_score < 0:
        _rl, _rc = "⚔️ Mútua", "#e74c3c"
    elif _sc < 0 and _recip_score >= 0:
        _rl, _rc = "🔍 Alvo cego", "#e67e22"
    elif _sc >= 0 and _recip_score < 0:
        _rl, _rc = "⚠️ Risco oculto", "#e67e22"
    else:
        _rl, _rc = "💚 Aliados", "#2ecc71"

    html += f'<td class="cell-compact" style="white-space:nowrap;">'
    html += f'<span class="fs-base" style="color:{_rc};">{_rl}</span> '
    html += f'<span class="text-muted fs-sm">({_recip_score:+.2f})</span></td>'

    # Streak
    _si = "🔴" if _has_break else ("🟢" if _streak_len >= 5 else "⚪")
    _bt = ' <span class="fs-sm" style="color:#e74c3c;">BREAK</span>' if _has_break else ""
    html += f'<td class="cell-compact tc" style="white-space:nowrap;">{_si} {_streak_len}d{_bt}</td>'

    # VIP
    if tname in vip_list:
        html += '<td class="cell-compact tc">'
        html += '<span class="fs-sm" style="background:#3498db33; color:#3498db; border:1px solid #3498db55; '
        html += 'border-radius:3px; padding:1px 5px;">VIP</span></td>'
    else:
        html += '<td class="cell-compact tc" style="color:#555;">—</td>'

    html += '</tr>'
    return html


def _render_detail_row(
    lider_name: str,
    tname: str,
    pair_edges: list[dict],
    hist_fwd: list[tuple[str, str]],
    hist_rev: list[tuple[str, str]],
    row_bg: str,
    avatars: dict[str, str],
) -> str:
    """Render the expandable <details> block with edges sub-table + queridometro timeline."""
    if not pair_edges and not hist_fwd:
        return ""

    html = ""
    html += f'<tr style="{row_bg}"><td colspan="8" style="padding:0;">'
    html += '<details style="margin:0 0.4rem 0.4rem 1.8rem;">'
    html += '<summary class="text-muted fs-sm" style="cursor:pointer; '
    html += f'padding:0.2rem 0;">📋 {len(pair_edges)} evento(s) · '
    html += f'{len(hist_fwd)} dia(s) de queridômetro</summary>'
    html += '<div style="display:flex; gap:1rem; flex-wrap:wrap; margin-top:0.4rem;">'

    # Edges sub-table
    if pair_edges:
        html += '<div style="flex:1; min-width:280px;">'
        html += '<div class="fs-sm" style="color:#aaa; margin-bottom:0.3rem;"><strong>Eventos & Edges</strong></div>'
        html += '<table class="table-full table-sm">'
        html += '<thead><tr class="sep-bottom">'
        html += '<th class="text-dim tl" style="padding:2px 4px;">Data</th>'
        html += '<th class="text-dim tl" style="padding:2px 4px;">Tipo</th>'
        html += '<th class="text-dim tl" style="padding:2px 4px;">Direção</th>'
        html += '<th class="text-dim tr" style="padding:2px 4px;">Peso</th>'
        html += '<th class="text-dim tl" style="padding:2px 4px;">Detalhe</th>'
        html += '</tr></thead><tbody>'
        for _edge in pair_edges:
            _e_type = _edge.get("type", "?")
            _e_actor = _edge.get("actor", "")
            _e_weight = _edge.get("weight", 0)
            _e_date = _edge.get("date", "?")
            _e_emoji, _e_label = _EDGE_DISPLAY.get(_e_type, ("❓", _e_type))
            _e_wcolor = "#e74c3c" if _e_weight < 0 else "#2ecc71"
            _is_backlash = _edge.get("backlash", False)
            _arrow = f'{safe_html(_e_actor.split()[0])} → {safe_html((tname if _e_actor == lider_name else lider_name).split()[0])}'
            _detail_parts = []
            if _edge.get("event_type"):
                _detail_parts.append(safe_html(_edge["event_type"]))
            if _edge.get("vote_kind"):
                _detail_parts.append(safe_html(_edge["vote_kind"]))
            if _is_backlash:
                _detail_parts.append('<span style="color:#e67e22;">backlash</span>')
            _detail_str = " · ".join(_detail_parts) if _detail_parts else "—"
            html += f'<tr style="border-bottom:1px solid #222;">'
            html += f'<td class="text-muted" style="padding:2px 4px; white-space:nowrap;">{_e_date}</td>'
            html += f'<td style="padding:2px 4px; white-space:nowrap;">{_e_emoji} {_e_label}</td>'
            html += f'<td class="fs-base" style="padding:2px 4px; color:#aaa;">{_arrow}</td>'
            html += f'<td class="tr tabnum" style="padding:2px 4px; color:{_e_wcolor};">{_e_weight:+.2f}</td>'
            html += f'<td class="text-muted" style="padding:2px 4px;">{_detail_str}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'

    # Queridômetro timeline
    if hist_fwd:
        _all_dates = sorted(set(d for d, _ in hist_fwd) | set(d for d, _ in hist_rev))
        _fwd_by_date = {d: lbl for d, lbl in hist_fwd}
        _rev_by_date = {d: lbl for d, lbl in hist_rev}
        _show_dates = _all_dates[-14:]

        html += '<div style="flex:1; min-width:240px;">'
        html += '<div class="fs-sm" style="color:#aaa; margin-bottom:0.3rem;">'
        html += f'<strong>Queridômetro</strong> (últimos {len(_show_dates)} dias)</div>'
        html += '<table class="table-full table-sm">'
        html += '<thead><tr class="sep-bottom">'
        html += f'<th class="text-dim tl" style="padding:2px 4px;">Data</th>'
        html += f'<th class="text-dim tc" style="padding:2px 4px;">{safe_html(lider_name.split()[0])}→</th>'
        html += f'<th class="text-dim tc" style="padding:2px 4px;">→{safe_html(lider_name.split()[0])}</th>'
        html += '</tr></thead><tbody>'
        for _dt in _show_dates:
            _fwd_lbl = _fwd_by_date.get(_dt, "")
            _rev_lbl = _rev_by_date.get(_dt, "")
            _fwd_e = _EMOJI_MAP.get(_fwd_lbl, "")
            _rev_e = _EMOJI_MAP.get(_rev_lbl, "")
            _fwd_sent = SENTIMENT_WEIGHTS.get(_fwd_lbl, 0)
            _rev_sent = SENTIMENT_WEIGHTS.get(_rev_lbl, 0)
            _fwd_c = "#2ecc71" if _fwd_sent > 0 else "#e74c3c" if _fwd_sent < -0.5 else "#e67e22" if _fwd_sent < 0 else "#555"
            _rev_c = "#2ecc71" if _rev_sent > 0 else "#e74c3c" if _rev_sent < -0.5 else "#e67e22" if _rev_sent < 0 else "#555"
            html += f'<tr style="border-bottom:1px solid #222;">'
            html += f'<td class="text-muted fs-base" style="padding:1px 4px;">{_dt[5:]}</td>'
            html += f'<td class="tc" style="padding:1px 4px; color:{_fwd_c};">{_fwd_e}</td>'
            html += f'<td class="tc" style="padding:1px 4px; color:{_rev_c};">{_rev_e}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'

    html += '</div></details></td></tr>'
    return html


def render_lider_prediction(
    lider_name: str | None,
    ranked: list[tuple[str, dict]],
    pairs_daily: dict,
    rel_edges: list[dict],
    vip_list: list[str],
    anjo_name: str | None,
    imunizado_nome: str | None,
    display_week: str,
    avatars: dict[str, str],
    querido_history: dict[tuple[str, str], list[tuple[str, str]]],
) -> str:
    """Render the full Líder nomination prediction section."""
    # Early return: no active leader
    if not lider_name:
        return (
            '<div class="tc fs-xl" style="background:#1a1a2e; border:1px solid #444; border-radius:10px; '
            'padding:1.5rem; margin:1rem 0; color:#aaa;">'
            '🏠 <strong>Sem líder ativo</strong> — previsão de indicação indisponível.</div>'
        )

    html = '<h2 id="previsao-indicacao">🎯 Previsão — Indicação do Líder</h2>'

    # Summary box with Líder identity, top-3 targets, Anjo note
    html += _render_lider_summary_box(
        lider_name, display_week, ranked[:3],
        vip_list, anjo_name, imunizado_nome, avatars,
    )

    # Full ranking table — header
    html += '<div class="scroll-x" style="margin-top:1.2rem;">'
    html += '<table class="table-full fs-base">'
    html += '<thead><tr style="border-bottom:2px solid #444;">'
    for _hdr in ["#", "Participante", "Score", "Barra", "Componentes", "Reciprocidade", "Streak", "VIP"]:
        html += f'<th style="padding:0.5rem 0.4rem; text-align:left; color:#aaa; white-space:nowrap;">{_hdr}</th>'
    html += '</tr></thead><tbody>'

    _max_abs = max((abs(e.get("score", 0)) for _, e in ranked), default=1) or 1

    # Ranking rows + detail rows
    for _rank, (_tname, _tentry) in enumerate(ranked, 1):
        html += _render_ranking_row(
            _rank, _tname, _tentry, lider_name,
            pairs_daily, vip_list, imunizado_nome, _max_abs, avatars,
        )

        # Expandable detail row: edges + queridômetro history
        _pair_edges = [e for e in rel_edges if
            (e.get("actor") == lider_name and e.get("target") == _tname) or
            (e.get("actor") == _tname and e.get("target") == lider_name)]
        _pair_edges.sort(key=lambda e: e.get("date", ""))

        _row_bg = "background:rgba(231,76,60,0.08);" if _rank <= 3 else ""
        html += _render_detail_row(
            lider_name, _tname, _pair_edges,
            querido_history.get((lider_name, _tname), []),
            querido_history.get((_tname, lider_name), []),
            _row_bg, avatars,
        )

    html += '</tbody></table></div>'

    # Methodology note
    html += '<div class="text-muted fs-md" style="background:#111; border:1px solid #333; border-radius:8px; '
    html += 'padding:0.8rem 1rem; margin:1rem 0;">'
    html += '<strong style="color:#aaa;">📐 Metodologia</strong><br>'
    html += 'A previsão é baseada no <strong>score acumulado do Líder → cada participante</strong>, '
    html += 'calculado pelo sistema de Sentiment Index (queridômetro com memória de streak + '
    html += 'eventos de poder, Sincerão, votos e VIP). O participante com o score mais negativo '
    html += 'é o alvo mais provável de indicação. '
    html += 'Membros do VIP foram escolhidos pelo Líder, indicando aliança — são alvos improváveis. '
    html += '<strong>Isto não é um modelo preditivo dedicado</strong> — é uma leitura dos dados '
    html += 'de relacionamento acumulados até o momento.'
    html += '</div>'

    return html
