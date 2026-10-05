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

## E8b. Search terms with the parsing fix (2026-10-02)

Question: with search terms parsed only from the final answer, does the search-terms change meet the thresholds set for E8?

Setup: commit `0970700`, batch `c198c7aa`, 3 repeats, fixed sampling, compared case by case against E7 with the same pre-set thresholds as E8. Changes since E8: search terms are parsed only from the text after the model's reasoning; short connecting words (of, the, to) do not count toward the 4-word limit; a one-item list is accepted as its string; the digit rule rejects only ages, doses, and numbers of 3 or more digits.

| Metric | E7 | E8b |
|---|---|---|
| PICO pass per repeat | 13, 16, 16 | 15, 19, 19 |
| Search terms pass | (no step) | 48/53 |
| Zero results after broadening | 28/43 that searched | 2/48 that searched |
| Completed | 14/60 | 42/60 |
| Answered | 1/14 completed | 1/42 completed |
| No Clear Answer | 13/14 completed | 41/42 completed |
| Words searched, population and intervention combined, median | 12 | 4 |

Paired by case, with empty searches counted out of runs that searched: improved 11, worsened 0, unchanged 5, not comparable 4.

Conclusion: met every threshold set before running (search terms pass 91% against at least 90%; 11 improved and 0 worsened against at least 8 and at most 2; zero results 4% against at most 50%; PICO pass within 3 of E7). Empty searches fell from 65% to 4% of searches, and completed runs tripled. The bottleneck has moved to the summary step: 41 of 42 completed summaries declined to answer, 40 of them carrying both labels. 4 runs failed at parsing, a failure that was rare while few runs reached it.

## E9. Complete abstracts (2026-10-05)

Question: with abstracts parsed from all their sections, do summaries answer more often?

Setup: commit `3e15703`, batch `fdf1e0e4`, 3 repeats, fixed sampling, compared against E8b. Thresholds set before running: answered at least 10% of completed; 0 parse failures and median abstract shown at least 1,500 characters; completed at least 36 of 60; cited PMIDs 100% valid. Abstract length was computed from the traces directly, since batch metrics does not report it.

| Metric | E8b | E9 |
|---|---|---|
| Answered | 1/42 completed | 11/36 completed |
| No Clear Answer | 41/42 | 25/36 |
| Median abstract shown, characters | about 350 | 2,058 |
| Parse failures | 4 | 0 |
| Completed | 42/60 | 36/60 |
| Summary failures | 0 | 10 |
| Valid cited PMIDs | 63/63 | 48/48 |

Conclusion: met every threshold set before running, with completed exactly at the bar. Answered summaries rose from 1 to 11. Summary failures rose from 0 to 10: 3 responses ignored the prompt's rules, 2 were reasoning text that never finished, 4 cited no PMID, and 1 had no abstracts left after dropping. A direct check found the cause: Ollama used its default 2,048-token context window and cut prompts from the start, so a failing 18,282-character summary prompt was processed as 2,051 tokens without its instructions. In E9, 49 of 56 summary prompts and 9 of 60 PICO prompts exceeded the window, so most E9 summaries were written without seeing their rules, and long notes have reached PICO generation without its rules in every batch since E1. Next: set the context window explicitly and rerun as E10.
