#!/bin/bash


# cd to file directory
cd "$(dirname "$0")/.."

# Initialize env variables
export $(grep -v '^#' .env | xargs)


# Execute commands inside the ollama container
echo "Checking olama models..."
docker-compose exec -e CHAT_MODEL="$CHAT_MODEL" -e EMBED_MODEL="$EMBED_MODEL" ollama bash -c '

  GREEN="\033[0;32m"
  NC="\033[0m"

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

  # Determine the correct manifest paths based on the format of CHAT_MODEL and EMBED_MODEL
  if [[ "$CHAT_MODEL" == */* ]]; then
    chat_model_path="$MANIFESTS_DIR/$CHAT_MODEL/latest"
  else
    chat_model_path="$MANIFESTS_DIR/library/$CHAT_MODEL/latest"
  fi

  if [[ "$EMBED_MODEL" == */* ]]; then
    embed_model_path="$MANIFESTS_DIR/$EMBED_MODEL/latest"
  else
    embed_model_path="$MANIFESTS_DIR/library/$EMBED_MODEL/latest"
  fi

  manifest_paths=(
    "$chat_model_path"
    "$embed_model_path"
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

          echo -e "${GREEN}Model Is ALready Pulled...${NC}"
      else
        echo Model Is Not Pulled Or Missing Digests...
        if is_substring "$EMBED_MODEL" "$manifest_path"; then
            echoo "Pulling ${EMBED_MODEL}..."
            ollama pull ${EMBED_MODEL}
            echo -e "${GREEN}Done.${NC}"
        fi 
        if is_substring "$CHAT_MODEL" "$manifest_path"; then
            echoo "Pulling ${CHAT_MODEL}..."
            ollama pull ${CHAT_MODEL}
            echo -e "${GREEN}Done.${NC}"
        fi 
      fi
  done
'
