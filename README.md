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
    ./setup.shreindex_es="false" defacto="true" reinit_prefect=true"

    # make sure env variables are exported from .env
    ## if not: > export $(grep -v '^#' .env | xargs)
    prefect worker start --pool "$WORK_POOL_NAME" 
```

## ad-hoc
```
    prefect deployment run init_db/ad-hoc -p reinit_db=true
```

## Weekly Pipeline
```
    prefect deployment ls
    prefect deployment run process_new_episodes/midnight-every-sunday #Run once for testing
    ## go to: http://127.0.0.1:4200/flow-runs
```

## DO NOT FORGET TO
```
kill $(ps aux | grep "prefect server" | grep -v grep | awk '{print $2}')
docker-compose down
```