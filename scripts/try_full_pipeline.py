"""One-time manual check: runs one real MTSamples case through run_pipeline, against the real model and real PubMed, and prints a compact view of the trace."""

import pandas as pd
from dotenv import load_dotenv

from pico_pubmed_rag.data_cleaning import clean_dataset
from pico_pubmed_rag.llm_client import call_llm
from pico_pubmed_rag.pipeline_run import run_pipeline
from pico_pubmed_rag.pubmed_search import efetch_get, esearch_get

CASE_ID = 87

if __name__ == "__main__":
    load_dotenv()

    raw_df = pd.read_csv("data/mtsamples.csv")
    clean_df = clean_dataset(raw_df)

    trace = run_pipeline(
        case_id=CASE_ID,
        dataset=clean_df,
        model_call=call_llm,
        search_call=esearch_get,
        fetch_call=efetch_get,
        run_metadata={"note": "manual smoke run"},
    )

    print(f"--- Run {trace['run_id']} | case {trace['case_id']} ---")
    print(f"Outcome: {trace['run_outcome']}")
    print(f"Total latency: {trace['total_latency_s']:.1f}s\n")

    for name, record in trace["stages"].items():
        latency = record.get("latency_s")
        latency_text = f"{latency:.2f}s" if latency is not None else "-"
        calls = len(record.get("call_records", []))
        detail = record.get("failure_type") or record.get("skip_reason") or ""
        print(
            f"{name:<26} {record['status']:<10} {record['service']:<9} "
            f"{latency_text:>8}  calls={calls}  {detail}"
        )

    print()
    for record in trace["stages"]["search"].get("call_records", []):
        print(f"Search query sent: {record['query']}")

    summary_record = trace["stages"]["generate_summary"]
    if summary_record["status"] == "succeeded":
        print(f"\n--- Summary ---\n{summary_record['output']}")
    elif summary_record["status"] == "failed":
        print(f"\n--- Summary failed ---\n{summary_record['traceback']}")

    print(f"\ncase_id type in trace output: {type(trace['stages']['load_case']['output']['case_id'])}")
