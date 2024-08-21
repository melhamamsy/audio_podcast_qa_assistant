"""
This module provides various utility functions to support data processing, 
indexing, transcription, and integration with Elasticsearch and Grafana. 
The main functionalities include:
    1. Loading and processing podcast data.
    2. Transcribing episodes and caching results.
    3. Chunking episodes for indexing.
    4. Integrating with Elasticsearch for indexing and search.
    5. Managing Grafana data sources and dashboards.
"""

import gc
import json
import os
import pickle
from pathlib import Path

from datasets import Dataset, load_dataset
from tqdm.auto import tqdm
from transformers import WhisperForConditionalGeneration, WhisperProcessor

from utils.asr import read_mp3, transcripe_episode
from utils.chunking import chunk_large_text, preindex_process_text
from utils.elasticsearch import (
    create_elasticsearch_index,
    get_index_mapping,
    get_indexed_documents_count,
    index_document,
    load_index_settings,
    remove_elasticsearch_index,
    search_elasticsearch_indecis,
)
from utils.grafana import (
    create_dashboard,
    create_grafana_data_source,
    create_grafana_token,
    delete_dashboard,
    delete_grafana_token,
    drop_grafana_data_source,
    get_dashboard_uid_by_name,
    get_grafana_data_source,
    get_grafana_token_ids,
    is_grafana_token_valid,
)
from utils.multithread import map_progress
from utils.ollama import embed_document
from utils.utils import (
    create_or_update_dotenv_var,
    get_json_files_in_dir,
    initialize_env_variables,
    print_log,
    read_json_file,
    save_json_file,
    sleep_seconds,
    standardize_array,
)
from utils.variables import (
    CACHE_DIR,
    ES_CLIENT,
    EXPECTED_MAPPING,
    INDEX_NAME,
    INDEX_SETTINGS_PATH,
    POSTGRES_DB,
    POSTGRES_GRAFANA_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
    PROJECT_DIR,
)


def load_podcast_data(
    new_episodes_dirs=None,
    defacto=True,
):
    """
    Load podcast data either from specified directories or from a dataset.

    Args:
        new_episodes_dirs (list, optional): A list of directories containing new episode data.
        defacto (bool, optional): Whether to enable defacto mode, bypassing data loading.
                                  Defaults to True.

    Returns:
        list or Dataset: The loaded podcast data as a list or Hugging Face Dataset object.
    """
    if defacto:
        print_log("load_podcast_data: Defacto mode is on ...")
        return None

    if new_episodes_dirs:
        dataset = []
        for dir_ in new_episodes_dirs:
            audio, sampling_rate = read_mp3(
                os.path.join(
                    PROJECT_DIR, f"bucket/{dir_}/{os.getenv('NEW_AUDIOS_NAME')}.mp3"
                )
            )
            audio = standardize_array(audio)

            episode = read_json_file(
                os.path.join(PROJECT_DIR, f"bucket/{dir_}/metadata.json")
            )
            episode["audio"] = {
                "array": audio,
                "sampling_rate": sampling_rate,
            }

            dataset.append(episode)
            del audio
            gc.collect()

        return dataset

    return load_dataset(
        path=os.getenv("PODCAST_DATASET"),
        cache_dir=CACHE_DIR,
        ignore_verifications=True,
    )["train"]


def create_whisper_processor_and_model(
    asr_model_name=None, cache_dir=None, defacto=True
):
    """
    Create and return the Whisper processor and model for transcription.

    Args:
        asr_model_name (str, optional): The name of the ASR model to load.
        cache_dir (str, optional): The directory to cache the model files.
        defacto (bool, optional): Whether to enable defacto mode, bypassing model creation.
                                  Defaults to True.

    Returns:
        tuple: A tuple containing the Whisper processor and model instances, or (None, None)
               if defacto mode is enabled.
    """
    if defacto:
        print_log("create_whisper_processor_and_model: Defacto mode is on ...")
        return None, None

    processor = WhisperProcessor.from_pretrained(asr_model_name, cache_dir=cache_dir)
    model = WhisperForConditionalGeneration.from_pretrained(
        asr_model_name, cache_dir=cache_dir
    )
    model.config.forced_decoder_ids = None

    return processor, model


def transcripe_and_cache_episodes(
    model, processor, dataset, transcripts_cache_dir=None, defacto=True
):
    """
    Transcribe and cache podcast episodes.

    Args:
        model: The Whisper model instance for transcription.
        processor: The Whisper processor instance.
        dataset (list or Dataset): The dataset containing episode data.
        transcripts_cache_dir (str, optional): The directory to store cached transcripts.
        defacto (bool, optional): Whether to enable defacto mode, bypassing transcription.
                                  Defaults to True.
    """
    if defacto:
        print_log("transcripe_and_cache_episodes: Defacto mode is on ...")
        return

    cached_episodes = get_json_files_in_dir(transcripts_cache_dir)
    dataset_len = len(dataset)

    for i in tqdm(range(0, dataset_len)):
        episode = dataset[i]
        episode_title = episode["title"].split(" | ")[0]

        if episode_title not in cached_episodes:
            episode["text"] = transcripe_episode(
                episode=episode["audio"],
                processor=processor,
                model=model,
                skip_special_tokens=True,
                minutes=0.4,  ## due to model output constraint
                target_sampling_rate=16_000,
            )

            if i % (max(dataset_len, 20) // 20) == 0:
                print(f"{i}/{dataset_len} items processed so far...")

            ## cache
            if transcripts_cache_dir:
                del episode["audio"]
                path = os.path.join(
                    transcripts_cache_dir,
                    episode_title + ".json",
                )
                save_json_file(episode, path, replace=True)
    print(f"{dataset_len}/{dataset_len} items processed.")


def load_cached_episodes(
    transcripts_cache_dir,
    defacto=True,
):
    """
    Load cached episodes from the specified directory.

    Args:
        transcripts_cache_dir (str): The directory containing cached transcripts.
        defacto (bool, optional): Whether to enable defacto mode, bypassing data loading.
                                  Defaults to True.

    Returns:
        list: A list of loaded episode data.
    """
    if defacto:
        print_log("load_cached_episodes: Defacto mode is on ...")
        return None

    dataset = []
    for path in get_json_files_in_dir(transcripts_cache_dir, return_full_path=True):
        dataset.append(read_json_file(path))

    return dataset


def chunk_episodes(
    dataset,
    chunking_function=chunk_large_text,
    max_chunk_size=2000,
    defacto=True,
):
    """
    Chunk episodes into smaller segments for indexing.

    Args:
        dataset (list or Dataset): The dataset containing episode data.
        chunking_function (function, optional): The function to use for chunking text.
                                                Defaults to chunk_large_text.
        max_chunk_size (int, optional): The maximum size of each chunk in characters.
                                        Defaults to 2000.
        defacto (bool, optional): Whether to enable defacto mode, loading pre-chunked data.
                                  Defaults to True.

    Returns:
        list: A list of chunked documents ready for indexing.
    """
    if defacto:
        print_log("chunk_episodes: Defacto mode is on ...")
        path = os.path.join(
            PROJECT_DIR, "data/generated_document_embeddings/vectorized_documents.pkl"
        )
        with open(path, "rb") as file:
            documents = pickle.load(file)

        return documents

    if isinstance(dataset, list) and all(isinstance(item, dict) for item in dataset):
        dataset = Dataset.from_list(dataset)
    # Check if the object is a Hugging Face Dataset
    elif isinstance(dataset, Dataset):
        pass
    else:
        raise TypeError(
            "Object is neither a list of dictionaries nor a Hugging Face Dataset."
        )

    documents = map_progress(
        f=lambda episode: preindex_process_text(
            episode=episode,
            chunking_function=chunking_function,
            max_chunk_size=max_chunk_size,
        ),
        seq=Dataset.from_list(dataset),
        max_workers=1,
    )
    documents = [item for sublist in documents for item in sublist]

    return documents


def init_es(reindex_es=False):
    """
    Initialize the Elasticsearch index.

    Args:
        reindex_es (bool, optional): Whether to recreate the index if it already exists.
                                     Defaults to False.
    """
    ## ====> ElasticSearch Index settings
    index_settings = load_index_settings(INDEX_SETTINGS_PATH)

    ## Check: if index is already created, do not recreate.
    if reindex_es:
        print(f"Recreating ElasticSearch Index {INDEX_NAME}...")
        remove_elasticsearch_index(ES_CLIENT, INDEX_NAME)

    if INDEX_NAME not in search_elasticsearch_indecis(ES_CLIENT):
        create_elasticsearch_index(ES_CLIENT, INDEX_NAME, index_settings)
    ## Check: if the mapping is correct, recreate if not.
    elif sorted(list(get_index_mapping(ES_CLIENT, INDEX_NAME).keys())) != sorted(
        EXPECTED_MAPPING
    ):
        print(f"Incorrect Mapping of index {INDEX_NAME}, recreating...")
        remove_elasticsearch_index(ES_CLIENT, INDEX_NAME)
        create_elasticsearch_index(ES_CLIENT, INDEX_NAME, index_settings)
    else:
        print(f"Index {INDEX_NAME} is already created.")


def index_documents_es(
    ollama_client, es_client, index_name, documents, is_run_indexing=False
):
    """
    Index documents in Elasticsearch.

    Args:
        ollama_client: The client instance used for embedding documents.
        es_client: The Elasticsearch client instance.
        index_name (str): The name of the index to use.
        documents (list): The list of documents to index.
        is_run_indexing (bool, optional): Whether to perform indexing or not.
                                          Defaults to False.
    """
    pre_indexing_count = get_indexed_documents_count(es_client, index_name)["count"]

    print(f"Index {index_name} previously had {pre_indexing_count} documents.")

    if is_run_indexing:
        ## ====> Model
        embed_model_name = os.environ.get("EMBED_MODEL")

        print("Starting documents vectorization ...")
        if "text_vector" not in documents[0]:
            vectorized_documents = map_progress(
                f=lambda document: embed_document(
                    ollama_client, document, embed_model_name
                ),
                seq=documents,
                max_workers=2,
            )
        else:
            vectorized_documents = documents
        print("Documents vectorization done.")

        ## ====> Indexing...
        print("Starting documents indexing in es ...")
        status = map_progress(
            f=lambda document: index_document(
                es_client, index_name, document, timeout=60
            ),
            seq=vectorized_documents,
            max_workers=2,
        )
        print("Documents indexing done.")

        n_removed_docs = sum(st["removed"] for st in status)
        n_indexed_docs = sum(st["indexed"] for st in status)

        print(f"Documents removed: {n_removed_docs}")
        print(f"Documents indexed: {n_indexed_docs}")
    else:
        print("No document-indexing will take place.")

    print(
        f"""Index {index_name} now has \
{pre_indexing_count - n_removed_docs + n_indexed_docs} documents."""
    )


def check_for_new_data(bucket_dir):
    """
    Check for new directories in the bucket directory.

    Args:
        bucket_dir (str): The directory to check for new data.

    Returns:
        list or None: A list of new directories, or None if no new data is found.
    """
    state_file_path = Path(bucket_dir) / "bucket_state.json"
    new_dirs = []

    # Load existing state if it exists, otherwise initialize an empty state
    if state_file_path.exists():
        with open(state_file_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"tracked_directories": []}

    # List directories in the bucket directory
    directories = [
        d for d in os.listdir(bucket_dir) if os.path.isdir(Path(bucket_dir) / d)
    ]

    # Check if new directories are present by comparing with tracked directories
    new_data = False
    for directory in directories:
        if directory not in state["tracked_directories"]:
            new_data = True
            state["tracked_directories"].append(directory)
            new_dirs.append(directory)
            print(f"New directory found: {directory}")

    if new_data:
        return new_dirs

    print("No new directories found.")
    return None


def update_bucket_state(bucket_dir, new_dirs=None):
    """
    Update the bucket state with newly indexed directories.

    Args:
        bucket_dir (str): The directory containing the bucket state.
        new_dirs (list, optional): A list of new directories to add to the state.
    """
    if not new_dirs:
        new_dirs = []

    state_file_path = Path(bucket_dir) / "bucket_state.json"

    if state_file_path.exists():
        with open(state_file_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    else:
        state = {"tracked_directories": []}

    state["tracked_directories"] += new_dirs
    with open(state_file_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)

    print("Updated Bucket state for newly indexed documents.")


def set_grafana_token(reset_token=False):
    """
    Set the Grafana API token, generating a new one if needed.

    Args:
        reset_token (bool, optional): Whether to reset the token if it already exists.
                                      Defaults to False.
    """
    if (
        not os.getenv("GRAFANA_ADMIN_TOKEN")
        or reset_token
        or not is_grafana_token_valid()
    ):
        for token_id in get_grafana_token_ids():
            delete_grafana_token(token_id)
        token = create_grafana_token()
        if token:
            create_or_update_dotenv_var("GRAFANA_ADMIN_TOKEN", token)
            initialize_env_variables()
        print("Token overwriten.")
    else:
        print(
            "Token already exists, if you want to overwrite it, pass 'reset_token=True'."
        )


def reinit_grafana_datasource(datasource_name, reinit_grafana=False):
    """
    Reinitialize the Grafana data source if needed.

    Args:
        datasource_name (str): The name of the Grafana data source.
        reinit_grafana (bool, optional): Whether to reinitialize the data source if it exists.
                                         Defaults to False.
    """
    # Grafana datasource configuration
    datasource_info = {
        "name": datasource_name,
        "type": "grafana-postgresql-datasource",
        "url": f"{POSTGRES_GRAFANA_HOST}:{POSTGRES_PORT}",
        "access": "proxy",
        "user": POSTGRES_USER,
        "secureJsonData": {"password": POSTGRES_PASSWORD},
        "jsonData": {
            "database": POSTGRES_DB,
            "postgresVersion": 903,
            "sslmode": "disable",
        },
    }

    if not get_grafana_data_source(datasource_name):
        print(f"Datasource {datasource_name} doesn't exist, recreating")
        create_grafana_data_source(datasource_info)

        print("Waiting for some seconds till DS connection is ready...")
        sleep_seconds(20)
    elif reinit_grafana:
        print(f"Datasource {datasource_name} exists, recreating...")
        drop_grafana_data_source(datasource_name)
        create_grafana_data_source(datasource_info)

        print("Waiting for some seconds till DS connection is ready...")
        sleep_seconds(20)
    else:
        print(
            f"Datasource {datasource_name} exists, and no recreation is requested, nothing to do..."
        )


def recreate_grafana_dashboard(
    dashboard_name, datasource_name, json_file_path=None, recreate_dashboards=False
):
    """
    Recreate a Grafana dashboard if needed.

    Args:
        dashboard_name (str): The name of the Grafana dashboard.
        datasource_name (str): The name of the data source associated with the dashboard.
        json_file_path (str, optional): The path to the JSON file
            containing the dashboard configuration. Defaults to None.
        recreate_dashboards (bool, optional): Whether to recreate the dashboard if it exists.
                                              Defaults to False.
    """
    datasource_uid = get_grafana_data_source(datasource_name)["uid"]

    # Reading dashboard
    if not json_file_path:
        json_file_path = os.path.join(
            os.getenv("PROJECT_SETUP_DIR"),
            "config/grafana/lex_fridman_bot_dashboard.json",
        )

    with open(json_file_path, "r", encoding="utf-8") as json_file:
        dashboard = json.load(json_file)
        for panel in dashboard["dashboard"]["panels"]:
            panel["datasource"]["uid"] = datasource_uid
            for target in panel["targets"]:
                target["datasource"]["uid"] = datasource_uid
        dashboard["dashboard"]["title"] = dashboard_name

    with open(json_file_path, "w", encoding="utf-8") as json_file:
        json.dump(dashboard, json_file, indent=4)

    ## Delete dashboard if exists
    dashboard_uid = get_dashboard_uid_by_name(dashboard_name)

    if not dashboard_uid:
        print(f"Dashboard {dashboard_name} doesn't exist, recreating")
        create_dashboard(dashboard)
    elif recreate_dashboards:
        print(f"Dashboard {dashboard_name} exists, recreating...")
        delete_dashboard(dashboard_uid)
        create_dashboard(dashboard)
    else:
        print(
            f"Dashboard {dashboard_name} exists, and no recreation is requested, nothing to do..."
        )
