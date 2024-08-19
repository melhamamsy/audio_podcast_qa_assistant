"""
This module provides utility functions for interacting with Grafana.
The utilities include functions to:
    1. Verify and manage Grafana API tokens.
    2. Create, retrieve, and delete data sources in Grafana.
    3. Create, retrieve, and delete dashboards in Grafana.

These functions help automate common administrative tasks for Grafana
using the Grafana HTTP API.
"""

import json

import requests

from utils.variables import (GRAFANA_ADMIN_PASSWORD, GRAFANA_ADMIN_TOKEN,
                             GRAFANA_ADMIN_USER, GRAFANA_URL)


def is_grafana_token_valid():
    """
    Check if the Grafana API token is valid.

    Returns:
        bool: True if the token is valid, otherwise False.
    """
    # Headers with the token for authentication
    headers = {
        "Authorization": f"Bearer {GRAFANA_ADMIN_TOKEN}",
        "Content-Type": "application/json",
    }

    # Make the GET request to verify the token
    response = requests.get(url=f"{GRAFANA_URL}/api/user", headers=headers, timeout=30)

    # Check if the token is valid
    if response.status_code == 200:
        user_info = response.json()
        print(f"Token is valid. user_info: {user_info}")
        return True

    print(f"Token is invalid. Status code: {response.status_code}")
    print(response.json())
    return False


def create_grafana_token(seconds_to_live=0):
    """
    Create a new Grafana API token.

    Args:
        seconds_to_live (int, optional): The duration in seconds for the token's
                                         validity. Set to 0 for no expiration.
                                         Defaults to 0.

    Returns:
        str: The created API token, or None if the creation fails.
    """
    # Payload for creating the API key
    payload = {"name": "AdminToken", "role": "Admin", "secondsToLive": seconds_to_live}

    # Headers with basic authentication
    headers = {"Content-Type": "application/json"}

    # Make the POST request to create the API key
    response = requests.post(
        url=f"{GRAFANA_URL}/api/auth/keys",
        json=payload,
        headers=headers,
        timeout=30,
        auth=(GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD),
    )

    # Check if the request was successful
    token = None
    if response.status_code == 200:
        token = response.json().get("key")
        print(f"API Key: {token}")
    else:
        print(f"Failed to create API key. Status code: {response.status_code}")
        print(response.json())

    return token


def get_grafana_token_ids():
    """
    Retrieve and return a list of existing Grafana API token IDs.

    Returns:
        list: A list of Grafana API token IDs.
    """
    headers = {"Content-Type": "application/json"}

    # Make the GET request to list the API keys
    response = requests.get(
        url=f"{GRAFANA_URL}/api/auth/keys",
        headers=headers,
        timeout=30,
        auth=(GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD),
    )

    # Check if the request was successful
    token_ids = []

    if response.status_code == 200:
        keys = response.json()
        if keys:
            print("Existing Grafana API Keys:")
            for key in keys:
                print(key)
                token_ids.append(key["id"])
        else:
            print("No Grafana API keys found.")
    else:
        print(f"Failed to retrieve API keys. Status code: {response.status_code}")
        print(response.json())

    return token_ids


def delete_grafana_token(token_id):
    """
    Delete a Grafana API token by its ID.

    Args:
        token_id (int): The ID of the Grafana API token to delete.
    """
    headers = {"Content-Type": "application/json"}

    # Make the DELETE request to delete the API key
    response = requests.delete(
        url=f"{GRAFANA_URL}/api/auth/keys/{token_id}",
        headers=headers,
        timeout=30,
        auth=(GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD),
    )

    # Check if the request was successful
    if response.status_code == 200:
        print(f"API Key with ID {token_id} successfully deleted.")
    else:
        print(f"Failed to delete API key. Status code: {response.status_code}")
        print(response.json())


def get_grafana_data_source(datasource_name):
    """
    Retrieve and return the details of a Grafana data source by its name.

    Args:
        datasource_name (str): The name of the Grafana data source.

    Returns:
        dict: The details of the data source, or None if the request fails.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRAFANA_ADMIN_TOKEN}",
    }

    response = requests.get(
        url=f"{GRAFANA_URL}/api/datasources/name/{datasource_name}",
        headers=headers,
        timeout=30,
    )

    if response.status_code == 200:
        print(f"Found datasource {datasource_name} with uid {response.json()['uid']}")
        return response.json()

    print(
        "Failed to get datasource ID. Status code:",
        response.status_code,
        f"Response: {response.text}",
    )
    return None


def drop_grafana_data_source(datasource_name):
    """
    Delete a Grafana data source by its name.

    Args:
        datasource_name (str): The name of the Grafana data source to delete.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRAFANA_ADMIN_TOKEN}",
    }

    response = requests.get(
        url=f"{GRAFANA_URL}/api/datasources/name/{datasource_name}",
        headers=headers,
        timeout=30,
    )
    if response.status_code == 200:
        datasource_id = response.json()["id"]
        # Delete the datasource by ID
        delete_response = requests.delete(
            url=f"{GRAFANA_URL}/api/datasources/{datasource_id}",
            headers=headers,
            timeout=30,
        )
        if delete_response.status_code == 200:
            print("Datasource deleted successfully.")
        else:
            print(
                "Failed to delete datasource. Status code:",
                delete_response.status_code,
                f"Response: {delete_response.text}",
            )


def create_grafana_data_source(datasource_info):
    """
    Create a new Grafana data source.

    Args:
        datasource_info (dict): The details of the data source to create.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRAFANA_ADMIN_TOKEN}",
    }

    response = requests.post(
        url=f"{GRAFANA_URL}/api/datasources",
        headers=headers,
        timeout=30,
        data=json.dumps(datasource_info),
    )

    if response.status_code == 200:
        print("Datasource created successfully.")
    else:
        print(
            "Failed to create datasource. Status code:",
            response.status_code,
            f"Response: {response.text}",
        )


def create_dashboard(dashboard):
    """
    Create a new Grafana dashboard.

    Args:
        dashboard (dict): The details of the dashboard to create.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GRAFANA_ADMIN_TOKEN}",
    }

    # Create the dashboard
    response = requests.post(
        url=f"{GRAFANA_URL}/api/dashboards/db",
        headers=headers,
        timeout=30,
        data=json.dumps(dashboard),
    )

    if response.status_code == 200:
        print("Dashboard created successfully.")
    else:
        print(
            "Failed to create dashboard. Status code:",
            response.status_code,
            f"Response: {response.text}",
        )


def get_dashboard_uid_by_name(dashboard_name):
    """
    Get the UID of a Grafana dashboard by its name.

    Args:
        dashboard_name (str): The name of the dashboard to search for.

    Returns:
        str: The UID of the dashboard, or None if it is not found.
    """
    headers = {"Authorization": f"Bearer {GRAFANA_ADMIN_TOKEN}"}

    # List all dashboards
    response = requests.get(
        url=f"{GRAFANA_URL}/api/search",
        headers=headers,
        timeout=30,
    )

    if response.status_code == 200:
        dashboards = response.json()
        for dashboard in dashboards:
            if dashboard.get("title") == dashboard_name:
                return dashboard.get("uid")
        print("Dashboard {dashboard_name} not found.")
    else:
        print(
            "Failed to retrieve dashboards. Status code:",
            response.status_code,
            f"Response: {response.text}",
        )
    return None


def delete_dashboard(dashboard_uid):
    """
    Delete a Grafana dashboard by its UID.

    Args:
        dashboard_uid (str): The UID of the dashboard to delete.
    """
    headers = {"Authorization": f"Bearer {GRAFANA_ADMIN_TOKEN}"}

    # Delete the dashboard
    response = requests.delete(
        url=f"{GRAFANA_URL}/api/dashboards/uid/{dashboard_uid}",
        headers=headers,
        timeout=30,
    )

    if response.status_code == 200:
        print(f"Dashboard {dashboard_uid} deleted successfully.")
    else:
        print(
            "Failed to delete dashboard. Status code:",
            response.status_code,
            f"Response: {response.text}",
        )
