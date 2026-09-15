"""Acceptance-criteria tests for build_search_query and search_pubmed in pubmed_search.py."""

import pytest

from pico_pubmed_rag.pubmed_search import build_search_query, search_pubmed


@pytest.fixture
def sample_pico():
    return {
        "population": "adults with strep throat",
        "intervention": "amoxicillin",
        "comparison": "penicillin",
        "outcome": "symptom resolution",
    }


@pytest.fixture
def fake_http_get():
    def _fake_http_get(query):
        return {"esearchresult": {"idlist": ["12345", "23456", "34567"]}}

    return _fake_http_get


@pytest.fixture
def empty_http_get():
    def _empty_http_get(query):
        return {"esearchresult": {"idlist": []}}

    return _empty_http_get


@pytest.fixture
def malformed_http_get():
    def _malformed_http_get(query):
        return {"esearchresult": "some_error"}

    return _malformed_http_get


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


def test_search_pubmed_returns_list_of_pmids(fake_http_get):
    result = search_pubmed("some query", fake_http_get)
    assert result == ["12345", "23456", "34567"]


def test_search_pubmed_returns_empty_pmids_list(empty_http_get):
    result = search_pubmed("some_query", empty_http_get)
    assert result == []


def test_search_pubmed_returns_malformed_response(malformed_http_get):
    with pytest.raises(ValueError):
        search_pubmed("some_query", malformed_http_get)
