"""Thin client for calling the local Ollama-hosted LLM, shared by PICO generation and summary generation."""

import os

import ollama


def call_llm(prompt):
    model = os.environ.get("OLLAMA_LLM_MODEL")
    if not model:
        raise ValueError(
            "OLLAMA_LLM_MODEL is not set. Copy .env.example to .env and fill it in."
        )

    response = ollama.generate(model=model, prompt=prompt)
    return response["response"]
