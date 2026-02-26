"""Shared fixtures for BBB26 tests."""
import json
import pytest
from pathlib import Path


@pytest.fixture
def sample_participant():
    """Single participant matching real API format (characteristics wrapper)."""
    return {
        "id": "1",
        "name": "Test User",
        "avatar": "https://example.com/avatar.jpg",
        "characteristics": {
            "group": "Vip",
            "memberOf": "Pipoca",
            "balance": 500,
            "roles": [],
            "mainRole": None,
            "eliminated": False,
            "receivedReactions": [
                {
                    "label": "Coração",
                    "amount": 2,
                    "participants": [
                        {"id": "2", "name": "Friend A"},
                        {"id": "3", "name": "Friend B"},
                    ],
                },
                {
                    "label": "Cobra",
                    "amount": 1,
                    "participants": [
                        {"id": "4", "name": "Enemy A"},
                    ],
                },
                {
                    "label": "Planta",
                    "amount": 1,
                    "participants": [
                        {"id": "5", "name": "Neutral A"},
                    ],
                },
            ],
        },
    }


@pytest.fixture
def sample_participants():
    """4 participants with cross-reactions for matrix testing (real API format)."""
    return [
        {
            "name": "Alice",
            "characteristics": {
                "roles": [],
                "group": "Vip",
                "memberOf": "Pipoca",
                "eliminated": False,
                "balance": 500,
                "receivedReactions": [
                    {
                        "label": "Coração",
                        "amount": 2,
                        "participants": [
                            {"id": "2", "name": "Bob"},
                            {"id": "3", "name": "Carol"},
                        ],
                    },
                    {
                        "label": "Cobra",
                        "amount": 1,
                        "participants": [
                            {"id": "4", "name": "Dave"},
                        ],
                    },
                ],
            },
        },
        {
            "name": "Bob",
            "characteristics": {
                "roles": [],
                "group": "Vip",
                "memberOf": "Pipoca",
                "eliminated": False,
                "balance": 500,
                "receivedReactions": [
                    {
                        "label": "Coração",
                        "amount": 1,
                        "participants": [
                            {"id": "1", "name": "Alice"},
                        ],
                    },
                    {
                        "label": "Planta",
                        "amount": 1,
                        "participants": [
                            {"id": "3", "name": "Carol"},
                        ],
                    },
                    {
                        "label": "Alvo",
                        "amount": 1,
                        "participants": [
                            {"id": "4", "name": "Dave"},
                        ],
                    },
                ],
            },
        },
        {
            "name": "Carol",
            "characteristics": {
                "roles": [],
                "group": "Xepa",
                "memberOf": "Veterano",
                "eliminated": False,
                "balance": 800,
                "receivedReactions": [
                    {
                        "label": "Coração",
                        "amount": 3,
                        "participants": [
                            {"id": "1", "name": "Alice"},
                            {"id": "2", "name": "Bob"},
                            {"id": "4", "name": "Dave"},
                        ],
                    },
                ],
            },
        },
        {
            "name": "Dave",
            "characteristics": {
                "roles": [],
                "group": "Xepa",
                "memberOf": "Veterano",
                "eliminated": False,
                "balance": 300,
                "receivedReactions": [
                    {
                        "label": "Cobra",
                        "amount": 2,
                        "participants": [
                            {"id": "1", "name": "Alice"},
                            {"id": "2", "name": "Bob"},
                        ],
                    },
                    {
                        "label": "Coração",
                        "amount": 1,
                        "participants": [
                            {"id": "3", "name": "Carol"},
                        ],
                    },
                ],
            },
        },
    ]


@pytest.fixture
def real_snapshot():
    """Load first available real snapshot (integration test)."""
    snapshots_dir = Path("data/snapshots")
    if not snapshots_dir.exists():
        pytest.skip("No snapshots directory available")
    files = sorted(snapshots_dir.glob("*.json"))
    if not files:
        pytest.skip("No snapshot files available")
    with open(files[0], encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "participants" in data:
        return data["participants"]
    return data
