"""Turns a selected PICO into short PubMed search terms via an injected LLM call, and validates them."""

import json
import re

TERM_KEYS = ("population_terms", "intervention_terms")
MAX_TERM_WORDS = 4
QUERY_SYNTAX_CHARACTERS = set('()[]"/')
BOOLEAN_OPERATORS = {"AND", "OR", "NOT"}
AGE_PATTERN = re.compile(r"\d+\s*-?\s*(year|yr)", re.IGNORECASE)
DOSE_PATTERN = re.compile(r"\d+\s*(mg|mcg|g|ml|units?)\b", re.IGNORECASE)
LONG_NUMBER_PATTERN = re.compile(r"\d{3,}")


EXAMPLE_SEARCH_TERMS = {
    "population_terms": "streptococcal pharyngitis",
    "intervention_terms": "amoxicillin",
}


def build_search_terms_prompt(pico):
    return f"""
    You are a medical librarian building a PubMed search for a clinical question.

    Give the standard medical name of the question's condition and of its treatment or procedure, as each would appear as a medical subject heading. Follow these rules:
    - Use 1 to 4 words for each term.
    - Do not include ages, doses, years, laterality (left or right), brand names, or device names.
    - Do not use parentheses, quotation marks, slashes, or the words AND, OR, or NOT in capitals.
    - Return a JSON object with exactly two keys, "population_terms" and "intervention_terms", and nothing else.

    Example clinical question: adults with confirmed strep throat treated with amoxicillin compared with penicillin.
    Response: {json.dumps(EXAMPLE_SEARCH_TERMS)}

    The example shows the required format only. Do not reuse its terms. Use only the clinical question below.

    Clinical question:
    Population: {pico["population"]}
    Intervention: {pico["intervention"]}
    Comparison: {pico.get("comparison") or "none stated"}
    Outcome: {pico["outcome"]}
"""


def _extract_json_object(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in LLM response: {text!r}")
    return text[start : end + 1]


def extract_search_terms(pico, llm_call):
    response = llm_call(build_search_terms_prompt(pico))
    try:
        terms = json.loads(_extract_json_object(response))
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM response was not valid JSON: {e}") from e

    if not isinstance(terms, dict) or not set(terms) <= set(TERM_KEYS):
        raise ValueError(f"Search terms have unexpected keys: {terms!r}")

    for key in TERM_KEYS:
        if not isinstance(terms.get(key), str) or not terms[key].strip():
            raise ValueError(f"Search term {key!r} is missing or empty: {terms!r}")
        if len(terms[key].split()) > MAX_TERM_WORDS:
            raise ValueError(f"Search term has more than {MAX_TERM_WORDS} words: {terms[key]!r}")
        if any(pattern.search(terms[key]) for pattern in (AGE_PATTERN, DOSE_PATTERN, LONG_NUMBER_PATTERN)):
            raise ValueError(f"Search term contains an age, dose, or long number: {terms[key]!r}")
        if QUERY_SYNTAX_CHARACTERS & set(terms[key]) or BOOLEAN_OPERATORS & set(terms[key].split()):
            raise ValueError(f"Search term contains PubMed query syntax: {terms[key]!r}")

    return terms
