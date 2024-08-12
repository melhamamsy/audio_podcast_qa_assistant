"""
This module provides utility functions for handling various
tasks such as parameter extraction from text, environment
variable initialization, JSON document loading, duplicate
finding, document ID generation, and JSON response parsing.
"""

import hashlib
import json
import os
import re
import time

from dotenv import load_dotenv


def find_parameters(text):
    """
    Find and return all parameters in curly braces within the text.

    Args:
        text (str): The input text to search for parameters.

    Returns:
        list: A list of parameter names found in the text.
    """
    pattern = r"\{(.*?)\}"
    return re.findall(pattern, text)


def is_sublist(main_list, sublist):
    """
    Check if the sublist is a sublist of the main list.

    Args:
        main_list (list): The main list to search within.
        sublist (list): The sublist to check for.

    Returns:
        bool: True if the sublist is found within the main list,
        False otherwise.
    """
    it = iter(main_list)
    return all(any(sub_elem == main_elem for main_elem in it) for sub_elem in sublist)


def initialize_env_variables(project_root=None):
    """
    Initialize environment variables from a .env file.

    Args:
        project_root (str, optional): The root directory of the
        project. Default is None.
    """
    # Construct the full path to the .env file
    if not project_root:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

    dotenv_path = os.path.join(project_root, ".env")

    print("Initialized environment variables listed in:", dotenv_path)
    # Load the .env file
    load_dotenv(dotenv_path)


def load_json_document(path):
    """
    Load JSON documents from a file.

    Args:
        path (str): The path to the JSON file.

    Returns:
        list: A list of documents with 'course' and other fields.
    """
    with open(path, "rt", encoding="utf-8") as f_in:
        docs_raw = json.load(f_in)
    documents = []

    for course_dict in docs_raw:
        for doc in course_dict["documents"]:
            doc["course"] = course_dict["course"]
            documents.append(doc)

    return documents


def find_duplicates(lst):
    """
    Find and return duplicate items in a list.

    Args:
        lst (list): The list to search for duplicates.

    Returns:
        list: A list of tuples, each containing the indices of
        duplicate items.
    """
    index_dict = {}

    for index, item in enumerate(lst):
        if item in index_dict:
            index_dict[item].append(index)
        else:
            index_dict[item] = [index]

    duplicates = [tuple(indices) for indices in index_dict.values() if len(indices) > 1]

    return duplicates


def generate_document_id(doc):
    """
    Generate a unique document ID using a hash.

    Args:
        doc (dict): The document containing 'course', 'question',
        and 'text' fields.

    Returns:
        str: A unique document ID.
    """
    combined = f"{doc['course']}-{doc['question']}-{doc['text'][:10]}"
    hash_object = hashlib.md5(combined.encode())
    hash_hex = hash_object.hexdigest()
    document_id = hash_hex[:8]
    return document_id


def id_documents(docs):
    """
    Assign unique IDs to a list of documents.

    Args:
        docs (list): A list of documents to assign IDs to.

    Returns:
        list: The list of documents with assigned IDs.
    """
    ## We might need to return hashes dict
    for doc in docs:
        doc["id"] = generate_document_id(doc)

    return docs


def correct_json_string(input_string):
    """
    Correct JSON string by replacing single backslashes with
    double backslashes.

    Args:
        input_string (str): The input JSON string.

    Returns:
        str: The corrected JSON string.
    """
    corrected_string = input_string.replace("\\", "\\\\")
    return corrected_string


def parse_json_response(response):
    """
    Parse a JSON response, correcting it if necessary.

    Args:
        response (str): The JSON response string.

    Returns:
        dict: The parsed JSON response.
    """
    try:
        return json.loads(response)
    except ValueError:
        return json.loads(correct_json_string(response))
    

def sleep_seconds(total_wait_time, logging_interval=5):
    """
    """
    logging_interval = 5

    for remaining in range(total_wait_time, 0, -logging_interval):
        print(f"Time remaining: {remaining} seconds")
        time.sleep(logging_interval)
