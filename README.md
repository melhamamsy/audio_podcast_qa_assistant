<!-- pgcli postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_SETUP_HOST:$POSTGRES_PORT/$POSTGRES_DB -->

<!-- go to: http://127.0.0.1:4200/flow-runs -->


# Lex Fridman Podcast QA Assistant

This project is a QA assistant built using retrieval-augmented generation (RAG) on Lex Fridman's podcast episodes.

- [Podcast Playlist on YouTube](https://www.youtube.com/playlist?list=PLrAXtmErZgOdP_8GztsuKi9nrraNbKKp4)
- [Download Episodes](https://lexfridman.com/podcast/)
- [Hugging Face Dataset](https://huggingface.co/datasets/Whispering-GPT/lex-fridman-podcast-transcript-audio)


## Problem Description

The Lex Fridman Podcast features in-depth conversations covering a broad range of topics. With hundreds of hours of content, finding specific information across episodes can be challenging. This project aims to address that by building a question-answering (QA) system using retrieval-augmented generation (RAG).

We begin by using the `openai/whisper-small` ASR model to transcribe podcast episodes into text. The transcriptions are then intelligently chunked while preserving context, ensuring meaningful segments. Next, the chunks are vectorized using `nomic-embed-text` for semantic understanding and stored in Elasticsearch, which serves as the knowledge base for the RAG system.

The RAG system relies on either a self-hosted `phi3` chat model or OpenAI-hosted models like `gpt-4` to generate contextually relevant answers based on user queries. This setup makes it easier to explore and extract insights from the vast content of Lex Fridman's podcast episodes.


## System Requirements

This project was developed and tested in a local environment. Below are the key system specifications and operating system details:

- **Operating System**: Linux Ubuntu 6.8.0-40-generic
- **CPU**: Intel(R) Core(TM) i7-9750H CPU @ 2.60GHz (12 CPUs)
- **RAM**: 15 GiB
- **GPU**: NVIDIA GeForce GTX 1660 Ti Mobile

The project was tested under the above requirements. If tested for Windows, a separate branch will be linked here.


## Environment Setup and Configuration

Before getting started, ensure that the following dependencies are met:

1. **Conda** must be installed on your system. You can follow the official [Conda installation guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) if you don't have it set up yet.

2. Additionally, you’ll need the following packages installed:

    ```bash
    sudo apt-get update
    sudo apt-get install build-essential
    sudo apt-get install ffmpeg # Needed for reading mp3 files
    ```

3. Create a directory named `hf_cache/` in the project root:

    ```bash
    mkdir hf_cache/
    ```

    This directory will be used as the caching directory for Hugging Face models and datasets.

4. Create a `.env` file in the project root with the following content. Be sure to update the `PROJECT_SETUP_DIR`, `OPENAI_API_KEY`, and `HF_READING_TOKEN` values. You can also optionally change other configurations such as names, users, passwords, etc. Leave the `GRAFANA_ADMIN_TOKEN` variable empty since it will be auto-generated later and populated in the `.env` file:

    ```dotenv
    # Setup
    IS_SETUP=true # Use {SERVICE}_SETUP_HOST or {SERVICE}_HOST depending on running context, DO NOT CHANGE
    ENV_NAME=dtc-llm-env # Name of local conda environment to be created
    PYTHON_VERSION=3.11.5 # Python version of the conda environment

    # PostgreSQL Configuration
    POSTGRES_SETUP_HOST=localhost # Host of postgres with respect to local env
    POSTGRES_HOST=postgres # Host of postgres with respect to streamlit & grafana
    POSTGRES_DB=lex_fridman_podcast # Name of database used as backend to streamlit app
    POSTGRES_USER=postgres
    POSTGRES_PASSWORD=example
    POSTGRES_PORT=5432

    # Elasticsearch Configuration
    ELASTIC_SETUP_HOST=localhost # Host of elasticsearch with respect to local env
    ELASTIC_HOST=elasticsearch # Host of elasticsearch with respect to streamlit
    ELASTIC_PORT=9200
    ES_INDEX_NAME=lex-fridman-podcast # Name of the elasticsearch index to create

    # Ollama Configuration
    OLLAMA_SETUP_HOST=localhost # Host of ollama with respect to local env
    OLLAMA_HOST=ollama # Host of ollama with respect to streamlit
    OLLAMA_PORT=11434
    CHAT_MODEL=phi3 # Chat model to recieve prompt and give back a response, hosted in ollama
    EMBED_MODEL=nomic-embed-text # Sentence-embedding model, hosted in ollama (768 dims)

    # Streamlit Configuration
    STREAMLIT_PORT=8501

    # OpenAI API Key
    OPENAI_API_KEY= # your_openai_key, e.g., sk-proj-[48 characters]

    # Grafana
    GRAFANA_SETUP_HOST=localhost # Host of grafana with respect to local env
    GRAFANA_PORT=3000
    GRAFANA_ADMIN_USER=admin
    GRAFANA_ADMIN_PASSWORD=admin
    GRAFANA_DS_NAME=lex_fridman_podcast_pg_grafana # Name of the datasource linked to PG database in grafana
    GRAFANA_DASHBOARD_NAME=lex_fridman_podcast_monitoring
    GRAFANA_ADMIN_TOKEN=

    # Project Directory Info
    PROJECT_DIR=/app # DO NOT CHANGE (unless changed WORKDIR in Dockerfile.streamlit)
    PROJECT_SETUP_DIR= # /absolute/local/path/to/audio_podcast_qa_assistant
    NEW_AUDIOS_NAME=episode-mini # bucket/[ep-no]/{NEW_AUDIOS_NAME}.mp3

    # Evaluation Model
    EVAL_MODEL=openai/gpt-4o-mini # llm-as-a-judge model, alternatives: (ollama/phi3, openai/gpt-4o, ...)

    # Huggingface
    HF_READING_TOKEN= # your_hf_token, e.g., hf_[34 characters]
    PODCAST_DATASET=Whispering-GPT/lex-fridman-podcast-transcript-audio # Dataset name in HF
    ASR_MODEL=openai/whisper-small # Model Used to perform ASR, sampling_rate:16_000, ~0.4 Min/Input (Heuristic)

    # Prefect
    WORK_POOL_NAME=podcast-process-pool # Name of prefect process workpool
    ```

5. Create the local environment using `requirements.txt` (for necessary functionalities) and `requirements-dev.txt` (for linting, testing, formatting, etc.):

    Run the following command:

    ```bash
    make create_local_env
    ```

    This command sets up the conda environment, installs all necessary dependencies, and prepares your development environment.

    Additionally, it creates a Jupyter kernel with the same name as the environment, allowing you to easily experiment in a Jupyter notebook if needed.

6. Run integration tests, which start all containers, check for health using commands specified in the `healthcheck` section of `docker-compose.yml`, verify container connectivity, and keep containers running by passing `keep-containers-running=true`. Running these tests is also beneficial as it downloads all necessary layers not available locally and creates local images using `Dockerfile.[service-name]`. The images are recreated to include the `curl` command, which is essential for health and connectivity checks:

    Run the following command:

    ```bash
    make integration_tests keep-containers-running=true
    ```


7. Set up `Ollama` (used to host models without the need for a GPU) by downloading the `$EMBED_MODEL` and `$CHAT_MODEL` specified in the `.env` file you just created. The script checks if the models are missing or if there are any issues with the SHA layers, and if so, it downloads them:

    Run the following command:

    ```bash
    make setup_ollama
    ```

8. Cache the Automatic Speech Recognition (ASR) model specified in `$ASR_MODEL` in the `.env` file, used to transcribe episode audio. The model is cached in the `./hf_cache` directory created earlier. If the directory doesn’t exist, it gets created here. If the model is partially loaded, Hugging Face will resume from where it stopped. If the model is already cached, it won’t be redownloaded:

    Run the following command:

    ```bash
    make cache_asr_model
    ```

9. Cache the Hugging Face podcast dataset to `hf_cache`. <span style="color:orange;">**Warning:**</span> This process is very costly in terms of time and resources, and you may need to spread the download over a few days due to potential download limits. However, this step can be skipped altogether since Defacto Mode is enabled by default. I have already gone through the process and stored the transcribed, chunked, and vectorized data:

    - `data/generated_document_embeddings/vectorized_documents.pkl` (Text+Vectors)
    - `data/generated_documents/documents.json` (Text only)

    You can use these files directly without needing to download the dataset.

    If you still choose to cache the dataset, run the following command:

    ```bash
    make cache_dataset
    ```

10. Prefect Setup (More details will follow regarding its role and how it works).

    a. Update Prefect profiles in `~/.prefect/profiles.toml` with the following configuration:

    ```bash
    echo 'active = "local-server"

    [profiles.default]
    PREFECT_API_URL = "http://localhost:4200/api"

    [profiles.local-server]
    PREFECT_API_URL = "http://localhost:4200/api"
    PREFECT_API_DATABASE_CONNECTION_URL = "postgresql+asyncpg://postgres:example@localhost:5432/prefect"' >  ~/.prefect/profiles.toml
    ```

    **Note:** This assumes that the PostgreSQL user is `postgres`, the password is `example`, the host is `localhost`, and the port is `5432`.

    b. Initialize (or reinitialize) Prefect by creating or recreating the Prefect database in the same PostgreSQL instance that hosts the app database. Use the `local-server` profile specified in step (a) and recreate a process work-pool (details will be explained later):

    Run the following command:

    ```bash
    make reinit_prefect
    ```


These pre-requisites ensure that your environment is set up correctly before running the project.


## Data

The dataset is available as a [Hugging Face dataset](https://huggingface.co/datasets/Whispering-GPT/lex-fridman-podcast-transcript-audio) containing 351 episodes along with their transcripts. This is a significant advantage because it allows us to skip the time-consuming process of transcribing all the episodes. For example, transcribing a single episode on my local machine takes around 30 minutes. 

However, if needed, we can still [download the episodes](https://lexfridman.com/podcast/) individually and transcribe them manually. I call this process of skipping heavy processing **Defacto Mode**, which is applied in the code. You can disable this mode by setting `defacto=False` during the setup process (details covered later).

The transcribed, chunked, and vectorized data is stored in:
- `data/generated_document_embeddings/vectorized_documents.pkl`

The same data without vectorization is stored in:
- `data/generated_documents/documents.json`

To test the pipeline, two additional episodes not included in the dataset were downloaded:
1. [MrBeast: Future of YouTube, Twitter, TikTok, and Instagram | Lex Fridman Podcast #351](https://lexfridman.com/mrbeast)
2. [Sam Altman: OpenAI CEO on GPT-4, ChatGPT, and the Future of AI | Lex Fridman Podcast #367](https://lexfridman.com/sam-altman)

A 1-minute segment was extracted from each episode and saved as `episode-mini.mp3`. Metadata was also created for each episode, and they were placed in the `bucket/` directory in subdirectories named after the episode number (e.g., `351` or `367`).

For these episodes, you can run the setup pipeline with Defacto Mode off, which takes around 5 minutes for the two mini episodes. The resulting transcripts are saved in `data/generated_transcriptions/` as JSON files with metadata (e.g., `MrBeast: Future of YouTube, Twitter, TikTok, and Instagram.json`) to prevent reprocessing if the pipeline fails before indexing.

Regarding the `bucket/` directory, a `bucket_state.json` file tracks new episodes:

```json
{
    "tracked_directories": []
}
```
When a new directory is added to the bucket (e.g., 351) and the setup pipeline is run, the directory is tracked in bucket_state.json like this:
```json
{
    "tracked_directories": ["351"]
}
```
To avoid reindexing, if you manually remove a directory from tracked_directories, the pipeline will re-run, delete the indexed documents for that episode, and index the new documents (essentially updating the data).


## DO NOT FORGET TO
```
docker-compose down
```

## Formatting
```
pylint $(find . -name "*.py")
git config core.hooksPath git-hooks
```

## episode-mini.mp3
```ffmpeg -ss 00:01:30 -i input.mp3 -t 60 -c copy output.mp3```
