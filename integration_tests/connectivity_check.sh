#!/bin/bash


RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'


# Parse the keep-containers-running argument if passed
if [[ "$1" == "true" || "$1" == "false" ]]; then
  keep_containers_running=$1
elif [[ -z "$1" ]]; then
  keep_containers_running=false
else
  echo -e "${RED}ERROR: keep-containers-running should be either 'true' or 'false'.${NC}"
  exit 1
fi

# cd to the root directory where docker-compose.yml is located
cd "$(dirname "$0")/.."

# Initialize env variables
export $(grep -v '^#' .env | xargs)

# Function to check if a service is healthy
check_service_health() {
  local service_name=$1
  local container_name=$2

  echo "Checking health of ${service_name}..."

  # Wait until the container is healthy or times out
  for i in {1..30}; do
    if docker inspect --format "{{.State.Health.Status}}" "${container_name}" | grep -q "healthy"; then
      echo -e "${GREEN}${service_name} is healthy!${NC}"
      return 0
    else
      echo "Waiting for ${service_name} to become healthy..."
      sleep 5
    fi
  done

  docker-compose down
  echo -e "${RED}ERROR: ${service_name} did not become healthy in time.${NC}"
  exit 1
}

# Function to check connectivity between services
check_connectivity() {
  local source_name=$1
  local source_container=$2
  local target_name=$3
  local target_url=$4
  local protocol=$5

  echo "Checking connectivity from ${source_name} to ${target_name}..."

  if [[ "${protocol}" == "http" ]]; then
    if docker exec "${source_container}" curl -s --fail "${target_url}"; then
      echo -e "${GREEN}${source_name} can successfully communicate with ${target_name} at ${target_url}!${NC}"
    else
      docker-compose down
      echo -e "${RED}ERROR: ${source_name} cannot communicate with ${target_name} at ${target_url}.${NC}"
      exit 1
    fi
  elif [[ "${protocol}" == "postgres" ]]; then
    # Extract host and port from the URL
    local host=$(echo "${target_url}" | awk -F[/:] '{print $4}')
    local port=$(echo "${target_url}" | awk -F[/:] '{print $5}')

    if docker exec "${source_container}" bash -c "cat < /dev/null > /dev/tcp/${host}/${port}"; then
      echo -e "${GREEN}${source_name} can successfully communicate with ${target_name} at ${target_url}!${NC}"
    else
      docker-compose down
      echo -e "${RED}ERROR: ${source_name} cannot communicate with ${target_name} at ${target_url}.${NC}"
      exit 1
    fi
  else
    docker-compose down
    echo -e "${RED}ERROR: Unsupported protocol for connectivity check: ${protocol}${NC}"
    exit 1
  fi
}

# Start the Docker Compose services
docker-compose up -d

# Check health of each service
check_service_health "Elasticsearch" "elasticsearch"
check_service_health "Ollama" "ollama"
check_service_health "Postgres" "postgres"
check_service_health "Streamlit" "streamlit"
check_service_health "Grafana" "grafana"

# Check connectivity between services
check_connectivity "Streamlit" "streamlit" "Elasticsearch" "http://${ELASTIC_HOST}:${ELASTIC_PORT:-9200}" "http"
check_connectivity "Streamlit" "streamlit" "Ollama" "http://${OLLAMA_HOST}:${OLLAMA_PORT:-11434}" "http"
check_connectivity "Streamlit" "streamlit" "Postgres" "postgres://${POSTGRES_HOST}:${POSTGRES_PORT:-5432}" "postgres"
check_connectivity "Grafana" "grafana" "Postgres" "postgres://${POSTGRES_HOST}:${POSTGRES_PORT:-5432}" "postgres"


# Optionally stop the containers if keep_containers_running is not true
if [ "$keep_containers_running" != "true" ]; then
  docker-compose down
else
  echo -e "${GREEN}Containers are kept running as requested.${NC}"; echo; echo
fi

echo -e "${GREEN}All services are healthy and can communicate with each other.${NC}"