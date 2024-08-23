"""
Module for caching Hugging Face speech-to-text models.

This script provides a utility to download and cache a Hugging Face model and its processor 
into a specified directory. The model name is passed as an argument from the command line, 
typically as an environment variable from a Makefile job.

Usage:
    python cache_model.py <model_name>

Example:
    python cache_model.py facebook/wav2vec2-large-960h

The script uses the AutoModelForSpeechSeq2Seq and AutoProcessor classes from the Hugging Face 
transformers library to load and cache the model and its processor. It also logs the download 
and caching process.

Functions:
    cache_model(model_name: str, cache_dir: str = "hf_cache"): Caches the specified model.
"""

import logging
import os
import sys

from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def cache_model(model_name: str, cache_dir: str = "hf_cache"):
    """Caches the specified Hugging Face model into a given directory.

    Args:
        model_name (str): The name of the model to cache.
        cache_dir (str): The directory where the model should be cached.
    """
    os.makedirs(cache_dir, exist_ok=True)

    logging.info(
        "Downloading and caching the model '%s' into '%s'...",
        model_name,
        cache_dir,
    )

    # Download and cache model and tokenizer
    AutoModelForSpeechSeq2Seq.from_pretrained(model_name, cache_dir=cache_dir)
    AutoProcessor.from_pretrained(model_name, cache_dir=cache_dir)

    logging.info(
        "Speech-to-text model '%s' has been cached successfully in '%s'.",
        model_name,
        cache_dir,
    )

    print(f"Model '{model_name}' has been cached successfully in '{cache_dir}'.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python cache_model.py <model_name>")
        sys.exit(1)

    MODEL_NAME = sys.argv[1]
    cache_model(MODEL_NAME)
