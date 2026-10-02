"""Acceptance-criteria tests for build_search_terms_prompt and extract_search_terms in search_terms.py."""

import json

import pytest

from pico_pubmed_rag.search_terms import (
    EXAMPLE_SEARCH_TERMS,
    build_search_terms_prompt,
    extract_search_terms,
)

SELECTED_PICO = {
    "population": "adults with symptomatic degenerative knee arthritis requiring surgery",
    "intervention": "total left knee replacement",
    "comparison": "conservative management",
    "outcome": "pain relief",
}


def test_extracts_valid_terms_from_reasoning_text():
    terms = {"population_terms": "knee osteoarthritis", "intervention_terms": "total knee replacement"}
    response = "<unused94>thought\nThe core condition is osteoarthritis.<unused95>```json\n" + json.dumps(terms) + "\n```"

    result = extract_search_terms(SELECTED_PICO, lambda prompt: response)

    assert result == terms


def respond_with(population_terms, intervention_terms):
    response = json.dumps({"population_terms": population_terms, "intervention_terms": intervention_terms})
    return lambda prompt: response


def test_accepts_four_words_and_rejects_five():
    four = extract_search_terms(SELECTED_PICO, respond_with("severe knee osteoarthritis adults", "knee replacement"))
    assert four["population_terms"] == "severe knee osteoarthritis adults"

    with pytest.raises(ValueError):
        extract_search_terms(SELECTED_PICO, respond_with("older adults with knee osteoarthritis", "knee replacement"))


@pytest.mark.parametrize(
    "population_terms, intervention_terms",
    [("64-year-old women", "hysterectomy"), ("prostate cancer", "iodine-125 brachytherapy")],
)
def test_rejects_terms_containing_digits(population_terms, intervention_terms):
    with pytest.raises(ValueError):
        extract_search_terms(SELECTED_PICO, respond_with(population_terms, intervention_terms))


def test_rejects_missing_or_empty_terms():
    missing_key = json.dumps({"population_terms": "knee osteoarthritis"})
    with pytest.raises(ValueError):
        extract_search_terms(SELECTED_PICO, lambda prompt: missing_key)

    with pytest.raises(ValueError):
        extract_search_terms(SELECTED_PICO, respond_with("knee osteoarthritis", "  "))


@pytest.mark.parametrize(
    "response",
    [
        "I could not determine search terms for this question.",
        '["knee osteoarthritis", "total knee replacement"]',
        '{"population_terms": "knee osteoarthritis", "intervention_terms": "knee replacement", "comparison_terms": "physical therapy"}',
    ],
)
def test_rejects_malformed_responses(response):
    with pytest.raises(ValueError):
        extract_search_terms(SELECTED_PICO, lambda prompt: response)


@pytest.mark.parametrize(
    "population_terms",
    ["uterine fibroids (symptomatic)", "chest pain OR angina", 'knee "osteoarthritis"', "neck pain/radiculopathy"],
)
def test_rejects_terms_with_pubmed_boolean_syntax(population_terms):
    with pytest.raises(ValueError):
        extract_search_terms(SELECTED_PICO, respond_with(population_terms, "knee replacement"))


def test_accepts_ordinary_words_that_resemble_operators():
    result = extract_search_terms(SELECTED_PICO, respond_with("head and neck cancer", "radiotherapy"))
    assert result["population_terms"] == "head and neck cancer"

    result = extract_search_terms(SELECTED_PICO, respond_with("Crohn's disease", "infliximab"))
    assert result["population_terms"] == "Crohn's disease"


def test_prompt_contains_the_pico_the_rules_and_the_example():
    prompt = build_search_terms_prompt(SELECTED_PICO)

    for value in SELECTED_PICO.values():
        assert value in prompt
    for rule in ["1 to 4 words", "digits", "brand names", "laterality"]:
        assert rule in prompt
    for example_term in EXAMPLE_SEARCH_TERMS.values():
        assert example_term in prompt
