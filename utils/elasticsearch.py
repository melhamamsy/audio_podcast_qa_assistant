"""
This module provides utility functions for interacting with Elasticsearch.
It includes functions to create an Elasticsearch client, manage indices, 
search, and index documents.
Custom exceptions are also handled for connection and query errors.
"""

import json

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError, RequestError

from exceptions.exceptions import ElasticsearchConnectionError


def create_elasticsearch_client(host, port):
    """
    Create and return an Elasticsearch client.

    Args:
        host (str): The hostname for the Elasticsearch instance.
        port (int): The port for the Elasticsearch instance.

    Returns:
        Elasticsearch: An Elasticsearch client instance.

    Raises:
        ElasticsearchConnectionError: If the connection to Elasticsearch fails.
    """
    try:
        es_client = Elasticsearch(f"http://{host}:{port}")
        # Perform a simple request to check if the connection is successful
        if not es_client.ping():
            raise ElasticsearchConnectionError("Could not connect to Elasticsearch")
        print("Connected to Elasticsearch")
        return es_client
    except ConnectionError as e:
        raise ElasticsearchConnectionError(
            "ConnectionError: Could not connect to Elasticsearch"
        ) from e


def create_elasticsearch_index(es_client, index_name, index_settings, timeout=60):
    """
    Create an Elasticsearch index with the specified settings.

    Args:
        es_client (Elasticsearch): The Elasticsearch client instance.
        index_name (str): The name of the index to create.
        index_settings (dict): The settings for the index.
        timeout (int): The timeout for the index creation request in seconds. Default is 60.
    """
    try:
        es_client.indices.create(
            index=index_name, body=index_settings, timeout=f"{timeout}s"
        )
        print(f"Successfully created index {index_name}.")
    except RequestError as e:
        if e.info.get("error", {}).get("type") == "resource_already_exists_exception":
            print(f"Found an existing index with name {index_name}, nothing to do.")
        else:
            print(e)


def search_elasticsearch_indecis(
    es_client,
):
    """
    Retrieve and return the list of indices in the Elasticsearch cluster.

    Args:
        es_client (Elasticsearch): The Elasticsearch client instance.

    Returns:
        list: A list of index names.
    """
    indices = list(es_client.indices.get_alias(index="*"))
    return indices


def get_indexed_documents_count(
    es_client,
    index_name,
):
    """
    Get the count of documents indexed in a specific Elasticsearch index.

    Args:
        es_client (Elasticsearch): The Elasticsearch client instance.
        index_name (str): The name of the index.

    Returns:
        int: The number of documents in the index.
    """
    return es_client.count(index=index_name)


def remove_elasticsearch_index(
    es_client,
    index_name,
):
    """
    Remove an Elasticsearch index.

    Args:
        es_client (Elasticsearch): The Elasticsearch client instance.
        index_name (str): The name of the index to remove.
    """
    try:
        es_client.indices.delete(index=index_name)
        print(f"Successfully removed index {index_name}.")

    except NotFoundError:
        print(f"Found no index with name {index_name}, nothing to remove.")


def load_index_settings(index_settings_path):
    """
    Load and return the index settings from a JSON file.

    Args:_
        index_settings_path (str): The file path to the index settings JSON file.

    Returns:
        dict: The index settings.
    """
    with open(index_settings_path, "rt", encoding="utf-8") as f_in:
        index_settings = json.load(f_in)
    return index_settings


def delete_indexed_document(es_client, index_name, document):
    """
    Remove indexed documents with the same id and chunk_id from an Elasticsearch index.

    Args:
        es_client (Elasticsearch): The Elasticsearch client instance.
        index_name (str): The name of the index.
        document (dict): The document containing the id and chunk_id for deletion.

    Returns:
        int: The number of documents deleted.
    """
    # Remove indexed documents with same id & chunk_id
    _ids_response = es_client.search(
        index=index_name,
        body={
            "query": {
                "bool": {
                    "must": [
                        {"term": {"id": document["id"]}},
                        {"term": {"chunk_id": document["chunk_id"]}},
                    ]
                }
            }
        },
    )

    # Extract document IDs from the search results
    ## Should be one, but just to make sure
    _ids = [hit["_id"] for hit in _ids_response["hits"]["hits"]]
    for _id in _ids:
        _ = es_client.delete(index=index_name, id=_id)

    return len(_ids)


def index_document(es_client, index_name, document, timeout=60, replace=True):
    """
    Index a document into an Elasticsearch index.

    Args:
        es_client (Elasticsearch): The Elasticsearch client instance.
        index_name (str): The name of the index.
        document (dict): The document to index.
        timeout (int, optional): The timeout for indexing requests in seconds.
                                 Default is 60.
        replace (bool, optional): Whether to replace existing documents with
                                  the same id and chunk_id. Defaults to True.

    Returns:
        dict: A status dictionary containing the number of documents removed and indexed.
    """

    status = {
        "removed": 0,
        "indexed": 0,
    }

    if replace:
        try:
            status["removed"] += delete_indexed_document(
                es_client, index_name, document
            )
        except NotFoundError:
            pass

    try:
        es_client.index(index=index_name, document=document, timeout=f"{timeout}s")
        status["indexed"] = 1
    except RequestError as e:
        print(f"{e}", "id:", document["id"], "-> Skipped...")

    return status


def get_index_mapping(es_client, index_name):
    """
    Retrieve and return the mapping for an Elasticsearch index.

    Args:
        es_client (Elasticsearch): The Elasticsearch client instance.
        index_name (str): The name of the index.

    Returns:
        dict: A dictionary containing field names and their types, or None if an error occurs.
    """
    try:
        # Retrieve the mapping for the given index
        mapping = es_client.indices.get_mapping(index=index_name)

        # Extract the properties section which contains the field mappings
        properties = mapping[index_name]["mappings"]["properties"]

        # Extract field names and their types
        field_types = {field: properties[field]["type"] for field in properties}

        return field_types

    except RequestError as e:
        print(f"An error occurred: {e}")
        return None
