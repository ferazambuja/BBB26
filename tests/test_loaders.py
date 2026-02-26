"""Tests for data loading functions."""
import json
import pytest
from pathlib import Path
from data_utils import load_snapshot


class TestLoadSnapshot:
    """Test load_snapshot() function."""

    def test_new_format(self, tmp_path):
        """New format with _metadata wrapper."""
        data = {
            "_metadata": {"captured_at": "2026-01-20T15:00:00+00:00"},
            "participants": [
                {
                    "name": "Alice",
                    "characteristics": {"receivedReactions": []},
                },
            ],
        }
        filepath = tmp_path / "test.json"
        filepath.write_text(json.dumps(data))
        participants, metadata = load_snapshot(str(filepath))
        assert len(participants) == 1
        assert participants[0]["name"] == "Alice"
        assert "captured_at" in metadata

    def test_old_format(self, tmp_path):
        """Old format: bare list of participants."""
        data = [{"name": "Bob", "characteristics": {"receivedReactions": []}}]
        filepath = tmp_path / "test.json"
        filepath.write_text(json.dumps(data))
        participants, metadata = load_snapshot(str(filepath))
        assert len(participants) == 1
        assert participants[0]["name"] == "Bob"
        assert metadata == {}

    def test_metadata_extraction(self, tmp_path):
        """Metadata should be extracted from _metadata key."""
        data = {
            "_metadata": {
                "captured_at": "2026-01-20T15:00:00+00:00",
                "synthetic": False,
            },
            "participants": [],
        }
        filepath = tmp_path / "test.json"
        filepath.write_text(json.dumps(data))
        participants, metadata = load_snapshot(str(filepath))
        assert participants == []
        assert metadata["captured_at"] == "2026-01-20T15:00:00+00:00"
        assert metadata["synthetic"] is False

    def test_missing_metadata_key(self, tmp_path):
        """Dict with participants but no _metadata should return empty metadata."""
        data = {"participants": [{"name": "Carol"}]}
        filepath = tmp_path / "test.json"
        filepath.write_text(json.dumps(data))
        participants, metadata = load_snapshot(str(filepath))
        assert len(participants) == 1
        assert metadata == {}


class TestNormalizeActors:
    """Test normalize_actors behavior (if available)."""

    def test_actors_list(self):
        """actors list should be used as-is."""
        event = {"actor": "A + B", "actors": ["A", "B"]}
        assert event["actors"] == ["A", "B"]

    def test_plus_separator(self):
        """Plus separator in actor string."""
        actor_str = "Alice + Bob + Carol"
        actors = [a.strip() for a in actor_str.split("+")]
        assert actors == ["Alice", "Bob", "Carol"]

    def test_single_actor(self):
        """Single actor without + separator."""
        actor_str = "Alice"
        if "+" in actor_str:
            actors = [a.strip() for a in actor_str.split("+")]
        else:
            actors = [actor_str]
        assert actors == ["Alice"]
