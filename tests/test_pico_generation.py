"""Acceptance-criteria tests for generate_pico_candidates in pico_generation.py."""

import json

import pytest

from pico_pubmed_rag.pico_generation import EXAMPLE_CANDIDATES, build_prompt, generate_pico_candidates

EXAMPLE_DECISION = "Elective repair chosen for a symptomatic condition."


def pico_response(candidates, decision=EXAMPLE_DECISION):
    return json.dumps({"clinical_decision": decision, "candidates": candidates})


@pytest.fixture
def fake_llm_call():
    def _fake_llm_call(prompt):
        return pico_response(
            [
                {
                    "population": "adult patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": "penicillin",
                    "outcome": "symptom resolution",
                },
                {
                    "population": "pediatric patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": "watchful waiting",
                    "outcome": "symptom resolution",
                },
            ]
        )

    return _fake_llm_call


@pytest.fixture
def different_comparison_llm_call():
    def _different_comparison_llm_call(prompt):
        return pico_response(
            [
                {
                    "population": "adult patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": "penicillin",
                    "outcome": "symptom resolution",
                },
                {
                    "population": "adult patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": "watchful waiting",
                    "outcome": "symptoms not resolved timely",
                },
            ]
        )

    return _different_comparison_llm_call


@pytest.fixture
def out_of_bounds_llm_call():
    def _out_of_bounds_llm_call(prompt):
        return pico_response(
            [
                {
                    "population": "p1",
                    "intervention": "i1",
                    "comparison": "c1",
                    "outcome": "o1",
                },
                {
                    "population": "p2",
                    "intervention": "i2",
                    "comparison": "c2",
                    "outcome": "o2",
                },
                {
                    "population": "p3",
                    "intervention": "i3",
                    "comparison": "c3",
                    "outcome": "o3",
                },
                {
                    "population": "p4",
                    "intervention": "i4",
                    "comparison": "c4",
                    "outcome": "o4",
                },
                {
                    "population": "p5",
                    "intervention": "i5",
                    "comparison": "c5",
                    "outcome": "o5",
                },
                {
                    "population": "p6",
                    "intervention": "i6",
                    "comparison": "c6",
                    "outcome": "o6",
                },
                {
                    "population": "p7",
                    "intervention": "i7",
                    "comparison": "c7",
                    "outcome": "o7",
                },
            ]
        )

    return _out_of_bounds_llm_call


@pytest.fixture
def malformed_json_llm_call():
    def _malformed_json_llm_call(prompt):
        return "not valid json"

    return _malformed_json_llm_call


@pytest.fixture
def wrong_keys_llm_call():
    def _wrong_keys_llm_call(prompt):
        return pico_response(
            [
                {
                    "population": "adult patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": "penicillin",
                    "outcome": "symptom resolution",
                },
                {
                    "population": "pediatric patients with strep throat",
                    "intervention": "amoxicillin",
                    "rationale": "children respond well to amoxicillin",
                },
            ]
        )

    return _wrong_keys_llm_call


@pytest.fixture
def noisy_response_llm_call():
    def _noisy_response_llm_call(prompt):
        return (
            "Here's my resoning about this case...\n"
            "```json\n"
            + pico_response(
                [
                    {
                        "population": "p1",
                        "intervention": "i1",
                        "comparison": "c1",
                        "outcome": "o1",
                    },
                    {
                        "population": "p2",
                        "intervention": "i2",
                        "comparison": "c2",
                        "outcome": "o2",
                    },
                ]
            )
            + "\n```"
        )

    return _noisy_response_llm_call


@pytest.fixture
def null_comparison_llm_call():
    def _null_comparison_llm_call(prompt):
        return pico_response(
            [
                {
                    "population": "adult patients with strep throat",
                    "intervention": "amoxicillin",
                    "comparison": None,
                    "outcome": "symptom resolution",
                },
                {
                    "population": "child with strep throat",
                    "intervention": "watchful waiting",
                    "comparison": None,
                    "outcome": "symptoms worsen",
                },
            ]
        )

    return _null_comparison_llm_call


def test_generate_pico_candidates_returns_one_to_four_candidates(fake_llm_call):
    result = generate_pico_candidates("case text", fake_llm_call)

    assert 1 <= len(result) <= 4


def test_generate_pico_candidates_accepts_different_comparison(different_comparison_llm_call):
    result = generate_pico_candidates("case text", different_comparison_llm_call)

    assert len(result) == 2


def test_generate_pico_candidates_returns_formatted_output(fake_llm_call):
    result = generate_pico_candidates("case text", fake_llm_call)

    for pico_candidate in result:
        assert set(pico_candidate.keys()) == {
            "population",
            "intervention",
            "comparison",
            "outcome",
        }


def test_generate_pico_candidates_raises_on_out_of_bounds_count(out_of_bounds_llm_call):
    with pytest.raises(ValueError):
        generate_pico_candidates("case text", out_of_bounds_llm_call)


def test_generate_pico_candidates_raises_on_malformed_json(malformed_json_llm_call):
    with pytest.raises(ValueError):
        generate_pico_candidates("case text", malformed_json_llm_call)


def test_generate_pico_candidates_raises_on_wrong_keys(wrong_keys_llm_call):
    with pytest.raises(ValueError):
        generate_pico_candidates("case text", wrong_keys_llm_call)


def test_build_prompt_returns_a_string():
    result = build_prompt("case text")
    assert isinstance(result, str)


def test_build_prompt_includes_case_text():
    result = build_prompt("case text")
    assert "case text" in result


def test_build_prompt_includes_required_keys():
    result = build_prompt("case text")
    for key in ["population", "intervention", "comparison", "outcome"]:
        assert key in result


def test_generate_pico_candidates_parses_response_with_noise(noisy_response_llm_call):
    result = generate_pico_candidates("case text", noisy_response_llm_call)
    assert len(result) == 2


def test_generate_pico_candidates_accepts_null_comparison(null_comparison_llm_call):
    result = generate_pico_candidates("case text", null_comparison_llm_call)

    assert len(result) == 2
    assert all(candidate["comparison"] is None for candidate in result)


@pytest.fixture
def single_candidate_llm_call():
    def _single_candidate_llm_call(prompt):
        return pico_response(
            [
                {
                    "population": "adults with prostate cancer",
                    "intervention": "iodine-125 brachytherapy",
                    "comparison": "watchful waiting",
                    "outcome": "biochemical recurrence",
                }
            ]
        )

    return _single_candidate_llm_call


def test_generate_pico_candidates_accepts_one_candidate(single_candidate_llm_call):
    result = generate_pico_candidates("case text", single_candidate_llm_call)

    assert len(result) == 1


@pytest.fixture
def five_candidates_llm_call():
    def _five_candidates_llm_call(prompt):
        return pico_response(
            [
                {
                    "population": f"population {n}",
                    "intervention": f"intervention {n}",
                    "comparison": f"comparison {n}",
                    "outcome": f"outcome {n}",
                }
                for n in range(1, 6)
            ]
        )

    return _five_candidates_llm_call


def test_generate_pico_candidates_raises_on_zero_candidates():
    with pytest.raises(ValueError):
        generate_pico_candidates("case text", lambda prompt: pico_response([]))


def test_generate_pico_candidates_raises_on_five_candidates(five_candidates_llm_call):
    with pytest.raises(ValueError):
        generate_pico_candidates("case text", five_candidates_llm_call)


PACEMAKER_CANDIDATE = {
    "population": "older adults with symptomatic bradycardia",
    "intervention": "permanent pacemaker implantation",
    "comparison": "medical management",
    "outcome": "syncope recurrence",
}


def test_generate_pico_candidates_drops_candidate_differing_only_in_outcome():
    other_question = {**PACEMAKER_CANDIDATE, "intervention": "temporary pacing"}
    response = pico_response(
        [
            PACEMAKER_CANDIDATE,
            other_question,
            {**PACEMAKER_CANDIDATE, "outcome": "all-cause mortality"},
        ]
    )

    result = generate_pico_candidates("case text", lambda prompt: response)

    assert result == [PACEMAKER_CANDIDATE, other_question]


def test_generate_pico_candidates_drops_exact_copies():
    response = pico_response([PACEMAKER_CANDIDATE, PACEMAKER_CANDIDATE])

    result = generate_pico_candidates("case text", lambda prompt: response)

    assert result == [PACEMAKER_CANDIDATE]


def test_generate_pico_candidates_treats_null_string_and_null_comparison_as_duplicates():
    no_comparison = {**PACEMAKER_CANDIDATE, "comparison": None}
    response = pico_response(
        [no_comparison, {**no_comparison, "comparison": "null", "outcome": "all-cause mortality"}]
    )

    result = generate_pico_candidates("case text", lambda prompt: response)

    assert result == [no_comparison]


def _numbered_candidates(count):
    return [{**PACEMAKER_CANDIDATE, "intervention": f"intervention {n}"} for n in range(1, count + 1)]


def test_generate_pico_candidates_counts_candidates_after_dropping_duplicates():
    distinct = _numbered_candidates(4)
    response = pico_response(distinct + [distinct[0]])

    result = generate_pico_candidates("case text", lambda prompt: response)

    assert result == distinct


def test_generate_pico_candidates_raises_on_five_distinct_after_dropping_duplicates():
    distinct = _numbered_candidates(5)
    response = pico_response(distinct + [distinct[0]])

    with pytest.raises(ValueError):
        generate_pico_candidates("case text", lambda prompt: response)


def test_generate_pico_candidates_raises_on_null_outcome():
    response = pico_response([{**PACEMAKER_CANDIDATE, "outcome": None}])

    with pytest.raises(ValueError):
        generate_pico_candidates("case text", lambda prompt: response)


def test_generate_pico_candidates_raises_on_empty_population():
    response = pico_response([{**PACEMAKER_CANDIDATE, "population": ""}])

    with pytest.raises(ValueError):
        generate_pico_candidates("case text", lambda prompt: response)


def test_build_prompt_asks_for_one_to_four_candidates():
    result = build_prompt("case text")

    assert "1 to 4" in result
    assert "2 to 4" not in result


def test_build_prompt_asks_for_searchable_population_without_patient_details():
    result = build_prompt("case text")

    for phrase in ["laterality", "brand names", "not as a description of this patient"]:
        assert phrase in result


def test_build_prompt_carries_sourced_pico_rules():
    result = build_prompt("case text")

    for phrase in [
        "main clinical decision",
        "the condition, not the procedure",
        "usual care",
        "no intervention",
        "important to patients",
        "If the note contains no clinical decision",
    ]:
        assert phrase in result
    assert "If the note states no alternative, use null" not in result


@pytest.mark.parametrize("null_text", ["null", " NULL "])
def test_generate_pico_candidates_treats_null_string_comparison_as_none(null_text):
    response = pico_response([{**PACEMAKER_CANDIDATE, "comparison": null_text}])

    result = generate_pico_candidates("case text", lambda prompt: response)

    assert result[0]["comparison"] is None


def test_build_prompt_example_is_a_procedure_note_with_comparator():
    result = build_prompt("case text")

    assert "cholecystectomy" in result
    assert "strep" not in result.lower()
    assert all(candidate["comparison"] for candidate in EXAMPLE_CANDIDATES)


def test_generate_pico_candidates_reads_candidates_from_decision_object():
    response = pico_response([PACEMAKER_CANDIDATE], decision="Pacemaker chosen for symptomatic bradycardia.")

    assert generate_pico_candidates("case text", lambda prompt: response) == [PACEMAKER_CANDIDATE]


def test_generate_pico_candidates_rejects_bare_list():
    response = json.dumps([PACEMAKER_CANDIDATE])

    with pytest.raises(ValueError):
        generate_pico_candidates("case text", lambda prompt: response)


def test_build_prompt_asks_for_decision_object():
    result = build_prompt("case text")

    assert '"clinical_decision"' in result
    assert '"candidates"' in result


@pytest.mark.parametrize("decision", [None, "", "  "])
def test_generate_pico_candidates_raises_distinct_error_without_clinical_decision(decision):
    response = pico_response([], decision=decision)

    with pytest.raises(ValueError, match="No clinical decision in the note"):
        generate_pico_candidates("case text", lambda prompt: response)


def test_build_prompt_says_how_to_report_no_clinical_decision():
    assert 'set "clinical_decision" to null and "candidates" to an empty list' in build_prompt("case text")
