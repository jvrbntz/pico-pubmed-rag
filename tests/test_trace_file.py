"""Acceptance-criteria tests for write_trace and read_traces in trace_file.py."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from pico_pubmed_rag.trace_file import read_traces, write_trace


@pytest.fixture
def completed_trace():
    return {
        "run_id": "b2c3d4",
        "case_id": 87,
        "started_at": "2026-09-30T16:00:00+00:00",
        "total_latency_s": 36.0,
        "schema_version": 1,
        "run_metadata": {"git_commit": "abc123"},
        "run_outcome": "completed",
        "stages": {
            "load_case": {
                "status": "succeeded",
                "output": {"case_id": 87, "transcription": "A synthetic case note."},
                "latency_s": 0.001,
                "service": "none",
            },
            "generate_summary": {
                "status": "succeeded",
                "output": "Evidence Summary: A finding (PMID: 1234567).",
                "latency_s": 13.37,
                "call_records": [{"prompt": "...", "response": "Evidence Summary: ..."}],
                "service": "local",
            },
        },
    }


@pytest.fixture
def failed_trace():
    return {
        "run_id": "a1b2c3",
        "case_id": 12,
        "started_at": "2026-09-30T15:59:00+00:00",
        "total_latency_s": 0.4,
        "schema_version": 1,
        "run_metadata": {"git_commit": "abc123"},
        "run_outcome": "failed",
        "stages": {
            "fetch": {
                "status": "failed",
                "failure_tag": "unexpected",
                "failure_type": "ConnectionError",
                "traceback": "Traceback (most recent call last):\n  ...\nConnectionError: NCBI unreachable\n",
                "latency_s": 0.2,
                "call_records": [
                    {"pmids": ["1234567"], "error": "ConnectionError: NCBI unreachable"}
                ],
                "service": "external",
            },
            "parse": {"status": "skipped", "skip_reason": "not reached", "service": "none"},
        },
    }


def test_first_save_creates_file_with_one_line(tmp_path, completed_trace):
    path = tmp_path / "new_dir" / "traces.jsonl"

    write_trace(completed_trace, path)

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    json.loads(lines[0])


def test_round_trip_preserves_multiline_text_and_floats(tmp_path, completed_trace):
    path = tmp_path / "traces.jsonl"
    load_case = completed_trace["stages"]["load_case"]
    load_case["output"]["transcription"] = "Right knee pain.\nNo acute distress, café au lait spots noted."
    load_case["latency_s"] = 3.49e-07

    write_trace(completed_trace, path)

    assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    assert read_traces(path) == [completed_trace]


def test_saves_append_in_order(tmp_path, failed_trace, completed_trace):
    path = tmp_path / "traces.jsonl"
    write_trace(failed_trace, path)

    write_trace(completed_trace, path)

    assert read_traces(path) == [failed_trace, completed_trace]


def test_nan_trace_refused_file_unchanged(tmp_path, failed_trace, completed_trace):
    path = tmp_path / "traces.jsonl"
    write_trace(failed_trace, path)
    bytes_before = path.read_bytes()
    completed_trace["stages"]["load_case"]["output"]["description"] = float("nan")

    with pytest.raises(ValueError):
        write_trace(completed_trace, path)

    assert path.read_bytes() == bytes_before


def test_datetime_trace_refused_file_unchanged(tmp_path, failed_trace, completed_trace):
    path = tmp_path / "traces.jsonl"
    write_trace(failed_trace, path)
    bytes_before = path.read_bytes()
    completed_trace["started_at"] = datetime(2026, 9, 30, 16, 0)

    with pytest.raises(TypeError):
        write_trace(completed_trace, path)

    assert path.read_bytes() == bytes_before


def test_blank_lines_ignored(tmp_path, failed_trace, completed_trace):
    path = tmp_path / "traces.jsonl"
    path.write_text(
        json.dumps(failed_trace) + "\n\n" + json.dumps(completed_trace) + "\n",
        encoding="utf-8",
    )

    assert read_traces(path) == [failed_trace, completed_trace]


def test_malformed_line_reports_line_number(tmp_path, failed_trace):
    path = tmp_path / "traces.jsonl"
    path.write_text(json.dumps(failed_trace) + "\n\n{not json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="line 3"):
        read_traces(path)


def test_empty_file_reads_as_empty_list(tmp_path):
    path = tmp_path / "traces.jsonl"
    path.write_text("", encoding="utf-8")

    assert read_traces(path) == []


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_traces(tmp_path / "no_such_file.jsonl")


def test_runs_folder_is_gitignored():
    repo_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "runs/any_name.jsonl"],
        cwd=repo_root,
    )

    assert result.returncode == 0
