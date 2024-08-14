<!-- pgcli postgresql://postgres:example@localhost:5432/lex_fridman_podcast -->

### Needed for Chunking
```python -m spacy download en_core_web_sm```

### Needed for reading mp3 files
sudo apt-get update
sudo apt-get install ffmpeg

## Lex Fridman podcast
https://lexfridman.com/podcast
https://huggingface.co/datasets/Whispering-GPT/lex-fridman-podcast-transcript-audio
- Note: metadata tags created manually

## Bucket State
To indicate tracked directories for orchestration to decide if there are new episodes to index.

## Prefect conf
~/.prefect/profiles.toml


## Setup
```
    cd path/to/project
    docker-compose up postgres ollama elasticsearch #grafana
    ./setup.sh reinit_db="true" reindex_es="false" defacto="true" reinit_prefect="false"

    # make sure env variables are exported from .env
    ## if not: > export $(grep -v '^#' .env | xargs)
    prefect worker start --pool "$WORK_POOL_NAME" 
```

## DO NOT FORGET TO
```
kill $(ps aux | grep "prefect server" | grep -v grep | awk '{print $2}')
docker-compose down
```