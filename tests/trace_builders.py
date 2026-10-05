"""Builds minimal hand-made run traces for tests that read traces (batch metrics, review)."""

from pico_pubmed_rag.pipeline_run import STAGE_NAMES

VALID_CANDIDATE = {
    "population": "adults with knee osteoarthritis",
    "intervention": "total knee replacement",
    "comparison": None,
    "outcome": "pain",
}


def make_trace(
    case_id,
    repeat=1,
    outcome="completed",
    failed_stage="generate_pico_candidates",
    failure_tag="validation",
    summary="Evidence Summary: A finding (PMID: 1111111).",
    broadened=False,
    summary_attempts=1,
    shown_pmids=("1111111",),
    candidates=(VALID_CANDIDATE,),
    search_terms=None,
    search_terms_failed=False,
):
    """Builds a minimal schema-v1 trace with the given outcome."""
    stages = {name: {"status": "skipped", "skip_reason": "not reached"} for name in STAGE_NAMES}

    def succeed(name, output=None, call_records=None):
        stages[name] = {"status": "succeeded", "output": output}
        if call_records is not None:
            stages[name]["call_records"] = call_records

    if outcome == "failed" and failed_stage == "load_case":
        stages["load_case"] = {"status": "failed", "failure_tag": failure_tag}
        return _trace(case_id, repeat, outcome, stages)

    succeed("load_case", {
        "case_id": case_id,
        "medical_specialty": " Orthopedic",
        "description": f"Synthetic note {case_id}.",
        "transcription": f"Full synthetic note text for case {case_id}.",
    })
    if outcome == "failed" and failed_stage == "generate_pico_candidates":
        stages["generate_pico_candidates"] = {"status": "failed", "failure_tag": failure_tag}
        return _trace(case_id, repeat, outcome, stages)

    succeed("generate_pico_candidates", list(candidates))
    succeed("select_pico", candidates[0])
    if search_terms_failed:
        stages["extract_search_terms"] = {"status": "failed", "failure_tag": "validation"}
        return _trace(case_id, repeat, "failed", stages)
    if search_terms is not None:
        succeed("extract_search_terms", search_terms)
    query = "adults with knee osteoarthritis AND total knee replacement"
    succeed("build_search_query", query)

    def search_record(idlist):
        return {"query": query, "response": {"esearchresult": {"idlist": idlist}}}

    if outcome == "no_evidence":
        succeed("search", [], [search_record([]), search_record([])])
        for name in ["fetch", "parse", "rank", "generate_summary"]:
            stages[name] = {"status": "skipped", "skip_reason": "no_evidence"}
        return _trace(case_id, repeat, outcome, stages)

    search_records = [search_record([]), search_record(["1111111"])] if broadened else [search_record(["1111111"])]
    succeed("search", ["1111111"], search_records)
    succeed("fetch", "<xml/>", [{"pmids": ["1111111"], "response": "<xml/>"}])
    abstracts = [
        {
            "pmid": pmid,
            "title": f"Trial {pmid}",
            "text": f"Abstract text {pmid}.",
            "publication_type": ["Randomized Controlled Trial"],
            "publication_date": "2020",
        }
        for pmid in shown_pmids
    ]
    succeed("parse", abstracts)
    succeed("rank", abstracts)

    if outcome == "failed":
        stages[failed_stage] = {"status": "failed", "failure_tag": failure_tag}
        return _trace(case_id, repeat, outcome, stages)

    succeed("generate_summary", summary, [{"prompt": "...", "response": summary}] * summary_attempts)
    return _trace(case_id, repeat, outcome, stages)


def _trace(case_id, repeat, outcome, stages):
    return {
        "run_id": f"run-{case_id}-{repeat}",
        "case_id": case_id,
        "run_metadata": {"repeat": repeat, "batch_id": "test-batch"},
        "run_outcome": outcome,
        "stages": stages,
    }
