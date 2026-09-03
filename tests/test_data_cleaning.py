"""Acceptance-criteria tests for clean_dataset in data_cleaning.py."""

import pandas as pd
import pytest

from pico_pubmed_rag.data_cleaning import clean_dataset


@pytest.fixture
def raw_df():
    return pd.DataFrame(
        {
            "Unnamed: 0": [0, 1, 2],
            "description": ["Allergy check", "Knee surgery", "Chest pain"],
            "medical_specialty": [
                "Allergy / Immunology",
                "Orthopedic",
                "Cardiovascular / Pulmonary",
            ],
            "sample_name": [
                "Allergic Rhinitis",
                "Knee Replacement",
                "Chest Pain Consult",
            ],
            "transcription": [
                "SUBJECTIVE:, patient has allergies.",
                None,
                "History, patient has chest pain",
            ],
            "keywords": [
                "allergy, rhinitis",
                "orthopedic, knee",
                "cardiology, chest pain",
            ],
        }
    )


def test_clean_dataset_drops_keywords_column(raw_df):
    result = clean_dataset(raw_df)
    assert "keywords" not in result.columns


def test_clean_dataset_drops_rows_missing_transcription(raw_df):
    result = clean_dataset(raw_df)
    assert result["transcription"].isna().sum() == 0


def test_clean_dataset_case_id_matches_original_unnamed_column(raw_df):
    result = clean_dataset(raw_df)
    assert (
        raw_df.loc[result.index, "Unnamed: 0"].values == result["case_id"].values
    ).all()


def test_clean_dataset_row_count_matches_expected_after_dropna(raw_df):
    result = clean_dataset(raw_df)
    assert len(result) == 2


def test_clean_dataset_preserves_column_values(raw_df):
    result = clean_dataset(raw_df)
    matching_raw = raw_df.loc[result.index]

    for col in ["description", "medical_specialty", "sample_name", "transcription"]:
        assert (matching_raw[col].values == result[col].values).all()
