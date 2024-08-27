"""
This module provides utility functions for working with Ollama's embedding API.
The utility functions are used to:
    1. Embed a document using a specified model (must be available in Ollama).
    2. Embed a batch of documents containing 'questions' and 'text' keys.
    3. Additional functions to interact with Ollama models.

The functions simplify embedding operations and ensure that the embedding
results can be directly used for further analysis or search tasks.
"""

from openai import OpenAI


def create_ollama_client(ollama_host, ollama_port):
    """
    Create and return an Ollama client configured with the given host and port.

    Args:
        ollama_host (str): The hostname of the Ollama server.
        ollama_port (int): The port number for the Ollama server.

    Returns:
        OpenAI: An instance of the OpenAI client configured for Ollama.
    """
    return OpenAI(
        base_url=f"http://{ollama_host}:{ollama_port}/v1/",
        api_key="ollama",
    )


def get_embedding(client, text, model_name="nomic-embed-text"):
    """
    Get the embedding for a given text using a specified model.

    Args:
        client: The client instance to use for generating embeddings.
        text (str): The text to be embedded.
        model_name (str, optional): The name of the model to use for embedding.
                                    Default is 'nomic-embed-text'.

    Returns:
        list: The embedding of the text as a list of floats.
    """
    text = text.replace("\n", " ")
    return client.embeddings.create(input=[text], model=model_name).data[0].embedding


def embed_document(
    client,
    document,
    keys=None,
    vector_key="text_vector",
    model_name="nomic-embed-text",
):
    """
    Embed a document using a specified model.

    Args:
        client: The client instance to use for generating embeddings.
        document (dict): A dictionary containing fields specified in `keys`.
        keys (list, optional): A list of keys in the document to concatenate for embedding.
                               Default is ["title", "text", "question"] if not provided.
        vector_key (str, optional): The key under which the embedding vector is stored.
                                    Default is 'text_vector'.
        model_name (str, optional): The name of the model to use for embedding.
                                    Default is 'nomic-embed-text'.

    Returns:
        dict: The original document with an added embedding vector for the
              concatenated fields specified by `keys`.
    """
    if not keys:
        keys = ["title", "text", "question"]

    text = "\n".join([document.get(key, "") for key in keys])

    document[vector_key] = get_embedding(
        client=client, text=text, model_name=model_name
    )

    return document
