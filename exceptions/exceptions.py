"""
This module defines custom exceptions for handling all modules related errors.
"""

class ElasticsearchError(Exception):
    """Base class for all Elasticsearch-related exceptions."""


class ElasticsearchConnectionError(ElasticsearchError):
    """Exception raised for errors in establishing a connection to Elasticsearch."""


class ElasticsearchQueryError(ElasticsearchError):
    """Exception raised for errors in querying Elasticsearch."""


class SearchContextWrongValueError(Exception):
    """Ensure that search_context is defined (either minsearch or elasticseach)"""


class QueryTypeWrongValueError(Exception):
    """Ensure that query_type is defined (either text or vector)"""


class WrongPomptParams(Exception):
    """Ensure that the params passed to the prompt template are the expected params"""


class ModelNotCached(Exception):
    """Ensure that the passed `model_name` is previously cached, 'gpt-4o', or None"""


class WrongCliParams(Exception):
    """Ensure correct params passed to the script call."""
