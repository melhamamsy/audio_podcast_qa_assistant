"""
This module provides utility functions for working with Hugging Face models, 
including functions to vectorize text and documents, normalize vectors to unit 
length, and embed documents by concatenating specified fields.
"""

import numpy as np


def vectorize_text(model, text, precision=10):
    """
    Vectorize a given text using a specified model and normalize
    the resulting vector to unit length.

    Args:
        model: The model to use for encoding the text,
               typically a sentence or document embedding model.
        text (str): The text to be vectorized.
        precision (int): The number of decimal places to which the vector
                         components should be rounded. Default is 10.

    Returns:
        list: A list representing the normalized vector (unit length) of the
              encoded text, rounded to the specified precision.
    """
    vec = model.encode(text)
    vec = vec / np.linalg.norm(vec).tolist()

    return [round(d, precision) for d in vec]


def vectorize_document(
    model,
    document,
    keys=None,
    vector_key="text_vector",
    precision=10,
):
    """
    Embed a document by concatenating specified fields and vectorizing
    the resulting text using a specified model.

    Args:
        model: The model to use for generating embeddings.
        document (dict): A dictionary containing fields specified in `keys`.
        keys (list, optional): A list of keys in the document to concatenate
                               for embedding. Default is ["title", "text", "question"].
        vector_key (str, optional): The key under which the embedding vector
                                    is stored. Default is 'text_vector'.
        precision (int, optional): The number of decimal places to which the
                                   vector components should be rounded. Default is 10.

    Returns:
        dict: The original document with an added embedding vector for the
              concatenated fields specified by `keys`.
    """
    if not keys:
        keys = ["title", "text", "question"]

    text = "\n".join([document.get(key, "") for key in keys])

    document[vector_key] = vectorize_text(model=model, text=text, precision=precision)

    return document
