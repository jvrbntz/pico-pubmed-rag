"""Acceptance-criteria tests for build_search_query in pubmed_search.py."""

import pytest

from pico_pubmed_rag.pubmed_search import build_search_query


@pytest.fixture
def sample_pico():
    return {
        "population": "adults with strep throat",
        "intervention": "amoxicillin",
        "comparison": "penicillin",
        "outcome": "symptom resolution",
    }


def test_build_search_query_returns_string(sample_pico):
    result = build_search_query(sample_pico)
    assert isinstance(result, str)


def test_build_search_query_includes_population_and_intervention(sample_pico):
    result = build_search_query(sample_pico)
    assert sample_pico["population"] in result
    assert sample_pico["intervention"] in result


def test_build_search_query_joins_population_and_intervention_with_and(sample_pico):
    result = build_search_query(sample_pico)
    assert f"{sample_pico['population']} AND {sample_pico['intervention']}" in result


def test_build_search_query_includes_publication_type_filter(sample_pico):
    result = build_search_query(sample_pico)
    assert "(Randomized Controlled Trial[pt] OR Systematic Review[pt])" in result
