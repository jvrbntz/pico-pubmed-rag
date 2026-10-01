"""Draws a seeded case sample and runs a batch of cases through run_pipeline, saving each trace to one batch file."""

import random


def draw_case_sample(dataset, size, seed):
    case_ids = sorted(dataset["case_id"].tolist())
    return sorted(random.Random(seed).sample(case_ids, size))
