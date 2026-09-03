"""Acceptance-criteria tests for load_case in case_loading.py."""

import pandas as pd
import pytest

from pico_pubmed_rag.case_loading import load_case


@pytest.fixture
def clean_df():

    return pd.DataFrame(
        [
            {
                "case_id": 0,
                "description": "Allergy check",
                "medical_specialty": "Allergy / Immunology",
                "sample_name": "Allergic Rhinitis",
                "transcription": "SUBJECTIVE:, patient has allergies.",
            },
            {
                "case_id": 1,
                "description": "Chest pain",
                "medical_specialty": "Cardiovascular / Pulmonary",
                "sample_name": "Chest pain consult",
                "transcription": "History, patient has chest pain",
            },
        ]
    )


def test_load_case_returns_valid_case(clean_df):
    result = load_case(clean_df, 0)
    assert result == {
        "case_id": 0,
        "description": "Allergy check",
        "medical_specialty": "Allergy / Immunology",
        "sample_name": "Allergic Rhinitis",
        "transcription": "SUBJECTIVE:, patient has allergies.",
    }


def test_load_case_raises_when_case_id_not_found(clean_df):
    with pytest.raises(KeyError):
        load_case(clean_df, 99)
