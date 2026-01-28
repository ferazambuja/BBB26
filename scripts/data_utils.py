#!/usr/bin/env python3
"""Shared data loading utilities for QMD pages."""

import json
from pathlib import Path


def require_clean_manual_events(audit_path=None):
    """Raise if manual events audit reports inconsistencies."""
    if audit_path is None:
        audit_path = Path("data/derived/manual_events_audit.json")
    else:
        audit_path = Path(audit_path)

    if not audit_path.exists():
        raise RuntimeError("manual_events_audit.json não encontrado. Execute scripts/build_derived_data.py")

    with open(audit_path, encoding="utf-8") as f:
        audit = json.load(f)

    issues = audit.get("issues_count", 0)
    if issues:
        raise RuntimeError(f"Manual events audit falhou com {issues} problema(s). Veja docs/MANUAL_EVENTS_AUDIT.md")


def load_snapshot(filepath):
    """Load snapshot JSON (new or old format)."""
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "participants" in data:
        return data["participants"], data.get("_metadata", {})
    return data, {}


def get_all_snapshots(data_dir=Path("data/snapshots")):
    """Return list of (filepath, date_str) sorted by filename."""
    if not data_dir.exists():
        return []
    snapshots = sorted(data_dir.glob("*.json"))
    result = []
    for fp in snapshots:
        date_str = fp.stem.split("_")[0]
        result.append((fp, date_str))
    return result


def parse_roles(roles_data):
    """Extract role labels from roles array (strings or dicts)."""
    if not roles_data:
        return []
    labels = []
    for r in roles_data:
        if isinstance(r, dict):
            labels.append(r.get("label", ""))
        else:
            labels.append(str(r))
    return [l for l in labels if l]


def build_reaction_matrix(participants):
    """Build {(giver_name, receiver_name): reaction_label} dict."""
    matrix = {}
    for receiver in participants:
        rname = receiver.get("name")
        if not rname:
            continue
        for rxn in receiver.get("characteristics", {}).get("receivedReactions", []):
            label = rxn.get("label", "")
            for giver in rxn.get("participants", []):
                gname = giver.get("name")
                if gname:
                    matrix[(gname, rname)] = label
    return matrix


def load_votalhada_polls(filepath=None):
    """Load Votalhada poll aggregation data.

    Returns dict with 'paredoes' list, or empty structure if file missing.
    """
    if filepath is None:
        filepath = Path("data/votalhada/polls.json")
    else:
        filepath = Path(filepath)

    if not filepath.exists():
        return {"paredoes": []}

    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def load_sincerao_edges(filepath=None):
    """Load derived Sincerão edges/aggregates."""
    if filepath is None:
        filepath = Path("data/derived/sincerao_edges.json")
    else:
        filepath = Path(filepath)

    if not filepath.exists():
        return {"weeks": [], "edges": [], "aggregates": []}

    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def get_poll_for_paredao(polls_data, numero):
    """Get poll data for a specific paredão number.

    Args:
        polls_data: Dict from load_votalhada_polls()
        numero: Paredão number (1, 2, 3, ...)

    Returns:
        Poll dict for that paredão, or None if not found.
    """
    for p in polls_data.get("paredoes", []):
        if p.get("numero") == numero:
            return p
    return None


def calculate_poll_accuracy(poll_data):
    """Calculate accuracy metrics for a finalized paredão poll.

    Args:
        poll_data: Single paredão poll dict with 'resultado_real' field

    Returns:
        Dict with accuracy metrics, or None if no result data.
    """
    if not poll_data or "resultado_real" not in poll_data:
        return None

    consolidado = poll_data.get("consolidado", {})
    resultado = poll_data.get("resultado_real", {})
    participantes = poll_data.get("participantes", [])

    # Check if prediction was correct
    predicao_correta = consolidado.get("predicao_eliminado") == resultado.get("eliminado")

    # Calculate mean absolute error
    errors = []
    for nome in participantes:
        pred = consolidado.get(nome, 0)
        real = resultado.get(nome, 0)
        errors.append(abs(pred - real))

    erro_medio = sum(errors) / len(errors) if errors else 0

    return {
        "predicao_correta": predicao_correta,
        "erro_medio": round(erro_medio, 2),
        "erros_por_participante": {
            nome: round(consolidado.get(nome, 0) - resultado.get(nome, 0), 2)
            for nome in participantes
        }
    }
