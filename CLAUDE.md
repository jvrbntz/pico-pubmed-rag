# CLAUDE.md

Session-start context only. For scope, architecture, and eval design see `README.md`.

## What this is

A clinical evidence-support tool: clinical case → candidate PICO queries → user picks one → PubMed search → ranked, evidence-grounded summary with citations. Portfolio project, not a clinical tool. See `README.md`'s Intended Use section.

## Stack

- Python 3.11+
- LLM: MedGemma 1.5 4B via local Ollama, for PICO generation and summary generation
- Retrieval: NCBI E-utilities (esearch/efetch) against PubMed; no third-party search API
- Embeddings: nomic-embed-text via local Ollama; index is in-memory only (session-scoped), no persistent vector DB
- Eval: hand-annotated gold set (`eval/gold_set.jsonl`, 15-20 MTSamples cases), RAGAS-style faithfulness scoring
- Data: MTSamples (public, non-PHI transcribed samples); attribution required, see README

## Hard constraints

- No PHI, ever. Data is public/synthetic only (MTSamples). Non-PHI-shaped field names (`case_id`, not `patient_id`).
- No persistent storage of retrieved literature or embeddings across sessions: retrieval index is ephemeral, rebuilt per session, discarded after.
- Output must explicitly self-label as an evidence summary, not a diagnostic or treatment recommendation; this is stated in the output itself, not just the README.
- No naive keyword-concatenation search: PubMed queries go through MeSH mapping + Boolean structure + publication-type filters.
- Scope-first workflow: acceptance criteria are written before implementation. `README.md`'s scope sections define what a phase covers and aren't rewritten to match the code after the fact. If the code diverges from what's written there, that's a decision recorded in the commit message, not a reason to silently edit the README's scope.

## Build workflow

README's phase table groups related work into milestones. The unit of work is the component within a phase, not the phase itself: Phase 1's dataset-cleaning, case-loading, and PICO-candidate generation are three separate components, each with its own acceptance criteria and tests.

Before starting a component, write its acceptance criteria as a short list, concrete and checkable ("2-4 PICO candidates, no two identical on both P and I," not "generates output"). Acceptance criteria become tests: write the failing test for a criterion, then the code that passes it. A component isn't done when the code runs. It's done when every criterion has a passing test. A phase is done when all its components are done. Commit messages state what was built and which criteria the tests now cover.

Spec one component at a time. Don't write acceptance criteria for a future component before the current one's tests pass.

Solo dev, direct to `main`. No feature branches, no pull requests.

## Where things live

- `README.md`: scope, MVP boundary, architecture, eval design, status
- `eval/gold_set.jsonl`: hand-annotated gold-standard PICO framings (once created)
