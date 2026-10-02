"""Generates candidate PICO framings from case text via an injected LLM call."""

import json

EXAMPLE_CANDIDATES = [
    {
        "population": "adults with confirmed strep throat",
        "intervention": "amoxicillin",
        "comparison": "penicillin",
        "outcome": "symptom resolution",
    },
    {
        "population": "adults with confirmed strep throat",
        "intervention": "watchful waiting",
        "comparison": "amoxicillin",
        "outcome": "complication rate",
    },
]


def _format_example_candidates():
    return ",\n".join("        " + json.dumps(candidate) for candidate in EXAMPLE_CANDIDATES)


def build_prompt(case_text):
    return f"""
    You are a helpful clinical AI assistant and an expert in extracting the most important PICO elements from a case note. 

    Given a clinical case note, extract 1 to 4 distinct PICO (Population, Intervention, Comparison, Outcome) candidates. \
    Return only as many as the note supports: a note describing a single procedure or decision usually supports one. \
    Candidates are distinct when they differ in population, intervention, or comparison.
    Each candidate must be a JSON object with exactly these four keys: "population", "intervention", "comparison", "outcome".
    Return a JSON list of these objects, and nothing else.

    Write each candidate as a clinical question that can be searched in the medical literature, not as a description of this patient:
    - Population: the condition and the clinical characteristics that define who the question applies to, for example "women with symptomatic uterine fibroids". Leave out the exact age, laterality (left or right), obstetric history, and other details specific to this patient unless they change which treatment applies. Do not make the population so broad that it includes people outside that group.
    - Intervention and comparison: name the treatment or procedure generically, without brand names, device names, or doses.
    - Comparison: the alternative being weighed. If the note states no alternative, use null. Do not invent one.

    Here's an example: "45 year-old man presents with sore throat, fever, and tonsillar exudate. Rapid strep test is positive."

    Response:
    [
{_format_example_candidates()}
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

        comparison = candidate["comparison"]
        if isinstance(comparison, str) and comparison.strip().lower() == "null":
            candidate["comparison"] = None

        if not all(candidate[key] for key in ("population", "intervention", "outcome")):
            raise ValueError(
                f"PICO candidate has a missing or empty value: {candidate}"
            )

    if len(candidates) != len(
        {(c["population"], c["intervention"], c["comparison"]) for c in candidates}
    ):
        raise ValueError(
            "Duplicate PICO candidates: same population, intervention, and comparison"
        )

    if len(candidates) < 1 or len(candidates) > 4:
        raise ValueError("Number of PICO candidates can only be between 1 and 4")

    return candidates
