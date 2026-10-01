"""Acceptance-criteria tests for draw_case_sample and run_batch in batch_run.py."""

import logging

import pandas as pd
import pytest

from pico_pubmed_rag.batch_run import draw_case_sample, run_batch
from pico_pubmed_rag.trace_file import read_traces
from tests.pipeline_fakes import routing_model_call


@pytest.fixture
def twenty_case_dataset():
    case_ids = [0, 2, 3, 7, 8, 11, 14, 15, 19, 22, 23, 30, 31, 35, 40, 41, 44, 50, 52, 57]
    return pd.DataFrame(
        {"case_id": case_ids, "transcription": [f"Synthetic note {i}." for i in case_ids]}
    )


def test_sample_is_reproducible(twenty_case_dataset):
    first = draw_case_sample(twenty_case_dataset, size=5, seed=42)
    second = draw_case_sample(twenty_case_dataset, size=5, seed=42)

    assert first == second
    assert first == sorted(first)
    assert len(set(first)) == 5
    assert set(first) <= set(twenty_case_dataset["case_id"])


def test_sample_depends_on_seed(twenty_case_dataset):
    assert draw_case_sample(twenty_case_dataset, size=5, seed=42) != draw_case_sample(
        twenty_case_dataset, size=5, seed=7
    )


def test_sample_draws_only_existing_ids():
    dataset = pd.DataFrame({"case_id": [0, 1, 5, 9], "transcription": ["a", "b", "c", "d"]})

    assert draw_case_sample(dataset, size=4, seed=42) == [0, 1, 5, 9]


def test_sample_larger_than_dataset_raises():
    dataset = pd.DataFrame({"case_id": [0, 1, 5, 9], "transcription": ["a", "b", "c", "d"]})

    with pytest.raises(ValueError):
        draw_case_sample(dataset, size=5, seed=42)


@pytest.fixture
def dataset_with_cases_87_and_12():
    return pd.DataFrame(
        [
            {"case_id": 87, "description": "Synthetic case 87.", "transcription": "A synthetic note for case 87."},
            {"case_id": 12, "description": "Synthetic case 12.", "transcription": "A synthetic note for case 12."},
        ]
    )


def test_batch_writes_one_trace_per_run_in_order(
    tmp_path, dataset_with_cases_87_and_12, search_call_strict_hits, fetch_call_valid_xml
):
    batch_file = tmp_path / "batch.jsonl"

    run_batch(
        case_ids=[87, 12],
        repeats=2,
        dataset=dataset_with_cases_87_and_12,
        model_call=routing_model_call(),
        search_call=search_call_strict_hits,
        fetch_call=fetch_call_valid_xml,
        batch_file=batch_file,
        run_metadata={"git_commit": "abc123"},
    )

    traces = read_traces(batch_file)
    assert [(t["case_id"], t["run_metadata"]["repeat"]) for t in traces] == [
        (87, 1),
        (87, 2),
        (12, 1),
        (12, 2),
    ]
    assert len({t["run_metadata"]["batch_id"] for t in traces}) == 1
    assert all(t["run_metadata"]["git_commit"] == "abc123" for t in traces)
    assert all(t["run_outcome"] == "completed" for t in traces)


def test_batch_summary_counts_outcomes(
    tmp_path, dataset_with_cases_87_and_12, search_call_strict_hits, fetch_call_valid_xml
):
    batch_file = tmp_path / "batch.jsonl"

    summary = run_batch(
        case_ids=[87, 999],
        repeats=1,
        dataset=dataset_with_cases_87_and_12,
        model_call=routing_model_call(),
        search_call=search_call_strict_hits,
        fetch_call=fetch_call_valid_xml,
        batch_file=batch_file,
        run_metadata={},
    )

    assert summary["outcome_counts"] == {"completed": 1, "no_evidence": 0, "failed": 1}
    assert summary["unsaved"] == 0
    assert summary["batch_id"] == read_traces(batch_file)[0]["run_metadata"]["batch_id"]


def test_each_batch_gets_its_own_id(
    tmp_path, dataset_with_cases_87_and_12, search_call_strict_hits, fetch_call_valid_xml
):
    batch_ids = [
        run_batch(
            case_ids=[87],
            repeats=1,
            dataset=dataset_with_cases_87_and_12,
            model_call=routing_model_call(),
            search_call=search_call_strict_hits,
            fetch_call=fetch_call_valid_xml,
            batch_file=tmp_path / "batch.jsonl",
            run_metadata={},
        )["batch_id"]
        for _ in range(2)
    ]

    assert batch_ids[0] != batch_ids[1]


def test_trace_saved_before_next_run(
    tmp_path, dataset_with_cases_87_and_12, search_call_strict_hits, fetch_call_valid_xml
):
    batch_file = tmp_path / "batch.jsonl"
    lines_seen_when_case_12_started = []
    route = routing_model_call()

    # Records how many traces are on disk at the moment case 12's run first calls the model.
    def model_call(prompt):
        if "case 12" in prompt and not lines_seen_when_case_12_started:
            lines_seen_when_case_12_started.append(len(read_traces(batch_file)))
        return route(prompt)

    run_batch(
        case_ids=[87, 12],
        repeats=1,
        dataset=dataset_with_cases_87_and_12,
        model_call=model_call,
        search_call=search_call_strict_hits,
        fetch_call=fetch_call_valid_xml,
        batch_file=batch_file,
        run_metadata={},
    )

    assert lines_seen_when_case_12_started == [1]


def test_unsaved_trace_does_not_stop_batch(
    tmp_path, caplog, search_call_strict_hits, fetch_call_valid_xml
):
    dataset = pd.DataFrame(
        [
            {"case_id": 87, "description": float("nan"), "transcription": "A synthetic note for case 87."},
            {"case_id": 12, "description": "Synthetic case 12.", "transcription": "A synthetic note for case 12."},
        ]
    )
    batch_file = tmp_path / "batch.jsonl"

    with caplog.at_level(logging.INFO):
        summary = run_batch(
            case_ids=[87, 12],
            repeats=1,
            dataset=dataset,
            model_call=routing_model_call(),
            search_call=search_call_strict_hits,
            fetch_call=fetch_call_valid_xml,
            batch_file=batch_file,
            run_metadata={},
        )

    assert [t["case_id"] for t in read_traces(batch_file)] == [12]
    assert summary["unsaved"] == 1
    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) == 1
    assert "case 87" in error_records[0].getMessage()


def test_keyboard_interrupt_propagates(
    tmp_path, dataset_with_cases_87_and_12, search_call_strict_hits, fetch_call_valid_xml
):
    batch_file = tmp_path / "batch.jsonl"
    route = routing_model_call()

    def model_call(prompt):
        if "case 12" in prompt:
            raise KeyboardInterrupt
        return route(prompt)

    with pytest.raises(KeyboardInterrupt):
        run_batch(
            case_ids=[87, 12],
            repeats=1,
            dataset=dataset_with_cases_87_and_12,
            model_call=model_call,
            search_call=search_call_strict_hits,
            fetch_call=fetch_call_valid_xml,
            batch_file=batch_file,
            run_metadata={},
        )

    assert [t["case_id"] for t in read_traces(batch_file)] == [87]


def test_failed_runs_logged_at_warning(
    tmp_path, caplog, dataset_with_cases_87_and_12, search_call_strict_hits, fetch_call_valid_xml
):
    batch_file = tmp_path / "batch.jsonl"

    with caplog.at_level(logging.INFO):
        run_batch(
            case_ids=[87, 999],
            repeats=1,
            dataset=dataset_with_cases_87_and_12,
            model_call=routing_model_call(),
            search_call=search_call_strict_hits,
            fetch_call=fetch_call_valid_xml,
            batch_file=batch_file,
            run_metadata={},
        )

    completed_trace, failed_trace = read_traces(batch_file)
    completed_records = [r for r in caplog.records if completed_trace["run_id"] in r.getMessage()]
    failed_records = [r for r in caplog.records if failed_trace["run_id"] in r.getMessage()]

    assert len(completed_records) == 1
    assert completed_records[0].levelno == logging.INFO
    assert "completed" in completed_records[0].getMessage()

    assert len(failed_records) == 1
    assert failed_records[0].levelno == logging.WARNING
    assert "load_case" in failed_records[0].getMessage()


def test_logs_never_contain_note_text(
    tmp_path, caplog, search_call_strict_hits, fetch_call_valid_xml
):
    marker = "ZEBRA-NOTE-MARKER"
    dataset = pd.DataFrame(
        [
            {"case_id": 87, "description": "Synthetic case 87.", "transcription": f"A note with {marker}."},
            {"case_id": 12, "description": float("nan"), "transcription": f"Another note with {marker}."},
        ]
    )
    model_call = routing_model_call(
        summary_response=f"Evidence Summary: {marker} finding (PMID: 1234567)."
    )

    with caplog.at_level(logging.DEBUG):
        run_batch(
            case_ids=[87, 12, 999],
            repeats=1,
            dataset=dataset,
            model_call=model_call,
            search_call=search_call_strict_hits,
            fetch_call=fetch_call_valid_xml,
            batch_file=tmp_path / "batch.jsonl",
            run_metadata={},
        )

    assert caplog.records
    assert not any(marker in record.getMessage() for record in caplog.records)


def test_progress_logged_at_batch_and_run_start_and_batch_end(
    tmp_path, caplog, dataset_with_cases_87_and_12, search_call_strict_hits, fetch_call_valid_xml
):
    batch_file = tmp_path / "batch.jsonl"

    with caplog.at_level(logging.INFO):
        summary = run_batch(
            case_ids=[87, 12],
            repeats=1,
            dataset=dataset_with_cases_87_and_12,
            model_call=routing_model_call(),
            search_call=search_call_strict_hits,
            fetch_call=fetch_call_valid_xml,
            batch_file=batch_file,
            run_metadata={},
        )

    messages = [r.getMessage() for r in caplog.records]
    assert all(r.levelno == logging.INFO for r in caplog.records)

    first, last = messages[0], messages[-1]
    assert summary["batch_id"] in first
    assert "2 runs" in first
    assert str(batch_file) in first

    assert any("run 1/2: case 87, repeat 1" in m for m in messages)
    assert any("run 2/2: case 12, repeat 1" in m for m in messages)

    assert "completed 2" in last
    assert "unsaved 0" in last
