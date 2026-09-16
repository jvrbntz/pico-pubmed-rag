"""Generates candidate PICO framings from case text via an injected LLM call."""

import json


def build_prompt(case_text):
    return f"""
    You are a helpful clinical AI assistant and an expert in extracting the most important PICO elements from a case note. 

    Given a clinical case note, extract 2 to 4 distinct PICO (Population, Intervention, Comparison, Outcome) candidates. \
    Each candidate must be a JSON object with exactly these four keys: "population", "intervention", "comparison", "outcome".
    Return a JSON list of these objects, and nothing else.

    Here's an example: "45 year-old man presents with sore throat, fever, and tonsillar exudate. Rapid strep test is positive."

    Response:
    [
        {{"population": "adults with confirmed strep throat", "intervention": "amoxicillin", "comparison": "penicillin", "outcome": "symptom resolution"}},
        {{"population": "adults with confirmed strep throat", "intervention": "watchful waiting", "comparison": "amoxicillin", "outcome": "complication rate"}}
        ]

    The example above shows the required format only. Do not reuse its population, intervention, comparison, or outcome in your answer. Every candidate must come only from the case note below, not from the example.

    Now extract PICO candidates from this case note:
    {case_text}
"""


def _extract_json_array(text):
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON array found in LLM response: {text!r}")
    return text[start : end + 1]


def generate_pico_candidates(case_text, llm_call):
    response = llm_call(build_prompt(case_text))

    try:
        candidates = json.loads(_extract_json_array(response))
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM response was not valid JSON: {e}") from e

    for candidate in candidates:
        if set(candidate.keys()) != {
            "population",
            "intervention",
            "comparison",
            "outcome",
        }:
            raise ValueError(
                f"PICO candidate has unexpected keys: {sorted(candidate.keys())}"
            )

        if not all(candidate.values()):
            raise ValueError(
                f"PICO candidate has a missing or empty value: {candidate}"
            )

    if len(candidates) != len(
        {(c["population"], c["intervention"]) for c in candidates}
    ):
        raise ValueError("Duplicate PICO candidates: same population and intervention")

    if len(candidates) < 2 or len(candidates) > 4:
        raise ValueError("Number of PICO candidates can only be between 2 and 4")

    return candidates
