# pico-pubmed-rag

A clinical evidence-support tool. Given a clinical case, it generates candidate PICO (Population/Intervention/Comparison/Outcome) questions, lets the user pick one, searches PubMed for relevant literature, and returns an evidence-grounded, citation-backed summary.

## Intended use

A portfolio project: a practice prototype applying AI engineering competence on a clinically grounded task. Not intended for patient care. Its output is an evidence summary of retrieved literature, nothing more.

## MVP

The MVP carries one MTSamples case through the full pipeline once: PICO generation, automated position-1 selection, PubMed search, ranking, summary. Rough edges are fine. What matters is that the pipeline runs end to end and produces a PMID-cited summary.

## How it works (v1 scope)

1. Ingest one clinical case (free text) from MTSamples.
2. Generate 1-4 distinct PICO candidates as structured P/I/C/O records, comparable to the gold set. Distinct means differing on Population, Intervention, or Comparison, not just phrasing. Comparison may be empty when the note states none. Each candidate must trace to the case text.
3. Select one PICO. A human picks in interactive mode. In batch/eval mode, and in the MVP, the top-ranked candidate (position 1) is selected by documented policy.
4. Turn the selected PICO into a PubMed search: the model names the population and intervention as short search terms (1 to 4 words each), validated in code, and the query combines them with Boolean structure and publication-type filters, leaving MeSH mapping to PubMed. A query returning few or no results broadens automatically, dropping a filter, widening a MeSH term, or dropping a less-essential PICO element.
5. Query PubMed via NCBI E-utilities (esearch, efetch). Each abstract carries PMID, title, text, publication type, and publication date.
6. Embed retrieved abstracts into an in-memory index, scoped to the session and discarded after. PubMed changes continuously; a persistent index would go stale.
7. Rank by publication type (systematic review and RCT weighted above case report and cohort) and recency.
8. Generate a summary grounded in the ranked abstracts. Cite a PMID for every claim. Label the output as an evidence summary.

## Out of scope (v1)

Parking lot for mid-build feature ideas, logged here and not built:

- Multi-turn conversation / follow-up questions about the summary
- Persistent storage of cases, queries, or retrieved literature across sessions
- Data sources other than MTSamples, or search sources other than PubMed
- Fine-tuned/custom-trained models (off-the-shelf LLM + embedding APIs only)
- A UI beyond what's needed to demonstrate the pipeline (CLI or minimal web form)
- Automatic PICO selection in interactive mode (a human always picks; see batch-mode exception above)
- Confidence scoring/calibration on the summary's claims

## Eval

A hand-annotated gold set of 15-20 MTSamples cases, held fixed once created, scored on:

- PICO-extraction quality: candidates against the gold PICO framing.
- Retrieval relevance: whether the top-K ranked abstracts are relevant to the gold PICO.
- Faithfulness (RAGAS-style): whether summary claims trace to retrieved evidence.

Batch-mode eval scores against the position-1 candidate, stated as policy in every report. This keeps a weak position-1 candidate distinguishable from weak retrieval or an unfaithful summary.

Latency, case-in to summary-out, is logged per run but not scored against a threshold in v1. Threshold-scoring waits until the three quality metrics above are reliable. See Key Design Decisions.

## Status

| Phase | Delivers | Status |
|---|---|---|
| 1 | Repo scaffolding + case ingestion + PICO-candidate generation | done |
| 2 | PubMed search translation, retrieval, and parsing (MeSH mapping, Boolean structure, zero-result broadening, esearch/efetch, abstract parsing) | done |
| 3 | Ranking + evidence-summary generation (walking skeleton complete once this lands) | done |
| 4 | Eval harness (gold set, PICO-extraction / retrieval-relevance / faithfulness scoring, latency logging) | in progress |
| 5 | Embeddings re-ranking (lexical vs hybrid, measured on the gold set) and results write-up | not started |

Acceptance criteria per phase are written before that phase's code, and enforced as tests. See `CLAUDE.md`'s Build workflow section.

## Data

Clinical cases come from [MTSamples](https://mtsamples.com) (educational use, with attribution), a de-identified collection of transcribed medical notes. This project pulls the dataset via kagglehub from a Kaggle mirror (tboyle10/medicaltranscriptions, labeled CC0) that scraped mtsamples.com. Field names follow a non-PHI-shaped convention (`case_id`, not `patient_id`) regardless, and no case is modified to inject or simulate real patient identifiers.

## Setup

```bash
uv sync
cp .env.example .env   # fill in NCBI_EMAIL (required); NCBI_API_KEY and OLLAMA_HOST are optional
ollama pull nomic-embed-text
ollama pull <the model tag you set in OLLAMA_LLM_MODEL>
uv run python scripts/download_data.py
```

The last step downloads MTSamples via kagglehub and copies it into `data/` (gitignored). Requires Kaggle API credentials configured on your machine.

Requires Python 3.11+; `uv` will provision it if your system interpreter is older.

## Running it

`uv run python scripts/try_full_pipeline.py` runs one MTSamples case through the full pipeline against the local model and live PubMed, prints its trace (each stage's status, service, and latency, the search queries sent, and the summary), and appends it to `runs/smoke_runs.jsonl`. `uv run python scripts/run_batch.py --size 20 --seed 42` runs a seeded sample of cases and saves every trace to a timestamped file in `runs/`, logging progress as it goes. `scripts/export_review_sheet.py` turns a batch file's runs into a CSV sheet for error analysis. `uv run python scripts/batch_metrics.py <batch file> --baseline <batch file>` reports a batch's metrics and compares it with a baseline case by case. `uv run pytest` runs the test suite, which uses fakes and needs neither Ollama nor network access.

## Known limitations

- Input quality from MTSamples can be poor: dictated notes, informal phrasing, abbreviations, incomplete sentences. A bad extraction from a messy case is a different failure than bad reasoning over a clear one, and eval reporting keeps them distinguishable.
- The `medical_specialty` field mixes actual clinical specialties (Surgery, Cardiovascular / Pulmonary) with document types (Discharge Summary, SOAP / Chart / Progress Notes, Letters). Anything that filters or samples by specialty needs to account for this, not treat every value as a real specialty.
- PICO extraction can misframe a clear case (wrong population, intervention, or outcome). This shows up repeatedly on diagnostic-report notes like echocardiograms and imaging follow-ups, where a diagnostic or monitoring action gets labeled as the intervention instead of an actual treatment choice. The failure is silent and propagates through search, ranking, and summary, producing a fluent, well-cited, wrong result.
- PICO candidates can be entirely unrelated to the case, not just misframed. Observed once on 2026-09-16: a candidate for "adults with confirmed strep throat, amoxicillin" generated for a case entirely about bariatric surgery, verbatim matching `build_prompt`'s own worked example. The model leaked its few-shot example back as content instead of treating it as a format template. The prompt now explicitly instructs against reusing the example; not yet confirmed whether this fully resolves it.
- Candidate distinctness is enforced by exact string match on population, intervention, and comparison, not semantic equivalence. Two candidates that describe the same question in different words can both pass as distinct, even though they aren't.
- Search translation can under- or over-constrain the query: irrelevant results from poor MeSH mapping, or zero results even after broadening, when the literature is genuinely thin.
- External dependencies can fail: NCBI rate limits, downtime, or a fetched record missing a field. This needs retry and backoff, not better prompting.
- Summary generation can hallucinate claims the retrieved abstracts don't support. PMID citations make an unfaithful claim look more credible than an uncited one.
- Abstracts are assembled from all of their sections, each keeping its label (BACKGROUND, RESULTS, CONCLUSIONS), and articles without an abstract are dropped. Before 2026-10-05 only the first section was kept, so the model usually saw only the background; summaries from earlier batches (E1 to E8b) were written from truncated abstracts.
- Zero-result broadening only tries one fallback: dropping the publication-type filter. It does not yet widen MeSH terms or drop a less-essential PICO element if that single broadening step still returns nothing.
- Searches use only the population and intervention search terms, never comparison or outcome (see Key Design Decisions). Searches can match abstracts about the right population and intervention that never address the actual comparison being asked about, which is a real, observed cause of `generate_summary`'s abstracts-don't-answer-the-question responses, not just a search-relevance issue.

## Key Design Decisions

- Output is scoped to avoid Software as a Medical Device (SaMD) classification: the tool cites and summarizes evidence, never a diagnosis or treatment directive for an individual patient. This keeps it aligned with FDA's non-device Clinical Decision Support carve-out.
- Latency is logged, not scored against a threshold, in v1. Scoring it before the three correctness metrics are reliable risks optimizing speed at correctness's expense. Threshold scoring is deferred to v2.
- The MVP is a walking skeleton: one case through the full pipeline once, rough edges allowed. This proves the architecture holds together before any phase gets polished.
- LLM and embeddings run locally via Ollama (MedGemma 1.5 4B, nomic-embed-text) instead of a hosted API. Chosen to get hands-on experience running open-weight models locally.
- Case ingestion splits into two components: a dataset-cleaning step (runs once on the full CSV) and a case-loading step (runs per case). This avoids re-cleaning the whole dataset every time one case loads.
- PICO-candidate generation takes its LLM call as an injected argument rather than calling Ollama directly. Production code passes the real client; tests pass a fake that returns a fixed response. This keeps the parsing and validation logic (count bounds, distinctness, key structure, malformed-output handling) unit-testable without a live model call.
- A response with any malformed candidate is rejected entirely, not filtered candidate by candidate. Testing against real cases found that a null or missing value usually shows up across every candidate in a response, not just one, so filtering wouldn't have saved the cases that exposed this gap. Retry could fix this more directly and is left for a later, evidence-backed decision.
- PubMed's own automatic term mapping (ATM) is used for MeSH mapping instead of a hand-built lookup. ATM already maps free-text terms to MeSH headings server-side, so building a separate mapping layer would duplicate work PubMed already does. Boolean structure and publication-type filtering are still built by hand, that part isn't automatic.
- `publication_type` captures every `PublicationType` value per article as a list, not just the first. A live query on 2026-09-15 showed why: every result came back as "Journal Article" only, even though the search filtered for RCT/systematic review, since the first parsing pass grabbed the generic type instead of the one that actually matched.
- Zero-result broadening is a separate function from `search_pubmed`, not a change to it. Modifying `search_pubmed` directly to retry internally would have broken its own already-tested guarantee that it returns `[]` on zero results with no retry.
- Summary generation skips the embedding/in-memory-index step for now, working directly off ranked abstracts. Ranking already selects by evidence tier and recency, and with only ~10 fetched abstracts, embeddings aren't proven necessary yet. Still planned via nomic-embed-text, once the simpler version runs end to end.
- Each pipeline run returns a trace instead of raising on failure. `run_pipeline` records every stage's status, output, and latency, plus every model and NCBI call it made, including retried attempts and broadened searches. A stage failure ends the run with a recorded reason, so a batch of cases keeps going and failures can be counted.
- Run traces are saved to disk, including the case text and the abstracts each run retrieved. They are a record of what a run saw, used for evaluation, not a store the pipeline reads from: every run still searches PubMed live. They live in a gitignored `runs/` folder.
- PICO validation accepts 1-4 candidates, treats a different comparison as a distinct question, and allows an empty comparison. On a 20-case development batch on 2026-10-01, 13 of 14 PICO failures came from the earlier rules (2-4 candidates, distinct on population or intervention only, comparison required). Notes describing a single procedure contain one decision and often no stated comparator, so the earlier rules pushed the model to pad its answer or invent a comparator.
- The PICO stays a descriptive clinical question, and search runs on separate short terms. PubMed's automatic term mapping splits an unquoted phrase into words that must all appear, so descriptive phrases found nothing: on 2026-10-01, "adults with symptomatic degenerative knee arthritis requiring surgical intervention AND total left knee replacement" returned 0 results while "knee osteoarthritis AND total knee replacement" returned 16,513. A separate step asks the model only for short terms, so PICO generation is unchanged and the descriptive question still drives the summary and the gold-set comparison. Comparison and outcome are left out of the search, as in standard systematic-review search practice, and are used in the summary instead.

## Docs

- [`CLAUDE.md`](CLAUDE.md): session-start context for AI-assisted development on this repo
