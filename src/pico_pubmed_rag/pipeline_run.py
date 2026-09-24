"""Runs one case through the pico-pubmed-rag pipeline and returns a trace."""

import traceback

from pico_pubmed_rag.case_loading import load_case
from pico_pubmed_rag.pico_generation import generate_pico_candidates
from pico_pubmed_rag.pico_selection import select_pico
from pico_pubmed_rag.pubmed_search import build_search_query

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

    # Remaining stages not implemented yet; each stage's skip stays in place
    # until its own criterion is built.
    return {"run_outcome": "failed", "stages": stages}


def _failure_record(exc):
    tag = "validation" if isinstance(exc, ValueError) else "unexpected"
    return {
        "status": "failed",
        "failure_tag": tag,
        "failure_type": type(exc).__name__,
        "traceback": traceback.format_exc(),
    }
