"""One-time setup: downloads MTSamples via kagglehub and copies it into data/."""

import shutil
from pathlib import Path

import kagglehub


def download_mtsamples(dest: Path = Path("data")) -> Path:
    cached_path = kagglehub.dataset_download("tboyle10/medicaltranscriptions")
    dest.mkdir(exist_ok=True)
    shutil.copytree(cached_path, dest, dirs_exist_ok=True)
    return dest


if __name__ == "__main__":
    path = download_mtsamples()
    print(f"MTSamples data ready at {path}")
