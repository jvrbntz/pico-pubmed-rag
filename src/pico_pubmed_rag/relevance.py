"""Loads a relevance sheet of abstracts to judge, and saves one yes/no relevance label per case and PMID."""

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_SHEET_COLUMNS = ["case_id", "pmid", "pico", "title", "abstract"]
RELEVANCE_VALUES = {"yes", "no"}


def load_sheet(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        missing = [c for c in REQUIRED_SHEET_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"Relevance sheet is missing required columns: {missing}")
        items = list(reader)

    for item in items:
        item["case_id"] = int(item["case_id"])
        item["pmid"] = item["pmid"].strip()
    return items


def load_labels(path):
    path = Path(path)
    if not path.exists():
        return {}
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {(r["case_id"], r["pmid"]): r for r in records}


def save_label(path, case_id, pmid, relevant, notes):
    if relevant not in RELEVANCE_VALUES:
        raise ValueError(f"Relevance must be 'yes' or 'no', got {relevant!r}")

    path = Path(path)
    records = load_labels(path)
    records[(case_id, pmid)] = {
        "case_id": case_id,
        "pmid": pmid,
        "relevant": relevant,
        "judged_on": datetime.now(timezone.utc).date().isoformat(),
        "notes": notes,
    }
    text = "".join(json.dumps(record) + "\n" for record in records.values())
    temporary_path = path.with_name(path.name + ".tmp")
    temporary_path.write_text(text, encoding="utf-8")
    os.replace(temporary_path, path)


def next_unlabeled(items, labels):
    for index, item in enumerate(items):
        if (item["case_id"], item["pmid"]) not in labels:
            return index
    return None


def labeling_progress(items, labels):
    labeled = sum((item["case_id"], item["pmid"]) in labels for item in items)
    return labeled, len(items)
