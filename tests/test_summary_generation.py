"""Acceptance-criteria tests for build_summary_prompt and generate_summary in summary_generation.py."""

import pytest

from pico_pubmed_rag.summary_generation import build_summary_prompt, generate_summary


@pytest.fixture
def sample_pico():
    return {
        "population": "adults with strep throat",
        "intervention": "amoxicillin",
        "comparison": "penicillin",
        "outcome": "symptom resolution",
    }


@pytest.fixture
def sample_abstracts():
    return [
        {
            "pmid": "12345678",
            "title": "Amoxicillin versus penicillin for strep throat",
            "text": "A randomized trial comparing outcomes between amoxicillin and penicillin.",
            "publication_type": ["Journal Article", "Randomized Controlled Trial"],
            "publication_date": "2019",
        },
        {
            "pmid": "23456789",
            "title": "Watchful waiting versus antibiotics for strep throat",
            "text": "A systematic review of watchful waiting versus immediate antibiotic treatment.",
            "publication_type": ["Journal Article", "Systematic Review"],
            "publication_date": "2021",
        },
    ]


@pytest.fixture
def fake_summary_llm_call():
    def _fake_summary_llm_call(prompt):
        return (
            "Evidence Summary: Amoxicillin and penicillin show comparable "
            "effectiveness for treating strep throat (PMID: 12345678)."
        )

    return _fake_summary_llm_call


@pytest.fixture
def summary_missing_label_llm_call():
    def _summary_missing_label_llm_call(prompt):
        return (
            "Amoxicillin and penicillin show comparable effectiveness for "
            "treating strep throat (PMID: 12345678)."
        )

    return _summary_missing_label_llm_call


@pytest.fixture
def summary_missing_pmid_llm_call():
    def _summary_missing_pmid_llm_call(prompt):
        return (
            "Evidence Summary: Amoxicillin and penicillin show comparable "
            "effectiveness for treating strep throat."
        )

    return _summary_missing_pmid_llm_call


@pytest.fixture
def llm_call_should_not_be_called():
    def _llm_call_should_not_be_called(prompt):
        raise AssertionError("llm_call should not have been called with no abstracts")

    return _llm_call_should_not_be_called


@pytest.fixture
def summary_with_reasoning_trace_llm_call():
    def _summary_with_reasoning_trace_llm_call(prompt):
        return (
            "<unused94>thought\nSome internal reasoning here...\n<unused95>"
            "Evidence Summary: Amoxicillin and penicillin show comparable "
            "effectiveness for treating strep throat (PMID: 12345678)."
        )

    return _summary_with_reasoning_trace_llm_call


@pytest.fixture
def summary_no_clear_answer_llm_call():
    def _summary_no_clear_answer_llm_call(prompt):
        return (
            "No Clear Answer: None of the provided abstracts address this "
            "specific comparison, so no answer can be given from this evidence."
        )

    return _summary_no_clear_answer_llm_call


@pytest.fixture
def summary_both_labels_llm_call():
    def _summary_both_labels_llm_call(prompt):
        return (
            "Evidence Summary:\nNo Clear Answer:\nNone of the provided abstracts "
            "address this specific comparison, so no answer can be given."
        )

    return _summary_both_labels_llm_call


@pytest.fixture
def llm_call_fails_once_then_succeeds():
    call_count = {"count": 0}

    def _llm_call(prompt):
        call_count["count"] += 1
        if call_count["count"] == 1:
            return "Evidence Summary: no PMID citation on this attempt."
        return (
            "Evidence Summary: Amoxicillin and penicillin show comparable "
            "effectiveness for treating strep throat (PMID: 12345678)."
        )

    return _llm_call


def test_build_summary_prompt_returns_string(sample_pico, sample_abstracts):
    result = build_summary_prompt(sample_pico, sample_abstracts)
    assert isinstance(result, str)


def test_build_summary_prompt_includes_pico_and_abstracts(
    sample_pico, sample_abstracts
):
    result = build_summary_prompt(sample_pico, sample_abstracts)
    assert sample_pico["population"] in result
    assert sample_pico["intervention"] in result
    for abstract in sample_abstracts:
        assert abstract["pmid"] in result
        assert abstract["title"] in result
        assert abstract["text"] in result


def test_build_summary_prompt_includes_citation_instructions(
    sample_pico, sample_abstracts
):
    result = build_summary_prompt(sample_pico, sample_abstracts)
    for phrase in [
        "PMID",
        "Evidence Summary:",
        "not a diagnosis or treatment recommendation",
    ]:
        assert phrase in result


def test_generate_summary_returns_string(
    sample_pico, sample_abstracts, fake_summary_llm_call
):
    result = generate_summary(sample_pico, sample_abstracts, fake_summary_llm_call)
    assert isinstance(result, str)


def test_generate_summary_raises_on_missing_label(
    sample_pico, sample_abstracts, summary_missing_label_llm_call
):
    with pytest.raises(ValueError):
        generate_summary(sample_pico, sample_abstracts, summary_missing_label_llm_call)


def test_generate_summary_raises_on_missing_pmid(
    sample_pico, sample_abstracts, summary_missing_pmid_llm_call
):
    with pytest.raises(ValueError):
        generate_summary(sample_pico, sample_abstracts, summary_missing_pmid_llm_call)


def test_generate_summary_raises_immediately_on_empty_abstracts(
    sample_pico, llm_call_should_not_be_called
):
    with pytest.raises(ValueError):
        generate_summary(sample_pico, [], llm_call_should_not_be_called)


def test_generate_summary_strips_reasoning_trace(
    sample_pico, sample_abstracts, summary_with_reasoning_trace_llm_call
):
    result = generate_summary(
        sample_pico, sample_abstracts, summary_with_reasoning_trace_llm_call
    )
    assert "<unused94>" not in result
    assert "<unused95>" not in result
    assert result.startswith("Evidence Summary:")


def test_generate_summary_accepts_no_clear_answer_without_pmid(
    sample_pico, sample_abstracts, summary_no_clear_answer_llm_call
):
    result = generate_summary(
        sample_pico, sample_abstracts, summary_no_clear_answer_llm_call
    )
    assert result.startswith("No Clear Answer:")


def test_generate_summary_accepts_no_clear_answer_even_with_both_labels(
    sample_pico, sample_abstracts, summary_both_labels_llm_call
):
    result = generate_summary(
        sample_pico, sample_abstracts, summary_both_labels_llm_call
    )
    assert "No Clear Answer:" in result


def test_generate_summary_retries_once_on_validation_failure(
    sample_pico, sample_abstracts, llm_call_fails_once_then_succeeds
):
    result = generate_summary(
        sample_pico, sample_abstracts, llm_call_fails_once_then_succeeds
    )
    assert "12345678" in result
