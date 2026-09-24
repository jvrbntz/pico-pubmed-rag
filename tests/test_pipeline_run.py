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


VALID_PICO_RESPONSE = (
    '[{"population": "adults with type 2 diabetes", "intervention": "metformin", '
    '"comparison": "sulfonylurea", "outcome": "HbA1c reduction"}, '
    '{"population": "adults with type 2 diabetes", "intervention": "lifestyle modification", '
    '"comparison": "metformin", "outcome": "weight loss"}]'
)

NO_CLEAR_ANSWER_SUMMARY = (
    "No Clear Answer: None of the retrieved abstracts compare metformin "
    "with sulfonylurea for this population."
)


def scripted_model_call(responses):
    remaining = list(responses)

    def _model_call(prompt):
        return remaining.pop(0)

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
def search_call_always_empty():
    def _search_call(query):
        return {"esearchresult": {"idlist": []}}

    return _search_call


@pytest.fixture
def search_call_malformed_response():
    def _search_call(query):
        return {}

    return _search_call


@pytest.fixture
def search_call_strict_hits():
    def _search_call(query):
        return {"esearchresult": {"idlist": ["1234567", "2345678", "3456789"]}}

    return _search_call


@pytest.fixture
def fetch_call_raises_connection_error():
    def _fetch_call(pmids):
        raise ConnectionError("NCBI unreachable")

    return _fetch_call


XML_MISSING_ABSTRACT = """<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>1234567</PMID>
      <Article>
        <ArticleTitle>Metformin versus sulfonylurea in type 2 diabetes</ArticleTitle>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2020</Year></PubDate>
          </JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


VALID_XML = """<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>1234567</PMID>
      <Article>
        <ArticleTitle>Metformin versus sulfonylurea in type 2 diabetes</ArticleTitle>
        <Abstract>
          <AbstractText>A randomized trial comparing HbA1c reduction between metformin and sulfonylurea.</AbstractText>
        </Abstract>
        <PublicationTypeList>
          <PublicationType>Randomized Controlled Trial</PublicationType>
        </PublicationTypeList>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2020</Year></PubDate>
          </JournalIssue>
        </Journal>
      </Article>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""

SEVEN_PMIDS = ["1111111", "2222222", "3333333", "4444444", "5555555", "6666666", "7777777"]


@pytest.fixture
def search_call_seven_hits():
    def _search_call(query):
        return {"esearchresult": {"idlist": SEVEN_PMIDS}}

    return _search_call


@pytest.fixture
def fetch_call_valid_xml():
    def _fetch_call(pmids):
        return VALID_XML

    return _fetch_call


@pytest.fixture
def fetch_call_missing_abstract():
    def _fetch_call(pmids):
        return XML_MISSING_ABSTRACT

    return _fetch_call


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


def test_no_evidence_when_both_searches_return_nothing(
    dataset_with_case_87,
    valid_pico_llm_call,
    search_call_always_empty,
    fetch_call_should_not_be_called,
):
    trace = run_pipeline(
        case_id=87,
        dataset=dataset_with_case_87,
        model_call=valid_pico_llm_call,
        search_call=search_call_always_empty,
        fetch_call=fetch_call_should_not_be_called,
        run_metadata=RUN_METADATA,
    )

    assert trace["run_outcome"] == "no_evidence"

    search_record = trace["stages"]["search"]
    assert search_record["status"] == "succeeded"
    assert len(search_record["call_records"]) == 2

    for stage_name in ["fetch", "parse", "rank", "generate_summary"]:
        assert trace["stages"][stage_name]["status"] == "skipped"
        assert trace["stages"][stage_name]["skip_reason"] == "no_evidence"

    assert all(record["status"] != "failed" for record in trace["stages"].values())


def test_malformed_search_response_fails_and_keeps_raw_response(
    dataset_with_case_87,
    valid_pico_llm_call,
    search_call_malformed_response,
    fetch_call_should_not_be_called,
):
    trace = run_pipeline(
        case_id=87,
        dataset=dataset_with_case_87,
        model_call=valid_pico_llm_call,
        search_call=search_call_malformed_response,
        fetch_call=fetch_call_should_not_be_called,
        run_metadata=RUN_METADATA,
    )

    assert trace["run_outcome"] == "failed"

    search_record = trace["stages"]["search"]
    assert search_record["status"] == "failed"
    assert search_record["failure_tag"] == "validation"
    assert search_record["call_records"][0]["response"] == {}


def test_fetch_connection_error_fails_without_raising(
    dataset_with_case_87,
    valid_pico_llm_call,
    search_call_strict_hits,
    fetch_call_raises_connection_error,
):
    trace = run_pipeline(
        case_id=87,
        dataset=dataset_with_case_87,
        model_call=valid_pico_llm_call,
        search_call=search_call_strict_hits,
        fetch_call=fetch_call_raises_connection_error,
        run_metadata=RUN_METADATA,
    )

    assert trace["run_outcome"] == "failed"

    fetch_record = trace["stages"]["fetch"]
    assert fetch_record["status"] == "failed"
    assert fetch_record["failure_tag"] == "unexpected"
    assert fetch_record["failure_type"] == "ConnectionError"

    for stage_name in ["parse", "rank", "generate_summary"]:
        assert trace["stages"][stage_name]["status"] == "skipped"


def test_parse_failure_keeps_raw_xml_from_fetch(
    dataset_with_case_87,
    valid_pico_llm_call,
    search_call_strict_hits,
    fetch_call_missing_abstract,
):
    trace = run_pipeline(
        case_id=87,
        dataset=dataset_with_case_87,
        model_call=valid_pico_llm_call,
        search_call=search_call_strict_hits,
        fetch_call=fetch_call_missing_abstract,
        run_metadata=RUN_METADATA,
    )

    assert trace["run_outcome"] == "failed"

    fetch_record = trace["stages"]["fetch"]
    assert fetch_record["status"] == "succeeded"
    assert fetch_record["call_records"][0]["response"] == XML_MISSING_ABSTRACT

    parse_record = trace["stages"]["parse"]
    assert parse_record["status"] == "failed"
    assert parse_record["failure_tag"] == "unexpected"
    assert parse_record["failure_type"] == "AttributeError"

    for stage_name in ["rank", "generate_summary"]:
        assert trace["stages"][stage_name]["status"] == "skipped"


def test_fetch_records_pmids_sent_and_raw_xml(
    dataset_with_case_87,
    valid_pico_llm_call,
    search_call_seven_hits,
    fetch_call_valid_xml,
):
    trace = run_pipeline(
        case_id=87,
        dataset=dataset_with_case_87,
        model_call=valid_pico_llm_call,
        search_call=search_call_seven_hits,
        fetch_call=fetch_call_valid_xml,
        run_metadata=RUN_METADATA,
    )

    fetch_record = trace["stages"]["fetch"]
    assert fetch_record["status"] == "succeeded"

    call_records = fetch_record["call_records"]
    assert len(call_records) == 1
    assert call_records[0]["pmids"] == SEVEN_PMIDS[:5]
    assert call_records[0]["response"] == VALID_XML


def test_no_clear_answer_summary_completes_run(
    dataset_with_case_87,
    search_call_strict_hits,
    fetch_call_valid_xml,
):
    trace = run_pipeline(
        case_id=87,
        dataset=dataset_with_case_87,
        model_call=scripted_model_call([VALID_PICO_RESPONSE, NO_CLEAR_ANSWER_SUMMARY]),
        search_call=search_call_strict_hits,
        fetch_call=fetch_call_valid_xml,
        run_metadata=RUN_METADATA,
    )

    assert trace["run_outcome"] == "completed"

    summary_record = trace["stages"]["generate_summary"]
    assert summary_record["status"] == "succeeded"
    assert summary_record["output"].startswith("No Clear Answer:")


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
