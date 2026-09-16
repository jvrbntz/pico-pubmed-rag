"""One-time manual check: calls generate_summary repeatedly on the same real PICO and abstracts, to estimate how often MedGemma complies with the citation-format instruction on the first attempt."""

import pandas as pd
from dotenv import load_dotenv

from pico_pubmed_rag.abstract_ranking import rank_abstracts
from pico_pubmed_rag.case_loading import load_case
from pico_pubmed_rag.data_cleaning import clean_dataset
from pico_pubmed_rag.llm_client import call_llm
from pico_pubmed_rag.pico_generation import generate_pico_candidates
from pico_pubmed_rag.pico_selection import select_pico
from pico_pubmed_rag.pubmed_search import (
    build_search_query,
    efetch_get,
    esearch_get,
    fetch_abstracts,
    parse_pubmed_xml,
    search_pubmed_with_broadening,
)
from pico_pubmed_rag.summary_generation import generate_summary

CASE_ID = 2
ATTEMPTS = 8

if __name__ == "__main__":
    load_dotenv()

    raw_df = pd.read_csv("data/mtsamples.csv")
    clean_df = clean_dataset(raw_df)
    case = load_case(clean_df, CASE_ID)

    candidates = generate_pico_candidates(case["transcription"], call_llm)
    pico = select_pico(candidates)
    print(f"PICO: {pico}\n")

    query = build_search_query(pico)
    pmids = search_pubmed_with_broadening(query, esearch_get)
    print(f"Found {len(pmids)} PMIDs\n")

    if not pmids:
        print("No PMIDs found for this PICO, rerun to get a different one.")
    else:
        xml_text = fetch_abstracts(pmids[:5], efetch_get)
        abstracts = parse_pubmed_xml(xml_text)
        ranked = rank_abstracts(abstracts)
        print(f"Using {len(ranked)} abstracts for all {ATTEMPTS} attempts.\n")

        successes = 0
        for i in range(1, ATTEMPTS + 1):
            try:
                generate_summary(pico, ranked, call_llm)
                print(f"Attempt {i}: PASS")
                successes += 1
            except ValueError as e:
                print(f"Attempt {i}: FAIL ({e})")

        print(f"\n{successes}/{ATTEMPTS} attempts passed validation on the first try.")
