"""Acceptance-criteria tests for the relevance labeling logic in relevance.py."""

import csv
import json
from datetime import datetime, timezone

import pytest

from pico_pubmed_rag.relevance import labeling_progress, load_labels, load_sheet, next_unlabeled, save_label

SHEET_COLUMNS = ["case_id", "note_description", "pico", "pmid", "year", "publication_type", "title", "abstract", "relevant", "notes"]


def write_sheet(path, rows, columns=SHEET_COLUMNS, encoding="utf-8-sig"):
    with open(path, "w", newline="", encoding=encoding) as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sheet_row(case_id, pmid, title="A trial"):
    return {
        "case_id": case_id,
        "note_description": "Synthetic note.",
        "pico": "P: adults | I: drug | C: None | O: pain",
        "pmid": pmid,
        "year": "2020",
        "publication_type": "Randomized Controlled Trial",
        "title": title,
        "abstract": "RESULTS: Pain fell.",
        "relevant": "",
        "notes": "",
    }


def test_load_sheet_returns_items_in_file_order_with_typed_keys(tmp_path):
    path = tmp_path / "sheet.csv"
    write_sheet(path, [sheet_row(207, "41943456", "Café au lait"), sheet_row(12, "1111111")])

    items = load_sheet(path)

    assert [(item["case_id"], item["pmid"]) for item in items] == [(207, "41943456"), (12, "1111111")]
    assert items[0]["title"] == "Café au lait"


def test_load_sheet_names_missing_required_column(tmp_path):
    path = tmp_path / "sheet.csv"
    columns = [c for c in SHEET_COLUMNS if c != "abstract"]
    write_sheet(path, [sheet_row(207, "41943456")], columns=columns)

    with pytest.raises(ValueError, match="abstract"):
        load_sheet(path)


def read_records(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_save_label_writes_relevance_record(tmp_path):
    path = tmp_path / "labels.jsonl"

    save_label(path, 207, "41943456", "yes", "on topic")

    assert read_records(path) == [
        {
            "case_id": 207,
            "pmid": "41943456",
            "relevant": "yes",
            "judged_on": datetime.now(timezone.utc).date().isoformat(),
            "notes": "on topic",
        }
    ]


def test_relabeling_replaces_the_record(tmp_path):
    path = tmp_path / "labels.jsonl"
    save_label(path, 207, "41943456", "yes", "")
    save_label(path, 12, "1111111", "no", "")

    save_label(path, 207, "41943456", "no", "second look")

    records = read_records(path)
    assert [(r["case_id"], r["pmid"], r["relevant"]) for r in records] == [
        (207, "41943456", "no"),
        (12, "1111111", "no"),
    ]


@pytest.mark.parametrize("relevant", ["", "maybe", "Yes", None])
def test_save_label_refuses_anything_but_yes_or_no(tmp_path, relevant):
    path = tmp_path / "labels.jsonl"
    save_label(path, 12, "1111111", "no", "")
    bytes_before = path.read_bytes()

    with pytest.raises(ValueError):
        save_label(path, 207, "41943456", relevant, "")

    assert path.read_bytes() == bytes_before


def test_save_label_leaves_no_temporary_file(tmp_path):
    path = tmp_path / "labels.jsonl"

    save_label(path, 207, "41943456", "yes", "")

    assert [p.name for p in tmp_path.iterdir()] == ["labels.jsonl"]


def test_load_labels_is_empty_before_any_label(tmp_path):
    assert load_labels(tmp_path / "labels.jsonl") == {}


def test_load_labels_keys_by_case_and_pmid(tmp_path):
    path = tmp_path / "labels.jsonl"
    save_label(path, 207, "41943456", "yes", "")
    save_label(path, 12, "1111111", "no", "off topic")

    labels = load_labels(path)

    assert set(labels) == {(207, "41943456"), (12, "1111111")}
    assert labels[(12, "1111111")]["relevant"] == "no"
    assert labels[(12, "1111111")]["notes"] == "off topic"


@pytest.fixture
def three_items(tmp_path):
    path = tmp_path / "sheet.csv"
    write_sheet(path, [sheet_row(207, "1"), sheet_row(207, "2"), sheet_row(12, "3")])
    return load_sheet(path)


def test_next_unlabeled_skips_labeled_items(tmp_path, three_items):
    path = tmp_path / "labels.jsonl"
    save_label(path, 207, "1", "yes", "")
    save_label(path, 12, "3", "no", "")

    assert next_unlabeled(three_items, load_labels(path)) == 1


def test_next_unlabeled_is_none_when_all_labeled(tmp_path, three_items):
    path = tmp_path / "labels.jsonl"
    for item in three_items:
        save_label(path, item["case_id"], item["pmid"], "no", "")

    assert next_unlabeled(three_items, load_labels(path)) is None


def test_labeling_progress_counts_only_sheet_items(tmp_path, three_items):
    path = tmp_path / "labels.jsonl"
    save_label(path, 207, "2", "yes", "")
    save_label(path, 999, "9", "yes", "")

    assert labeling_progress(three_items, load_labels(path)) == (1, 3)
