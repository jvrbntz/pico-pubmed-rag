"""Acceptance-criteria tests for generate_pico_candidates in pico_generation.py."""

import json

import pytest

from pico_pubmed_rag.pico_generation import generate_pico_candidates


@pytest.fixture
def fake_llm_call():
    def _fake_llm_call(prompt):
        return json.dumps(
            [
                {
                    "population": "adult patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": "penicillin",
                    "outcome": "symptom resolution",
                },
                {
                    "population": "pediatric patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": "watchful waiting",
                    "outcome": "symptom resolution",
                },
            ]
        )

    return _fake_llm_call


@pytest.fixture
def duplicate_llm_call():
    def _duplicate_llm_call(prompt):
        return json.dumps(
            [
                {
                    "population": "adult patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": "penicillin",
                    "outcome": "symptom resolution",
                },
                {
                    "population": "adult patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": "watchful waiting",
                    "outcome": "symptoms not resolved timely",
                },
            ]
        )

    return _duplicate_llm_call


@pytest.fixture
def out_of_bounds_llm_call():
    def _out_of_bounds_llm_call(prompt):
        return json.dumps(
            [
                {
                    "population": "p1",
                    "intervention": "i1",
                    "comparison": "c1",
                    "outcome": "o1",
                },
                {
                    "population": "p2",
                    "intervention": "i2",
                    "comparison": "c2",
                    "outcome": "o2",
                },
                {
                    "population": "p3",
                    "intervention": "i3",
                    "comparison": "c3",
                    "outcome": "o3",
                },
                {
                    "population": "p4",
                    "intervention": "i4",
                    "comparison": "c4",
                    "outcome": "o4",
                },
                {
                    "population": "p5",
                    "intervention": "i5",
                    "comparison": "c5",
                    "outcome": "o5",
                },
                {
                    "population": "p6",
                    "intervention": "i6",
                    "comparison": "c6",
                    "outcome": "o6",
                },
                {
                    "population": "p7",
                    "intervention": "i7",
                    "comparison": "c7",
                    "outcome": "o7",
                },
            ]
        )

    return _out_of_bounds_llm_call


@pytest.fixture
def malformed_json_llm_call():
    def _malformed_json_llm_call(prompt):
        return "not valid json"

    return _malformed_json_llm_call


@pytest.fixture
def wrong_keys_llm_call():
    def _wrong_keys_llm_call(prompt):
        return json.dumps(
            [
                {
                    "population": "adult patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": "penicillin",
                    "outcome": "symptom resolution",
                },
                {
                    "population": "pediatric patients with strep throat",
                    "intervention": "amoxicillin",
                    "rationale": "children respond well to amoxicillin",
                },
            ]
        )

    return _wrong_keys_llm_call


def test_generate_pico_candidates_returns_two_four_candidates(fake_llm_call):
    result = generate_pico_candidates("case text", fake_llm_call)

    assert 2 <= len(result) <= 4


def test_generate_pico_candidates_raises_on_duplicates(duplicate_llm_call):
    with pytest.raises(ValueError):
        generate_pico_candidates("case text", duplicate_llm_call)


def test_generate_pico_candidates_returns_formatted_output(fake_llm_call):
    result = generate_pico_candidates("case text", fake_llm_call)

    for pico_candidate in result:
        assert set(pico_candidate.keys()) == {
            "population",
            "intervention",
            "comparison",
            "outcome",
        }


def test_generate_pico_candidates_raises_on_out_of_bounds_count(out_of_bounds_llm_call):
    with pytest.raises(ValueError):
        generate_pico_candidates("case text", out_of_bounds_llm_call)


def test_generate_pico_candidates_raises_on_malformed_json(malformed_json_llm_call):
    with pytest.raises(ValueError):
        generate_pico_candidates("case text", malformed_json_llm_call)


def test_generate_pico_candidates_raises_on_wrong_keys(wrong_keys_llm_call):
    with pytest.raises(ValueError):
        generate_pico_candidates("case text", wrong_keys_llm_call)
