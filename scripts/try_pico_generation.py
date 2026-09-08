"""One-time manual check: runs several real MTSamples cases through PICO-candidate generation using the real MedGemma model via Ollama."""

import json

import pandas as pd
from dotenv import load_dotenv

from pico_pubmed_rag.case_loading import load_case
from pico_pubmed_rag.data_cleaning import clean_dataset
from pico_pubmed_rag.llm_client import call_llm
from pico_pubmed_rag.pico_generation import generate_pico_candidates

SAMPLE_SIZE = 5

if __name__ == "__main__":
    load_dotenv()

    raw_df = pd.read_csv("data/mtsamples.csv")
    clean_df = clean_dataset(raw_df)

    case_ids_to_test = clean_df["case_id"].sample(n=SAMPLE_SIZE).tolist()

    for case_id in case_ids_to_test:
        print(f"--- case_id {case_id} ---")

        case = load_case(clean_df, case_id)

        try:
            candidates = generate_pico_candidates(case["transcription"], call_llm)
            print(json.dumps(candidates, indent=2))
        except ValueError as e:
            print(f"failed: {e}")
