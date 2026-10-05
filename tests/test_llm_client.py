"""Acceptance-criteria tests for call_llm in llm_client.py."""

import pytest

from pico_pubmed_rag.llm_client import SAMPLING_OPTIONS, call_llm


@pytest.fixture
def recorded_generate_calls():
    return []


@pytest.fixture
def fake_generate(recorded_generate_calls, monkeypatch):
    monkeypatch.setenv("OLLAMA_LLM_MODEL", "test-model")

    def _fake_generate(**kwargs):
        recorded_generate_calls.append(kwargs)
        return {"response": "fake response"}

    return _fake_generate


def test_call_llm_sends_fixed_sampling_options(fake_generate, recorded_generate_calls):
    call_llm("some prompt", generate=fake_generate)

    call = recorded_generate_calls[0]
    assert call["options"] == SAMPLING_OPTIONS
    assert call["options"] == {"temperature": 0.3, "seed": 42, "num_ctx": 16384, "num_predict": 4096}
    assert call["prompt"] == "some prompt"
    assert call["model"] == "test-model"


def test_call_llm_uses_same_options_on_every_call(fake_generate, recorded_generate_calls):
    call_llm("first prompt", generate=fake_generate)
    call_llm("a different, longer second prompt", generate=fake_generate)

    first, second = recorded_generate_calls
    assert first["options"] == second["options"] == SAMPLING_OPTIONS
