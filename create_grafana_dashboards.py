import os
import json
import argparse

from utils.utils import initialize_env_variables, sleep_seconds
from utils.grafana import (drop_grafana_data_source,
                           create_grafana_data_source, get_grafana_data_source,
                           create_dashboard, get_dashboard_uid_by_name,
                           delete_dashboard)
from exceptions.exceptions import WrongCliParams

def main(datasource_name, recreate_ds=True):
    # Grafana settings
    grafana_host = os.getenv('GRAFANA_SETUP_HOST')
    grafana_port = os.getenv('GRAFANA_PORT')
    grafana_admin_token = os.getenv('GRAFANA_ADMIN_TOKEN')

    # Datasource info
    postgres_host = os.getenv('POSTGRES_HOST')
    postgres_port = os.getenv('POSTGRES_PORT')

    # Grafana datasource configuration
    dashboard_name = os.getenv('GRAFANA_DASHBOARD_NAME')
    datasource_info = {
        "name": datasource_name,
        "type": "grafana-postgresql-datasource",
        "url": f"{postgres_host}:{postgres_port}",
        "access": "proxy",
        "user": os.getenv('POSTGRES_USER'),
        "secureJsonData": {
            "password": os.getenv('POSTGRES_PASSWORD')
        },
        "jsonData": {
            "database": os.getenv('POSTGRES_DB'),
            "postgresVersion": 903,
            "sslmode": "disable"
        }
    }

    print('--',os.getenv('POSTGRES_PASSWORD'),'--', sep='')

    # Drop Datasource if exists
    if recreate_ds:
        drop_grafana_data_source(
            grafana_host=grafana_host, 
            grafana_port=grafana_port, 
            datasource_name=datasource_name, 
            grafana_admin_token=grafana_admin_token,
        )

        # Create the datasource
        create_grafana_data_source(
            grafana_host=grafana_host, 
            grafana_port=grafana_port, 
            datasource_info=datasource_info, 
            grafana_admin_token=grafana_admin_token,
        )

        print("Waiting for some seconds till DS connection is ready...")
        sleep_seconds(20)
    else:
        print("No datasource recreation is requested...")

    datasource_uid = get_grafana_data_source(
        grafana_host, 
        grafana_port, 
        datasource_name,
        grafana_admin_token
    )['uid']


    # Reading dashboard
    json_file_path = os.path.join(
        os.getenv('PROJECT_SETUP_DIR'),
        "config/grafana/course_assistant_bot_dashboard.json",
    )
    with open(json_file_path, "r") as json_file:
        dashboard = json.load(json_file)
        for panel in dashboard['dashboard']['panels']:
            panel['datasource']['uid'] = datasource_uid
            for target in panel['targets']:
                target['datasource']['uid'] = datasource_uid
        dashboard['dashboard']['title'] = dashboard_name

    with open(json_file_path, 'w') as json_file:
        json.dump(dashboard, json_file, indent=4)


    ## Delete dashboard if exists
    dashboard_uid = get_dashboard_uid_by_name(
        grafana_host, grafana_port, dashboard_name, grafana_admin_token
    )
    if dashboard_uid:
        delete_dashboard(grafana_host, grafana_port, dashboard_uid, grafana_admin_token)

    create_dashboard(
        grafana_host, 
        grafana_port, 
        dashboard,
        grafana_admin_token
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reading control parameters.")
    parser.add_argument('--recreate_ds', type=str, required=False, help='Value of reindex_es')
    args = parser.parse_args()

    recreate_ds = args.recreate_ds

    if recreate_ds == 'false' or not recreate_ds:
        recreate_ds = False
    elif recreate_ds == 'true':
        recreate_ds = True
    else:
        raise WrongCliParams(
            "`recreate_ds` parameter must be either true, false, or leave plank."
        )


    initialize_env_variables()
    datasource_name = os.getenv("GRAFANA_DS_NAME")
    main(datasource_name, recreate_ds)

    