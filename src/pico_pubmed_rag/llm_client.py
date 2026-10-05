"""Thin client for calling the local Ollama-hosted LLM, shared by PICO generation and summary generation."""

import os

import ollama

SAMPLING_OPTIONS = {"temperature": 0.3, "seed": 42, "num_ctx": 16384, "num_predict": 4096}


def call_llm(prompt, generate=ollama.generate):
    model = os.environ.get("OLLAMA_LLM_MODEL")
    if not model:
        raise ValueError(
            "OLLAMA_LLM_MODEL is not set. Copy .env.example to .env and fill it in."
        )

    response = generate(model=model, prompt=prompt, options=SAMPLING_OPTIONS)
    return response["response"]
