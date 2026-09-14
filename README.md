# pico-pubmed-rag

A clinical evidence-support tool. Given a clinical case, it generates candidate PICO (Population/Intervention/Comparison/Outcome) questions, lets the user pick one, searches PubMed for relevant literature, and returns an evidence-grounded, citation-backed summary.

## Intended use

A portfolio project: a practice prototype applying AI engineering competence on a clinically grounded task. Not intended for patient care. Its output is an evidence summary of retrieved literature, nothing more.

## MVP

The MVP carries one MTSamples case through the full pipeline once: PICO generation, automated position-1 selection, PubMed search, ranking, summary. Rough edges are fine. What matters is that the pipeline runs end to end and produces a PMID-cited summary.

## How it works (v1 scope)

1. Ingest one clinical case (free text) from MTSamples.
2. Generate 2-4 distinct PICO candidates as structured P/I/C/O records, comparable to the gold set. Distinct means differing on Population or Intervention, not just phrasing. Each candidate must trace to the case text.
3. Select one PICO. A human picks in interactive mode. In batch/eval mode, and in the MVP, the top-ranked candidate (position 1) is selected by documented policy.
4. Translate the selected PICO into a PubMed search: MeSH mapping, Boolean structure, publication-type filters. A query returning few or no results broadens automatically, dropping a filter, widening a MeSH term, or dropping a less-essential PICO element.
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
| 2 | PubMed search translation (MeSH mapping, Boolean structure, zero-result broadening) | not started |
| 3 | Ranking + evidence-summary generation (walking skeleton complete once this lands) | not started |
| 4 | Eval harness (gold set, PICO-extraction / retrieval-relevance / faithfulness scoring, latency logging) | not started |

Acceptance criteria per phase are written before that phase's code, and enforced as tests. See `CLAUDE.md`'s Build workflow section.

## Data

Clinical cases come from [MTSamples](https://mtsamples.com) (educational use, with attribution), a de-identified collection of transcribed medical notes. This project pulls the dataset via kagglehub from a Kaggle mirror (tboyle10/medicaltranscriptions, labeled CC0) that scraped mtsamples.com. Field names follow a non-PHI-shaped convention (`case_id`, not `patient_id`) regardless, and no case is modified to inject or simulate real patient identifiers.

## Setup

```bash
uv sync
cp .env.example .env   # fill in NCBI_API_KEY, NCBI_EMAIL, OLLAMA_LLM_MODEL
ollama pull nomic-embed-text
ollama pull <the model tag you set in OLLAMA_LLM_MODEL>
uv run python scripts/download_data.py
```

The last step downloads MTSamples via kagglehub and copies it into `data/` (gitignored). Requires Kaggle API credentials configured on your machine.

Requires Python 3.11+; `uv` will provision it if your system interpreter is older.

## Known limitations

- Input quality from MTSamples can be poor: dictated notes, informal phrasing, abbreviations, incomplete sentences. A bad extraction from a messy case is a different failure than bad reasoning over a clear one, and eval reporting keeps them distinguishable.
- The `medical_specialty` field mixes actual clinical specialties (Surgery, Cardiovascular / Pulmonary) with document types (Discharge Summary, SOAP / Chart / Progress Notes, Letters). Anything that filters or samples by specialty needs to account for this, not treat every value as a real specialty.
- PICO extraction can misframe a clear case (wrong population, intervention, or outcome). This shows up repeatedly on diagnostic-report notes like echocardiograms and imaging follow-ups, where a diagnostic or monitoring action gets labeled as the intervention instead of an actual treatment choice. The failure is silent and propagates through search, ranking, and summary, producing a fluent, well-cited, wrong result.
- Candidate distinctness is enforced by exact string match on population and intervention, not semantic equivalence. Two candidates that describe the same population or intervention in different words can both pass as distinct, even though they aren't.
- Search translation can under- or over-constrain the query: irrelevant results from poor MeSH mapping, or zero results even after broadening, when the literature is genuinely thin.
- External dependencies can fail: NCBI rate limits, downtime, or a fetched record missing a field. This needs retry and backoff, not better prompting.
- Summary generation can hallucinate claims the retrieved abstracts don't support. PMID citations make an unfaithful claim look more credible than an uncited one.

## Key Design Decisions

- Output is scoped to avoid Software as a Medical Device (SaMD) classification: the tool cites and summarizes evidence, never a diagnosis or treatment directive for an individual patient. This keeps it aligned with FDA's non-device Clinical Decision Support carve-out.
- Latency is logged, not scored against a threshold, in v1. Scoring it before the three correctness metrics are reliable risks optimizing speed at correctness's expense. Threshold scoring is deferred to v2.
- The MVP is a walking skeleton: one case through the full pipeline once, rough edges allowed. This proves the architecture holds together before any phase gets polished.
- LLM and embeddings run locally via Ollama (MedGemma 1.5 4B, nomic-embed-text) instead of a hosted API. Chosen to get hands-on experience running open-weight models locally.
- Case ingestion splits into two components: a dataset-cleaning step (runs once on the full CSV) and a case-loading step (runs per case). This avoids re-cleaning the whole dataset every time one case loads.
- PICO-candidate generation takes its LLM call as an injected argument rather than calling Ollama directly. Production code passes the real client; tests pass a fake that returns a fixed response. This keeps the parsing and validation logic (count bounds, distinctness, key structure, malformed-output handling) unit-testable without a live model call.
- A response with any malformed candidate is rejected entirely, not filtered candidate by candidate. Testing against real cases found that a null or missing value usually shows up across every candidate in a response, not just one, so filtering wouldn't have saved the cases that exposed this gap. Retry could fix this more directly and is left for a later, evidence-backed decision.
- PubMed's own automatic term mapping (ATM) is used for MeSH mapping instead of a hand-built lookup. ATM already maps free-text terms to MeSH headings server-side, so building a separate mapping layer would duplicate work PubMed already does. Boolean structure and publication-type filtering are still built by hand, that part isn't automatic.

## Docs

- [`CLAUDE.md`](CLAUDE.md): session-start context for AI-assisted development on this repo
