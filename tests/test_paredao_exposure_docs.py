"""Tests for paredão exposure docs renderer and updater."""
from __future__ import annotations

import json
import pytest
from pathlib import Path

from derived_pipeline import (
    render_paredao_exposure_docs_markdown,
    update_paredao_docs_section,
    _MARKER_START,
    _MARKER_END,
)
from data_utils import stable_json_hash, read_json_if_exists


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def sample_stats():
    return {
        "metrics": {
            "first_timer": {"rate": 0.7143, "n": 5, "total": 7, "scope": "real_only"},
            "route_casa": {"rate": 0.2, "n": 1, "total": 5, "scope": "real_only"},
            "route_lider": {"rate": 0.2857, "n": 2, "total": 7, "scope": "real_only"},
            "bv_presence_by_paredao": {"rate": 0.8571, "n": 6, "total": 7, "scope": "real_only"},
            "bv_winners_escaped": {"rate": 1.0, "n": 8, "total": 8, "scope": "real_only"},
            "bv_losers_survived": {"rate": 0.6, "n": 6, "total": 10, "scope": "real_only"},
            "bv_losers_eliminated": {"rate": 0.4, "n": 4, "total": 10, "scope": "real_only"},
        },
        "facts": {
            "bv_total_participants": 18,
            "single_sample_routes": [
                {"route": "Big Fone", "n": 1, "total": 1, "eliminated": True},
            ],
            "route_key_labels": {"route_casa": "Casa", "route_lider": "Líder"},
            "unknown_routes": [],
            "scope_sizes": {"with_indicados": 8, "all_finalized": 8, "real_only": 7},
            "biggest_swing": {"name": "Brigido", "from_pct": 4.97, "to_pct": 77.88,
                              "swing_pp": 72.91, "from_paredao": 2, "to_paredao": 3},
            "bv_queen": {"name": "Jordana", "count": 2},
            "lider_favorite_target": {"name": "Milena", "count": 3},
        },
    }


@pytest.fixture
def sample_paredoes():
    return [
        {"numero": 1, "status": "finalizado",
         "indicados_finais": [{"nome": "Ana", "como": "Líder"}],
         "resultado": {"eliminado": "Ana", "votos": {"Ana": {"voto_total": 55.0}}}},
        {"numero": 2, "status": "finalizado",
         "indicados_finais": [{"nome": "Breno", "como": "Casa (3 votos)"}],
         "resultado": {"eliminado": "Breno", "votos": {"Breno": {"voto_total": 62.5}}}},
        {"numero": 3, "status": "em_andamento",
         "indicados_finais": [{"nome": "Caio", "como": "Contragolpe"}]},
    ]


# ── Pure renderer tests ─────────────────────────────────────────────────


class TestRenderMarkdown:

    def test_returns_string(self, sample_stats, sample_paredoes):
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert isinstance(result, str)

    def test_contains_section_heading(self, sample_stats, sample_paredoes):
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert "## Paredão Exposure Analysis" in result

    def test_contains_scope_table(self, sample_stats, sample_paredoes):
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert "`with_indicados`" in result
        assert "`real_only`" in result

    def test_contains_paredao_matrix(self, sample_stats, sample_paredoes):
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert "P1" in result
        assert "P2" in result
        assert "P3" in result
        assert "Ana" in result

    def test_em_andamento_shows_dashes(self, sample_stats, sample_paredoes):
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        # P3 has no resultado — should show dashes
        lines = result.split("\n")
        p3_line = next(l for l in lines if l.startswith("| P3"))
        assert "—" in p3_line

    def test_contains_route_effectiveness(self, sample_stats, sample_paredoes):
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert "Route Effectiveness" in result
        assert "Casa" in result

    def test_single_sample_routes_noted(self, sample_stats, sample_paredoes):
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert "n=1" in result
        assert "Big Fone" in result

    def test_route_labels_use_canonical_names(self, sample_stats, sample_paredoes):
        """Route labels must use canonical names (Líder not Lider)."""
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert "| Líder |" in result
        assert "| Lider |" not in result
        assert "| Casa |" in result

    def test_contains_bv_section(self, sample_stats, sample_paredoes):
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert "Bate-e-Volta" in result
        assert "18" in result  # bv_total_participants

    def test_contains_facts(self, sample_stats, sample_paredoes):
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert "Brigido" in result  # biggest swing
        assert "Jordana" in result  # BV champion
        assert "Milena" in result  # leader favorite

    def test_contains_fake_paredao_note(self, sample_stats, sample_paredoes):
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert "paredao_falso" in result

    def test_no_hardcoded_range(self, sample_stats, sample_paredoes):
        """Renderer must not hardcode P1-P8 or similar ranges."""
        result = render_paredao_exposure_docs_markdown(sample_stats, sample_paredoes)
        assert "P1–P8" not in result
        assert "P1-P8" not in result

    def test_empty_stats(self):
        result = render_paredao_exposure_docs_markdown(
            {"metrics": {}, "facts": {"scope_sizes": {}, "single_sample_routes": []}},
            [],
        )
        assert "## Paredão Exposure Analysis" in result


# ── Updater tests ────────────────────────────────────────────────────────


class TestUpdateDocsSection:

    def test_append_to_file_without_markers(self, tmp_path, sample_stats, sample_paredoes):
        doc = tmp_path / "test.md"
        doc.write_text("# Existing Content\n\nSome text.\n", encoding="utf-8")
        result = update_paredao_docs_section(sample_stats, sample_paredoes, doc)
        assert result is True
        content = doc.read_text()
        assert _MARKER_START in content
        assert _MARKER_END in content
        assert "# Existing Content" in content

    def test_replace_existing_markers(self, tmp_path, sample_stats, sample_paredoes):
        doc = tmp_path / "test.md"
        doc.write_text(
            f"# Header\n\n{_MARKER_START}\nold content\n{_MARKER_END}\n\n# Footer\n",
            encoding="utf-8",
        )
        result = update_paredao_docs_section(sample_stats, sample_paredoes, doc)
        assert result is True
        content = doc.read_text()
        assert "old content" not in content
        assert "Paredão Exposure Analysis" in content
        assert "# Footer" in content

    def test_idempotent_second_run(self, tmp_path, sample_stats, sample_paredoes):
        doc = tmp_path / "test.md"
        doc.write_text("# Header\n", encoding="utf-8")
        update_paredao_docs_section(sample_stats, sample_paredoes, doc)
        content_after_first = doc.read_text()
        result = update_paredao_docs_section(sample_stats, sample_paredoes, doc)
        assert result is False  # no change
        assert doc.read_text() == content_after_first

    def test_legacy_heading_migration(self, tmp_path, sample_stats, sample_paredoes):
        doc = tmp_path / "test.md"
        doc.write_text(
            "# Header\n\n## Paredão Exposure Analysis\n\nOld manual content here.\n\n## Next Section\n",
            encoding="utf-8",
        )
        result = update_paredao_docs_section(sample_stats, sample_paredoes, doc)
        assert result is True
        content = doc.read_text()
        assert _MARKER_START in content
        assert "Old manual content here." not in content
        assert "## Next Section" in content

    def test_legacy_migration_stops_at_h1(self, tmp_path, sample_stats, sample_paredoes):
        """Legacy migration must not delete content after an H1 heading."""
        doc = tmp_path / "test.md"
        doc.write_text(
            "# Header\n\n## Paredão Exposure Analysis\n\nOld content.\n\n# Appendix\n\nKeep this.\n",
            encoding="utf-8",
        )
        result = update_paredao_docs_section(sample_stats, sample_paredoes, doc)
        assert result is True
        content = doc.read_text()
        assert _MARKER_START in content
        assert "Old content." not in content
        assert "# Appendix" in content
        assert "Keep this." in content

    def test_legacy_migration_replaces_entire_h2_block_with_internal_h3(self, tmp_path, sample_stats, sample_paredoes):
        """Legacy migration should remove internal H3 content before next H2 section."""
        doc = tmp_path / "test.md"
        doc.write_text(
            "# Header\n\n## Paredão Exposure Analysis\n\nLegacy intro.\n\n### Legacy Subsection\n\nLegacy tail.\n\n## Next Section\n\nKeep this.\n",
            encoding="utf-8",
        )
        result = update_paredao_docs_section(sample_stats, sample_paredoes, doc)
        assert result is True
        content = doc.read_text()
        assert _MARKER_START in content
        assert "Legacy intro." not in content
        assert "### Legacy Subsection" not in content
        assert "Legacy tail." not in content
        assert "## Next Section" in content
        assert "Keep this." in content

    def test_creates_file_if_missing(self, tmp_path, sample_stats, sample_paredoes):
        doc = tmp_path / "nonexistent.md"
        result = update_paredao_docs_section(sample_stats, sample_paredoes, doc)
        assert result is True
        assert doc.exists()
        assert _MARKER_START in doc.read_text()

    def test_accepts_raw_paredoes_list(self, tmp_path, sample_paredoes):
        """Updater works with the raw paredões list format."""
        doc = tmp_path / "test.md"
        doc.write_text("# Header\n", encoding="utf-8")
        stats = {"metrics": {}, "facts": {"scope_sizes": {}, "single_sample_routes": []}}
        result = update_paredao_docs_section(stats, sample_paredoes, doc)
        assert result is True


# ── Shared helper tests ─────────────────────────────────────────────────


class TestSharedHelpers:

    def test_stable_json_hash_deterministic(self):
        obj = {"b": 2, "a": 1}
        h1 = stable_json_hash(obj)
        h2 = stable_json_hash(obj)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256

    def test_stable_json_hash_key_order_independent(self):
        assert stable_json_hash({"a": 1, "b": 2}) == stable_json_hash({"b": 2, "a": 1})

    def test_read_json_if_exists_missing(self, tmp_path):
        assert read_json_if_exists(tmp_path / "nope.json") is None

    def test_read_json_if_exists_valid(self, tmp_path):
        p = tmp_path / "test.json"
        p.write_text('{"key": "val"}')
        result = read_json_if_exists(p)
        assert result == {"key": "val"}
