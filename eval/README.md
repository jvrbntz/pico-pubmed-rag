# eval/

This directory records how this project is evaluated: the procedure, the gold set, and the results.

## Status

Operational metrics are counted by `scripts/batch_metrics.py` on a 20-case development batch (seed 42), used for error analysis and tuning, not as a test set. There's no gold set yet, so nothing in this repo says how good the PICO extraction, retrieval, or summaries actually are. Experiment history, with each run's question, setup, and result, is in `experiments.md`.

## Operational metrics

Computed from run traces. No hand labels needed, only a fixed sample of cases. Batches run with `scripts/run_batch.py` and save traces to `runs/`. `scripts/batch_metrics.py` counts them per repeat, per case, and pooled, and compares two batches case by case.

| Metric | Measures | How counted |
|---|---|---|
| Leak rate | PICO candidates copied from the prompt's worked example | Candidates whose four fields all exactly match an example candidate, over all candidates generated |
| PICO pass rate | PICO responses that pass validation | Calls that pass validation, over all PICO calls. There's no retry yet, so a failure raises |
| Summary first-attempt pass rate | Summaries that pass validation without a retry | Calls where the first response passes, over all summary calls |
| No Clear Answer rate | Summaries where the model declines to answer | Summaries labeled "No Clear Answer:", over all summaries |
| Zero-result rate | Searches that find nothing | Runs where the strict query returns zero PMIDs, and separately, runs where the broadened query also returns zero |
| Citation validity | Summaries citing PMIDs that were never fetched | Cited PMIDs found among the run's fetched PMIDs, over all cited PMIDs |
| Answered | Completed summaries that answer instead of declining | Completed runs whose summary has no "No Clear Answer:" label, over completed runs |
| Both labels | Summaries carrying both labels | Completed summaries containing "Evidence Summary:" and "No Clear Answer:", over completed runs |
| Search terms pass | Search terms that pass validation | Runs where the search-terms step succeeds, over runs that reached it |
| Descriptive queries | Searches phrased as descriptions | Queries whose population and intervention exceed 8 words, over queries built |

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

Cases are a seeded random sample of 15-20 from the cleaned dataset, drawn with a different seed from the development batch and excluding its 20 cases, with the seed recorded here once chosen. Weak notes, such as diagnostic reports with no treatment decision, are kept and flagged `no_answerable_pico`, not excluded.

The gold PICO is the main clinical decision in the note's plan, in plain phrasing. Cases are annotated before looking at any system output. If a note has more than one defensible decision point, the primary one is recorded. An abstract is relevant if it studies the case PICO's population and intervention and reports the comparison or the outcome.

There is one annotator, the project author, so no agreement measure is possible. The gold PICO and the relevance labels are made by hand, with no LLM judge.

## Error analysis

Failed and empty-search runs are reviewed by hand, one run at a time. Each run gets a one-sentence note on what went wrong, then a category assigned after all runs in the review are read.

Each note behind a reviewed run is also marked answerable or not. A note is answerable when all of these hold: the note's clinician faced a decision about care; the decision is a foreground question of type therapy, diagnosis, prognosis, or etiology/harm; population, intervention, and outcome can be stated for a definable group of patients, with comparison optional; and published studies on it plausibly exist. Answerable notes also record the question type. Criteria as of 2026-10-01, revised if grading changes them.
