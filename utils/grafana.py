import requests
import json
from utils.variables import (
    GRAFANA_URL,
    GRAFANA_ADMIN_USER,
    GRAFANA_ADMIN_PASSWORD,
    GRAFANA_ADMIN_TOKEN,
)


def create_grafana_token(seconds_to_live=0):
    """
    """
    # Payload for creating the API key
    payload = {
        "name": "AdminToken",
        "role": "Admin",
        "secondsToLive": seconds_to_live  # Set to 0 for no expiration
    }

    # Headers with basic authentication
    headers = {
        "Content-Type": "application/json"
    }

    # Make the POST request to create the API key
    response = requests.post(
        url=f"{GRAFANA_URL}/api/auth/keys",
        json=payload,
        headers=headers,
        auth=(GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD)
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
    """
    headers = {
        "Content-Type": "application/json"
    }

    # Make the GET request to list the API keys
    response = requests.get(
        url=f"{GRAFANA_URL}/api/auth/keys",
        headers=headers,
        auth=(GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD)
    )

    # Check if the request was successful
    token_ids = []

    if response.status_code == 200:
        keys = response.json()
        if keys:
            print("Existing Grafana API Keys:")
            for key in keys:
                print(key)
                token_ids.append(key['id'])
        else:
            print("No Grafana API keys found.")
    else:
        print(f"Failed to retrieve API keys. Status code: {response.status_code}")
        print(response.json())

    return token_ids


def delete_grafana_token(token_id):
    """
    """
    headers = {
        "Content-Type": "application/json"
    }

    # Make the DELETE request to delete the API key
    response = requests.delete(
        url=f"{GRAFANA_URL}/api/auth/keys/{token_id}",
        headers=headers,
        auth=(GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD)
    )

    # Check if the request was successful
    if response.status_code == 200:
        print(f"API Key with ID {token_id} successfully deleted.")
    else:
        print(f"Failed to delete API key. Status code: {response.status_code}")
        print(response.json())


def get_grafana_data_source(datasource_name):
    """
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {GRAFANA_ADMIN_TOKEN}'
    }

    response = requests.get(
        f'{GRAFANA_URL}/api/datasources/name/{datasource_name}', headers=headers
    )

    if response.status_code == 200:
        print(f"Found datasource {datasource_name} with uid {response.json()['uid']}")
        return response.json()
    else:
        print(
            f'Failed to get datasource ID. Status code:',
            response.status_code,
            f'Response: {response.text}'
        )


def drop_grafana_data_source(datasource_name):
    """
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {GRAFANA_ADMIN_TOKEN}'
    }

    response = requests.get(
        f'{GRAFANA_URL}/api/datasources/name/{datasource_name}', headers=headers
    )
    if response.status_code == 200:
        datasource_id = response.json()['id']
        # Delete the datasource by ID
        delete_response = requests.delete(
            f'{GRAFANA_URL}/api/datasources/{datasource_id}', headers=headers
        )
        if delete_response.status_code == 200:
            print('Datasource deleted successfully.')
        else:
            print(
                f'Failed to delete datasource. Status code:',
                delete_response.status_code, 
                f'Response: {delete_response.text}'
            )
            

def create_grafana_data_source(datasource_info):
    """
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {GRAFANA_ADMIN_TOKEN}'
    }

    response = requests.post(
        f'{GRAFANA_URL}/api/datasources', headers=headers, data=json.dumps(datasource_info)
    )

    if response.status_code == 200:
        print('Datasource created successfully.')
    else:
        print(
            f'Failed to create datasource. Status code:', 
            response.status_code,
            f'Response: {response.text}'
        )
        exit()
        

def create_dashboard(dashboard):
    """
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {GRAFANA_ADMIN_TOKEN}'
    }

    # Create the dashboard
    response = requests.post(
        f'{GRAFANA_URL}/api/dashboards/db', headers=headers, data=json.dumps(dashboard)
    )

    if response.status_code == 200:
        print('Dashboard created successfully.')
    else:
        print(
            f'Failed to create dashboard. Status code:',
            response.status_code,
            f'Response: {response.text}'
        )


def get_dashboard_uid_by_name(dashboard_name):
    """
    Function to get the UID of a Grafana dashboard by its name.
    """
    headers = {
        'Authorization': f'Bearer {GRAFANA_ADMIN_TOKEN}'
    }

    # List all dashboards
    response = requests.get(f'{GRAFANA_URL}/api/search', headers=headers)

    if response.status_code == 200:
        dashboards = response.json()
        for dashboard in dashboards:
            if dashboard.get('title') == dashboard_name:
                return dashboard.get('uid')
        print('Dashboard {dashboard_name} not found.')
        return None
    else:
        print(f'Failed to retrieve dashboards. Status code: {response.status_code}, Response: {response.text}')
        return None
    

def delete_dashboard(dashboard_uid):
    """
    Function to delete a Grafana dashboard.
    """
    headers = {
        'Authorization': f'Bearer {GRAFANA_ADMIN_TOKEN}'
    }

    # Delete the dashboard
    response = requests.delete(
        f'{GRAFANA_URL}/api/dashboards/uid/{dashboard_uid}', headers=headers
    )

    if response.status_code == 200:
        print(f'Dashboard {dashboard_uid} deleted successfully.')
    else:
        print(
            f'Failed to delete dashboard. Status code: {response.status_code}, Response: {response.text}'
        )
