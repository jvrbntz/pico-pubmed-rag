"""Draws a seeded case sample and runs a batch of cases through run_pipeline, saving each trace to one batch file."""

import logging
import random
import time
import uuid

from pico_pubmed_rag.pipeline_run import run_pipeline
from pico_pubmed_rag.trace_file import write_trace

logger = logging.getLogger(__name__)


def draw_case_sample(dataset, size, seed):
    case_ids = sorted(dataset["case_id"].tolist())
    return sorted(random.Random(seed).sample(case_ids, size))


def run_batch(
    case_ids,
    repeats,
    dataset,
    model_call,
    search_call,
    fetch_call,
    batch_file,
    run_metadata,
):
    batch_id = uuid.uuid4().hex
    outcome_counts = {"completed": 0, "no_evidence": 0, "failed": 0}
    unsaved = 0
    total_runs = len(case_ids) * repeats
    run_number = 0
    batch_start = time.perf_counter()
    logger.info("Batch %s: %s runs, saving to %s", batch_id, total_runs, batch_file)

    for case_id in case_ids:
        for repeat in range(1, repeats + 1):
            run_number += 1
            logger.info("run %s/%s: case %s, repeat %s", run_number, total_runs, case_id, repeat)
            trace = run_pipeline(
                case_id=case_id,
                dataset=dataset,
                model_call=model_call,
                search_call=search_call,
                fetch_call=fetch_call,
                run_metadata={**run_metadata, "batch_id": batch_id, "repeat": repeat},
            )
            outcome_counts[trace["run_outcome"]] += 1
            _log_run_end(trace, case_id, repeat)
            try:
                write_trace(trace, batch_file)
            except (ValueError, TypeError) as exc:
                unsaved += 1
                logger.error(
                    "Trace not saved: case %s, repeat %s, run %s: %s",
                    case_id,
                    repeat,
                    trace["run_id"],
                    exc,
                )

    logger.info(
        "Batch %s done in %.1fs: completed %s, no_evidence %s, failed %s, unsaved %s",
        batch_id,
        time.perf_counter() - batch_start,
        outcome_counts["completed"],
        outcome_counts["no_evidence"],
        outcome_counts["failed"],
        unsaved,
    )
    return {"batch_id": batch_id, "outcome_counts": outcome_counts, "unsaved": unsaved}


def _log_run_end(trace, case_id, repeat):
    if trace["run_outcome"] == "failed":
        stage_name, record = next(
            (name, record)
            for name, record in trace["stages"].items()
            if record["status"] == "failed"
        )
        logger.warning(
            "Run %s: case %s, repeat %s, failed at %s (%s), %.1fs",
            trace["run_id"],
            case_id,
            repeat,
            stage_name,
            record["failure_tag"],
            trace["total_latency_s"],
        )
    else:
        logger.info(
            "Run %s: case %s, repeat %s, %s, %.1fs",
            trace["run_id"],
            case_id,
            repeat,
            trace["run_outcome"],
            trace["total_latency_s"],
        )
