# eval/

This directory records how this project is evaluated: the procedure, the gold set, and the results.

## Status

Nothing has been measured yet. There's no gold set and no eval has been run, so nothing in this repo says how good the PICO extraction, retrieval, or summaries actually are.

## Operational metrics

Computed from run traces. No hand labels needed, only a fixed sample of cases. Traces record each call, but aren't saved to disk yet, so none of them can be counted today.

| Metric | Measures | How counted |
|---|---|---|
| Leak rate | PICO candidates copied from the prompt's worked example | Candidates whose four fields all exactly match an example candidate, over all candidates generated |
| PICO pass rate | PICO responses that pass validation | Calls that pass validation, over all PICO calls. There's no retry yet, so a failure raises |
| Summary first-attempt pass rate | Summaries that pass validation without a retry | Calls where the first response passes, over all summary calls |
| No Clear Answer rate | Summaries where the model declines to answer | Summaries labeled "No Clear Answer:", over all summaries |
| Zero-result rate | Searches that find nothing | Runs where the strict query returns zero PMIDs, and separately, runs where the broadened query also returns zero |

## Quality metrics

Computed on the gold set. These need hand labels.

| Metric | Measures | How scored |
|---|---|---|
| Retrieval precision@5 | How relevant the top 5 ranked abstracts are | Relevant abstracts among the top 5, averaged over the gold cases, relevance judged by hand |
| PICO extraction quality | How well generated candidates match the gold PICO | Scoring method defined with the gold set |
| Faithfulness | Whether summary claims are supported by the abstracts they cite | Not defined yet |

## Gold set

Not created yet. Two files will live in this directory.

`gold_set.jsonl` has one record per case: `case_id` (matching the cleaned dataset), `gold_pico` (population, intervention, comparison, outcome), and `no_answerable_pico`, true for notes with no treatment decision.

`relevance.jsonl` has one record per case and PMID pair: `case_id`, `pmid`, `relevant` (yes or no), and the date judged.

Cases are a seeded random sample of 15-20 from the cleaned dataset, with the seed recorded here once chosen. Weak notes, such as diagnostic reports with no treatment decision, are kept and flagged `no_answerable_pico`, not excluded.

The gold PICO is the main clinical decision in the note's plan, in plain phrasing. Cases are annotated before looking at any system output. If a note has more than one defensible decision point, the primary one is recorded. An abstract is relevant if it studies the case PICO's population and intervention and reports the comparison or the outcome.

There is one annotator, the project author, so no agreement measure is possible. The gold PICO and the relevance labels are made by hand, with no LLM judge.