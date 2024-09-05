# Lex Fridman Podcast QA Assistant

This project is a QA assistant built using retrieval-augmented generation (RAG) on Lex Fridman's podcast episodes.

- [Podcast Playlist on YouTube](https://www.youtube.com/playlist?list=PLrAXtmErZgOdP_8GztsuKi9nrraNbKKp4)
- [Download Episodes](https://lexfridman.com/podcast/)
- [Hugging Face Dataset](https://huggingface.co/datasets/Whispering-GPT/lex-fridman-podcast-transcript-audio)


## Problem Description

The Lex Fridman Podcast features in-depth conversations covering a broad range of topics. With hundreds of hours of content, finding specific information across episodes can be challenging. This project aims to address that by building a question-answering (QA) system using retrieval-augmented generation (RAG).

We begin by using the `openai/whisper-small` ASR model to transcribe podcast episodes into text. The transcriptions are then intelligently chunked while preserving context, ensuring meaningful segments. Next, the chunks are vectorized using `nomic-embed-text` for semantic understanding and stored in Elasticsearch, which serves as the knowledge base for the RAG system.

The RAG system relies on either a self-hosted `gemma:2b` chat model or OpenAI-hosted models like `gpt-4` to generate contextually relevant answers based on user queries. This setup makes it easier to explore and extract insights from the vast content of Lex Fridman's podcast episodes.


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
    sudo apt-get install ffmpeg # For reading mp3 files
    # git config core.hooksPath git-hooks # Change default git-hooks dir
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
    CHAT_MODEL=gemma:2b # Chat model to recieve prompt and give back a response, hosted in ollama
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
    EVAL_MODEL=openai/gpt-4o-mini # llm-as-a-judge model, alternatives: (ollama/gemma:2b, openai/gpt-4o, ...)

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

    - `data/generated_embeddings/vectorized_documents.pkl` (Text+Vectors)
    - `data/generated_documents/documents.json` (Text only)

    You can use these files directly without needing to download the dataset.

    If you still choose to cache the dataset, run the following command:

    ```bash
    make cache_dataset
    ```

10. Prefect Setup (More details will follow regarding its role and how it works).

    a. Update Prefect profiles in `~/.prefect/profiles.toml` with the following command:

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
- `data/generated_embeddings/vectorized_documents.pkl`

The same data without vectorization is stored in:
- `data/generated_documents/documents.json`

To test the pipeline, two additional episodes not included in the dataset were downloaded:
1. [MrBeast: Future of YouTube, Twitter, TikTok, and Instagram | Lex Fridman Podcast #351](https://lexfridman.com/mrbeast)
2. [Sam Altman: OpenAI CEO on GPT-4, ChatGPT, and the Future of AI | Lex Fridman Podcast #367](https://lexfridman.com/sam-altman)

A 1-minute segment was extracted from each episode and saved as `episode-mini.mp3`. 

```> ffmpeg -ss 00:06:55 -i episode.mp3 -t 60 -c copy episode-mini.mp3```

Metadata was also created for each episode, and they were placed in the `bucket/` directory in subdirectories named after the episode number (e.g., `351` or `367`).

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

## Prefect (Orchestration)
This project uses Prefect to orchestrate, deploy, run, and monitor workflows effectively. Prefect serves as a critical component in managing both ad-hoc tasks and scheduled workflows, ensuring seamless execution and observability.

**Key Features:**

`Deployment`: Workflows are deployed and managed locally using Prefect, allowing for streamlined and efficient task execution.

`Execution`: Tasks can be run on-demand (ad-hoc) or scheduled to run at specific times, providing flexibility in operation.

`Monitoring`: Prefect provides real-time monitoring of workflows, making it easier to track progress, handle retries, and manage any failures.

`Process Work Pool`: Given that this project is orchestrated on a local PC, a Process Work Pool is utilized. This allows for executing tasks in separate processes, providing better resource management and isolation on local environments.

By leveraging Prefect's capabilities, the project ensures that workflows are managed with the robustness and reliability needed for complex operations, even within a local setup. Below is a simple diagram that depicts the idea.

![alt text](diagrams/Prefect.png)

Prefect requires a database to store its metadata, for this we will leverage already created postgres instance. This was done already in _Environment Setup and Configuration (10)_.

To start prefect server and a prefect worker:
```
> make prefect_start_server
> make prefect_start_worker # you can start multiple ones by rerunning command, but this is not required.
```

Go to: http://127.0.0.1:4200 to inspect UI (You should see one workpool, but no deployments nor runs yet).

## Workflows

To deploy all flows: 
```
> make redeploy_flows
```
To check deployemnts go to: http://127.0.0.1:4200

### 1. (Re)Set Up Elasticsearch Index (`setup_es`)
This workflow sets up Elasticsearch as the knowledge base for podcast transcriptions. The flow scheduling is `ad-hoc`.

- **(Re)Create ES Index**: If `reindex_es==True`, the index is created with the name `$ES_INDEX_NAME`, as defined in `config/elasticsearch/index_settings.json`.
  
- **Automatic Speech Recognition (ASR)**: We use the `$ASR_MODEL=openai/whisper-small` model to transcribe episodes into text. To prevent truncation, input segments are limited to 0.4 minutes, after which the transcriptions are merged using regex to ensure accuracy. The transcription of a single episode takes approximately 25 minutes. Fortunately, the Hugging Face dataset already contains episode transcripts (`defacto=True`), saving processing time. I verified the accuracy by comparing the transcriptions of two episodes. For new mini-episodes, the ASR process is applied (`defacto=False`).

- **Chunking**: Text is chunked using regex methods along with `en_core_web_sm` from `spacy`, with a maximum chunk length of 2000 characters (subject to optimization). A key consideration is that chunks should not end with questions, as questions are usually followed by their answers in interviews. This ensures that the question and its answer are retrieved together.

- **Embedding Creation**: The `$EMBED_MODEL=nomic-embed-text` model (768 dimensions) is used to create embeddings for each chunk. The model is hosted on Ollama, which avoids the need for the large `sentence-transformers` library and its dependencies in the app container. Although this method is approximately 8x slower than using a GPU, it prevents model output discrepancies. When comparing the Hugging Face and Ollama model outputs, 95% of vectors had a cosine distance of less than 0.001, but 5% showed a significant difference (up to 0.9), which was unacceptable. This experiment is detailed in `notebooks/compare-same-model-hf-vs-ollama.ipynb`. Vectorizing >300k documents with Ollama takes ~4 hours, while the Hugging Face version takes ~0.5 hours.

- **Indexing Documents**: Indexing ~300k documents in Elasticsearch takes approximately 40 minutes.

To run deployment in defacto mode:
```
make reindex_es_defacto
```

### 2. (Re)Initialize Postgres Database (`init_db`)
The Postgres database named `$POSTGRES_DB` is used to store the app's conversations and feedback. Additionally, the same Postgres instance hosts another database called `prefect` for Prefect metadata. The flow scheduling is `ad-hoc`.
To check tables creation:
```
pgcli postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_SETUP_HOST:$POSTGRES_PORT/$POSTGRES_DB
> \l
```

- **Re(Create Database)**: This step ensures that the `$POSTGRES_DB` database is created or recreated if it already exists if `reinit_db==True`.
  
- **Re(Create Tables)**: All necessary tables, including those for conversations and feedback, are created or recreated if `reinit_db==True` within the `$POSTGRES_DB` database. Tables definition are defined in `utils/postgres.py`.

To run deployment:
```
make reinit_db
```

### 3. (Re)Set up Grafana (`setup_grafana`)
Grafana is used to monitor and visualize statistics related to the app, such as user feedback, OpenAI costs, response times, and more. The flow scheduling is `ad-hoc`.

- **Generate Token**: A Grafana admin token is generated if it does not already exist, and the token is added to the `.env` file.

- **(Re)Create Grafana Data Source**: If `reinit_grafana==True`, this step recreates the data source used to connect Grafana to the PostgreSQL database for monitoring purposes.

- **(Re)Create Grafana Dashboard**: If `recreate_dashboards==True`, this step reads chart definitions (stored as JSON files in `config/grafana`) and recreates the Grafana dashboards. Each chart is defined in its own JSON file. To add more charts, simply place the corresponding JSON file in the directory and rerun the dashboard setup process.

To run deployment in non-defacto mode for a single run (doesn't interfere with schedule):
```
make process_new_episodes_run
```


### 4. Check For New Episodes (`process_new_episodes`)
This workflow checks for untracked episodes in `bucket/bucket_state.json`. If new episodes are found, they are indexed, and the bucket state is updated. This flow is scheduled to run every Sunday at midnight.

- **Check for New Unindexed Episodes**: New episodes should be placed in the `bucket` directory as `bucket/[ep-no]`. If a new directory is found that is not tracked in the `bucket/bucket_state.json` file (as described in the data section), it triggers further actions.

- **If New Episodes to Index are Found**: The `setup_es` flow is triggered for the new directories with Defacto Mode off. If no new episodes are found, no further action is taken.

- **Update Bucket State**: If the `setup_es` flow successfully indexes the new episodes, the `bucket_state.json` file is updated to track the newly indexed episodes.

To run deployment in defacto mode:
```
make resetup_grafana
```


## Questions Generation

## Questions Generation

Questions are generated from chunks to evaluate the performance of the retrieval/RAG system. A random sample of 250 chunks (out of >300k) was selected, where each chunk must contain at least 300 words to be considered. OpenAI's `gpt-4o-mini` model is prompted (using `prompts/questions_from_chunks.txt`) to generate self-sufficient questions that could be answered using the content of each chunk.

An alternative method was previously attempted, which involved extracting questions using regex from chunks and then prompting the LLM to select self-sufficient ones and rephrase them. However, this approach yielded poor performance and was subsequently discarded.

The full process of question extraction is documented in `notebooks/openai-generate-questions-from-chunks.ipynb`. The generated questions are stored in `data/generated_questions/questions.json`, and their vectorized versions are stored in `data/generated_embeddings/vectorized_questions.pkl`.

## Retrieval Evaluation

The evaluation of retrieval tests how precise the system is in retrieving documents (chunks) that answer the given questions. As mentioned in the previous section, each question is associated with a specific chunk. We use adjusted versions of Mean Reciprocal Rank (MRR) and Hit Rate (HR) to measure performance. For each question, five documents are retrieved.

- **Hit Rate (HR)**: The percentage of times the correct document is captured within the 5-document result.
  
  Example:
  - `[0, 0, 1, 0, 0] -> 1` 
  - `[0, 0, 0, 0, 0] -> 0` 
  - HR = 1/2

- **Mean Reciprocal Rank (MRR)**: A modified version of MRR, where we divide by the rank of the document.

  Example:
  - `[0, 0, 1, 0, 0] -> 1/3`
  - `[0, 1, 0, 0, 0] -> 1/2`
  - MRR = `(1/3 + 1/2) / 2`

The adjusted versions consider the same chunk as a hit, and the subsequent chunk in the original transcription is counted as a 1/2 hit (this is subject to further enhancement). If both documents are featured in the same 5 results, the HR is set to 1, and for MRR, `max([1 or 1/2]/rank)` is used. For more information, check `utils/evaluate.py`.

| Search Method                  | HR        | MRR       | Adjusted HR | Adjusted MRR |
|---------------------------------|-----------|-----------|-------------|--------------|
| elastic_search_text             | 0.641026  | 0.503775  | 0.643162    | 0.505912     |
| elastic_search_knn              | 0.705128  | 0.586111  | 0.722222    | 0.594017     |
| elastic_search_hybrid_rrf       | 0.786325  | 0.671795  | 0.799145    | 0.680520     |

For medium query size, response time increase from text to rrf is around 0.02 seconds per query, which is negligible.


## Query Re-writing

Query re-writing is used to enhance retrieval by rewriting the query (possibly multiple times) or generating a paragraph that could serve as an answer to the question (HyDE). The same metrics used for retrieval evaluation—Hit Rate (HR) and Mean Reciprocal Rank (MRR)—are applied here.

For more details on query re-writing, check this [Colab Notebook](https://colab.research.google.com/drive/1-NT0_mmyoSnaDQJ1Zuo0XX613TG5lzjZ?usp=sharing#scrollTo=DmcuJ-1DyFTO).

Both HyDE and Sub-queries techniques were tested (in combination with Hybrid RRF), but no improvement was observed over the baseline (Hybrid RRF without query re-writing). The query re-writing technique is costly in terms of both computational expense and response time. As a result, it was decided not to include it in the final RAG system of the app. You can find the details of the experiment in `notebooks/query-rewriting-assessment.ipynb`. Query re-writings are saved in `data/generated_rewriting/vectorized_questions_with_rewriting.pkl`.

| Search Method         | Adjusted HR | Adjusted MRR |
|-----------------------|-------------|--------------|
| baseline              | 0.799145    | 0.680520     |
| zero_shot             | 0.777778    | 0.629274     |
| hyde                  | 0.794872    | 0.636930     |


## RAG Evaluation

This section evaluates the performance of the RAG system as a whole. Since we do not have true answers for the questions, we rely on a Large Language Model (LLM) as a judge to inspect the query, context, and answer to assess relevance. In the future, user feedback within the app will also contribute to the evaluation. Another metric that could be considered later is "Answer Consistency," but this is currently skipped due to its high cost. The LLM prompt used for this evaluation is stored in `prompts/llm_as_a_judge.txt` and is also used in the app for real-time answer evaluation. OpenAI's `gpt-mini-4o` model is used as the judge. You can find the experiment details in `notebooks/assess-retrieval-and-rag.ipynb`.

- **Ollama/phi3**: Evaluated a single question. The answer was too long, took too much time, and was completely nonsensical.
  
- **Ollama/gemma:2b**: Evaluated a single question. The answer was shorter than phi3 and faster, but still nonsensical.
  
- **Ollama/llama3.1**: Evaluated a single question. The answer was shorter than phi3 and faster but worse than gemma:2b, and still nonsensical.
  
- **Ollama/gemma2:2b**: Evaluated a single question. The answer was longer than gemma:2b (making it a costlier evaluation) and still nonsensical.
  
- **OpenAI/gpt-3.5-turbo**: 
  - Results: {'RELEVANT': 219, 'PARTLY_RELEVANT': 10, 'NON_RELEVANT': 5}

- **OpenAI/gpt-4o-mini**: 
  - Results: {'RELEVANT': 229, 'PARTLY_RELEVANT': 5}


## DO NOT FORGET TO
```
> make prefect_kill_workers # Kill all running workers
> make prefect_stop_server # Stop prefect server
> docker-compose down # Stop & Remove all running containers
> #make remove_local_env # In case you want to remove local env and kernel.
```