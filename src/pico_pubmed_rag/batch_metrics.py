"""Computes operational metrics from a batch of run traces: per repeat, per case, and pooled."""

import re
from collections import defaultdict
from statistics import median

from pico_pubmed_rag.pico_generation import EXAMPLE_CANDIDATES

NO_CLEAR_ANSWER_LABEL = "No Clear Answer:"
EVIDENCE_SUMMARY_LABEL = "Evidence Summary:"
PMID_PATTERN = re.compile(r"\b\d{6,9}\b")
DESCRIPTIVE_QUERY_WORDS = 8


def compute_batch_metrics(traces):
    by_repeat = defaultdict(list)
    by_case = defaultdict(list)
    for trace in traces:
        by_repeat[_repeat(trace)].append(trace)
        by_case[trace["case_id"]].append(trace)

    case_profiles = {
        case_id: _case_profile(case_traces) for case_id, case_traces in by_case.items()
    }

    return {
        "per_repeat": {
            repeat: _outcome_counts(repeat_traces)
            for repeat, repeat_traces in sorted(by_repeat.items())
        },
        "case_profiles": case_profiles,
        "cases_changed": sum(profile["changed"] for profile in case_profiles.values()),
        "pooled": _pooled(traces),
    }


def _pooled(traces):
    searched = [t for t in traces if _stage_succeeded(t, "search")]
    reached_summary = [t for t in traces if _stage_ran(t, "generate_summary")]
    completed = [t for t in traces if t["run_outcome"] == "completed"]
    summaries = [t["stages"]["generate_summary"]["output"] for t in completed]
    return {
        "pico_pass": _rate(
            sum(_stage_succeeded(t, "generate_pico_candidates") for t in traces), len(traces)
        ),
        "strict_zero": _rate(sum(not _search_idlists(t)[0] for t in searched), len(searched)),
        "broadened_zero": _rate(sum(not _search_idlists(t)[-1] for t in searched), len(searched)),
        "failures": _failure_counts(traces),
        "summary_first_attempt_pass": _rate(
            sum(_first_attempt_passed(t) for t in reached_summary), len(reached_summary)
        ),
        "no_clear_answer": _rate(
            sum(NO_CLEAR_ANSWER_LABEL in s for s in summaries), len(completed)
        ),
        "both_labels": _rate(
            sum(NO_CLEAR_ANSWER_LABEL in s and EVIDENCE_SUMMARY_LABEL in s for s in summaries),
            len(completed),
        ),
        "answered": _rate(sum(_answered(t) for t in completed), len(completed)),
        **_citation_counts(completed),
        "leaked_candidates": _leak_count(traces),
        "query_words": _query_word_counts(traces),
    }


def _query_word_counts(traces):
    word_counts = [
        len(f"{pico['population']} {pico['intervention']}".split())
        for t in traces
        if _stage_succeeded(t, "build_search_query")
        for pico in [t["stages"]["select_pico"]["output"]]
    ]
    return {
        "descriptive": _rate(
            sum(count > DESCRIPTIVE_QUERY_WORDS for count in word_counts), len(word_counts)
        ),
        "median": median(word_counts) if word_counts else None,
        "max": max(word_counts) if word_counts else None,
    }


def _normalized(candidate):
    return tuple(
        str(candidate.get(key) or "").strip().lower()
        for key in ("population", "intervention", "comparison", "outcome")
    )


def _leak_count(traces):
    examples = {_normalized(example) for example in EXAMPLE_CANDIDATES}
    candidates = [
        candidate
        for t in traces
        if _stage_succeeded(t, "generate_pico_candidates")
        for candidate in t["stages"]["generate_pico_candidates"]["output"]
    ]
    return _rate(sum(_normalized(c) in examples for c in candidates), len(candidates))


def _citation_counts(completed):
    cited_total = valid_total = invalid_runs = citing_runs = 0
    for trace in completed:
        cited = set(PMID_PATTERN.findall(trace["stages"]["generate_summary"]["output"]))
        if not cited:
            continue
        shown = {abstract["pmid"] for abstract in trace["stages"]["rank"]["output"]}
        citing_runs += 1
        cited_total += len(cited)
        valid_total += len(cited & shown)
        invalid_runs += not cited <= shown
    return {
        "valid_cited_pmids": _rate(valid_total, cited_total),
        "runs_with_invalid_citation": _rate(invalid_runs, citing_runs),
        "runs_citing_nothing": _rate(len(completed) - citing_runs, len(completed)),
    }


def _stage_ran(trace, stage_name):
    return trace["stages"][stage_name]["status"] in ("succeeded", "failed")


def _first_attempt_passed(trace):
    summary = trace["stages"]["generate_summary"]
    return summary["status"] == "succeeded" and len(summary.get("call_records", [])) == 1


def _failure_counts(traces):
    counts = defaultdict(lambda: defaultdict(int))
    for trace in traces:
        for stage_name, record in trace["stages"].items():
            if record["status"] == "failed":
                counts[stage_name][record["failure_tag"]] += 1
    return {stage: dict(tags) for stage, tags in counts.items()}


def _rate(count, of):
    return {"count": count, "of": of}


def _search_idlists(trace):
    return [
        record["response"].get("esearchresult", {}).get("idlist", [])
        for record in trace["stages"]["search"]["call_records"]
    ]


def _case_profile(case_traces):
    outcomes = [t["run_outcome"] for t in sorted(case_traces, key=_repeat)]
    return {"outcomes": outcomes, "changed": len(set(outcomes)) > 1}


def _repeat(trace):
    return trace["run_metadata"].get("repeat", 1)


def _outcome_counts(traces):
    return {
        "runs": len(traces),
        "pico_pass": sum(_stage_succeeded(t, "generate_pico_candidates") for t in traces),
        "completed": sum(t["run_outcome"] == "completed" for t in traces),
        "answered": sum(_answered(t) for t in traces),
        "no_evidence": sum(t["run_outcome"] == "no_evidence" for t in traces),
        "failed": sum(t["run_outcome"] == "failed" for t in traces),
    }


def _stage_succeeded(trace, stage_name):
    return trace["stages"][stage_name]["status"] == "succeeded"


def _answered(trace):
    if trace["run_outcome"] != "completed":
        return False
    return NO_CLEAR_ANSWER_LABEL not in trace["stages"]["generate_summary"]["output"]


def compare_batches(baseline_traces, candidate_traces):
    baseline = _group_by_case(baseline_traces)
    candidate = _group_by_case(candidate_traces)
    shared = sorted(baseline.keys() & candidate.keys())

    cases = {case_id: _paired_case(baseline[case_id], candidate[case_id]) for case_id in shared}
    verdicts = {"improved": 0, "worsened": 0, "unchanged": 0}
    for case in cases.values():
        verdicts[case["verdict"]] += 1

    return {
        "cases": cases,
        "verdicts": verdicts,
        "only_in_baseline": sorted(baseline.keys() - candidate.keys()),
        "only_in_candidate": sorted(candidate.keys() - baseline.keys()),
        "repeats": _repeat_counts(baseline_traces, candidate_traces),
    }


def _repeat_counts(baseline_traces, candidate_traces):
    baseline_repeats = max((_repeat(t) for t in baseline_traces), default=0)
    candidate_repeats = max((_repeat(t) for t in candidate_traces), default=0)
    return {
        "baseline": baseline_repeats,
        "candidate": candidate_repeats,
        "differ": baseline_repeats != candidate_repeats,
    }


def _group_by_case(traces):
    by_case = defaultdict(list)
    for trace in traces:
        by_case[trace["case_id"]].append(trace)
    return by_case


def _outcome_share(traces, outcome):
    return _rate(sum(t["run_outcome"] == outcome for t in traces), len(traces))


def _paired_case(before, after):
    empty_before = _outcome_share(before, "no_evidence")
    empty_after = _outcome_share(after, "no_evidence")
    before_share = empty_before["count"] / empty_before["of"]
    after_share = empty_after["count"] / empty_after["of"]
    if after_share < before_share:
        verdict = "improved"
    elif after_share > before_share:
        verdict = "worsened"
    else:
        verdict = "unchanged"
    return {
        "empty_before": empty_before,
        "empty_after": empty_after,
        "completed_before": _outcome_share(before, "completed"),
        "completed_after": _outcome_share(after, "completed"),
        "verdict": verdict,
    }
