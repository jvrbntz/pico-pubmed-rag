"""Acceptance-criteria tests for rank_abstracts in abstract_ranking.py."""

import pytest

from pico_pubmed_rag.abstract_ranking import rank_abstracts


@pytest.fixture
def sample_abstracts():
    return [
        {
            "pmid": "1",
            "title": "RCT, newer",
            "text": "...",
            "publication_type": ["Journal Article", "Randomized Controlled Trial"],
            "publication_date": "2020",
        },
        {
            "pmid": "2",
            "title": "Case report, newest",
            "text": "...",
            "publication_type": ["Journal Article", "Case Reports"],
            "publication_date": "2023",
        },
        {
            "pmid": "3",
            "title": "Systematic review, older",
            "text": "...",
            "publication_type": ["Journal Article", "Systematic Review"],
            "publication_date": "2018",
        },
        {
            "pmid": "4",
            "title": "Case report, oldest",
            "text": "...",
            "publication_type": ["Journal Article", "Case Reports"],
            "publication_date": "2015",
        },
    ]


def test_rank_abstracts_returns_rank_order(sample_abstracts):
    result = rank_abstracts(sample_abstracts)

    assert [abstract["pmid"] for abstract in result] == ["1", "3", "2", "4"]
