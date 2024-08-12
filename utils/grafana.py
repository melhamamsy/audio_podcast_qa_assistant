import requests
import json


def get_grafana_data_source(grafana_host, grafana_port, datasource_name, grafana_admin_token):
    """
    """
    grafana_url = f'http://{grafana_host}:{grafana_port}'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {grafana_admin_token}'
    }

    response = requests.get(
        f'{grafana_url}/api/datasources/name/{datasource_name}', headers=headers
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


def drop_grafana_data_source(grafana_host, grafana_port, datasource_name, grafana_admin_token):
    """
    """
    grafana_url = f'http://{grafana_host}:{grafana_port}'

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {grafana_admin_token}'
    }

    response = requests.get(
        f'{grafana_url}/api/datasources/name/{datasource_name}', headers=headers
    )
    if response.status_code == 200:
        datasource_id = response.json()['id']
        # Delete the datasource by ID
        delete_response = requests.delete(
            f'{grafana_url}/api/datasources/{datasource_id}', headers=headers
        )
        if delete_response.status_code == 200:
            print('Datasource deleted successfully.')
        else:
            print(
                f'Failed to delete datasource. Status code:',
                delete_response.status_code, 
                f'Response: {delete_response.text}'
            )
            

def create_grafana_data_source(
    grafana_host, grafana_port, datasource_info, grafana_admin_token
):
    """
    """
    grafana_url = f'http://{grafana_host}:{grafana_port}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {grafana_admin_token}'
    }

    response = requests.post(
        f'{grafana_url}/api/datasources', headers=headers, data=json.dumps(datasource_info)
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
        

def create_dashboard(
    grafana_host, grafana_port, dashboard, grafana_admin_token
):
    """
    """
    grafana_url = f'http://{grafana_host}:{grafana_port}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {grafana_admin_token}'
    }

    # Create the dashboard
    response = requests.post(
        f'{grafana_url}/api/dashboards/db', headers=headers, data=json.dumps(dashboard)
    )

    if response.status_code == 200:
        print('Dashboard created successfully.')
    else:
        print(
            f'Failed to create dashboard. Status code:',
            response.status_code,
            f'Response: {response.text}'
        )


def get_dashboard_uid_by_name(grafana_host, grafana_port, dashboard_name, grafana_admin_token):
    """
    Function to get the UID of a Grafana dashboard by its name.
    """
    grafana_url = f'http://{grafana_host}:{grafana_port}'
    headers = {
        'Authorization': f'Bearer {grafana_admin_token}'
    }

    # List all dashboards
    response = requests.get(f'{grafana_url}/api/search', headers=headers)

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
    

def delete_dashboard(grafana_host, grafana_port, dashboard_uid, grafana_admin_token):
    """
    Function to delete a Grafana dashboard.
    """
    grafana_url = f'http://{grafana_host}:{grafana_port}'
    headers = {
        'Authorization': f'Bearer {grafana_admin_token}'
    }

    # Delete the dashboard
    response = requests.delete(
        f'{grafana_url}/api/dashboards/uid/{dashboard_uid}', headers=headers
    )

    if response.status_code == 200:
        print(f'Dashboard {dashboard_uid} deleted successfully.')
    else:
        print(
            f'Failed to delete dashboard. Status code: {response.status_code}, Response: {response.text}'
        )
