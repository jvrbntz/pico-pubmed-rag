"""Acceptance-criteria tests for run_pipeline in pipeline_run.py."""

import pandas as pd
import pytest

from pico_pubmed_rag.pipeline_run import run_pipeline

RUN_METADATA = {"git_commit": "abc123"}


@pytest.fixture
def empty_dataset():
    return pd.DataFrame(columns=["case_id", "transcription"])


@pytest.fixture
def dataset_with_case_87():
    return pd.DataFrame(
        [{"case_id": 87, "transcription": "A synthetic case note for testing."}]
    )


@pytest.fixture
def model_call_should_not_be_called():
    def _model_call(prompt):
        raise AssertionError("model call should not have been called")

    return _model_call


@pytest.fixture
def search_call_should_not_be_called():
    def _search_call(query):
        raise AssertionError("search call should not have been called")

    return _search_call


@pytest.fixture
def fetch_call_should_not_be_called():
    def _fetch_call(pmids):
        raise AssertionError("fetch call should not have been called")

    return _fetch_call


@pytest.fixture
def pico_response_not_json_llm_call():
    def _model_call(prompt):
        return "not json"

    return _model_call


@pytest.fixture
def pico_response_missing_outcome_llm_call():
    def _model_call(prompt):
        return (
            '[{"population": "adults with strep throat", "intervention": "amoxicillin", '
            '"comparison": "penicillin"}, '
            '{"population": "adults with strep throat", "intervention": "watchful waiting", '
            '"comparison": "amoxicillin", "outcome": "complication rate"}]'
        )

    return _model_call


@pytest.fixture
def valid_pico_llm_call():
    def _model_call(prompt):
        return (
            '[{"population": "adults with type 2 diabetes", "intervention": "metformin", '
            '"comparison": "sulfonylurea", "outcome": "HbA1c reduction"}, '
            '{"population": "adults with type 2 diabetes", "intervention": "lifestyle modification", '
            '"comparison": "metformin", "outcome": "weight loss"}]'
        )

    return _model_call


@pytest.fixture
def search_call_strict_empty_broadened_hits():
    def _search_call(query):
        if "Randomized Controlled Trial[pt]" in query:
            idlist = []
        else:
            idlist = ["1234567", "2345678", "3456789"]
        return {"esearchresult": {"idlist": idlist}}

    return _search_call


@pytest.fixture
def search_call_strict_hits():
    def _search_call(query):
        return {"esearchresult": {"idlist": ["1234567", "2345678", "3456789"]}}

    return _search_call


def test_unknown_case_id_fails_without_raising(
    empty_dataset,
    model_call_should_not_be_called,
    search_call_should_not_be_called,
    fetch_call_should_not_be_called,
):
    trace = run_pipeline(
        case_id=999,
        dataset=empty_dataset,
        model_call=model_call_should_not_be_called,
        search_call=search_call_should_not_be_called,
        fetch_call=fetch_call_should_not_be_called,
        run_metadata=RUN_METADATA,
    )

    assert trace["run_outcome"] == "failed"

    load_case_record = trace["stages"]["load_case"]
    assert load_case_record["status"] == "failed"
    assert load_case_record["failure_tag"] == "unexpected"
    assert load_case_record["failure_type"] == "KeyError"
    assert load_case_record["traceback"]

    other_stages = [
        "generate_pico_candidates",
        "select_pico",
        "build_search_query",
        "search",
        "fetch",
        "parse",
        "rank",
        "generate_summary",
    ]
    for stage_name in other_stages:
        assert trace["stages"][stage_name]["status"] == "skipped"
        assert trace["stages"][stage_name]["skip_reason"]


def test_pico_validation_failure_on_unparseable_response(
    dataset_with_case_87,
    pico_response_not_json_llm_call,
    search_call_should_not_be_called,
    fetch_call_should_not_be_called,
):
    trace = run_pipeline(
        case_id=87,
        dataset=dataset_with_case_87,
        model_call=pico_response_not_json_llm_call,
        search_call=search_call_should_not_be_called,
        fetch_call=fetch_call_should_not_be_called,
        run_metadata=RUN_METADATA,
    )

    assert trace["run_outcome"] == "failed"

    pico_record = trace["stages"]["generate_pico_candidates"]
    assert pico_record["status"] == "failed"
    assert pico_record["failure_tag"] == "validation"

    for stage_name in [
        "select_pico",
        "build_search_query",
        "search",
        "fetch",
        "parse",
        "rank",
        "generate_summary",
    ]:
        assert trace["stages"][stage_name]["status"] == "skipped"


def test_search_records_both_queries_when_broadened(
    dataset_with_case_87,
    valid_pico_llm_call,
    search_call_strict_empty_broadened_hits,
    fetch_call_should_not_be_called,
):
    trace = run_pipeline(
        case_id=87,
        dataset=dataset_with_case_87,
        model_call=valid_pico_llm_call,
        search_call=search_call_strict_empty_broadened_hits,
        fetch_call=fetch_call_should_not_be_called,
        run_metadata=RUN_METADATA,
    )

    search_record = trace["stages"]["search"]
    assert search_record["status"] == "succeeded"

    call_records = search_record["call_records"]
    assert len(call_records) == 2

    assert "Randomized Controlled Trial[pt]" in call_records[0]["query"]
    assert call_records[0]["response"] == {"esearchresult": {"idlist": []}}

    assert "Randomized Controlled Trial[pt]" not in call_records[1]["query"]
    assert call_records[1]["response"] == {
        "esearchresult": {"idlist": ["1234567", "2345678", "3456789"]}
    }


def test_search_records_one_query_when_strict_hits(
    dataset_with_case_87,
    valid_pico_llm_call,
    search_call_strict_hits,
    fetch_call_should_not_be_called,
):
    trace = run_pipeline(
        case_id=87,
        dataset=dataset_with_case_87,
        model_call=valid_pico_llm_call,
        search_call=search_call_strict_hits,
        fetch_call=fetch_call_should_not_be_called,
        run_metadata=RUN_METADATA,
    )

    search_record = trace["stages"]["search"]
    assert search_record["status"] == "succeeded"

    call_records = search_record["call_records"]
    assert len(call_records) == 1
    assert "Randomized Controlled Trial[pt]" in call_records[0]["query"]


def test_pico_validation_failure_on_missing_outcome_key(
    dataset_with_case_87,
    pico_response_missing_outcome_llm_call,
    search_call_should_not_be_called,
    fetch_call_should_not_be_called,
):
    trace = run_pipeline(
        case_id=87,
        dataset=dataset_with_case_87,
        model_call=pico_response_missing_outcome_llm_call,
        search_call=search_call_should_not_be_called,
        fetch_call=fetch_call_should_not_be_called,
        run_metadata=RUN_METADATA,
    )

    assert trace["run_outcome"] == "failed"

    pico_record = trace["stages"]["generate_pico_candidates"]
    assert pico_record["status"] == "failed"
    assert pico_record["failure_tag"] == "validation"

    for stage_name in [
        "select_pico",
        "build_search_query",
        "search",
        "fetch",
        "parse",
        "rank",
        "generate_summary",
    ]:
        assert trace["stages"][stage_name]["status"] == "skipped"
