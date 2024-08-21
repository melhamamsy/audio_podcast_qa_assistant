#!/bin/bash


GREEN='\033[0;32m'
NC='\033[0m'

# default of prefect deployments (you can adjust when creating a deployment run)
reindex_es="false"
reinit_db="false"
defacto="true"
reinit_grafana="false"
recreate_dashboards="false"


# Function to echo a new line before and after a message
echoo() {
  echo ""
  echo "$1"
  echo ""
}


# cd to file directory
cd "$(dirname "$0")/.."


# Initialize env variables
export $(grep -v '^#' .env | xargs)


# Check passed params
for param in "$@"
do
    case $param in
        reindex_es=*)
        reindex_es="${param#*=}"
        if [[ "$reindex_es" != "true" && "$reindex_es" != "false" ]]; then
            echo "Invalid value for x: $reindex_es. Must be 'true' or 'false'."
            exit 1
        fi
        shift # remove the current param from the list
        ;;
        reinit_db=*)
        reinit_db="${param#*=}"
        if [[ "$reinit_db" != "true" && "$reinit_db" != "false" ]]; then
            echo "Invalid value for x: $reinit_db. Must be 'true' or 'false'."
            exit 1
        fi
        shift # remove the current param from the list
        ;;
        defacto=*)
        defacto="${param#*=}"
        if [[ "$defacto" != "true" && "$defacto" != "false" ]]; then
            echo "Invalid value for x: $defacto. Must be 'true' or 'false'."
            exit 1
        fi
        shift # remove the current param from the list
        ;;
        reinit_grafana=*)
        reinit_grafana="${param#*=}"
        if [[ "$reinit_grafana" != "true" && "$reinit_grafana" != "false" ]]; then
            echo "Invalid value for x: $reinit_grafana. Must be 'true' or 'false'."
            exit 1
        fi
        shift # remove the current param from the list
        ;;
        recreate_dashboards=*)
        recreate_dashboards="${param#*=}"
        if [[ "$recreate_dashboards" != "true" && "$recreate_dashboards" != "false" ]]; then
            echo "Invalid value for x: $recreate_dashboards. Must be 'true' or 'false'."
            exit 1
        fi
        shift # remove the current param from the list
        ;;
        *)
        echo "Invalid parameter: $param"
        exit 1
        ;;
    esac
done


# Activate the conda environment and run setup.py
source activate $ENV_NAME


# Prefect Tasks
echo Re-deploying prefect flows ...
python scripts/redeploy_flows.py \
    --reindex_es "$reindex_es" \
    --reinit_db "$reinit_db" \
    --defacto "$defacto" \
    --reinit_grafana "$reinit_grafana" \
    --recreate_dashboards "$recreate_dashboards"
echo -e "${GREEN}Successfully redeployed prefect flows.${NC}"