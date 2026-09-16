"""One-time manual check: runs a PICO through the real PubMed search, fetch, parse, and rank chain against NCBI's live E-utilities API."""

from dotenv import load_dotenv

from pico_pubmed_rag.abstract_ranking import rank_abstracts
from pico_pubmed_rag.pubmed_search import (
    build_search_query,
    efetch_get,
    esearch_get,
    fetch_abstracts,
    parse_pubmed_xml,
    search_pubmed,
)

SAMPLE_PICO = {
    "population": "adults with strep throat",
    "intervention": "amoxicillin",
    "comparison": "penicillin",
    "outcome": "symptom resolution",
}

if __name__ == "__main__":
    load_dotenv()

    query = build_search_query(SAMPLE_PICO)
    print(f"Query: {query}\n")

    pmids = search_pubmed(query, esearch_get)
    print(f"Found {len(pmids)} PMIDs, showing the first 10: {pmids[:10]}\n")

    if pmids:
        xml_text = fetch_abstracts(pmids[:10], efetch_get)
        abstracts = parse_pubmed_xml(xml_text)

        ranked = rank_abstracts(abstracts)
        for abstract in ranked:
            print(abstract["pmid"], abstract["publication_type"], abstract["publication_date"])
