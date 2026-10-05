"""Builds the trace review queue, each run's review view, and saves the reviewer's annotations."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from pico_pubmed_rag.batch_metrics import (
    EVIDENCE_SUMMARY_LABEL,
    NO_CLEAR_ANSWER_LABEL,
    PMID_PATTERN,
)

ANNOTATION_FORMAT_VERSION = 1


def build_review_queue(traces, outcome):
    queue = [t for t in traces if t["run_outcome"] == outcome]
    return sorted(queue, key=lambda t: (t["case_id"], t["run_metadata"].get("repeat", 1)))


def build_run_view(trace):
    stages = trace["stages"]
    case = stages["load_case"].get("output") or {}
    terms_record = stages.get("extract_search_terms") or {}
    search_records = stages["search"].get("call_records", [])
    abstracts = stages["rank"].get("output") or []
    summary = stages["generate_summary"].get("output") or ""

    cited = list(dict.fromkeys(PMID_PATTERN.findall(summary)))
    shown = {abstract["pmid"] for abstract in abstracts}

    return {
        "header": {
            "case_id": trace["case_id"],
            "repeat": trace["run_metadata"].get("repeat", 1),
            "run_id": trace["run_id"],
            "specialty": str(case.get("medical_specialty", "")).strip(),
            "description": str(case.get("description", "")).strip(),
        },
        "note": str(case.get("transcription", "")).strip(),
        "pico": stages["select_pico"].get("output"),
        "search_terms": terms_record.get("output") if terms_record.get("status") == "succeeded" else None,
        "query_sent": search_records[0]["query"] if search_records else None,
        "abstracts": abstracts,
        "summary": summary,
        "labels": sorted(
            (label for label in (EVIDENCE_SUMMARY_LABEL, NO_CLEAR_ANSWER_LABEL) if label in summary),
            key=summary.index,
        ),
        "cited_pmids": cited,
        "unshown_cited_pmids": [pmid for pmid in cited if pmid not in shown],
    }


def load_annotations(path):
    path = Path(path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))["annotations"]


def save_annotation(path, run_id, case_id, answerable, summary_verdict, notes, deferred):
    path = Path(path)
    annotations = load_annotations(path)
    annotations[run_id] = {
        "case_id": case_id,
        "answerable": answerable,
        "summary_verdict": summary_verdict,
        "notes": notes,
        "deferred": deferred,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    text = json.dumps(
        {"format_version": ANNOTATION_FORMAT_VERSION, "annotations": annotations}, indent=2
    )
    temporary_path = path.with_name(path.name + ".tmp")
    temporary_path.write_text(text, encoding="utf-8")
    os.replace(temporary_path, path)


def _review_status(annotation):
    if annotation is None:
        return "unannotated"
    if annotation["deferred"]:
        return "deferred"
    if annotation["answerable"] and annotation["summary_verdict"]:
        return "annotated"
    return "unannotated"


def review_progress(queue, annotations):
    statuses = [_review_status(annotations.get(t["run_id"])) for t in queue]
    return {status: statuses.count(status) for status in ("annotated", "deferred", "unannotated")}


def unannotated_runs(queue, annotations):
    return [t for t in queue if _review_status(annotations.get(t["run_id"])) == "unannotated"]
