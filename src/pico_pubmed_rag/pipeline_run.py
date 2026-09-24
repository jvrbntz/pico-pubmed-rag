"""Runs one case through the pico-pubmed-rag pipeline and returns a trace."""

import traceback

from pico_pubmed_rag.abstract_ranking import rank_abstracts
from pico_pubmed_rag.case_loading import load_case
from pico_pubmed_rag.pico_generation import generate_pico_candidates
from pico_pubmed_rag.pico_selection import select_pico
from pico_pubmed_rag.pubmed_search import (
    build_search_query,
    fetch_abstracts,
    parse_pubmed_xml,
    search_pubmed_with_broadening,
)
from pico_pubmed_rag.summary_generation import generate_summary

FETCH_SIZE = 5

STAGE_NAMES = [
    "load_case",
    "generate_pico_candidates",
    "select_pico",
    "build_search_query",
    "search",
    "fetch",
    "parse",
    "rank",
    "generate_summary",
]


def run_pipeline(case_id, dataset, model_call, search_call, fetch_call, run_metadata):
    stages = {
        name: {"status": "skipped", "skip_reason": "not reached"}
        for name in STAGE_NAMES
    }

    try:
        case = load_case(dataset, case_id)
        stages["load_case"] = {"status": "succeeded", "output": case}
    except Exception as exc:
        stages["load_case"] = _failure_record(exc)
        return {"run_outcome": "failed", "stages": stages}

    try:
        candidates = generate_pico_candidates(case["transcription"], model_call)
        stages["generate_pico_candidates"] = {
            "status": "succeeded",
            "output": candidates,
        }
    except Exception as exc:
        stages["generate_pico_candidates"] = _failure_record(exc)
        return {"run_outcome": "failed", "stages": stages}

    try:
        pico = select_pico(candidates)
        stages["select_pico"] = {"status": "succeeded", "output": pico}
    except Exception as exc:
        stages["select_pico"] = _failure_record(exc)
        return {"run_outcome": "failed", "stages": stages}

    try:
        query = build_search_query(pico)
        stages["build_search_query"] = {"status": "succeeded", "output": query}
    except Exception as exc:
        stages["build_search_query"] = _failure_record(exc)
        return {"run_outcome": "failed", "stages": stages}

    recording_search_call, search_call_records = _recording_call(search_call, "query")

    try:
        pmids = search_pubmed_with_broadening(query, recording_search_call)
        stages["search"] = {
            "status": "succeeded",
            "output": pmids,
            "call_records": search_call_records,
        }
    except Exception as exc:
        stages["search"] = {
            **_failure_record(exc),
            "call_records": search_call_records,
        }
        return {"run_outcome": "failed", "stages": stages}

    if not pmids:
        for name in ["fetch", "parse", "rank", "generate_summary"]:
            stages[name] = {"status": "skipped", "skip_reason": "no_evidence"}
        return {"run_outcome": "no_evidence", "stages": stages}

    recording_fetch_call, fetch_call_records = _recording_call(fetch_call, "pmids")

    try:
        xml_text = fetch_abstracts(pmids[:FETCH_SIZE], recording_fetch_call)
        stages["fetch"] = {
            "status": "succeeded",
            "output": xml_text,
            "call_records": fetch_call_records,
        }
    except Exception as exc:
        stages["fetch"] = {
            **_failure_record(exc),
            "call_records": fetch_call_records,
        }
        return {"run_outcome": "failed", "stages": stages}

    try:
        abstracts = parse_pubmed_xml(xml_text)
        stages["parse"] = {"status": "succeeded", "output": abstracts}
    except Exception as exc:
        stages["parse"] = _failure_record(exc)
        return {"run_outcome": "failed", "stages": stages}

    try:
        ranked = rank_abstracts(abstracts)
        stages["rank"] = {"status": "succeeded", "output": ranked}
    except Exception as exc:
        stages["rank"] = _failure_record(exc)
        return {"run_outcome": "failed", "stages": stages}

    recording_summary_call, summary_call_records = _recording_call(model_call, "prompt")

    try:
        summary = generate_summary(pico, ranked, recording_summary_call)
        stages["generate_summary"] = {
            "status": "succeeded",
            "output": summary,
            "call_records": summary_call_records,
        }
    except Exception as exc:
        stages["generate_summary"] = {
            **_failure_record(exc),
            "call_records": summary_call_records,
        }
        return {"run_outcome": "failed", "stages": stages}

    return {"run_outcome": "completed", "stages": stages}


def _recording_call(real_call, input_name):
    records = []

    def recording_call(call_input):
        response = real_call(call_input)
        records.append({input_name: call_input, "response": response})
        return response

    return recording_call, records


def _failure_record(exc):
    tag = "validation" if isinstance(exc, ValueError) else "unexpected"
    return {
        "status": "failed",
        "failure_tag": tag,
        "failure_type": type(exc).__name__,
        "traceback": traceback.format_exc(),
    }
