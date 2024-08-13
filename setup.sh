#!/bin/bash


# Default params values
reindex_es="false"
reinit_db="false"

# Modify with your preferred models
CHAT_MODEL=phi3
EMBED_MODEL=locusai/multi-qa-minilm-l6-cos-v1


# Function to echo a new line before and after a message
echoo() {
  echo ""
  echo "$1"
  echo ""
}


# cd to file directory
cd "$(dirname "$0")"


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
        *)
        echo "Invalid parameter: $param, you can only use reinit_db and/or reindex_es or leave plank."
        exit 1
        ;;
    esac
done


# # Instead of scripting docker-compose up (as you may need to download the images)
# # docker-compose up on a terminal and wait till the services are up and running
# # you can use `docker ps` to verify. Afterwards ./setup.sh
# # Bring up Docker Compose
# docker-compose up -d
# # Wait for the containers to be fully up and running
# # Adjust the sleep duration if necessary
# sleep 30

# Execute commands inside the ollama container
echo "Checking olama models..."
docker-compose exec -e CHAT_MODEL="$CHAT_MODEL" -e EMBED_MODEL="$EMBED_MODEL" ollama bash -c '
  # Check if jq is installed, if not install it
  if ! command -v jq &> /dev/null
  then
      echo "jq could not be found, installing..."
      apt-get update > /dev/null && apt-get install -y jq > /dev/null
  else
      echo "jq is already installed."
  fi

  echoo() {
    echo ""
    echo "$1"
    echo ""
  }

  # Paths to the manifests and blobs directories
  MANIFESTS_DIR="$HOME/.ollama/models/manifests/registry.ollama.ai"
  BLOBS_DIR="$HOME/.ollama/models/blobs"

  manifest_paths=(
    "$MANIFESTS_DIR/library/$CHAT_MODEL/latest"
    "$MANIFESTS_DIR/$EMBED_MODEL/latest"
  )

  # Function to check if a file exists
  check_file_exists() {
      if [ ! -f "$1" ]; then
          echo "Manifest file $1 does not exist."
          return 1
      fi
      return 0
  }

  # Function to check if a blob exists
  check_blob_exists() {
        if [ ! -f "$BLOBS_DIR/$1" ]; then
            echo "Blob $1 not found."
            return 1
        fi
        return 0
  }

  # Function to check if a string is a substring of another string
  is_substring() {
        if [[ "$2" == *"$1"* ]]; then
            return 0  # True
        else
            return 1  # False
        fi
  }

  # Iterate over all manifests
  for manifest_path in "${manifest_paths[@]}"; do
      echo "Checking manifest: $manifest_path"

      # Check if the manifest file exists
      if check_file_exists "$manifest_path"; then
          # Read the manifest file and extract digests
          digests=$(jq -r ".config.digest, .layers[].digest" "$manifest_path")

          # Check each digest
          for digest in $digests; do
              # Extract the actual digest value (remove "sha256:")
              actual_digest=$(echo $digest | cut -d: -f2)
              
              # Check if the corresponding blob exists
              if ! check_blob_exists "sha256-$actual_digest"; then
                  echo "Required blob for digest $digest is missing."
                  echo "Redownloading Model for $manifest_path..."
                  break
              fi
          done

          echo Model Is ALready Pulled...
      else
        echo Model Is Not Pulled Or Missing Digests...
        if is_substring "$EMBED_MODEL" "$manifest_path"; then
            echoo "Pulling ${EMBED_MODEL}..."
            ollama pull ${EMBED_MODEL}
        fi 
        if is_substring "$CHAT_MODEL" "$manifest_path"; then
            echoo "Pulling ${CHAT_MODEL}..."
            ollama pull ${CHAT_MODEL}
        fi 
      fi
  done
'

# Activate the conda environment and run setup.py
source activate dtc-llm-env
echoo "Setting up postgres & es..."
python setup.py --reindex_es "$reindex_es" --reinit_db "$reinit_db"