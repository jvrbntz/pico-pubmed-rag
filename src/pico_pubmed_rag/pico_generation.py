"""Generates candidate PICO framings from case text via an injected LLM call."""

import json


def generate_pico_candidates(case_text, llm_call):
    response = llm_call(case_text)

    try:
        candidates = json.loads(response)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM response was not valid JSON: {e}") from e

    for candidate in candidates:
        if set(candidate.keys()) != {"population", "intervention", "comparison", "outcome"}:
            raise ValueError(f"PICO candidate has unexpected keys: {sorted(candidate.keys())}")

    if len(candidates) != len(
        {(c["population"], c["intervention"]) for c in candidates}
    ):
        raise ValueError("Duplicate PICO candidates: same population and intervention")

    if len(candidates) < 2 or len(candidates) > 4:
        raise ValueError("Number of PICO candidates can only be between 2 and 4")

    return candidates
