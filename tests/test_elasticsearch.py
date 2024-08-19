"""
Unit tests for utils.elasticsearch module.
"""

import pytest

# from utils.elasticsearch import get_index_mapping
from utils.elasticsearch import (
    create_elasticsearch_client,
    create_elasticsearch_index,
    delete_indexed_document,
    get_indexed_documents_count,
    index_document,
    remove_elasticsearch_index,
    search_elasticsearch_indecis,
)


@pytest.fixture(scope="module")
def es_client():
    """Fixture to create an Elasticsearch client for testing."""
    client = create_elasticsearch_client(host="localhost", port=9200)
    yield client
    # No cleanup here since we handle it in individual tests


@pytest.fixture(scope="module")
def test_index():
    """Fixture to provide a test index name."""
    return "test_index"


@pytest.fixture(scope="function")
def setup_index(es_client, test_index):
    """Fixture to set up and tear down the test index."""
    # Create index settings
    index_settings = {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {
            "dynamic": "false",
            "properties": {
                "id": {"type": "keyword"},
                "chunk_id": {"type": "integer"},
                "text": {"type": "text"},
            },
        },
    }

    # Ensure the index does not already exist
    if es_client.indices.exists(index=test_index):
        es_client.indices.delete(index=test_index)

    # Create the index
    es_client.indices.create(index=test_index, body=index_settings)
    es_client.indices.refresh(index=test_index)

    yield  # Control passes to the test function

    # Clean up: Remove the index after the test
    if es_client.indices.exists(index=test_index):
        es_client.indices.delete(index=test_index)


def test_create_and_remove_index(es_client, test_index):
    """Test creating and removing an Elasticsearch index."""
    index_settings = {
        "settings": {"number_of_shards": 1, "number_of_replicas": 0},
        "mappings": {
            "dynamic": "false",
            "properties": {
                "id": {"type": "keyword"},
                "chunk_id": {"type": "keyword"},
                "text": {"type": "text"},
            },
        },
    }

    # Create index
    create_elasticsearch_index(es_client, test_index, index_settings)
    indices = search_elasticsearch_indecis(es_client)
    assert test_index in indices

    # Remove index
    remove_elasticsearch_index(es_client, test_index)
    indices = search_elasticsearch_indecis(es_client)
    assert test_index not in indices


def test_index_document_and_count(es_client, test_index):
    """Test indexing a document and counting the documents."""
    document = {"id": "1", "chunk_id": "0", "text": "This is a test document."}

    # Index the document
    status = index_document(es_client, test_index, document)
    print("Indexing status:", status)

    es_client.indices.refresh(index=test_index)

    # Check that the document count is 1
    count = get_indexed_documents_count(es_client, test_index)
    print("Document count:", count)
    assert count["count"] == 1


# def test_get_index_mapping(es_client, test_index):
#     """Test retrieving the index mapping."""
#     mapping = get_index_mapping(es_client, test_index)
#     expected_mapping = {"id": "keyword", "chunk_id": "keyword", "text": "text"}
#     assert mapping == expected_mapping


def test_delete_document(es_client, test_index):
    """Test deleting a specific document."""
    document = {"id": "1", "chunk_id": "0", "text": "This is a test document."}
    index_document(es_client, test_index, document)

    es_client.indices.refresh(index=test_index)

    # Delete the document
    deleted_count = delete_indexed_document(es_client, test_index, document)
    assert deleted_count == 1

    es_client.indices.refresh(index=test_index)

    # Check that the document count is 0 after deletion
    count = get_indexed_documents_count(es_client, test_index)
    assert count["count"] == 0
