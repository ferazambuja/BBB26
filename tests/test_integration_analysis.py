"""Integration tests for build_paredao_analysis, build_clusters_data, and build_vote_prediction.

These functions depend on complex upstream data. We create synthetic data
for 5 participants over 10 days with 1 paredao, then run the real pipeline
functions and verify the output structures.
"""
import pytest
import sys
from pathlib import Path

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_derived_data import (
    build_paredao_analysis,
    build_clusters_data,
    build_vote_prediction,
    build_relations_scores,
    build_daily_roles,
    build_auto_events,
)
from data_utils import POSITIVE, MILD_NEGATIVE, STRONG_NEGATIVE


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_participant(name, group="Vip", member_of="Pipoca", roles=None,
                      received_reactions=None, balance=500, avatar=""):
    """Build a participant dict matching the real API format."""
    return {
        "name": name,
        "avatar": avatar or f"https://example.com/{name.lower()}.jpg",
        "characteristics": {
            "group": group,
            "memberOf": member_of,
            "balance": balance,
            "roles": roles or [],
            "mainRole": None,
            "eliminated": False,
            "receivedReactions": received_reactions or [],
        },
    }


def _make_reaction(label, givers):
    """Build a receivedReaction entry."""
    return {
        "label": label,
        "amount": len(givers),
        "participants": [{"id": str(i), "name": g} for i, g in enumerate(givers, 1)],
    }


def _make_snapshot(date, participants):
    """Build a snapshot dict with date and participants."""
    return {"date": date, "participants": participants}


# ─── Reaction patterns ───────────────────────────────────────────────────────
# 5 participants: Alice, Bob, Carol, Dave, Eve
# Each day every participant gives one reaction to each other.
# We vary reactions over 10 days to produce meaningful scoring.

NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve"]
DATES = [f"2026-01-{d:02d}" for d in range(13, 23)]  # 01-13 to 01-22


def _build_day_reactions(day_index):
    """Return per-participant received reactions for a given day index (0-9).

    Pattern:
    - Days 0-4: Alice/Bob/Carol form a positive cluster; Dave/Eve are negative toward them.
    - Days 5-9: Dave starts sending hearts to Carol (thaw); Eve stays hostile.
    - Alice always sends Cobra to Dave, creating a stable rivalry.
    """
    # Build an outgoing reaction map: giver -> receiver -> reaction label
    outgoing = {}
    for g in NAMES:
        outgoing[g] = {}
        for r in NAMES:
            if g == r:
                continue
            outgoing[g][r] = "Coração"  # default heart

    # Core alliance: Alice <-> Bob <-> Carol (hearts)
    # Already set by default.

    # Dave -> Alice: Cobra always
    outgoing["Dave"]["Alice"] = "Cobra"
    # Dave -> Bob: Planta (mild negative)
    outgoing["Dave"]["Bob"] = "Planta"
    # Alice -> Dave: Cobra always
    outgoing["Alice"]["Dave"] = "Cobra"
    # Bob -> Dave: Alvo (strong negative)
    outgoing["Bob"]["Dave"] = "Alvo"

    # Eve -> everyone except Dave: varies
    outgoing["Eve"]["Alice"] = "Cobra"
    outgoing["Eve"]["Bob"] = "Planta"
    outgoing["Eve"]["Carol"] = "Mala"

    # Dave -> Carol: evolves over time
    if day_index < 5:
        outgoing["Dave"]["Carol"] = "Planta"
    else:
        outgoing["Dave"]["Carol"] = "Coração"  # thaw

    # Dave -> Eve: hearts (allies)
    outgoing["Dave"]["Eve"] = "Coração"
    # Eve -> Dave: hearts (allies)
    outgoing["Eve"]["Dave"] = "Coração"

    # Carol -> Dave: mild negative early, then evolves
    if day_index < 7:
        outgoing["Carol"]["Dave"] = "Biscoito"
    else:
        outgoing["Carol"]["Dave"] = "Coração"

    # Carol -> Eve: always mild negative
    outgoing["Carol"]["Eve"] = "Mala"

    # Alice -> Eve: Cobra
    outgoing["Alice"]["Eve"] = "Cobra"
    # Bob -> Eve: Planta
    outgoing["Bob"]["Eve"] = "Planta"

    # Now convert outgoing -> per-receiver received reactions
    received = {n: {} for n in NAMES}
    for giver in NAMES:
        for receiver, label in outgoing[giver].items():
            received[receiver].setdefault(label, [])
            received[receiver][label].append(giver)

    return received


def _build_participants_for_day(day_index):
    """Build list of participant dicts for one day."""
    received = _build_day_reactions(day_index)
    participants = []
    for name in NAMES:
        reactions = []
        for label, givers in received[name].items():
            reactions.append(_make_reaction(label, givers))

        # Give Alice the Lider role on days 0-4 (week 1)
        roles = []
        if name == "Alice" and day_index < 5:
            roles = ["Líder"]
        elif name == "Bob" and day_index >= 5:
            roles = ["Líder"]

        member_of = {
            "Alice": "Pipoca", "Bob": "Pipoca",
            "Carol": "Veterano", "Dave": "Veterano", "Eve": "Camarote",
        }[name]

        group = "Vip" if name in ["Alice", "Bob", "Carol"] else "Xepa"

        participants.append(_make_participant(
            name,
            group=group,
            member_of=member_of,
            roles=roles,
            received_reactions=reactions,
        ))
    return participants


# ─── Module-scoped fixtures ──────────────────────────────────────────────────


@pytest.fixture(scope="module")
def synthetic_snapshots():
    """10 daily snapshots for 5 participants."""
    return [_make_snapshot(DATES[i], _build_participants_for_day(i)) for i in range(10)]


@pytest.fixture(scope="module")
def paredoes_data():
    """One finalized paredao."""
    return {
        "paredoes": [
            {
                "numero": 1,
                "status": "finalizado",
                "data": "2026-01-21",
                "data_formacao": "2026-01-19",
                "semana": 1,
                "titulo": "1\u00ba Pared\u00e3o",
                "total_esperado": 3,
                "formacao": {
                    "lider": "Alice",
                    "indicado_lider": "Dave",
                },
                "indicados_finais": [
                    {"nome": "Dave", "grupo": "Veterano", "como": "L\u00edder"},
                    {"nome": "Eve", "grupo": "Camarote", "como": "Casa"},
                    {"nome": "Carol", "grupo": "Veterano", "como": "Casa"},
                ],
                "votos_casa": {"Bob": "Dave", "Carol": "Eve"},
                "resultado": {
                    "eliminado": "Dave",
                    "votos": {
                        "Dave": {"voto_unico": 55.0, "voto_torcida": 65.0, "voto_total": 60.0},
                        "Eve": {"voto_unico": 30.0, "voto_torcida": 20.0, "voto_total": 25.0},
                        "Carol": {"voto_unico": 15.0, "voto_torcida": 15.0, "voto_total": 15.0},
                    },
                },
                "fontes": [],
            }
        ]
    }


@pytest.fixture(scope="module")
def manual_events():
    """Basic manual events with one power event (indicacao)."""
    return {
        "participants": {},
        "weekly_events": [],
        "special_events": [],
        "power_events": [
            {
                "date": "2026-01-19",
                "week": 1,
                "type": "indicacao",
                "actor": "Alice",
                "target": "Dave",
                "detail": "Indicou Dave ao pared\u00e3o",
                "impacto": "negativo",
                "origem": "manual",
            }
        ],
        "scheduled_events": [],
        "cartola_points_log": [],
    }


@pytest.fixture(scope="module")
def daily_roles(synthetic_snapshots):
    """Build daily roles from synthetic snapshots."""
    return build_daily_roles(synthetic_snapshots)


@pytest.fixture(scope="module")
def auto_events(daily_roles):
    """Build auto events from daily roles."""
    return build_auto_events(daily_roles)


@pytest.fixture(scope="module")
def sincerao_edges():
    """Empty sincerao edges."""
    return {"edges": [], "weeks": []}


@pytest.fixture(scope="module")
def participants_index():
    """Canonical participant index for 5 participants."""
    return [
        {"name": "Alice", "grupo": "Pipoca", "active": True, "avatar": "https://example.com/alice.jpg",
         "first_seen": "2026-01-13", "last_seen": "2026-01-22"},
        {"name": "Bob", "grupo": "Pipoca", "active": True, "avatar": "https://example.com/bob.jpg",
         "first_seen": "2026-01-13", "last_seen": "2026-01-22"},
        {"name": "Carol", "grupo": "Veterano", "active": True, "avatar": "https://example.com/carol.jpg",
         "first_seen": "2026-01-13", "last_seen": "2026-01-22"},
        {"name": "Dave", "grupo": "Veterano", "active": True, "avatar": "https://example.com/dave.jpg",
         "first_seen": "2026-01-13", "last_seen": "2026-01-22"},
        {"name": "Eve", "grupo": "Camarote", "active": True, "avatar": "https://example.com/eve.jpg",
         "first_seen": "2026-01-13", "last_seen": "2026-01-22"},
    ]


@pytest.fixture(scope="module")
def relations_scores_output(
    synthetic_snapshots, manual_events, auto_events,
    sincerao_edges, paredoes_data, daily_roles, participants_index,
):
    """Pre-build relations_scores for tests that depend on it."""
    return build_relations_scores(
        synthetic_snapshots[-1],
        synthetic_snapshots,
        manual_events,
        auto_events,
        sincerao_edges,
        paredoes_data,
        daily_roles,
        participants_index=participants_index,
    )


# ─── TestBuildParedaoAnalysis ─────────────────────────────────────────────────


class TestBuildParedaoAnalysis:
    """Tests for build_paredao_analysis."""

    @pytest.fixture(scope="class")
    def paredao_output(self, synthetic_snapshots, paredoes_data):
        return build_paredao_analysis(synthetic_snapshots, paredoes_data)

    def test_smoke_returns_by_paredao(self, paredao_output):
        """Output has by_paredao dict with key '1'."""
        assert "by_paredao" in paredao_output
        assert "1" in paredao_output["by_paredao"]

    def test_paredao_has_nominee_stats(self, paredao_output):
        """Paredao 1 has indicados_stats with 3 entries (Dave, Eve, Carol)."""
        p1 = paredao_output["by_paredao"]["1"]
        stats = p1["quick_insights"]["indicados_stats"]
        assert len(stats) == 3
        stat_names = {s["nome"] for s in stats}
        assert stat_names == {"Dave", "Eve", "Carol"}

    def test_sentiment_values_are_numeric(self, paredao_output):
        """For each nominee in indicados_stats, sentimento is a number."""
        p1 = paredao_output["by_paredao"]["1"]
        for stat in p1["quick_insights"]["indicados_stats"]:
            assert isinstance(stat["sentimento"], (int, float)), (
                f"sentimento for {stat['nome']} is {type(stat['sentimento'])}, not numeric"
            )

    def test_historical_series_present(self, paredao_output):
        """historical_series is a non-empty list of dicts with date, name, sentiment."""
        p1 = paredao_output["by_paredao"]["1"]
        series = p1["quick_insights"]["historical_series"]
        assert isinstance(series, list)
        assert len(series) > 0
        for entry in series:
            assert "date" in entry
            assert "name" in entry
            assert "sentiment" in entry
            assert isinstance(entry["sentiment"], (int, float))


# ─── TestBuildClustersData ────────────────────────────────────────────────────


class TestBuildClustersData:
    """Tests for build_clusters_data."""

    @pytest.fixture(scope="class")
    def clusters_output(self, relations_scores_output, participants_index, paredoes_data):
        result = build_clusters_data(relations_scores_output, participants_index, paredoes_data)
        if result is None:
            pytest.skip("networkx not installed — cannot test clusters")
        return result

    def test_smoke_returns_communities(self, clusters_output):
        """Output has communities list with at least 1 entry."""
        assert "communities" in clusters_output
        assert isinstance(clusters_output["communities"], list)
        assert len(clusters_output["communities"]) >= 1

    def test_all_participants_assigned(self, clusters_output):
        """Every active participant appears in exactly one community."""
        all_members = []
        for comm in clusters_output["communities"]:
            all_members.extend(comm["members"])
        # All 5 participants should be assigned
        assert set(all_members) == set(NAMES)
        # No duplicates
        assert len(all_members) == len(NAMES)

    def test_community_structure(self, clusters_output):
        """Each community has label, members, cohesion, color."""
        for comm in clusters_output["communities"]:
            assert "label" in comm, "community missing 'label'"
            assert "members" in comm, "community missing 'members'"
            assert isinstance(comm["members"], list)
            assert len(comm["members"]) > 0
            assert "cohesion" in comm, "community missing 'cohesion'"
            assert isinstance(comm["cohesion"], (int, float))
            assert "color" in comm, "community missing 'color'"

    def test_metadata_present(self, clusters_output):
        """_metadata has n_active, n_clusters, silhouette_coefficient."""
        meta = clusters_output["_metadata"]
        assert "n_active" in meta
        assert meta["n_active"] == 5
        assert "n_clusters" in meta
        assert meta["n_clusters"] >= 1
        assert "silhouette_coefficient" in meta


# ─── TestBuildVotePrediction ──────────────────────────────────────────────────


class TestBuildVotePrediction:
    """Tests for build_vote_prediction."""

    @pytest.fixture(scope="class")
    def clusters_data(self, relations_scores_output, participants_index, paredoes_data):
        return build_clusters_data(relations_scores_output, participants_index, paredoes_data)

    @pytest.fixture(scope="class")
    def prediction_output(self, synthetic_snapshots, paredoes_data,
                          clusters_data, relations_scores_output):
        return build_vote_prediction(
            synthetic_snapshots, paredoes_data,
            clusters_data, relations_scores_output,
        )

    def test_smoke_returns_by_paredao(self, prediction_output):
        """Output has by_paredao with key '1' and cumulative."""
        assert "by_paredao" in prediction_output
        assert "1" in prediction_output["by_paredao"]
        assert "cumulative" in prediction_output

    def test_predictions_for_each_voter(self, prediction_output):
        """Paredao 1 has predictions dict with entries for eligible voters."""
        p1 = prediction_output["by_paredao"]["1"]
        preds = p1["predictions"]
        assert isinstance(preds, dict)
        # Bob and Carol are the voters in votos_casa, so they should have predictions
        # (Alice is Lider so can't vote; Dave is indicado_lider so can't be voted)
        assert len(preds) > 0
        # Each prediction should have 'predicted' and 'score'
        for voter, pred in preds.items():
            assert "predicted" in pred, f"prediction for {voter} missing 'predicted'"
            assert "score" in pred, f"prediction for {voter} missing 'score'"

    def test_aggregate_vote_concentration(self, prediction_output):
        """Aggregate section has vote_concentration dict."""
        p1 = prediction_output["by_paredao"]["1"]
        agg = p1["aggregate"]
        assert "vote_concentration" in agg
        assert isinstance(agg["vote_concentration"], dict)
        # At least one target should appear
        assert len(agg["vote_concentration"]) > 0

    def test_retrospective_present_for_finalized(self, prediction_output):
        """Since paredao 1 is finalized with votos_casa, retrospective exists."""
        p1 = prediction_output["by_paredao"]["1"]
        assert "retrospective" in p1, "retrospective missing for finalized paredao"
        retro = p1["retrospective"]
        assert "individual" in retro
        indiv = retro["individual"]
        assert "correct" in indiv
        assert "total" in indiv
        assert "pct" in indiv
        # Accuracy should be between 0 and 100
        assert 0 <= indiv["pct"] <= 100
