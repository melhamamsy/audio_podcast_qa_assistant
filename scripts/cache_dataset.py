"""
Module for caching a Hugging Face dataset.

This script provides a utility to download and cache a Hugging Face dataset
into a specified directory. The dataset name is passed as an argument from the
command line, typically as an environment variable from a Makefile job.

Usage:
    python cache_dataset.py <dataset_name>

Example:
    python cache_dataset.py lex-fridman-podcast-dataset

The script uses the datasets library from Hugging Face to load and cache the dataset.
It also logs the download and caching process.

Functions:
    cache_dataset(dataset_name: str, cache_dir: str = "hf_cache"): Caches the specified dataset.
"""

import logging
import os
import sys

from datasets import load_dataset

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def cache_dataset(dataset_name: str, cache_dir: str = "hf_cache"):
    """Caches the specified Hugging Face dataset into a given directory.

    Args:
        dataset_name (str): The name of the dataset to cache.
        cache_dir (str): The directory where the dataset should be cached.
    """
    os.makedirs(cache_dir, exist_ok=True)

    logging.info(
        "Downloading and caching the dataset '%s' into '%s'...",
        dataset_name,
        cache_dir,
    )

    # Download and cache dataset
    load_dataset(dataset_name, cache_dir=cache_dir)

    logging.info(
        "Dataset '%s' has been cached successfully in '%s'.",
        dataset_name,
        cache_dir,
    )

    print(f"Dataset '{dataset_name}' has been cached successfully in '{cache_dir}'.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cache_dataset.py <dataset_name>")
        sys.exit(1)

    DATASET_NAME = sys.argv[1]
    cache_dataset(DATASET_NAME)
