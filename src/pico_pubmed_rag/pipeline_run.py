"""Runs one case through the pico-pubmed-rag pipeline and returns a trace."""

import time
import traceback
import uuid
from datetime import datetime, timezone

from pico_pubmed_rag.abstract_ranking import rank_abstracts
from pico_pubmed_rag.case_loading import load_case
from pico_pubmed_rag.pico_generation import generate_pico_candidates
from pico_pubmed_rag.pico_selection import select_pico
from pico_pubmed_rag.pubmed_search import (
    ConfigurationError,
    build_search_query,
    fetch_abstracts,
    parse_pubmed_xml,
    search_pubmed_with_broadening,
)
from pico_pubmed_rag.summary_generation import generate_summary

FETCH_SIZE = 5

TRACE_SCHEMA_VERSION = 1

SERVICE_TAGS = {
    "load_case": "none",
    "generate_pico_candidates": "local",
    "select_pico": "none",
    "build_search_query": "none",
    "search": "external",
    "fetch": "external",
    "parse": "none",
    "rank": "none",
    "generate_summary": "local",
}

STAGE_NAMES = list(SERVICE_TAGS)


def run_pipeline(case_id, dataset, model_call, search_call, fetch_call, run_metadata):
    started_at = datetime.now(timezone.utc).isoformat()
    start_time = time.perf_counter()
    stages = {
        name: {"status": "skipped", "skip_reason": "not reached"}
        for name in STAGE_NAMES
    }

    def finish(run_outcome):
        for name, record in stages.items():
            record["service"] = SERVICE_TAGS[name]
        return {
            "run_id": uuid.uuid4().hex,
            "case_id": case_id,
            "started_at": started_at,
            "total_latency_s": time.perf_counter() - start_time,
            "schema_version": TRACE_SCHEMA_VERSION,
            "run_metadata": run_metadata,
            "run_outcome": run_outcome,
            "stages": stages,
        }

    def run_stage(name, work, call_records=None):
        stage_start = time.perf_counter()
        try:
            output = work()
        except Exception as exc:
            stages[name] = _failure_record(exc)
            succeeded, output = False, None
        else:
            stages[name] = {"status": "succeeded", "output": output}
            succeeded = True
        stages[name]["latency_s"] = time.perf_counter() - stage_start
        if call_records is not None:
            stages[name]["call_records"] = call_records
        return succeeded, output

    ok, case = run_stage("load_case", lambda: load_case(dataset, case_id))
    if not ok:
        return finish("failed")

    recording_pico_call, pico_call_records = _recording_call(model_call, "prompt")
    ok, candidates = run_stage(
        "generate_pico_candidates",
        lambda: generate_pico_candidates(case["transcription"], recording_pico_call),
        pico_call_records,
    )
    if not ok:
        return finish("failed")

    ok, pico = run_stage("select_pico", lambda: select_pico(candidates))
    if not ok:
        return finish("failed")

    ok, query = run_stage("build_search_query", lambda: build_search_query(pico))
    if not ok:
        return finish("failed")

    recording_search_call, search_call_records = _recording_call(search_call, "query")
    ok, pmids = run_stage(
        "search",
        lambda: search_pubmed_with_broadening(query, recording_search_call),
        search_call_records,
    )
    if not ok:
        return finish("failed")

    if not pmids:
        for name in ["fetch", "parse", "rank", "generate_summary"]:
            stages[name] = {"status": "skipped", "skip_reason": "no_evidence"}
        return finish("no_evidence")

    recording_fetch_call, fetch_call_records = _recording_call(fetch_call, "pmids")
    ok, xml_text = run_stage(
        "fetch",
        lambda: fetch_abstracts(pmids[:FETCH_SIZE], recording_fetch_call),
        fetch_call_records,
    )
    if not ok:
        return finish("failed")

    ok, abstracts = run_stage("parse", lambda: parse_pubmed_xml(xml_text))
    if not ok:
        return finish("failed")

    ok, ranked = run_stage("rank", lambda: rank_abstracts(abstracts))
    if not ok:
        return finish("failed")

    recording_summary_call, summary_call_records = _recording_call(model_call, "prompt")
    ok, _ = run_stage(
        "generate_summary",
        lambda: generate_summary(pico, ranked, recording_summary_call),
        summary_call_records,
    )
    if not ok:
        return finish("failed")

    return finish("completed")


def _recording_call(real_call, input_name):
    records = []

    def recording_call(call_input):
        try:
            response = real_call(call_input)
        except Exception as exc:
            records.append(
                {input_name: call_input, "error": f"{type(exc).__name__}: {exc}"}
            )
            raise
        records.append({input_name: call_input, "response": response})
        return response

    return recording_call, records


def _failure_record(exc):
    if isinstance(exc, ConfigurationError):
        tag = "configuration"
    elif isinstance(exc, ValueError):
        tag = "validation"
    else:
        tag = "unexpected"
    return {
        "status": "failed",
        "failure_tag": tag,
        "failure_type": type(exc).__name__,
        "traceback": traceback.format_exc(),
    }
