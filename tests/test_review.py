"""Acceptance-criteria tests for the trace review logic in review.py."""

import json

import pytest

from pico_pubmed_rag.review import (
    build_review_queue,
    build_run_view,
    load_annotations,
    review_progress,
    save_annotation,
    unannotated_runs,
)
from tests.trace_builders import make_trace


def test_queue_keeps_one_outcome_sorted_by_case_then_repeat():
    traces = [
        make_trace(30, repeat=2, outcome="completed"),
        make_trace(10, repeat=1, outcome="failed"),
        make_trace(30, repeat=1, outcome="completed"),
        make_trace(20, repeat=1, outcome="no_evidence"),
        make_trace(10, repeat=2, outcome="completed"),
    ]

    queue = build_review_queue(traces, outcome="completed")

    assert [(t["case_id"], t["run_metadata"]["repeat"]) for t in queue] == [(10, 2), (30, 1), (30, 2)]


def test_run_view_contains_what_the_reviewer_judges():
    trace = make_trace(
        87,
        repeat=2,
        search_terms={"population_terms": "knee osteoarthritis", "intervention_terms": "knee replacement"},
        shown_pmids=("1111111", "2222222"),
        summary="Evidence Summary: not a recommendation. No Clear Answer: (PMIDs: 1111111, 9999999).",
    )

    view = build_run_view(trace)

    assert view["header"] == {
        "case_id": 87, "repeat": 2, "run_id": "run-87-2",
        "specialty": "Orthopedic", "description": "Synthetic note 87.",
    }
    assert view["note"] == "Full synthetic note text for case 87."
    assert view["pico"]["population"] == "adults with knee osteoarthritis"
    assert view["search_terms"] == {"population_terms": "knee osteoarthritis", "intervention_terms": "knee replacement"}
    assert view["query_sent"] == "adults with knee osteoarthritis AND total knee replacement"
    assert [a["pmid"] for a in view["abstracts"]] == ["1111111", "2222222"]
    assert view["abstracts"][0]["title"] == "Trial 1111111"
    assert view["summary"].startswith("Evidence Summary:")
    assert view["labels"] == ["Evidence Summary:", "No Clear Answer:"]
    assert view["cited_pmids"] == ["1111111", "9999999"]
    assert view["unshown_cited_pmids"] == ["9999999"]


def test_run_view_reads_version_one_traces_without_search_terms():
    trace = make_trace(12)
    del trace["stages"]["extract_search_terms"]

    view = build_run_view(trace)

    assert view["search_terms"] is None
    assert view["query_sent"] == "adults with knee osteoarthritis AND total knee replacement"


def test_missing_annotation_file_loads_as_no_annotations(tmp_path):
    assert load_annotations(tmp_path / "annotations_batch.json") == {}


def test_saved_annotation_reloads_with_timestamp_and_format_version(tmp_path):
    path = tmp_path / "annotations_batch.json"

    save_annotation(path, run_id="run-87-1", case_id=87, answerable="yes",
                    summary_verdict="fail", notes="Abstract 1 answers it; summary declined.", deferred=False)

    annotation = load_annotations(path)["run-87-1"]
    assert annotation["case_id"] == 87
    assert annotation["answerable"] == "yes"
    assert annotation["summary_verdict"] == "fail"
    assert annotation["notes"] == "Abstract 1 answers it; summary declined."
    assert annotation["deferred"] is False
    assert annotation["updated_at"].endswith("+00:00")
    assert json.loads(path.read_text(encoding="utf-8"))["format_version"] == 1


def test_saving_again_replaces_the_annotation(tmp_path):
    path = tmp_path / "annotations_batch.json"
    save_annotation(path, run_id="run-87-1", case_id=87, answerable="no",
                    summary_verdict=None, notes="first look", deferred=True)

    save_annotation(path, run_id="run-87-1", case_id=87, answerable="yes",
                    summary_verdict="pass", notes="second look", deferred=False)

    annotations = load_annotations(path)
    assert list(annotations) == ["run-87-1"]
    assert annotations["run-87-1"]["answerable"] == "yes"
    assert annotations["run-87-1"]["notes"] == "second look"


def test_failed_save_leaves_the_file_unchanged(tmp_path):
    path = tmp_path / "annotations_batch.json"
    save_annotation(path, run_id="run-87-1", case_id=87, answerable="yes",
                    summary_verdict="pass", notes="kept", deferred=False)
    bytes_before = path.read_bytes()

    with pytest.raises(TypeError):
        save_annotation(path, run_id="run-12-1", case_id=12, answerable="yes",
                        summary_verdict="pass", notes=object(), deferred=False)

    assert path.read_bytes() == bytes_before


def test_progress_counts_and_unannotated_filter(tmp_path):
    queue = [make_trace(case_id) for case_id in (1, 2, 3, 4, 5)]
    path = tmp_path / "annotations_batch.json"
    save_annotation(path, run_id="run-1-1", case_id=1, answerable="yes", summary_verdict="pass", notes="", deferred=False)
    save_annotation(path, run_id="run-2-1", case_id=2, answerable="no", summary_verdict="pass", notes="", deferred=False)
    save_annotation(path, run_id="run-3-1", case_id=3, answerable=None, summary_verdict=None, notes="unsure", deferred=True)
    save_annotation(path, run_id="run-4-1", case_id=4, answerable="yes", summary_verdict=None, notes="", deferred=False)
    annotations = load_annotations(path)

    assert review_progress(queue, annotations) == {"annotated": 2, "deferred": 1, "unannotated": 2}
    assert [t["case_id"] for t in unannotated_runs(queue, annotations)] == [4, 5]


def test_run_view_includes_raw_model_responses_by_stage():
    trace = make_trace(87, summary_attempts=2, summary="Evidence Summary: A finding (PMID: 1111111).")
    trace["stages"]["generate_pico_candidates"]["call_records"] = [{"prompt": "...", "response": "raw PICO text"}]

    view = build_run_view(trace)

    assert view["raw_responses"]["generate_pico_candidates"] == ["raw PICO text"]
    assert len(view["raw_responses"]["generate_summary"]) == 2
