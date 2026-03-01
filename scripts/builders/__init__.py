"""Builders package — domain modules for the derived data pipeline.

Each module owns a specific domain (relations, cartola, clusters, etc.).
All public build_* functions are re-exported here for backwards compatibility.
"""
from builders.relations import (
    build_relations_scores,
    compute_streak_data,
    get_all_snapshots,
    _blend_streak,
    _compute_base_weights,
    _compute_base_weights_all,
    _build_power_event_edges,
    _build_sincerao_edges_section,
    _build_vote_edges,
    _classify_sentiment,
    _sentiment_value_for_category,
    RELATION_POWER_WEIGHTS,
    RELATION_SINC_WEIGHTS,
    RELATION_SINC_BACKLASH_FACTOR,
    RELATION_VOTE_WEIGHTS,
    RELATION_ANJO_WEIGHTS,
    RELATION_VIP_WEIGHT,
    RELATION_VISIBILITY_FACTOR,
    RELATION_POWER_BACKLASH_FACTOR,
    SYSTEM_ACTORS,
    STREAK_REACTIVE_WEIGHT,
    STREAK_MEMORY_WEIGHT,
    STREAK_BREAK_PENALTY,
    STREAK_BREAK_MAX_LEN,
    STREAK_MEMORY_MAX_LEN,
    REACTIVE_WINDOW_WEIGHTS,
)

from builders.daily_analysis import (
    build_daily_metrics,
    build_daily_changes_summary,
    build_hostility_daily_counts,
    build_vulnerability_history,
    build_impact_history,
    format_date_label,
)

from builders.participants import (
    ROLES,
    build_participants_index,
    build_daily_roles,
    build_auto_events,
    apply_big_fone_context,
)

from builders.plant_index import (
    build_plant_index,
    PLANT_INDEX_WEIGHTS,
    PLANT_POWER_ACTIVITY_WEIGHTS,
    PLANT_INDEX_BONUS_PLATEIA,
    PLANT_INDEX_EMOJI_CAP,
    PLANT_INDEX_HEART_CAP,
    PLANT_INDEX_SINCERAO_DECAY,
    PLANT_INDEX_ROLLING_WEEKS,
    PLANT_GANHA_GANHA_WEIGHT,
)

from builders.sincerao import (
    build_sincerao_edges,
    validate_manual_events,
    split_names,
)

from builders.cartola import build_cartola_data

from builders.provas import (
    build_prova_rankings,
    PROVA_TYPE_MULTIPLIER,
    PROVA_PLACEMENT_POINTS,
    PROVA_PLACEMENT_DEFAULT,
    PROVA_DQ_POINTS,
)

from builders.clusters import (
    build_clusters_data,
    build_cluster_evolution,
    CLUSTER_COLORS,
)

from builders.timeline import (
    build_game_timeline,
    build_power_summary,
)

from builders.paredao_analysis import (
    build_paredao_analysis,
    build_paredao_badges,
)

from builders.vote_prediction import (
    build_vote_prediction,
    extract_paredao_eligibility,
    VOTE_PREDICTION_CONFIG,
)

__all__ = [
    # relations
    "build_relations_scores", "compute_streak_data",
    "RELATION_POWER_WEIGHTS", "RELATION_SINC_WEIGHTS", "RELATION_SINC_BACKLASH_FACTOR",
    "RELATION_VOTE_WEIGHTS", "RELATION_ANJO_WEIGHTS", "RELATION_VIP_WEIGHT",
    "RELATION_VISIBILITY_FACTOR", "RELATION_POWER_BACKLASH_FACTOR",
    "SYSTEM_ACTORS", "STREAK_REACTIVE_WEIGHT", "STREAK_MEMORY_WEIGHT",
    "STREAK_BREAK_PENALTY", "STREAK_BREAK_MAX_LEN", "STREAK_MEMORY_MAX_LEN",
    "REACTIVE_WINDOW_WEIGHTS",
    # daily_analysis
    "build_daily_metrics", "build_daily_changes_summary",
    "build_hostility_daily_counts", "build_vulnerability_history",
    "build_impact_history", "format_date_label",
    # participants
    "ROLES", "build_participants_index", "build_daily_roles",
    "build_auto_events", "apply_big_fone_context",
    # plant_index
    "build_plant_index", "PLANT_INDEX_WEIGHTS", "PLANT_POWER_ACTIVITY_WEIGHTS",
    "PLANT_INDEX_BONUS_PLATEIA", "PLANT_INDEX_EMOJI_CAP", "PLANT_INDEX_HEART_CAP",
    "PLANT_INDEX_SINCERAO_DECAY", "PLANT_INDEX_ROLLING_WEEKS", "PLANT_GANHA_GANHA_WEIGHT",
    # sincerao
    "build_sincerao_edges", "validate_manual_events", "split_names",
    # cartola
    "build_cartola_data",
    # provas
    "build_prova_rankings", "PROVA_TYPE_MULTIPLIER", "PROVA_PLACEMENT_POINTS",
    "PROVA_PLACEMENT_DEFAULT", "PROVA_DQ_POINTS",
    # clusters
    "build_clusters_data", "build_cluster_evolution", "CLUSTER_COLORS",
    # timeline
    "build_game_timeline", "build_power_summary",
    # paredao_analysis
    "build_paredao_analysis", "build_paredao_badges",
    # vote_prediction
    "build_vote_prediction", "extract_paredao_eligibility", "VOTE_PREDICTION_CONFIG",
]
