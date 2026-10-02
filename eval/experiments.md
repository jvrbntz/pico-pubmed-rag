# Experiment log

One entry per experiment, written when it runs. Numbers are counts of runs. Raw traces stay local in the gitignored `runs/` folder and are identified here by batch ID and commit. Unless noted, the sample is the 20-case development sample (seed 42, 9 of 20 surgical), used for tuning, not as a test set.

## E1. Baseline (2026-10-01)

Question: how does the pipeline do on a fixed sample before any tuning?

Setup: commit `df72d42`, batch `12b2eee6`, 1 repeat, default sampling.

| Metric | Result |
|---|---|
| PICO pass | 6/20 |
| Zero results after broadening | 6/6 that searched |
| Completed | 0/20 |

All 14 failures were at PICO generation: 13 from the validation rules (6 duplicates, 4 single candidates, 3 null comparisons) and 1 malformed JSON. Conclusion: the rules (2-4 candidates, distinct on population or intervention, comparison required) reject notes that describe a single procedure.

## E2. Validation rules matched to clinical judgment (2026-10-01)

Question: do 1-4 candidates, distinctness on population, intervention, or comparison, and an optional comparison fix the E1 failures?

Setup: code committed as `efc5916`; the batch ran on that code before it was committed, so its traces record `df72d42`. Batch `b0122739`, 1 repeat, default sampling.

| Metric | E1 | E2 |
|---|---|---|
| PICO pass | 6/20 | 15/20 |
| Zero results after broadening | 6/6 | 4/15 |
| Completed | 0/20 | 11/20 |

About 10 of the 11 completed summaries were "No Clear Answer". Conclusion: a large improvement in PICO pass; the bottleneck moved to retrieval.

## E3. Prompt asks for searchable, abstracted PICO questions (2026-10-01)

Question: does instructing the model to drop patient-specific detail (age, laterality, brand names) and allow one candidate and a null comparison reduce empty searches?

Setup: commit `ff91e56`, batch `07215ade`, 1 repeat, default sampling.

| Metric | E2 | E3 |
|---|---|---|
| PICO pass | 15/20 | 13/20 |
| Zero results after broadening | 4/15 | 5/13 |
| Completed | 11/20 | 7/20 |

Conclusion: no measurable change; both differences are within the noise measured in E4. The model followed the abstraction instructions only partly (dates, laterality, and brand names remained in some outputs).

## E4. Run-to-run variance (2026-10-01)

Question: how much do results change between identical runs?

Setup: commit `e36fc0c`, batch `02553567`, 3 repeats, default sampling.

| Repeat | PICO pass | Completed | No evidence | Failed |
|---|---|---|---|---|
| 1 | 16 | 7 | 9 | 4 |
| 2 | 15 | 9 | 6 | 5 |
| 3 | 16 | 9 | 7 | 4 |

14 of 20 cases changed outcome across identical runs. Pooled: PICO pass 47/60; zero results after broadening 22/47 that searched. Conclusion: at this sample size, differences of 3 or fewer runs per count are noise, and single-run comparisons are unreliable.

## E5. Error analysis of empty searches (2026-10-01)

Question: why do searches return nothing?

Setup: the 22 no-evidence runs from E4 (11 distinct notes). The reviewer labeled each note answerable or not (criterion in `README.md`, Error analysis) before seeing any proposed categories; categories were then proposed by an LLM and approved by the reviewer.

| Category | Runs |
|---|---|
| Descriptive phrasing: every word of a long phrase becomes required | 15 |
| Wrong question framed for the note | 4 |
| No answerable question in the note | 3 |

9 of 11 notes were answerable, all as therapy questions. The reviewer overruled 0 of 22 proposed categories; this likely overstates agreement, since the reviewer saw the proposals first. PubMed's query translation confirmed the mechanism: "adults with symptomatic degenerative knee arthritis requiring surgical intervention AND total left knee replacement" returned 0 results, while "knee osteoarthritis AND total knee replacement" returned 16,513. Conclusion: search with short concept terms instead of descriptive PICO phrases.

## E6. Fixed sampling, temperature 0 and seed 42 (2026-10-02)

Question: does fixed sampling make repeated runs identical?

Setup: commit `854a120`, batch `81a7b95b`, cases 207, 720, 1808, 1845, 2024 (all changed outcome in E4), 2 repeats.

| Case | Default sampling (E4): first difference between repeats, in characters | Fixed sampling: first difference |
|---|---|---|
| 207 | 10 | 154 |
| 720 | 52 | 2300 |
| 1808 | 68 | 208 |
| 1845 | 86 | 915 |
| 2024 | 10 | 1080 |

Raw PICO responses still differed in 5 of 5 cases, and the outcome changed in 3 of 5. Responses matched for longer, then split on a near-tie between two words, and the model's long reasoning text (1,500 to 7,500 characters) carried the split into a different answer. Conclusion: fixed sampling reduces variance but does not remove it on this setup; comparisons still need repeats.

## E7. Run-to-run variance under fixed sampling (2026-10-02)

Question: with temperature 0 and seed 42, how much do results still change between identical runs, and do the rates themselves change?

Setup: commit `854a120`, batch `edde8017`, 3 repeats.

| | E4 (default sampling) | E7 (fixed sampling) |
|---|---|---|
| PICO pass per repeat | 16, 15, 16 | 13, 16, 16 |
| Completed per repeat | 7, 9, 9 | 4, 5, 5 |
| Cases that changed outcome across repeats | 14/20 | 9/20 |
| Cases with identical PICO text on every repeat | 0/20 | 0/20 |
| Zero results after broadening, pooled | 22/47 that searched | 28/43 that searched |

Conclusion: fixed sampling reduced outcome changes between repeats but did not remove them, and PICO pass still varied by 3 between repeats. Completed runs were lower under fixed sampling; strict queries had the same length under both settings (median 20 words), so the cause is not yet known. Fixed sampling is kept for experiments, and E7 replaces E4 as the baseline for later comparisons. Correction (2026-10-02): the zero-results denominator was first hand-counted as 28/45, using PICO passes; batch metrics showed 2 runs (cases 247 and 4499) passed PICO but failed at search on a non-JSON response from NCBI, so 43 runs searched.

## E8. Search on short search terms (2026-10-02)

Question: does building the PubMed query from short search terms, produced by a separate model step, reduce empty searches?

Setup: commit `f07cb95`, batch `603eb81b`, 3 repeats, fixed sampling, compared case by case against E7. Thresholds set before running: at least 8 of 20 cases improved and at most 2 worsened on empty searches; zero results after broadening at most 50% of runs that searched; search terms pass at least 90% of runs that reached the step; PICO pass per repeat within 3 of E7. Measurement follows the eval audit: paired at the case level, with mechanism checks.

| Metric | E7 | E8 |
|---|---|---|
| PICO pass per repeat | 13, 16, 16 | 15, 19, 19 |
| Search terms pass | (no step) | 8/53 |
| Runs that searched | 43/60 | 8/60 |
| Zero results after broadening | 28/43 | 0/8 |
| Completed | 14/60 | 7/60 |

Conclusion: failed at the mechanism check (8/53 against at least 90%). 40 of the 45 search-terms failures were a parsing problem: the model writes draft JSON in its reasoning text before the final answer, and the parser read from the first brace to the last, spanning both. The other 5 were caught by validation as intended (lists instead of strings, more than 4 words, an uppercase AND). The paired comparison reported 12 improved and 0 worsened, but that result is invalid: runs that failed before searching were counted as not empty. Recounted with empty searches out of runs that searched: improved 3, worsened 0, unchanged 3, not comparable 14. The 0 of 8 empty searches among runs that did search is a hint only. Next: parse only the text after the reasoning marker, count empty searches out of runs that searched, and rerun as E8b.
