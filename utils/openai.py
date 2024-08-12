"""
"""

from openai import OpenAI
import os

def create_openai_client(api_key=None):
    """
    """
    if not api_key:
        api_key = os.getenv('OPENAI_API_KEY')
    return OpenAI(api_key=api_key)