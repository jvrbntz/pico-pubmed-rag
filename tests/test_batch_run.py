"""Acceptance-criteria tests for draw_case_sample and run_batch in batch_run.py."""

import pandas as pd
import pytest

from pico_pubmed_rag.batch_run import draw_case_sample


@pytest.fixture
def twenty_case_dataset():
    case_ids = [0, 2, 3, 7, 8, 11, 14, 15, 19, 22, 23, 30, 31, 35, 40, 41, 44, 50, 52, 57]
    return pd.DataFrame(
        {"case_id": case_ids, "transcription": [f"Synthetic note {i}." for i in case_ids]}
    )


def test_sample_is_reproducible(twenty_case_dataset):
    first = draw_case_sample(twenty_case_dataset, size=5, seed=42)
    second = draw_case_sample(twenty_case_dataset, size=5, seed=42)

    assert first == second
    assert first == sorted(first)
    assert len(set(first)) == 5
    assert set(first) <= set(twenty_case_dataset["case_id"])


def test_sample_depends_on_seed(twenty_case_dataset):
    assert draw_case_sample(twenty_case_dataset, size=5, seed=42) != draw_case_sample(
        twenty_case_dataset, size=5, seed=7
    )


def test_sample_draws_only_existing_ids():
    dataset = pd.DataFrame({"case_id": [0, 1, 5, 9], "transcription": ["a", "b", "c", "d"]})

    assert draw_case_sample(dataset, size=4, seed=42) == [0, 1, 5, 9]


def test_sample_larger_than_dataset_raises():
    dataset = pd.DataFrame({"case_id": [0, 1, 5, 9], "transcription": ["a", "b", "c", "d"]})

    with pytest.raises(ValueError):
        draw_case_sample(dataset, size=5, seed=42)
