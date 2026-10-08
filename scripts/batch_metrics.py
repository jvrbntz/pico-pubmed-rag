"""Prints operational metrics for a batch file as Markdown tables, and a paired comparison against a baseline batch when one is given."""

import argparse

from pico_pubmed_rag.batch_metrics import compare_batches, compute_batch_metrics
from pico_pubmed_rag.trace_file import read_traces


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch_file", help="batch file to report on")
    parser.add_argument("--baseline", help="baseline batch file for a paired, case-by-case comparison")
    return parser.parse_args()


def fmt(rate):
    return f"{rate['count']}/{rate['of']}"


def print_metrics(name, metrics):
    print(f"## {name}\n")
    print("| Repeat | Runs | PICO pass | Completed | Answered | No evidence | Failed |")
    print("|---|---|---|---|---|---|---|")
    for repeat, counts in metrics["per_repeat"].items():
        print(
            f"| {repeat} | {counts['runs']} | {counts['pico_pass']} | {counts['completed']} "
            f"| {counts['answered']} | {counts['no_evidence']} | {counts['failed']} |"
        )
    print(f"\nCases whose outcome changed across repeats: {metrics['cases_changed']}/{len(metrics['case_profiles'])}\n")

    pooled = metrics["pooled"]
    print("| Pooled metric | Result |")
    print("|---|---|")
    rows = [
        ("PICO pass", fmt(pooled["pico_pass"])),
        ("Search terms pass (of runs that reached the stage)", fmt(pooled["search_terms_pass"])),
        ("Strict query zero results (of runs that searched)", fmt(pooled["strict_zero"])),
        ("Zero results after broadening (of runs that searched)", fmt(pooled["broadened_zero"])),
        ("Summary first-attempt pass (of runs that reached the summary)", fmt(pooled["summary_first_attempt_pass"])),
        ("No Clear Answer (of completed)", fmt(pooled["no_clear_answer"])),
        ("Both labels (of completed)", fmt(pooled["both_labels"])),
        ("Answered (of completed)", fmt(pooled["answered"])),
        ("Repetitive summaries, a line repeated 3+ times (of completed)", fmt(pooled["repetitive_summaries"])),
        ("Valid cited PMIDs (of cited PMIDs)", fmt(pooled["valid_cited_pmids"])),
        ("Runs with an invalid citation (of runs that cite)", fmt(pooled["runs_with_invalid_citation"])),
        ("Runs citing nothing (of completed)", fmt(pooled["runs_citing_nothing"])),
        ("Leaked example candidates (of candidates)", fmt(pooled["leaked_candidates"])),
        ("PICO responses with duplicates dropped (of PICO passes)", fmt(pooled["pico_duplicates_dropped"])),
        ("Descriptive queries, over 8 words searched (of queries)", fmt(pooled["query_words"]["descriptive"])),
        ("Query words, median / max", f"{pooled['query_words']['median']} / {pooled['query_words']['max']}"),
    ]
    for label, value in rows:
        print(f"| {label} | {value} |")

    print("\nFailures by stage and tag:")
    for stage, tags in pooled["failures"].items():
        print(f"- {stage}: " + ", ".join(f"{tag} {count}" for tag, count in tags.items()))
    print()


def print_comparison(comparison):
    print("## Paired comparison, per case\n")
    repeats = comparison["repeats"]
    if repeats["differ"]:
        print(f"Repeat counts differ: baseline {repeats['baseline']}, candidate {repeats['candidate']}; shares are compared.\n")
    print("Empty searches are counted out of the runs that searched.\n")
    print("| Case | Empty before | Empty after | Completed before | Completed after | Verdict |")
    print("|---|---|---|---|---|---|")
    for case_id, case in comparison["cases"].items():
        print(
            f"| {case_id} | {fmt(case['empty_before'])} | {fmt(case['empty_after'])} "
            f"| {fmt(case['completed_before'])} | {fmt(case['completed_after'])} | {case['verdict']} |"
        )
    verdicts = comparison["verdicts"]
    print(
        f"\nImproved {verdicts['improved']}, worsened {verdicts['worsened']}, "
        f"unchanged {verdicts['unchanged']}, not comparable {verdicts['not comparable']}."
    )
    if comparison["only_in_baseline"] or comparison["only_in_candidate"]:
        print(f"Only in baseline: {comparison['only_in_baseline']}; only in candidate: {comparison['only_in_candidate']}")


if __name__ == "__main__":
    args = parse_args()
    candidate = read_traces(args.batch_file)
    print_metrics(args.batch_file, compute_batch_metrics(candidate))
    if args.baseline:
        baseline = read_traces(args.baseline)
        print_metrics(args.baseline, compute_batch_metrics(baseline))
        print_comparison(compare_batches(baseline, candidate))
