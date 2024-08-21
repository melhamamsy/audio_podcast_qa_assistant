#!/bin/sh

GREEN='\033[0;32m'
NC='\033[0m'

# cd to file directory
cd "$(dirname "$0")/.."

# Initialize env variables
export $(grep -v '^#' .env | xargs)

# Count the number of workers matching the pattern
count=$(ps aux | grep "prefect worker start --pool ${WORK_POOL_NAME}" | grep -v grep | wc -l)

# Check if any workers were found and kill them if they exist
if [ "$count" -gt 0 ]; then
    sleep 2
    ps aux | grep "prefect worker start --pool ${WORK_POOL_NAME}" | grep -v grep | awk '{print $2}' | xargs kill
    sleep 2
    ps aux | grep "prefect worker start --pool ${WORK_POOL_NAME}" | grep -v grep | awk '{print $2}' | xargs kill
    echo "$((count / 2)) workers killed."
else
    echo "No workers found to kill."
fi