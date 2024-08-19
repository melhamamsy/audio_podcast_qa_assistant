"""
This module provides functionality to chunk large text documents while ensuring
that questions and their answers remain together. It also includes utilities for
processing episode data for pre-indexing, which involves applying the chunking
function and preparing the text for indexing in search systems.

The module utilizes the spaCy library for sentence segmentation and provides
flexibility in how the chunking is performed through customizable parameters.
"""

import spacy

NLP = spacy.load("en_core_web_sm")


def chunk_large_text(text, max_chunk_size=1000):
    """
    Splits a large text into smaller chunks while ensuring that questions
    and their corresponding answers stay together.

    Args:
        text (str): The large text to be chunked.
        max_chunk_size (int, optional): The maximum size for each chunk in
                                        characters. Defaults to 1000.

    Returns:
        list of str: A list of text chunks.
    """
    doc = NLP(text)
    sentences = [sent.text.strip() for sent in doc.sents]

    chunks = []
    current_chunk = ""

    i = 0
    while i < len(sentences):
        sentence = sentences[i]

        # Handle questions and their answers
        if "?" in sentence:
            question_chunk = sentence
            i += 1

            # Include following sentences as the answer, ensuring not to exceed the max_chunk_size
            while (
                i < len(sentences)
                and len(question_chunk) + len(sentences[i]) <= max_chunk_size
            ):
                question_chunk += " " + sentences[i]
                i += 1

            # Add the combined question-answer chunk to the list
            if len(current_chunk) > 0:
                chunks.append(current_chunk.strip())
                current_chunk = ""

            chunks.append(question_chunk.strip())
        else:
            # If the current chunk can accommodate the sentence
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += sentence + " "
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + " "
            i += 1

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def preindex_process_text(
    episode,
    chunking_function,
    **chunking_function_params,
):
    """
    Processes an episode's text by applying a chunking function and preparing
    it for indexing.

    Args:
        episode (dict): The episode data containing various metadata and text.
        chunking_function (function): The function used to chunk the text.
        **chunking_function_params: Additional parameters to pass to the
                                    chunking function.

    Returns:
        list of dict: A list of processed documents ready for indexing, with
                      each chunk having a unique chunk ID.
    """
    documents = []

    if "audio" in episode:
        del episode["audio"]
    if "description" in episode:
        del episode["description"]
    if "segments" in episode:
        del episode["segments"]

    text = episode["text"]
    del episode["text"]

    chunks = chunking_function(
        text,
        **chunking_function_params,
    )

    for i, chunk in enumerate(chunks):
        episode_doc = episode.copy()

        episode_doc["text"] = chunk
        episode_doc["chunk_id"] = i

        documents.append(episode_doc)

    return documents
