"""Exports the runs of one batch file with a chosen outcome to a CSV review sheet under runs/, with blank columns for error analysis."""

import argparse
import csv
from pathlib import Path

from pico_pubmed_rag.trace_file import read_traces

REVIEW_COLUMNS = ["your_note", "category", "answerable_question"]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_file", help="path to a batch file, e.g. runs/batch_20261001T203635Z.jsonl")
    parser.add_argument(
        "--outcome",
        default="no_evidence",
        choices=["completed", "no_evidence", "failed"],
        help="which run outcome to export",
    )
    return parser.parse_args()


def review_row(trace):
    stages = trace["stages"]
    case = stages["load_case"].get("output") or {}
    pico = stages["select_pico"].get("output") or {}
    queries = [record["query"] for record in stages["search"].get("call_records", [])]
    return {
        "case_id": trace["case_id"],
        "repeat": trace["run_metadata"].get("repeat"),
        "run_id": trace["run_id"],
        "specialty": str(case.get("medical_specialty", "")).strip(),
        "sample_name": str(case.get("sample_name", "")).strip(),
        "description": str(case.get("description", "")).strip(),
        "population": pico.get("population"),
        "intervention": pico.get("intervention"),
        "comparison": pico.get("comparison"),
        "outcome": pico.get("outcome"),
        "strict_query": queries[0] if queries else "",
        "broadened_query": queries[1] if len(queries) > 1 else "",
        **{column: "" for column in REVIEW_COLUMNS},
        "transcription": str(case.get("transcription", "")).strip(),
    }


if __name__ == "__main__":
    args = parse_args()
    batch_path = Path(args.batch_file)
    traces = [t for t in read_traces(batch_path) if t["run_outcome"] == args.outcome]
    rows = sorted((review_row(t) for t in traces), key=lambda r: (r["case_id"], r["repeat"]))

    sheet_path = batch_path.parent / f"review_{batch_path.stem}_{args.outcome}.csv"
    with sheet_path.open("w", encoding="utf-8-sig", newline="") as sheet:
        writer = csv.DictWriter(sheet, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} {args.outcome} runs written to {sheet_path}")
