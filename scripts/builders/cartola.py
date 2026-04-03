"""Cartola BBB points computation — role detection, manual events, formatting."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from data_utils import CARTOLA_POINTS, get_cycle_number, normalize_route_label, parse_roles
from builders.participants import _normalize_big_fone


def _is_pre_vote_commitment_route(como_text: str | None) -> bool:
    """Return True when a nomination route puts someone on paredão before house voting."""
    route = normalize_route_label(como_text)
    if route in {
        'Líder',
        'Big Fone',
        'Bloco do Paredão',
        'Caixas-Surpresa',
        'Consenso Anjo+Monstro',
        'Duelo de Risco',
        'Exilado',
    }:
        return True

    como_lower = (como_text or '').lower()
    return (
        'dinâmica' in como_lower or
        'dinamica' in como_lower or
        'triângulo' in como_lower or
        'triangulo' in como_lower or
        'máquina' in como_lower or
        'maquina' in como_lower
    )


def _collect_current_holders_and_vip(snap_participants: list[dict]) -> tuple[dict, set[str]]:
    """Iterate snapshot participants to build current role holders dict and VIP set.

    Returns (current_holders, current_vip) where current_holders maps role names
    to a set of names. Líder/Anjo are typically single-holder but may have multiple
    (e.g., dual leadership in Week 8).
    """
    current_holders: dict = {
        'Líder': set(), 'Anjo': set(),
        'Monstro': set(), 'Imune': set(), 'Paredão': set(),
    }
    current_vip: set[str] = set()

    for p in snap_participants:
        name = p.get('name', '').strip()
        if not name:
            continue
        roles = parse_roles(p.get('characteristics', {}).get('roles', []))
        group = p.get('characteristics', {}).get('group', '')

        for role in roles:
            if role == 'Líder':
                current_holders['Líder'].add(name)
            elif role == 'Anjo':
                current_holders['Anjo'].add(name)
            elif role == 'Monstro':
                current_holders['Monstro'].add(name)
            elif role == 'Imune':
                current_holders['Imune'].add(name)
            elif role == 'Paredão':
                current_holders['Paredão'].add(name)

        if group == 'Vip':
            current_vip.add(name)

    return current_holders, current_vip


def _detect_cartola_roles(daily_snapshots: list[dict], calculated_points: dict) -> None:
    """Auto-detect roles from API snapshots and populate calculated_points."""
    def has_event(name, week, event_key):
        week_events = calculated_points.get(name, {}).get(week, [])
        return any(e[0] == event_key for e in week_events)

    previous_holders = {
        'Líder': set(), 'Anjo': set(),
        'Monstro': set(), 'Imune': set(), 'Paredão': set(),
    }
    vip_awarded = defaultdict(set)
    role_awarded = defaultdict(lambda: defaultdict(set))
    previous_vip: set[str] = set()

    for snap in daily_snapshots:
        date = snap['date']
        week = get_cycle_number(date)

        current_holders, current_vip = _collect_current_holders_and_vip(snap['participants'])

        # Líder (may have multiple for dual leadership)
        new_lideres = current_holders['Líder'] - previous_holders['Líder']
        for name in new_lideres:
            if name not in role_awarded['Líder'][week]:
                calculated_points[name][week].append(('lider', CARTOLA_POINTS['lider'], date))
                role_awarded['Líder'][week].add(name)

        # Anjo (may have multiple in theory)
        new_anjos = current_holders['Anjo'] - previous_holders['Anjo']
        for name in new_anjos:
            if name not in role_awarded['Anjo'][week]:
                calculated_points[name][week].append(('anjo', CARTOLA_POINTS['anjo'], date))
                role_awarded['Anjo'][week].add(name)

        # Monstro
        new_monstros = current_holders['Monstro'] - previous_holders['Monstro']
        for name in new_monstros:
            if name not in role_awarded['Monstro'][week]:
                calculated_points[name][week].append(('monstro', CARTOLA_POINTS['monstro'], date))
                role_awarded['Monstro'][week].add(name)
                # Monstro retirado do VIP: if Monstro recipient was in VIP before
                if name in previous_vip:
                    calculated_points[name][week].append(('monstro_retirado_vip', CARTOLA_POINTS['monstro_retirado_vip'], date))

        # Imune (Líderes don't accumulate)
        new_imunes = current_holders['Imune'] - previous_holders['Imune']
        for name in new_imunes:
            if name in current_holders['Líder'] or has_event(name, week, 'lider'):
                continue
            if name not in role_awarded['Imune'][week]:
                calculated_points[name][week].append(('imunizado', CARTOLA_POINTS['imunizado'], date))
                role_awarded['Imune'][week].add(name)

        # Paredão
        new_paredao = current_holders['Paredão'] - previous_holders['Paredão']
        for name in new_paredao:
            if name not in role_awarded['Paredão'][week]:
                calculated_points[name][week].append(('emparedado', CARTOLA_POINTS['emparedado'], date))
                role_awarded['Paredão'][week].add(name)

        # VIP (Líderes don't accumulate)
        for name in current_vip:
            if name in current_holders['Líder'] or has_event(name, week, 'lider'):
                continue
            if name not in vip_awarded[week]:
                calculated_points[name][week].append(('vip', CARTOLA_POINTS['vip'], date))
                vip_awarded[week].add(name)

        previous_holders['Líder'] = current_holders['Líder'].copy()
        previous_holders['Anjo'] = current_holders['Anjo'].copy()
        previous_holders['Monstro'] = current_holders['Monstro'].copy()
        previous_holders['Imune'] = current_holders['Imune'].copy()
        previous_holders['Paredão'] = current_holders['Paredão'].copy()
        previous_vip = current_vip.copy()


def _event_exists(calculated_points: dict, name: str, week: int, event_key: str) -> bool:
    week_events = calculated_points.get(name, {}).get(week, [])
    return any(evt[0] == event_key for evt in week_events)


def _add_event_if_missing(calculated_points: dict, name: str, week: int, event_key: str, points: int, date_str: str | None) -> None:
    if not name:
        return
    if _event_exists(calculated_points, name, week, event_key):
        return
    calculated_points[name][week].append((event_key, points, date_str))


def _normalize_name_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else []
    return []


def _normalize_int_list(value) -> list[int]:
    out: list[int] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, int):
                out.append(item)
    elif isinstance(value, int):
        out.append(value)
    return out


def _week_from_payload(week_raw, date_str: str) -> int:
    if isinstance(week_raw, int) and week_raw > 0:
        return week_raw
    if date_str:
        return get_cycle_number(date_str)
    return 1


def _collect_api_detected(calculated_points: dict) -> dict:
    tracked = {'lider', 'anjo', 'monstro', 'imunizado', 'emparedado', 'vip'}
    detected = defaultdict(lambda: defaultdict(set))
    for name, weeks in calculated_points.items():
        for week, events in weeks.items():
            for evt, *_ in events:
                if evt in tracked:
                    detected[evt][week].add(name)
    return detected


def _normalize_cartola_round_overrides(manual_events: dict) -> list[dict]:
    raw = manual_events.get('cartola_rounds', [])
    if not isinstance(raw, list):
        return []

    normalized: list[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        round_num = entry.get('round')
        if not isinstance(round_num, int) or round_num <= 0:
            continue
        cycles = sorted(set(_normalize_int_list(entry.get('cycles')))) or [round_num]
        normalized.append({
            'round': round_num,
            'cycles': cycles,
            'status': str(entry.get('status') or '').strip(),
            'notes': str(entry.get('notes') or '').strip(),
            'fontes': list(entry.get('fontes') or []),
            'excluded_events': [
                sel for sel in entry.get('excluded_events', [])
                if isinstance(sel, dict)
            ],
        })
    return sorted(normalized, key=lambda item: item['round'])


def _event_selector_matches(name: str, cycle: int, event_data: tuple, selector: dict) -> bool:
    evt_name, points, date_str = event_data

    if selector.get('participant') and str(selector['participant']).strip() != name:
        return False
    if selector.get('cycle') is not None and selector.get('cycle') != cycle:
        return False
    if selector.get('event') and str(selector['event']).strip() != evt_name:
        return False
    if selector.get('date') and str(selector['date']).strip() != (date_str or ''):
        return False
    if selector.get('points') is not None and selector.get('points') != points:
        return False
    return True


def _build_cartola_round_views(all_points: dict, manual_events: dict, n_cycles: int) -> tuple[dict, list[dict], int, list[dict]]:
    all_cycles = sorted({
        cycle
        for participant_points in all_points.values()
        for cycle in participant_points.keys()
        if isinstance(cycle, int) and cycle > 0
    })
    max_cycle_seen = max([n_cycles, *all_cycles], default=n_cycles)
    cycle_to_round = {cycle: cycle for cycle in range(1, max_cycle_seen + 1)}

    overrides = _normalize_cartola_round_overrides(manual_events)
    overrides_by_round = {}
    for entry in overrides:
        overrides_by_round[entry['round']] = entry
        for cycle in entry['cycles']:
            cycle_to_round[cycle] = entry['round']

    n_rounds = max(cycle_to_round.values(), default=max_cycle_seen)
    round_points: dict[str, dict[str, list[list]]] = {str(rnd): {} for rnd in range(1, n_rounds + 1)}

    for participant, participant_points in all_points.items():
        for cycle, events in sorted(participant_points.items()):
            round_num = cycle_to_round.get(cycle, cycle)
            excluded = overrides_by_round.get(round_num, {}).get('excluded_events', [])
            selected_events = [
                [evt_name, pts, date_str]
                for evt_name, pts, date_str in events
                if not any(
                    _event_selector_matches(participant, cycle, (evt_name, pts, date_str), selector)
                    for selector in excluded
                )
            ]
            if selected_events:
                round_points[str(round_num)].setdefault(participant, []).extend(selected_events)

    rounds = []
    for round_num in range(1, n_rounds + 1):
        override = overrides_by_round.get(round_num, {})
        cycles = sorted([
            cycle for cycle, mapped_round in cycle_to_round.items()
            if mapped_round == round_num
        ])
        round_entry = {
            'round': round_num,
            'cycles': cycles or ([round_num] if round_num <= max_cycle_seen else []),
        }
        if override.get('status'):
            round_entry['status'] = override['status']
        if override.get('notes'):
            round_entry['notes'] = override['notes']
        if override.get('fontes'):
            round_entry['fontes'] = override['fontes']
        rounds.append(round_entry)

    current_candidates = [
        entry['round']
        for entry in rounds
        if str(entry.get('status') or '').lower() not in {'', 'finalized', 'closed'}
    ]
    current_round = max(current_candidates, default=n_rounds or 1)

    cumulative_round_evolution = []
    running_totals = defaultdict(int)
    per_participant_round_totals = defaultdict(dict)
    for round_str, participants in round_points.items():
        round_num = int(round_str)
        for participant, events in participants.items():
            per_participant_round_totals[participant][round_num] = sum(pts for _, pts, _ in events)

    for round_num in range(1, n_rounds + 1):
        for participant in per_participant_round_totals:
            if round_num in per_participant_round_totals[participant]:
                running_totals[participant] += per_participant_round_totals[participant][round_num]
            if running_totals[participant] != 0:
                cumulative_round_evolution.append({
                    'round': round_num,
                    'name': participant,
                    'cumulative_points': running_totals[participant],
                })

    return round_points, rounds, current_round, cumulative_round_evolution


def _collect_official_role_events(provas_data: dict | None, manual_events: dict, paredoes_data: dict) -> tuple[dict, dict, dict]:
    """Collect canonical event assignments from provas/manual/ paredões.

    Returns:
      official_events: event_key -> week -> {name: date}
      strict_weeks: event_key -> set(weeks) where unexpected API extras must fail
      leaders_by_week: week -> set(names)
    """
    official_events = defaultdict(lambda: defaultdict(dict))
    strict_weeks = defaultdict(set)
    leaders_by_week = defaultdict(set)

    def add_official(event_key: str, week: int, names: list[str], date_str: str, strict: bool = False) -> None:
        if strict:
            strict_weeks[event_key].add(week)
        for name in names:
            n = str(name or '').strip()
            if not n:
                continue
            if n not in official_events[event_key][week]:
                official_events[event_key][week][n] = date_str or None

    provas = provas_data.get('provas', []) if isinstance(provas_data, dict) else []
    if isinstance(provas, list):
        for prova in provas:
            if not isinstance(prova, dict):
                continue
            tipo = str(prova.get('tipo', '')).strip().lower()
            date_str = str(prova.get('date') or '').strip()
            week = _week_from_payload(prova.get('cycle'), date_str)
            winners = _normalize_name_list(prova.get('vencedores')) or _normalize_name_list(prova.get('vencedor'))

            if tipo in {'lider', 'líder'}:
                add_official('lider', week, winners, date_str, strict=True)
                leaders_by_week[week].update(winners)

                vip_names = _normalize_name_list(prova.get('vip'))
                if vip_names:
                    vip_source = str(prova.get('vip_source') or '').strip().lower()
                    vip_strict = vip_source != 'api_fallback'
                    add_official('vip', week, vip_names, date_str, strict=vip_strict)

            if tipo == 'anjo':
                add_official('anjo', week, winners, date_str, strict=True)

    for week_event in manual_events.get('cycles', []):
        if not isinstance(week_event, dict):
            continue
        week = week_event.get('cycle')
        if not isinstance(week, int):
            continue
        anjo = week_event.get('anjo')
        if not isinstance(anjo, dict):
            continue
        monstro_names = _normalize_name_list(anjo.get('monstro'))
        monstro_date = str(anjo.get('prova_date') or week_event.get('start_date') or '')
        if monstro_names:
            add_official('monstro', week, monstro_names, monstro_date, strict=False)

        imunizados = _normalize_name_list(anjo.get('imunizado'))
        imune_date = str(anjo.get('prova_date') or week_event.get('start_date') or '')
        if imunizados:
            add_official('imunizado', week, imunizados, imune_date, strict=False)

    for ev in manual_events.get('power_events', []):
        if not isinstance(ev, dict):
            continue
        ev_type = ev.get('type')
        date_str = str(ev.get('date') or '').strip()
        week = _week_from_payload(ev.get('cycle'), date_str)
        target = str(ev.get('target') or '').strip()
        if not target:
            continue
        if ev_type == 'imunidade':
            add_official('imunizado', week, [target], date_str, strict=False)
        elif ev_type == 'troca_vip':
            add_official('vip', week, [target], date_str, strict=True)

    for paredao in paredoes_data.get('paredoes', []):
        if not isinstance(paredao, dict):
            continue
        date_str = str(paredao.get('data_formacao') or paredao.get('data') or '').strip()
        week = _week_from_payload(paredao.get('cycle'), date_str)
        indicados = [
            str(item.get('nome') or '').strip()
            for item in paredao.get('indicados_finais', [])
            if isinstance(item, dict) and str(item.get('nome') or '').strip()
        ]
        if indicados:
            add_official('emparedado', week, indicados, date_str, strict=True)

    return official_events, strict_weeks, leaders_by_week


def _validate_unexpected_api_extras(api_detected: dict, official_events: dict, strict_weeks: dict, leaders_by_week: dict) -> None:
    """Fail fast if API has extra names not present in strict official sources."""
    for event_key, weeks in strict_weeks.items():
        for week in sorted(weeks):
            expected = set(official_events.get(event_key, {}).get(week, {}).keys())
            detected = set(api_detected.get(event_key, {}).get(week, set()))

            # Leaders and Anjos are auto-placed in VIP by the API but score
            # separate points (lider/anjo), so exclude them from the VIP strict check.
            if event_key in {'vip', 'imunizado'}:
                week_leaders = set(leaders_by_week.get(week, set()))
                expected -= week_leaders
                detected -= week_leaders
                # Anjo is also moved to VIP by the API — exclude from VIP check
                week_anjos = set(official_events.get('anjo', {}).get(week, {}).keys())
                detected -= week_anjos

            unexpected = sorted(detected - expected)
            if unexpected:
                raise RuntimeError(
                    f"Cartola strict mismatch ({event_key}, week {week}): "
                    f"API has unexpected names {unexpected}; expected subset={sorted(expected)}"
                )


def _apply_official_role_fallbacks(calculated_points: dict, official_events: dict, leaders_by_week: dict) -> None:
    points_by_event = {
        'lider': CARTOLA_POINTS['lider'],
        'anjo': CARTOLA_POINTS['anjo'],
        'monstro': CARTOLA_POINTS['monstro'],
        'imunizado': CARTOLA_POINTS['imunizado'],
        'emparedado': CARTOLA_POINTS['emparedado'],
        'vip': CARTOLA_POINTS['vip'],
    }

    for event_key, points in points_by_event.items():
        for week, names_with_date in official_events.get(event_key, {}).items():
            for name, date_str in names_with_date.items():
                if event_key in {'vip', 'imunizado'} and (
                    name in leaders_by_week.get(week, set()) or _event_exists(calculated_points, name, week, 'lider')
                ):
                    continue
                _add_event_if_missing(calculated_points, name, week, event_key, points, date_str)

    # If Monstro recipient had VIP points in the same week, apply extra -5.
    for week, monstros in official_events.get('monstro', {}).items():
        vip_names = set(official_events.get('vip', {}).get(week, {}).keys())
        for name, date_str in monstros.items():
            if name not in vip_names:
                continue
            _add_event_if_missing(
                calculated_points,
                name,
                week,
                'monstro_retirado_vip',
                CARTOLA_POINTS['monstro_retirado_vip'],
                date_str,
            )


def _apply_cartola_manual(calculated_points: dict, manual_events: dict, paredoes_data: dict, daily_snapshots: list[dict]) -> dict:
    """Apply manual events, paredão-derived events, and merge with cartola_points_log.

    Returns all_points (merged calculated + manual log).
    """
    def has_event(name, week, event_key):
        week_events = calculated_points.get(name, {}).get(week, [])
        return any(e[0] == event_key for e in week_events)

    def add_event_points(name, week, event_key, points, date_str):
        if not name:
            return
        week_events = calculated_points[name].get(week, [])
        if any(e[0] == event_key for e in week_events):
            return
        calculated_points[name][week].append((event_key, points, date_str))

    # Manual events
    for week_event in manual_events.get('cycles', []):
        week = week_event.get('cycle', 1)
        start_date = week_event.get('start_date', '')
        bf_list = _normalize_big_fone(week_event.get('big_fone'))
        for big_fone in bf_list:
            if big_fone.get('atendeu'):
                bf_date = big_fone.get('date', start_date)
                name = big_fone['atendeu'].strip()
                week_events = calculated_points[name].get(week, [])
                # Avoid duplicate: check both event type and date
                if not any(e[0] == 'atendeu_big_fone' and e[2] == bf_date for e in week_events):
                    calculated_points[name][week].append(('atendeu_big_fone', CARTOLA_POINTS['atendeu_big_fone'], bf_date))

    # Build paredão-to-cycle map for eliminated participants
    _paredao_cycle: dict[int, int] = {}
    for _p in paredoes_data.get('paredoes', []):
        if _p.get('cycle'):
            _paredao_cycle[_p['numero']] = _p['cycle']

    for name, info in manual_events.get('participants', {}).items():
        name = name.strip()
        status = info.get('status')
        exit_date = info.get('exit_date', '')
        # Use paredão's cycle for eliminations (handles cross-cycle dates)
        paredao_num = info.get('paredao') or info.get('paredao_numero')
        week = _paredao_cycle.get(paredao_num, get_cycle_number(exit_date) if exit_date else 1)
        if status == 'desistente':
            calculated_points[name][week].append(('desistente', CARTOLA_POINTS['desistente'], exit_date))
        elif status in ('eliminada', 'eliminado'):
            calculated_points[name][week].append(('eliminado', CARTOLA_POINTS['eliminado'], exit_date))
        elif status == 'desclassificado':
            calculated_points[name][week].append(('desclassificado', CARTOLA_POINTS['desclassificado'], exit_date))

    # Paredão-derived events
    def get_snapshot_on_or_before(date_str):
        if not daily_snapshots:
            return None
        chosen = None
        for snap in daily_snapshots:
            if snap['date'] <= date_str:
                chosen = snap
        return chosen or daily_snapshots[-1]

    for p in paredoes_data.get('paredoes', []):
        paredao_date = p.get('data', '')
        if not paredao_date:
            continue
        week = p.get('cycle') or get_cycle_number(paredao_date)
        indicados = [i.get('nome') for i in p.get('indicados_finais', []) if i.get('nome')]
        if not indicados:
            continue

        # Salvo do paredão (Bate e Volta winners — may be multiple)
        formacao = p.get('formacao', {})
        bv_winners_set = set()
        if isinstance(formacao, dict):
            bv = formacao.get('bate_volta')
            if isinstance(bv, dict):
                bv_winners_list = bv.get('vencedores') or ([bv['vencedor']] if bv.get('vencedor') else [])
                bv_winners_set = set(bv_winners_list)
                salvar_com_janela_aberta = bool(
                    bv.get('salvacao_com_janela_aberta') or bv.get('janela_escalacao_aberta')
                )
                for vencedor_bv in bv_winners_list:
                    if not has_event(vencedor_bv, week, 'imunizado'):
                        # Bate e Volta winner was emparedado before escaping.
                        add_event_points(vencedor_bv, week, 'emparedado',
                                         CARTOLA_POINTS['emparedado'], paredao_date)
                        if not salvar_com_janela_aberta:
                            add_event_points(vencedor_bv, week, 'salvo_paredao',
                                             CARTOLA_POINTS['salvo_paredao'], paredao_date)

        # Salvo do paredão via Máquina do Poder
        mdp = formacao.get('maquina_do_poder') if isinstance(formacao, dict) else None
        if mdp and isinstance(mdp, dict) and mdp.get('salvou'):
            salvou_mdp = mdp['salvou']
            if salvou_mdp not in bv_winners_set:  # avoid double-counting
                add_event_points(salvou_mdp, week, 'emparedado',
                                 CARTOLA_POINTS['emparedado'], paredao_date)
                add_event_points(salvou_mdp, week, 'salvo_paredao',
                                 CARTOLA_POINTS['salvo_paredao'], paredao_date)

        # Não eliminado no paredão / Quarto Secreto (Paredão Falso)
        resultado = p.get('resultado') or {}
        eliminado = resultado.get('eliminado')
        if p.get('status') == 'finalizado' and eliminado:
            if p.get('paredao_falso'):
                # Paredão Falso: "eliminado" goes to Quarto Secreto (+40)
                add_event_points(eliminado, week, 'quarto_secreto',
                                 CARTOLA_POINTS['quarto_secreto'], paredao_date)
            for nome in indicados:
                if nome != eliminado and nome not in bv_winners_set:
                    # BV winners get salvo_paredao (+25) instead of volta (+20)
                    add_event_points(nome, week, 'nao_eliminado_paredao',
                                     CARTOLA_POINTS['nao_eliminado_paredao'], paredao_date)

        # Elegíveis para votação da casa
        snap = get_snapshot_on_or_before(paredao_date)
        if snap:
            ativos = {pp.get('name', '').strip() for pp in snap['participants']}
            formacao_dict = p.get('formacao', {}) if isinstance(p.get('formacao', {}), dict) else {}
            # Support dual leaders: lideres array or single lider string
            _lideres_arr = formacao_dict.get('lideres', [])
            lider_form = (formacao_dict.get('lider') or '').strip()
            lider_names_form = set(n.strip() for n in _lideres_arr) if _lideres_arr else ({lider_form} if lider_form else set())
            imune_form = ''
            if isinstance(formacao_dict.get('imunizado'), dict):
                imune_form = (formacao_dict.get('imunizado', {}).get('quem') or '').strip()

            extra_imunes = set()
            for ev in manual_events.get('power_events', []):
                if ev.get('type') != 'imunidade':
                    continue
                ev_week = get_cycle_number(ev['date']) if ev.get('date') else ev.get('cycle', 0)
                if ev_week == week and ev.get('target'):
                    extra_imunes.add(ev['target'].strip())

            elegiveis = set(ativos)
            elegiveis -= lider_names_form
            # Anjo is NOT excluded from elegiveis — the Anjo is only
            # ineligible if they are also immune (handled by imune_form
            # or extra_imunes). In standard weeks the Anjo immunizes
            # someone else and remains eligible for voting/emparedamento.
            # In modo turbo (autoimune), the Anjo IS the imunizado.
            if imune_form:
                elegiveis.discard(imune_form)
            elegiveis -= extra_imunes

            # Não emparedado
            for nome in elegiveis:
                if nome in indicados:
                    continue
                if nome in bv_winners_set:
                    continue
                if has_event(nome, week, 'imunizado'):
                    continue
                add_event_points(nome, week, 'nao_emparedado',
                                 CARTOLA_POINTS['nao_emparedado'], paredao_date)

            # Não recebeu votos da casa
            # "Não recebeu votos" = was eligible to be voted by the house AND
            # was NOT voted against. Excludes: anyone who received votes,
            # BV winners, and anyone committed to paredão BEFORE voting
            # (Líder-indicados, dinâmica entries). Contragolpe targets ARE
            # eligible (they were available during voting, got pulled in after).
            votos_casa = p.get('votos_casa', {}) or {}
            if votos_casa:
                receberam = set(votos_casa.values())
                # Build set of people committed BEFORE house vote
                pre_vote_committed = set()
                pre_vote_committed |= lider_names_form  # Líder is excluded from voting pool
                for ind in p.get('indicados_finais', []):
                    como = (ind.get('como') or '').lower()
                    nome_ind = ind.get('nome', '')
                    # Pre-vote dynamics don't count for "não recebeu votos".
                    if _is_pre_vote_commitment_route(como):
                        pre_vote_committed.add(nome_ind)
                pre_vote_committed |= bv_winners_set

                for nome in elegiveis:
                    if nome in receberam:
                        continue
                    if nome in pre_vote_committed:
                        continue
                    if has_event(nome, week, 'imunizado'):
                        continue
                    add_event_points(nome, week, 'nao_recebeu_votos',
                                     CARTOLA_POINTS['nao_recebeu_votos'], paredao_date)

    # Rule normalization (Líder doesn't accumulate VIP or Imunizado,
    # but DOES accumulate Monstro penalties and other events).
    # VIP and Imunizado are already guarded at detection time (lines 96, 111),
    # but manual/official events could re-add them — this is the safety net.
    _LIDER_EXCLUDED = {'vip', 'imunizado'}
    for name, weeks in calculated_points.items():
        for week, events in weeks.items():
            if any(e[0] == 'lider' for e in events):
                calculated_points[name][week] = [e for e in events if e[0] not in _LIDER_EXCLUDED]

    # Merge with cartola_points_log
    all_points = defaultdict(lambda: defaultdict(list))
    for participant, weeks in calculated_points.items():
        for week, events in weeks.items():
            all_points[participant][week] = list(events)

    for entry in manual_events.get('cartola_points_log', []):
        participant = entry['participant']
        week = entry.get('cycle') or entry['week']
        for evt in entry.get('events', []):
            event_type = evt['event']
            points = evt['points']
            existing = all_points[participant].get(week, [])
            already_has = any(e[0] == event_type for e in existing)
            if not already_has:
                all_points[participant][week].append((event_type, points, evt.get('date')))

    return all_points


def _format_cartola_output(all_points: dict, participants_index: list[dict], manual_events: dict, daily_snapshots: list[dict]) -> dict:
    """Format Cartola output: leaderboard, weekly points, stats, cumulative evolution."""
    # Build participant info from index
    participant_info = {}
    for rec in participants_index:
        name = rec.get('name', '').strip()
        if name:
            participant_info[name] = {
                'grupo': rec.get('grupo', 'Pipoca'),
                'avatar': rec.get('avatar', ''),
                'active': rec.get('active', True),
            }

    # Mark exited participants
    for name, info in manual_events.get('participants', {}).items():
        name = name.strip()
        if name in participant_info:
            participant_info[name]['active'] = False
        else:
            participant_info[name] = {'grupo': 'Pipoca', 'avatar': '', 'active': False}

    # Calculate totals
    totals = {}
    for participant in all_points:
        total = sum(pts for week_events in all_points[participant].values() for _, pts, _ in week_events)
        totals[participant] = total

    # Build leaderboard
    leaderboard = []
    for name, total in totals.items():
        info = participant_info.get(name, {'grupo': 'Pipoca', 'avatar': '', 'active': False})
        events_list = []
        for week, events in sorted(all_points[name].items()):
            for evt, pts, date in events:
                events_list.append({"cycle": week, "event": evt, "points": pts, "date": date})
        leaderboard.append({
            'name': name,
            'total': total,
            'grupo': info.get('grupo', 'Pipoca'),
            'avatar': info.get('avatar', ''),
            'active': info.get('active', False),
            'events': events_list,
        })

    # Add 0-point participants
    for name, info in participant_info.items():
        if name not in totals:
            leaderboard.append({
                'name': name, 'total': 0,
                'grupo': info.get('grupo', 'Pipoca'),
                'avatar': info.get('avatar', ''),
                'active': info.get('active', True),
                'events': [],
            })

    leaderboard = sorted(leaderboard, key=lambda x: (-x['total'], x['name']))

    # Cycle points (serializable)
    cycle_points = {}
    for participant in all_points:
        for week, events in all_points[participant].items():
            week_str = str(week)
            if week_str not in cycle_points:
                cycle_points[week_str] = {}
            cycle_points[week_str][participant] = [[evt, pts, date] for evt, pts, date in events]

    # Stats
    n_cycles = max([get_cycle_number(s['date']) for s in daily_snapshots], default=1) if daily_snapshots else 1
    round_points, rounds, current_round, cumulative_round_evolution = _build_cartola_round_views(
        all_points, manual_events, n_cycles
    )

    seen_roles = {"Líder": [], "Anjo": [], "Monstro": []}
    for entry in leaderboard:
        for evt in entry['events']:
            if evt['event'] == 'lider' and entry['name'] not in seen_roles['Líder']:
                seen_roles['Líder'].append(entry['name'])
            elif evt['event'] == 'anjo' and entry['name'] not in seen_roles['Anjo']:
                seen_roles['Anjo'].append(entry['name'])
            elif evt['event'] == 'monstro' and entry['name'] not in seen_roles['Monstro']:
                seen_roles['Monstro'].append(entry['name'])

    current_roles = {'Líder': [], 'Anjo': None, 'Monstro': [], 'Paredão': []}
    if daily_snapshots:
        latest = daily_snapshots[-1]
        for p_data in latest['participants']:
            name = p_data.get('name', '').strip()
            roles = parse_roles(p_data.get('characteristics', {}).get('roles', []))
            if 'Líder' in roles:
                current_roles['Líder'].append(name)
            if 'Anjo' in roles:
                current_roles['Anjo'] = name
            if 'Monstro' in roles:
                current_roles['Monstro'].append(name)
            if 'Paredão' in roles:
                current_roles['Paredão'].append(name)

    # Cumulative evolution: running totals per participant per week
    cumulative_evolution = []
    running_totals_evo = defaultdict(int)
    for week in range(1, n_cycles + 1):
        for participant in all_points:
            if week in all_points[participant]:
                week_pts = sum(pts for _, pts, _ in all_points[participant][week])
                running_totals_evo[participant] += week_pts
            if running_totals_evo[participant] != 0:
                cumulative_evolution.append({
                    "cycle": week,
                    "name": participant,
                    "cumulative_points": running_totals_evo[participant],
                })

    return {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_cycles": n_cycles,
            "n_rounds": len(rounds),
            "n_snapshots": len(daily_snapshots),
            "current_round": current_round,
        },
        "leaderboard": leaderboard,
        "cycle_points": cycle_points,
        "round_points": round_points,
        "rounds": rounds,
        "cumulative_evolution": cumulative_evolution,
        "cumulative_round_evolution": cumulative_round_evolution,
        "stats": {
            "n_with_points": len([p for p in leaderboard if p['total'] != 0]),
            "n_active": len([p for p in leaderboard if p['active']]),
            "total_positive": sum(p['total'] for p in leaderboard if p['total'] > 0),
            "total_negative": sum(p['total'] for p in leaderboard if p['total'] < 0),
            "seen_roles": seen_roles,
            "current_roles": current_roles,
        },
    }


def build_cartola_data(
    daily_snapshots: list[dict],
    manual_events: dict,
    paredoes_data: dict,
    participants_index: list[dict],
    provas_data: dict | None = None,
) -> dict:
    """Build Cartola BBB points data from snapshots, manual events, and paredões.

    Returns a dict suitable for writing to cartola_data.json.
    """
    calculated_points = defaultdict(lambda: defaultdict(list))

    _detect_cartola_roles(daily_snapshots, calculated_points)
    api_detected = _collect_api_detected(calculated_points)
    official_events, strict_weeks, leaders_by_week = _collect_official_role_events(provas_data, manual_events, paredoes_data)
    _validate_unexpected_api_extras(api_detected, official_events, strict_weeks, leaders_by_week)
    _apply_official_role_fallbacks(calculated_points, official_events, leaders_by_week)
    all_points = _apply_cartola_manual(calculated_points, manual_events, paredoes_data, daily_snapshots)
    return _format_cartola_output(all_points, participants_index, manual_events, daily_snapshots)
