"""Generates candidate PICO framings from case text via an injected LLM call."""

import json

EXAMPLE_NOTE = (
    "52-year-old woman with recurrent right upper quadrant pain after fatty meals. "
    "Ultrasound shows gallstones without cholecystitis. Plan: elective laparoscopic cholecystectomy."
)

NO_CLINICAL_DECISION_MESSAGE = "No clinical decision in the note"

EXAMPLE_DECISION = "Elective laparoscopic cholecystectomy chosen for symptomatic gallstones."

EXAMPLE_CANDIDATES = [
    {
        "population": "adults with symptomatic gallstones",
        "intervention": "laparoscopic cholecystectomy",
        "comparison": "watchful waiting",
        "outcome": "recurrent biliary pain and gallstone complications",
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
    Return a single JSON object with exactly two keys, and nothing else: \
    "clinical_decision", one sentence stating the main clinical decision, and "candidates", a list of candidate objects.
    Each candidate must be a JSON object with exactly these four keys: "population", "intervention", "comparison", "outcome".

    First, identify the main clinical decision in the note: what was chosen, and for which condition. \
    If the note contains no clinical decision, for example a diagnostic report or a template, say so instead of inventing one: \
    set "clinical_decision" to null and "candidates" to an empty list.

    Then write each candidate as a clinical question that can be searched in the medical literature, not as a description of this patient:
    - Population: the condition, not the procedure or test, plus the clinical characteristics that define who the question applies to, for example "women with symptomatic uterine fibroids". Leave out the exact age, laterality (left or right), obstetric history, and other details specific to this patient unless they change which treatment applies. Do not make the population so broad that it includes people outside that group.
    - Intervention: the treatment, procedure, or test strategy that was chosen.
    - Comparison: what the intervention is weighed against: an alternative treatment, usual care, or no intervention. Always give one.
    - Name the intervention and comparison generically, without brand names, device names, or doses.
    - Outcome: an outcome important to patients, such as symptom relief, complications, recurrence, stroke, or death. Not a procedure finding or "successful completion" of the procedure.

    Here's an example: "{EXAMPLE_NOTE}"

    Response:
    {{
    "clinical_decision": "{EXAMPLE_DECISION}",
    "candidates": [
{_format_example_candidates()}
        ]
    }}

    The example above shows the required format only. Do not reuse its population, intervention, comparison, or outcome in your answer. Every candidate must come only from the case note below, not from the example.

    Now extract PICO candidates from this case note:
    {case_text}
"""


def _parse_response(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in LLM response: {text!r}")
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM response was not valid JSON: {e}") from e
    if not isinstance(parsed, dict) or set(parsed) != {"clinical_decision", "candidates"}:
        raise ValueError(
            f"PICO response must be an object with clinical_decision and candidates: {text!r}"
        )
    if not isinstance(parsed["candidates"], list):
        raise ValueError(f"PICO candidates must be a list: {parsed['candidates']!r}")
    return parsed


def _extract_json_array(text):
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON array found in LLM response: {text!r}")
    return text[start : end + 1]


def generate_pico_candidates(case_text, llm_call):
    response = llm_call(build_prompt(case_text))

    parsed = _parse_response(response)
    if not (parsed["clinical_decision"] or "").strip():
        raise ValueError(NO_CLINICAL_DECISION_MESSAGE)
    candidates = parsed["candidates"]

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

    # Keeps the first candidate for each question; later ones differ at most in outcome.
    seen_questions = set()
    distinct_candidates = []
    for candidate in candidates:
        question = (candidate["population"], candidate["intervention"], candidate["comparison"])
        if question not in seen_questions:
            seen_questions.add(question)
            distinct_candidates.append(candidate)
    candidates = distinct_candidates

    if len(candidates) < 1 or len(candidates) > 4:
        raise ValueError("Number of PICO candidates can only be between 1 and 4")

    return candidates
