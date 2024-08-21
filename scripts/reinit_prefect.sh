#!/bin/bash


GREEN='\033[0;32m'
NC='\033[0m'


# cd to file directory
cd "$(dirname "$0")/.."


# Initialize env variables
export $(grep -v '^#' .env | xargs)


# Make sure prefect server is down
make prefect_kill_workers
make prefect_stop_server


# Execute in postgres database: Create prefect db if not exists
echo "Reinitializing 'prefect' database..."; echo
docker-compose exec postgres bash -c "
psql -U postgres -d \$POSTGRES_DB -tc \"
    DROP DATABASE IF EXISTS prefect;
\"
"

docker-compose exec postgres bash -c "
  psql -U postgres -d \$POSTGRES_DB -tc \"
    SELECT 1 FROM pg_database WHERE datname = 'prefect'
  \" | grep -q 1 || psql -U postgres -d \$POSTGRES_DB -c \"
    CREATE DATABASE prefect;
  \"
"
echo -e "${GREEN}'prefect' database is ready.${NC}"
sleep 2


# Start the prefect server
make prefect_start_server


# Use local-server profile defined in ~/.prefect/profiles.toml
conda run -n $ENV_NAME prefect profile use local-server


# Create prefect work-pool if not exists
if [ $(python scripts/check_work_pool_exists.py) == "false" ]; then
  conda run -n $ENV_NAME prefect work-pool create "$WORK_POOL_NAME" --type process
  echo -e "${GREEN}Work pool \"$WORK_POOL_NAME\" created.${NC}"
else
  echo "Work pool \"$WORK_POOL_NAME\" already exists."
fi


# Stopping the prefect server
make prefect_stop_server