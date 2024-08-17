"""
This module provides utility functions for handling various
tasks such as parameter extraction from text, environment
variable initialization, JSON document loading, duplicate
finding, document ID generation, and JSON response parsing.
"""

import hashlib
import base64
import json
import os
import glob
import re
import time
import numpy as np

from dotenv import load_dotenv, set_key, dotenv_values
from exceptions.exceptions import SetupWrongParam


def print_log(*message):
    """
    """
    print(*message, flush=True)


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


def initialize_env_variables(project_root=None, override=True):
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
    load_dotenv(dotenv_path, override=override)


def create_or_update_dotenv_var(dotenv_var, value, project_root=None):
    """
    """
    if not project_root:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

    dotenv_path = os.path.join(project_root, ".env")
    env_variables = dotenv_values(dotenv_path)

    set_key(dotenv_path, dotenv_var, value)

    if dotenv_var in env_variables:
        print(f"Updated existing dotenv variable: {dotenv_var}")
    else:
        print(f"Created new dotenv variable: {dotenv_var}")


def load_json_document(path):
    """
    Load JSON documents from a file.

    Args:
        path (str): The path to the JSON file.

    Returns:
        list: A list of documents with 'text' and meta fields.
    """
    with open(path, "rt", encoding="utf-8") as f_in:
        documents = json.load(f_in)
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


def generate_text_based_uuid(text, uuid_len=11):
    """
    """
    # Hash the text using SHA-256
    hash_object = hashlib.sha256(text.encode('utf-8'))
    
    # Convert the hash to bytes
    hash_bytes = hash_object.digest()
    
    # Encode the hash in base64 and strip padding, taking only the first 11 characters
    short_uuid = base64.urlsafe_b64encode(hash_bytes).rstrip(b'=').decode('utf-8')[:uuid_len]
    
    return short_uuid


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


def flatten_list_of_lists(list_of_lists):
    """
    """
    return [item for sublist in list_of_lists for item in sublist]


def sample_from_list(
    orig_list,
    sample_size=None,
    seed=42,
):
    """
    """
    indices = np.arange(0, len(orig_list))
    np.random.shuffle(indices)
    
    return list(np.array(orig_list)[indices])[:sample_size]


def read_json_file(path):
    """
    """
    if os.path.exists(path):
        with open(path, 'r') as file:
            data = json.load(file)
    else:
        print("File doesn't exist, returning None...")
        data = None
    return data


def save_json_file(data, path, replace=False):
    """
    """
    if not os.path.exists(path) or replace:
        with open(path, 'w') as json_file:
            json.dump(data, json_file, indent=4)
            print(f"Data successfully saved to {path}")
    else:
        print("Skipped...")


def get_json_files_in_dir(dir_path=None, return_full_path=False):
    """
    """
    if not dir_path:
        return []

    json_files = glob.glob(
        os.path.join(dir_path, '*.json')
    )

    if return_full_path:
        return json_files
    else:
        return [json_file.split('/')[-1] for json_file in json_files]


def standardize_array(array):
    """
    """
    return (array - array.mean()) / array.std()


def conf():
    if os.getenv('IS_SETUP') == "true":
        conf = '_SETUP'
    elif os.getenv('IS_SETUP') == "false":
        conf = ''
    else:
        raise SetupWrongParam(
            "'IS_SETUP' env variable must be either 'true' of 'false'")
    
    return conf
