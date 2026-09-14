"""Acceptance-criteria tests for select_pico in pico_selection.py."""

from pico_pubmed_rag.pico_selection import select_pico


def test_select_pico_first_candidate():
    candidates = [
        {"population": "p1", "intervention": "i1", "comparison": "c1", "outcome": "o1"},
        {"population": "p2", "intervention": "i2", "comparison": "c2", "outcome": "o2"},
    ]

    assert select_pico(candidates) == candidates[0]
