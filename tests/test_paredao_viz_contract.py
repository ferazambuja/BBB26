"""Contracts for the paredao_viz module surface."""

from __future__ import annotations

import ast
from collections import Counter
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
PAREDAO_VIZ = REPO_ROOT / "scripts" / "paredao_viz.py"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from paredao_viz import (
    build_formacao_curiosidades_items,
    build_nominee_related_relationship_narratives,
    build_poll_insights_blocks,
    ensure_live_context_block_items,
    ensure_live_poll_progress_items,
    render_poll_insights_blocks,
)


def test_paredao_viz_has_no_duplicate_top_level_function_names():
    tree = ast.parse(PAREDAO_VIZ.read_text(encoding="utf-8"))
    names = [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]
    duplicates = sorted(name for name, count in Counter(names).items() if count > 1)
    assert not duplicates, f"duplicate top-level function names: {duplicates}"


def test_build_poll_insights_blocks_skips_empty_items_and_blocks():
    payload = build_poll_insights_blocks(
        {
            "title_html": "Live signals",
            "items": [
                "Simple line",
                None,
                "",
                {"title_html": "", "bullets_html": [""]},
                {
                    "title_html": "<strong>Momentum</strong>",
                    "bullets_html": ["Closing fast", "", None],
                },
            ],
        },
        {"title_html": "", "items": ["Missing block title should skip"]},
        {"title_html": "Archive signals", "items": []},
        None,
    )

    assert payload == [
        {
            "title_html": "Live signals",
            "items": [
                "Simple line",
                {
                    "title_html": "<strong>Momentum</strong>",
                    "bullets_html": ["Closing fast"],
                },
            ],
        }
    ]


def test_build_poll_insights_blocks_flattens_mixed_positional_block_containers():
    live_block = {"title_html": "Live signals", "items": ["Simple line"]}
    archive_block = {"title_html": "Archive signals", "items": ["Historical context"]}
    extra_block = {"title_html": "Extra signals", "items": ["Third block"]}

    payload = build_poll_insights_blocks([live_block], archive_block, (extra_block,), None)

    assert payload == [
        {"title_html": "Live signals", "items": ["Simple line"]},
        {"title_html": "Archive signals", "items": ["Historical context"]},
        {"title_html": "Extra signals", "items": ["Third block"]},
    ]


def test_build_poll_insights_blocks_accepts_tuple_bullets_as_fragments():
    payload = build_poll_insights_blocks(
        {
            "title_html": "Live signals",
            "items": [
                {
                    "title_html": "<strong>Momentum</strong>",
                    "bullets_html": ("Closing fast", "Leader still ahead"),
                }
            ],
        }
    )

    assert payload == [
        {
            "title_html": "Live signals",
            "items": [
                {
                    "title_html": "<strong>Momentum</strong>",
                    "bullets_html": ["Closing fast", "Leader still ahead"],
                }
            ],
        }
    ]


def test_build_formacao_curiosidades_items_supports_strings_and_tolerant_object_keys():
    payload = build_formacao_curiosidades_items(
        [
            "Leitura manual simples",
            {
                "title": "Mudanças da dinâmica",
                "bullets": ["Ordem alterada", "", None],
            },
            {
                "titulo": "Nota extra",
                "items": "Big Fone sem imunidade",
            },
            {
                "title": "",
                "bullets": ["Deve pular"],
            },
            {
                "title": "Sem bullets",
                "bullets": [],
            },
            None,
        ]
    )

    assert payload == [
        "Leitura manual simples",
        {
            "title_html": "Mudanças da dinâmica",
            "bullets_html": ["Ordem alterada"],
        },
        {
            "title_html": "Nota extra",
            "bullets_html": ["Big Fone sem imunidade"],
        },
    ]


def test_build_nominee_related_relationship_narratives_keeps_only_edges_targeting_current_nominees():
    bullets = build_nominee_related_relationship_narratives(
        nominees=["Ana Paula Renault", "Breno", "Leandro"],
        relationship_history={
            "Marciele→Solange Couto": {
                "change_date": "2026-03-15",
                "narrative": "Unrelated but most recent.",
            },
            "Alberto Cowboy→Breno": {
                "change_date": "2026-03-15",
                "narrative": "Recent nominee-related edge.",
            },
            "Jonas Sulzbach→Solange Couto": {
                "change_date": "2026-03-14",
                "narrative": "Still unrelated.",
            },
            "Ana Paula Renault→Solange Couto": {
                "change_date": "2026-02-24",
                "narrative": "Outgoing nominee edge that should drop.",
            },
            "Breno→Marciele": {
                "change_date": "2026-02-15",
                "narrative": "Another outgoing nominee edge that should drop.",
            },
            "Marciele→Ana Paula Renault": {
                "change_date": "2026-02-20",
                "narrative": "Older target-nominee edge.",
            },
        },
        limit=2,
    )

    assert bullets == [
        "<strong>Alberto Cowboy→Breno</strong>: Recent nominee-related edge.",
        "<strong>Marciele→Ana Paula Renault</strong>: Older target-nominee edge.",
    ]


def test_ensure_live_context_block_items_adds_fallback_when_context_is_empty():
    items = ensure_live_context_block_items(
        [
            None,
            "",
            {"title_html": "", "bullets_html": [""]},
        ]
    )

    assert items == [
        "<strong>Contexto em formação</strong>: histórico recente, alinhamentos e notas manuais aparecem aqui assim que houver sinais suficientes deste paredão."
    ]


def test_live_summary_contract_keeps_two_blocks_before_first_poll():
    payload = build_poll_insights_blocks(
        {
            "title_html": "📈 Progresso das enquetes",
            "items": ensure_live_poll_progress_items([], has_poll=False),
        },
        {
            "title_html": "🧩 Contexto do paredão",
            "items": ensure_live_context_block_items([]),
        },
    )

    assert [block["title_html"] for block in payload] == [
        "📈 Progresso das enquetes",
        "🧩 Contexto do paredão",
    ]
    assert "Votalhada ainda não publicou" in str(payload[0]["items"][0])
    assert "Contexto em formação" in str(payload[1]["items"][0])


def test_render_poll_insights_blocks_supports_two_blocks_and_nested_bullets():
    payload = build_poll_insights_blocks(
        {
            "title_html": "Live signals",
            "items": [
                "Simple line with <strong>markup</strong>",
                {
                    "title_html": "<strong>Momentum</strong>",
                    "bullets_html": ["Closing fast", "Leader still ahead"],
                },
            ],
        },
        {
            "title_html": "Archive signals",
            "items": ["Historical context"],
        },
    )

    html = render_poll_insights_blocks(payload)

    assert 'class="poll-insights-blocks"' in html
    assert html.count('class="poll-insights"') == 2
    assert html.count('class="poll-insights-list"') == 2
    assert "Live signals" in html
    assert "Archive signals" in html
    assert "Simple line with <strong>markup</strong>" in html
    assert 'class="poll-insights-item-title"' in html
    assert 'class="poll-insights-sublist"' in html
    assert "<strong>Momentum</strong>" in html
    assert "Closing fast" in html
    assert "Leader still ahead" in html
