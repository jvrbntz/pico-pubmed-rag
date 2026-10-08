"""Acceptance-criteria tests for batch metrics in batch_metrics.py."""

import json

from pico_pubmed_rag.batch_metrics import compare_batches, compute_batch_metrics
from pico_pubmed_rag.pico_generation import EXAMPLE_CANDIDATES
from tests.trace_builders import VALID_CANDIDATE, make_trace

def test_per_repeat_counts():
    traces = [
        make_trace(1, repeat=1, outcome="completed"),
        make_trace(2, repeat=1, outcome="failed", failed_stage="generate_pico_candidates"),
        make_trace(1, repeat=2, outcome="no_evidence"),
        make_trace(2, repeat=2, outcome="completed", summary="No Clear Answer: nothing relevant."),
    ]

    per_repeat = compute_batch_metrics(traces)["per_repeat"]

    assert per_repeat[1] == {
        "runs": 2, "pico_pass": 1, "completed": 1, "answered": 1, "no_evidence": 0, "failed": 1,
    }
    assert per_repeat[2] == {
        "runs": 2, "pico_pass": 2, "completed": 1, "answered": 0, "no_evidence": 1, "failed": 0,
    }


def test_case_profiles_flag_cases_whose_outcome_changed():
    traces = [
        make_trace(10, repeat=1, outcome="no_evidence"),
        make_trace(10, repeat=2, outcome="no_evidence"),
        make_trace(20, repeat=1, outcome="completed"),
        make_trace(20, repeat=2, outcome="failed"),
    ]

    metrics = compute_batch_metrics(traces)

    assert metrics["case_profiles"][10] == {"outcomes": ["no_evidence", "no_evidence"], "changed": False}
    assert metrics["case_profiles"][20] == {"outcomes": ["completed", "failed"], "changed": True}
    assert metrics["cases_changed"] == 1


def test_pooled_counts_use_the_right_denominators():
    traces = [
        make_trace(1, outcome="failed", failed_stage="generate_pico_candidates"),
        make_trace(2, outcome="no_evidence"),
        make_trace(3, outcome="completed", broadened=True),
        make_trace(4, outcome="completed"),
    ]

    pooled = compute_batch_metrics(traces)["pooled"]

    assert pooled["pico_pass"] == {"count": 3, "of": 4}
    assert pooled["strict_zero"] == {"count": 2, "of": 3}
    assert pooled["broadened_zero"] == {"count": 1, "of": 3}


def test_failures_are_counted_by_stage_and_tag():
    traces = [
        make_trace(1, outcome="failed", failed_stage="generate_pico_candidates", failure_tag="validation"),
        make_trace(2, outcome="failed", failed_stage="generate_pico_candidates", failure_tag="validation"),
        make_trace(3, outcome="failed", failed_stage="load_case", failure_tag="unexpected"),
        make_trace(4, outcome="failed", failed_stage="generate_summary", failure_tag="validation"),
        make_trace(5, outcome="completed"),
    ]

    failures = compute_batch_metrics(traces)["pooled"]["failures"]

    assert failures == {
        "generate_pico_candidates": {"validation": 2},
        "load_case": {"unexpected": 1},
        "generate_summary": {"validation": 1},
    }


def test_summary_first_attempt_pass_counts_only_runs_that_reached_the_summary():
    traces = [
        make_trace(1, outcome="completed", summary_attempts=1),
        make_trace(2, outcome="completed", summary_attempts=2),
        make_trace(3, outcome="no_evidence"),
    ]

    pooled = compute_batch_metrics(traces)["pooled"]

    assert pooled["summary_first_attempt_pass"] == {"count": 1, "of": 2}


def test_no_clear_answer_both_labels_and_answered_out_of_completed_runs():
    traces = [
        make_trace(1, outcome="completed", summary="No Clear Answer: nothing relevant."),
        make_trace(2, outcome="completed", summary="Evidence Summary: not a recommendation.\nNo Clear Answer: none apply."),
        make_trace(3, outcome="completed", summary="Evidence Summary: A finding (PMID: 1111111)."),
        make_trace(4, outcome="no_evidence"),
    ]

    pooled = compute_batch_metrics(traces)["pooled"]

    assert pooled["no_clear_answer"] == {"count": 2, "of": 3}
    assert pooled["both_labels"] == {"count": 1, "of": 3}
    assert pooled["answered"] == {"count": 1, "of": 3}


def test_citation_validity_compares_cited_pmids_with_abstracts_shown():
    traces = [
        make_trace(1, summary="Evidence Summary: Two findings (PMIDs: 1111111, 9999999).",
                   shown_pmids=("1111111",)),
        make_trace(2, summary="Evidence Summary: A 2019 trial found benefit (PMID: 2222222).",
                   shown_pmids=("2222222", "3333333")),
        make_trace(3, summary="No Clear Answer: none of the abstracts apply."),
    ]

    pooled = compute_batch_metrics(traces)["pooled"]

    assert pooled["valid_cited_pmids"] == {"count": 2, "of": 3}
    assert pooled["runs_with_invalid_citation"] == {"count": 1, "of": 2}
    assert pooled["runs_citing_nothing"] == {"count": 1, "of": 3}


def test_leak_count_matches_example_candidates_on_all_four_fields():
    leaked = {key: f"  {value.upper()} " for key, value in EXAMPLE_CANDIDATES[0].items()}
    one_field_differs = {**EXAMPLE_CANDIDATES[0], "outcome": "length of stay"}
    traces = [
        make_trace(1, candidates=(leaked, VALID_CANDIDATE)),
        make_trace(2, candidates=(one_field_differs,)),
    ]

    pooled = compute_batch_metrics(traces)["pooled"]

    assert pooled["leaked_candidates"] == {"count": 1, "of": 3}


def test_descriptive_queries_flag_more_than_eight_words_of_population_and_intervention():
    eight_words = {**VALID_CANDIDATE, "population": "adults with knee osteoarthritis", "intervention": "total knee replacement surgery"}
    nine_words = {**VALID_CANDIDATE, "population": "older adults with knee osteoarthritis", "intervention": "total knee replacement surgery"}
    traces = [
        make_trace(1, candidates=(eight_words,)),
        make_trace(2, candidates=(nine_words,)),
        make_trace(3, outcome="failed", failed_stage="generate_pico_candidates"),
    ]

    queries = compute_batch_metrics(traces)["pooled"]["query_words"]

    assert queries["descriptive"] == {"count": 1, "of": 2}
    assert queries["median"] == 8.5
    assert queries["max"] == 9


def test_paired_comparison_gives_a_verdict_per_shared_case_and_lists_unmatched_cases():
    baseline = [
        make_trace(1, repeat=1, outcome="no_evidence"),
        make_trace(1, repeat=2, outcome="no_evidence"),
        make_trace(2, repeat=1, outcome="completed"),
        make_trace(2, repeat=2, outcome="completed"),
    ]
    candidate = [
        make_trace(1, repeat=1, outcome="completed"),
        make_trace(1, repeat=2, outcome="no_evidence"),
        make_trace(2, repeat=1, outcome="no_evidence"),
        make_trace(2, repeat=2, outcome="completed"),
        make_trace(4, repeat=1, outcome="completed"),
    ]

    comparison = compare_batches(baseline, candidate)

    assert comparison["cases"][1] == {
        "empty_before": {"count": 2, "of": 2}, "empty_after": {"count": 1, "of": 2},
        "completed_before": {"count": 0, "of": 2}, "completed_after": {"count": 1, "of": 2},
        "verdict": "improved",
    }
    assert comparison["cases"][2]["verdict"] == "worsened"
    assert comparison["verdicts"] == {"improved": 1, "worsened": 1, "unchanged": 0, "not comparable": 0}
    assert comparison["only_in_baseline"] == []
    assert comparison["only_in_candidate"] == [4]


def test_paired_comparison_states_when_repeat_counts_differ():
    baseline = [make_trace(1, repeat=r, outcome="no_evidence") for r in (1, 2, 3)]
    candidate = [
        make_trace(1, repeat=1, outcome="no_evidence"),
        make_trace(1, repeat=2, outcome="completed"),
    ]

    comparison = compare_batches(baseline, candidate)

    assert comparison["cases"][1]["verdict"] == "improved"
    assert comparison["repeats"] == {"baseline": 3, "candidate": 2, "differ": True}


def test_empty_batch_gives_zeros_and_traces_without_repeat_count_as_repeat_one():
    empty = compute_batch_metrics([])
    assert empty["per_repeat"] == {}
    assert empty["pooled"]["pico_pass"] == {"count": 0, "of": 0}
    assert empty["pooled"]["query_words"]["median"] is None

    smoke_trace = make_trace(87, outcome="completed")
    del smoke_trace["run_metadata"]["repeat"]
    assert compute_batch_metrics([smoke_trace])["per_repeat"][1]["completed"] == 1


def test_query_words_come_from_search_terms_when_present_and_terms_pass_rate_is_reported():
    long_pico = {**VALID_CANDIDATE, "population": "older adults with severe symptomatic knee osteoarthritis",
                 "intervention": "total knee replacement surgery"}
    traces = [
        make_trace(1, candidates=(long_pico,),
                   search_terms={"population_terms": "knee osteoarthritis", "intervention_terms": "knee replacement"}),
        make_trace(2, candidates=(long_pico,)),
        make_trace(3, candidates=(long_pico,), search_terms_failed=True),
    ]

    pooled = compute_batch_metrics(traces)["pooled"]

    assert pooled["query_words"]["median"] == 7.5
    assert pooled["query_words"]["max"] == 11
    assert pooled["search_terms_pass"] == {"count": 1, "of": 2}


def test_paired_comparison_counts_empty_searches_only_among_runs_that_searched():
    baseline = [
        make_trace(1, repeat=1, outcome="no_evidence"),
        make_trace(1, repeat=2, outcome="no_evidence"),
        make_trace(2, repeat=1, outcome="no_evidence"),
        make_trace(2, repeat=2, outcome="completed"),
    ]
    candidate = [
        make_trace(1, repeat=1, search_terms_failed=True),
        make_trace(1, repeat=2, search_terms_failed=True),
        make_trace(2, repeat=1, outcome="no_evidence"),
        make_trace(2, repeat=2, search_terms_failed=True),
    ]

    comparison = compare_batches(baseline, candidate)

    assert comparison["cases"][1]["empty_after"] == {"count": 0, "of": 0}
    assert comparison["cases"][1]["verdict"] == "not comparable"
    assert comparison["cases"][2]["empty_before"] == {"count": 1, "of": 2}
    assert comparison["cases"][2]["empty_after"] == {"count": 1, "of": 1}
    assert comparison["cases"][2]["verdict"] == "worsened"
    assert comparison["verdicts"]["not comparable"] == 1


def test_repetitive_summaries_are_counted():
    repeated = "No Clear Answer: the abstracts do not address this comparison in this population."
    traces = [
        make_trace(1, summary="\n".join([repeated] * 3)),
        make_trace(2, summary="Evidence Summary: A finding (PMID: 1111111).\nA second, different point."),
        make_trace(3, outcome="no_evidence"),
    ]

    pooled = compute_batch_metrics(traces)["pooled"]

    assert pooled["repetitive_summaries"] == {"count": 1, "of": 2}


def test_runs_with_dropped_pico_duplicates_are_counted():
    other_outcome = {**VALID_CANDIDATE, "outcome": "function"}
    traces = [
        make_trace(1, pico_response=json.dumps([VALID_CANDIDATE, other_outcome])),
        make_trace(2, pico_response=json.dumps([VALID_CANDIDATE])),
        make_trace(3, outcome="failed", failed_stage="generate_pico_candidates"),
    ]

    pooled = compute_batch_metrics(traces)["pooled"]

    assert pooled["pico_duplicates_dropped"] == {"count": 1, "of": 2}


def test_selected_pico_checks_are_counted():
    clean = {**VALID_CANDIDATE, "comparison": "physiotherapy"}
    no_comparison = {**VALID_CANDIDATE, "comparison": None}
    finding_outcome = {**clean, "outcome": "Successful completion of the procedure"}
    echoes_intervention = {**clean, "outcome": "knee replacement durability"}
    overlap = {**clean, "population": "umbilical hernia", "intervention": "umbilical hernia repair"}
    traces = [
        make_trace(1, candidates=(clean,)),
        make_trace(2, candidates=(no_comparison,)),
        make_trace(3, candidates=(finding_outcome,)),
        make_trace(4, candidates=(echoes_intervention,)),
        make_trace(5, candidates=(overlap,)),
        make_trace(6, outcome="failed", failed_stage="generate_pico_candidates"),
    ]

    pooled = compute_batch_metrics(traces)["pooled"]

    assert pooled["pico_comparison_empty"] == {"count": 1, "of": 5}
    assert pooled["pico_outcome_is_procedure_finding"] == {"count": 1, "of": 5}
    assert "pico_population_overlaps_intervention" not in pooled


def test_no_clinical_decision_failures_are_counted():
    no_decision = make_trace(1, outcome="failed", failed_stage="generate_pico_candidates")
    no_decision["stages"]["generate_pico_candidates"]["traceback"] = (
        "Traceback (most recent call last):\nValueError: No clinical decision in the note\n"
    )
    other_failure = make_trace(2, outcome="failed", failed_stage="generate_pico_candidates")
    other_failure["stages"]["generate_pico_candidates"]["traceback"] = "ValueError: LLM response was not valid JSON\n"

    pooled = compute_batch_metrics([no_decision, other_failure, make_trace(3)])["pooled"]

    assert pooled["pico_no_clinical_decision"] == {"count": 1, "of": 3}


def test_dropped_duplicates_counted_from_answer_after_reasoning():
    final = json.dumps({"clinical_decision": "Knee replacement chosen.", "candidates": [VALID_CANDIDATE]})
    response = f"<unused94>thought\nDraft: [1, 2, 3]<unused95>{final}"

    pooled = compute_batch_metrics([make_trace(1, pico_response=response)])["pooled"]

    assert pooled["pico_duplicates_dropped"] == {"count": 0, "of": 1}
