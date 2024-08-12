"""
This module provides utility functions for Huggingface.
The utility functions are used to:
    1. Setup cache directories
    2. Vectorize Sentences
    3. ...
"""

import os

from tqdm.auto import tqdm


def setup_hf_cache_dir(path):
    """
    Set the HuggingFace cache directory.

    Args:
        path (str): The path to set as the HuggingFace
        cache directory.
    """
    os.environ["HF_HOME"] = path
    print(
        f"""HuggingFace cache directory
($HF_HOME) has been set to: {path}
"""
    )


def setup_transformers_cache_dir(path):
    """
    Set the HuggingFace transformers cache directory.

    Args:
        path (str): The path to set as the HuggingFace
        transformers cache directory.
    """
    os.environ["TRANSFORMERS_CACHE"] = path
    print(
        f"""HuggingFace transformers cache directory 
($TRANSFORMERS_CACHE) has been set to: {path}
"""
    )


def setup_sentence_transformers_cache_dir(path):
    """
    Set the HuggingFace sentence transformers cache directory.

    Args:
        path (str): The path to set as the HuggingFace
        sentence transformers cache directory.
    """
    os.environ["SENTENCE_TRANSFORMERS_HOME"] = path
    print(
        f"""HuggingFace sentenct transformers cache directory
($SENTENCE_TRANSFORMERS_HOME) has been set to: {path}
"""
    )


def vectorize_sentences(model, documents, field="text"):
    """
    Vectorize sentences in documents using a specified model.

    Args:
        model: The model to use for encoding sentences.
        documents (list): A list of documents where each
        document is a dictionary containing the field to
        be vectorized.
        field (str, optional): The field in the document
        to be vectorized. Default is 'text'.

    Returns:
        list: A list of documents with the vectorized field
        added.
    """
    vectorized_documents = []
    for doc in tqdm(documents):
        # Transforming the title into an embedding using the model
        doc[f"{field}_vector"] = model.encode(doc[field]).tolist()
        vectorized_documents.append(doc)

    return vectorized_documents
