"""
This module provides utility functions for interacting with the OpenAI API.
The main functionality includes:
    1. Creating an OpenAI client using a provided API key or an environment variable.
    2. Handling JSON responses from the OpenAI API.

These utilities streamline the process of setting up and using OpenAI's services.
"""

import os

from openai import OpenAI


def create_openai_client(api_key=None):
    """
    Create and return an OpenAI client.

    Args:
        api_key (str, optional): The API key for authenticating with OpenAI.
                                 If not provided, the function attempts to
                                 retrieve it from the 'OPENAI_API_KEY' environment variable.

    Returns:
        OpenAI: An instance of the OpenAI client.
    """
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)
