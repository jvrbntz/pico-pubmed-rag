"""One-time manual check: runs one real MTSamples case through the entire pipeline, case to PMID-cited summary, against the real model and real PubMed. This is the MVP walking skeleton."""

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

if __name__ == "__main__":
    load_dotenv()

    raw_df = pd.read_csv("data/mtsamples.csv")
    clean_df = clean_dataset(raw_df)
    case = load_case(clean_df, CASE_ID)
    print(f"--- Case {CASE_ID} ---\n{case['transcription'][:300]}...\n")

    candidates = generate_pico_candidates(case["transcription"], call_llm)
    print(f"--- {len(candidates)} PICO candidates ---")
    for candidate in candidates:
        print(candidate)
    print()

    pico = select_pico(candidates)
    print(f"--- Selected PICO (position 1) ---\n{pico}\n")

    query = build_search_query(pico)
    print(f"--- Query ---\n{query}\n")

    pmids = search_pubmed_with_broadening(query, esearch_get)
    print(f"--- Found {len(pmids)} PMIDs, using the first 5: {pmids[:5]} ---\n")

    xml_text = fetch_abstracts(pmids[:5], efetch_get)
    abstracts = parse_pubmed_xml(xml_text)
    ranked = rank_abstracts(abstracts)
    print("--- Ranked abstracts ---")
    for abstract in ranked:
        print(abstract["pmid"], abstract["publication_type"], abstract["publication_date"])
    print()

    summary = generate_summary(pico, ranked, call_llm)
    print(f"--- Summary ---\n{summary}")
