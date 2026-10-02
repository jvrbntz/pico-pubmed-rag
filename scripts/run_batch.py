"""Runs a batch of MTSamples cases through the pipeline against the real model and real PubMed, saving every trace to a timestamped batch file under runs/."""

import argparse
import logging
import os
import subprocess
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv

from pico_pubmed_rag.batch_run import draw_case_sample, run_batch
from pico_pubmed_rag.data_cleaning import clean_dataset
from pico_pubmed_rag.llm_client import SAMPLING_OPTIONS, call_llm
from pico_pubmed_rag.pubmed_search import efetch_get, esearch_get


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=3, help="number of cases to sample")
    parser.add_argument("--seed", type=int, default=42, help="seed for the case sample")
    parser.add_argument("--repeats", type=int, default=1, help="runs per case")
    parser.add_argument(
        "--cases",
        type=lambda text: [int(case_id) for case_id in text.split(",")],
        help="comma-separated case IDs to run instead of a seeded sample, e.g. 87,12",
    )
    return parser.parse_args()


def current_git_commit():
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True
    )
    return result.stdout.strip() or None


if __name__ == "__main__":
    args = parse_args()
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    clean_df = clean_dataset(pd.read_csv("data/mtsamples.csv"))
    case_ids = args.cases or draw_case_sample(clean_df, size=args.size, seed=args.seed)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_file = f"runs/batch_{timestamp}.jsonl"

    summary = run_batch(
        case_ids=case_ids,
        repeats=args.repeats,
        dataset=clean_df,
        model_call=call_llm,
        search_call=esearch_get,
        fetch_call=efetch_get,
        batch_file=batch_file,
        run_metadata={
            "git_commit": current_git_commit(),
            "model": os.environ.get("OLLAMA_LLM_MODEL"),
            "sampling": SAMPLING_OPTIONS,
            "seed": None if args.cases else args.seed,
            "case_ids": case_ids,
        },
    )

    print(f"\nBatch summary: {summary}")
    print(f"Traces saved to {batch_file}")
