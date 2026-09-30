"""Saves run traces to a JSONL trace file, one trace per line, and reads them back."""

import json
from pathlib import Path


def write_trace(trace, path):
    trace_line = json.dumps(trace, allow_nan=False)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as trace_file:
        trace_file.write(trace_line + "\n")


def read_traces(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    traces = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            traces.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Malformed trace on line {line_number} of {path}: {e.msg}"
            ) from e
    return traces
