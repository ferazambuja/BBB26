"""Cartola BBB points computation — role detection, manual events, formatting."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from data_utils import CARTOLA_POINTS, get_week_number, parse_roles
from builders.participants import _normalize_big_fone


def _collect_current_holders_and_vip(snap_participants: list[dict]) -> tuple[dict, set[str]]:
    """Iterate snapshot participants to build current role holders dict and VIP set.

    Returns (current_holders, current_vip) where current_holders maps role names
    to either a single name (Líder, Anjo) or a set of names (Monstro, Imune, Paredão).
    """
    current_holders: dict = {
        'Líder': None, 'Anjo': None,
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
                current_holders['Líder'] = name
            elif role == 'Anjo':
                current_holders['Anjo'] = name
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
        'Líder': None, 'Anjo': None,
        'Monstro': set(), 'Imune': set(), 'Paredão': set(),
    }
    vip_awarded = defaultdict(set)
    role_awarded = defaultdict(lambda: defaultdict(set))
    previous_vip: set[str] = set()

    for snap in daily_snapshots:
        date = snap['date']
        week = get_week_number(date)

        current_holders, current_vip = _collect_current_holders_and_vip(snap['participants'])

        # Líder
        if current_holders['Líder'] and current_holders['Líder'] != previous_holders['Líder']:
            name = current_holders['Líder']
            if week not in role_awarded['Líder'] or name not in role_awarded['Líder'][week]:
                calculated_points[name][week].append(('lider', CARTOLA_POINTS['lider'], date))
                role_awarded['Líder'][week].add(name)

        # Anjo
        if current_holders['Anjo'] and current_holders['Anjo'] != previous_holders['Anjo']:
            name = current_holders['Anjo']
            if week not in role_awarded['Anjo'] or name not in role_awarded['Anjo'][week]:
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

        # Imune (Líder doesn't accumulate)
        new_imunes = current_holders['Imune'] - previous_holders['Imune']
        for name in new_imunes:
            if name == current_holders['Líder'] or has_event(name, week, 'lider'):
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

        # VIP (Líder doesn't accumulate)
        for name in current_vip:
            if name == current_holders['Líder'] or has_event(name, week, 'lider'):
                continue
            if name not in vip_awarded[week]:
                calculated_points[name][week].append(('vip', CARTOLA_POINTS['vip'], date))
                vip_awarded[week].add(name)

        previous_holders['Líder'] = current_holders['Líder']
        previous_holders['Anjo'] = current_holders['Anjo']
        previous_holders['Monstro'] = current_holders['Monstro'].copy()
        previous_holders['Imune'] = current_holders['Imune'].copy()
        previous_holders['Paredão'] = current_holders['Paredão'].copy()
        previous_vip = current_vip.copy()


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
    for week_event in manual_events.get('weekly_events', []):
        week = week_event.get('week', 1)
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

    for name, info in manual_events.get('participants', {}).items():
        name = name.strip()
        status = info.get('status')
        exit_date = info.get('exit_date', '')
        week = get_week_number(exit_date) if exit_date else 1
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
        week = p.get('semana') or get_week_number(paredao_date)
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
                for vencedor_bv in bv_winners_list:
                    if not has_event(vencedor_bv, week, 'imunizado'):
                        add_event_points(vencedor_bv, week, 'salvo_paredao',
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
                if nome != eliminado:
                    add_event_points(nome, week, 'nao_eliminado_paredao',
                                     CARTOLA_POINTS['nao_eliminado_paredao'], paredao_date)

        # Elegíveis para votação da casa
        snap = get_snapshot_on_or_before(paredao_date)
        if snap:
            ativos = {pp.get('name', '').strip() for pp in snap['participants']}
            formacao_dict = p.get('formacao', {}) if isinstance(p.get('formacao', {}), dict) else {}
            lider_form = (formacao_dict.get('lider') or '').strip()
            anjo_form = (formacao_dict.get('anjo') or '').strip()
            imune_form = ''
            if isinstance(formacao_dict.get('imunizado'), dict):
                imune_form = (formacao_dict.get('imunizado', {}).get('quem') or '').strip()

            extra_imunes = set()
            for ev in manual_events.get('power_events', []):
                if ev.get('type') != 'imunidade':
                    continue
                ev_week = get_week_number(ev['date']) if ev.get('date') else ev.get('week', 0)
                if ev_week == week and ev.get('target'):
                    extra_imunes.add(ev['target'].strip())

            elegiveis = set(ativos)
            if lider_form:
                elegiveis.discard(lider_form)
            if anjo_form:
                elegiveis.discard(anjo_form)
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
            votos_casa = p.get('votos_casa', {}) or {}
            if votos_casa:
                receberam = set(votos_casa.values())
                for nome in elegiveis:
                    if nome in receberam:
                        continue
                    if has_event(nome, week, 'imunizado'):
                        continue
                    add_event_points(nome, week, 'nao_recebeu_votos',
                                     CARTOLA_POINTS['nao_recebeu_votos'], paredao_date)

    # Rule normalization (Líder doesn't accumulate)
    for name, weeks in calculated_points.items():
        for week, events in weeks.items():
            if any(e[0] == 'lider' for e in events):
                calculated_points[name][week] = [e for e in events if e[0] == 'lider']

    # Merge with cartola_points_log
    all_points = defaultdict(lambda: defaultdict(list))
    for participant, weeks in calculated_points.items():
        for week, events in weeks.items():
            all_points[participant][week] = list(events)

    for entry in manual_events.get('cartola_points_log', []):
        participant = entry['participant']
        week = entry['week']
        for evt in entry.get('events', []):
            event_type = evt['event']
            points = evt['points']
            existing = all_points[participant].get(week, [])
            already_has = any(e[0] == event_type for e in existing)
            auto_types = {'lider', 'anjo', 'monstro', 'emparedado', 'imunizado', 'vip',
                          'desistente', 'eliminado', 'desclassificado', 'atendeu_big_fone',
                          'monstro_retirado_vip', 'quarto_secreto'}
            if not already_has and event_type not in auto_types:
                all_points[participant][week].append((event_type, points, None))

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
                events_list.append({"week": week, "event": evt, "points": pts, "date": date})
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

    # Weekly points (serializable)
    weekly_points = {}
    for participant in all_points:
        for week, events in all_points[participant].items():
            week_str = str(week)
            if week_str not in weekly_points:
                weekly_points[week_str] = {}
            weekly_points[week_str][participant] = [[evt, pts, date] for evt, pts, date in events]

    # Stats
    n_weeks = max([get_week_number(s['date']) for s in daily_snapshots], default=1) if daily_snapshots else 1

    seen_roles = {"Líder": [], "Anjo": [], "Monstro": []}
    for entry in leaderboard:
        for evt in entry['events']:
            if evt['event'] == 'lider' and entry['name'] not in seen_roles['Líder']:
                seen_roles['Líder'].append(entry['name'])
            elif evt['event'] == 'anjo' and entry['name'] not in seen_roles['Anjo']:
                seen_roles['Anjo'].append(entry['name'])
            elif evt['event'] == 'monstro' and entry['name'] not in seen_roles['Monstro']:
                seen_roles['Monstro'].append(entry['name'])

    current_roles = {'Líder': None, 'Anjo': None, 'Monstro': [], 'Paredão': []}
    if daily_snapshots:
        latest = daily_snapshots[-1]
        for p_data in latest['participants']:
            name = p_data.get('name', '').strip()
            roles = parse_roles(p_data.get('characteristics', {}).get('roles', []))
            if 'Líder' in roles:
                current_roles['Líder'] = name
            if 'Anjo' in roles:
                current_roles['Anjo'] = name
            if 'Monstro' in roles:
                current_roles['Monstro'].append(name)
            if 'Paredão' in roles:
                current_roles['Paredão'].append(name)

    # Cumulative evolution: running totals per participant per week
    cumulative_evolution = []
    running_totals_evo = defaultdict(int)
    for week in range(1, n_weeks + 1):
        for participant in all_points:
            if week in all_points[participant]:
                week_pts = sum(pts for _, pts, _ in all_points[participant][week])
                running_totals_evo[participant] += week_pts
            if running_totals_evo[participant] != 0:
                cumulative_evolution.append({
                    "week": week,
                    "name": participant,
                    "cumulative_points": running_totals_evo[participant],
                })

    return {
        "_metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_weeks": n_weeks,
            "n_snapshots": len(daily_snapshots),
        },
        "leaderboard": leaderboard,
        "weekly_points": weekly_points,
        "cumulative_evolution": cumulative_evolution,
        "stats": {
            "n_with_points": len([p for p in leaderboard if p['total'] != 0]),
            "n_active": len([p for p in leaderboard if p['active']]),
            "total_positive": sum(p['total'] for p in leaderboard if p['total'] > 0),
            "total_negative": sum(p['total'] for p in leaderboard if p['total'] < 0),
            "seen_roles": seen_roles,
            "current_roles": current_roles,
        },
    }


def build_cartola_data(daily_snapshots: list[dict], manual_events: dict, paredoes_data: dict, participants_index: list[dict]) -> dict:
    """Build Cartola BBB points data from snapshots, manual events, and paredões.

    Returns a dict suitable for writing to cartola_data.json.
    """
    calculated_points = defaultdict(lambda: defaultdict(list))

    _detect_cartola_roles(daily_snapshots, calculated_points)
    all_points = _apply_cartola_manual(calculated_points, manual_events, paredoes_data, daily_snapshots)
    return _format_cartola_output(all_points, participants_index, manual_events, daily_snapshots)
