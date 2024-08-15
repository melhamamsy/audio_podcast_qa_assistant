"""
"""

import os
import gc
import json
from pathlib import Path
import pickle
from tqdm.auto import tqdm
from utils.utils import (print_log, get_json_files_in_dir,
                         read_json_file, save_json_file,
                         standardize_array,
                         )
from utils.chunking import (chunk_large_text,
                            preindex_process_text)
from utils.elasticsearch import (index_document,
                                 get_indexed_documents_count)
from utils.elasticsearch import (remove_elasticsearch_index,
                                 search_elasticsearch_indecis,
                                 load_index_settings,
                                 create_elasticsearch_index,
                                 index_document,
                                 get_index_mapping,
                                 get_indexed_documents_count)
from utils.ollama import embed_document
from utils.asr import transcripe_episode
from utils.asr import read_mp3
from datasets import load_dataset, Dataset
from utils.multithread import map_progress
from transformers import (WhisperProcessor,
                          WhisperForConditionalGeneration)
from utils.variables import (PROJECT_DIR, ES_CLIENT,
                             INDEX_NAME, INDEX_SETTINGS_PATH,
                             EXPECTED_MAPPING, CACHE_DIR,
                             )


def load_podcast_data(new_episodes_dirs=None,
                      defacto=True,
                      ):
    """
    """
    if defacto:
        print_log("load_podcast_data: Defacto mode is on ...")
        return None

    if new_episodes_dirs:
        dataset = []
        for dir in new_episodes_dirs:
            audio, sampling_rate = read_mp3(
                os.path.join(PROJECT_DIR, f"bucket/{dir}/episode.mp3")
            )
            audio = standardize_array(audio)
            # [:4_800_000] #10 seconds for testing

            episode = read_json_file(
                os.path.join(PROJECT_DIR, f"bucket/{dir}/metadata.json")
            )
            episode['audio'] = {
                'array':audio,
                'sampling_rate':sampling_rate,
            }

            dataset.append(episode)
            del audio; gc.collect()

        return dataset
    else:
        return load_dataset(
            name=os.getenv('PODCAST_DATASET'), 
            cache_dir=CACHE_DIR,
            ignore_verifications=True
        )['train']


def create_whisper_processor_and_model(asr_model_name=None,
                                       cache_dir=None,
                                       defacto=True
                                       ):
    """
    """
    if defacto:
        print_log("create_whisper_processor_and_model: Defacto mode is on ...")
        return None, None
    
    processor = WhisperProcessor.from_pretrained(
        asr_model_name, cache_dir=cache_dir)
    model = WhisperForConditionalGeneration.from_pretrained(
        asr_model_name, cache_dir=cache_dir)
    model.config.forced_decoder_ids = None

    return processor, model


def transcripe_and_cache_episodes(model,
                                  processor,
                                  dataset,
                                  transcripts_cache_dir=None,
                                  defacto=True
                                  ):
    """
    """
    if defacto:
        print_log("transcripe_and_cache_episodes: Defacto mode is on ...")
        return

    cached_episodes = get_json_files_in_dir(transcripts_cache_dir)

    for i in tqdm(range(0, len(dataset))):
        episode = dataset[i]
        episode_title = episode['title'].split(" | ")[0]

        if episode_title not in cached_episodes:
            episode['text'] = transcripe_episode(
                episode=episode['audio'],
                processor=processor,
                model=model,
                skip_special_tokens=True,
                minutes=0.4, ## due to model output constraint
                target_sampling_rate=16_000,
            )
            
            ## cache
            if transcripts_cache_dir:
                del episode['audio']
                path = os.path.join(
                    transcripts_cache_dir,
                    episode_title + ".json",
                )
                save_json_file(episode, path, replace=True)


def load_cached_episodes(transcripts_cache_dir,
                         defacto=True,
                         ):
    """
    """
    if defacto:
        print_log("load_cached_episodes: Defacto mode is on ...")
        return

    dataset = []
    for path in get_json_files_in_dir(transcripts_cache_dir, return_full_path=True):   
        dataset.append(read_json_file(path))
        
    return dataset


def chunk_episodes(dataset, 
                   chunking_function=chunk_large_text,
                   max_chunk_size=2000,
                   defacto=True,
                   ):
    """
    """
    if defacto:
        print_log("chunk_episodes: Defacto mode is on ...")
        path = os.path.join(PROJECT_DIR,
                            "data/generated_document_embeddings/embeddings.pkl")
        with open(path, 'rb') as file:
            documents = pickle.load(file)

        return documents

    if isinstance(dataset, list) and all(isinstance(item, dict) for item in dataset):
        dataset = Dataset.from_list(dataset)
    # Check if the object is a Hugging Face Dataset
    elif isinstance(dataset, Dataset):
        pass
    else:
        raise TypeError("Object is neither a list of dictionaries nor a Hugging Face Dataset.")

    documents = map_progress(
        f=lambda episode:preindex_process_text(
            episode=episode, 
            chunking_function=chunking_function,
            max_chunk_size=max_chunk_size,
        ),
        seq=Dataset.from_list(dataset),
        max_workers=1
    )
    documents = [item for sublist in documents for item in sublist]

    return documents


def init_es(reindex_es=False):
    """
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
    elif sorted(
            list(get_index_mapping(ES_CLIENT, INDEX_NAME).keys())
        ) != sorted(EXPECTED_MAPPING):
        print(f"Incorrect Mapping of index {INDEX_NAME}, recreating...")
        remove_elasticsearch_index(ES_CLIENT, INDEX_NAME)
        create_elasticsearch_index(ES_CLIENT, INDEX_NAME, index_settings)
    else:
        print(f"Index {INDEX_NAME} is already created.")


def index_documents_es(ollama_client, es_client, index_name, documents, is_run_indexing=False):
    """
    """
    indexed_docs_count = get_indexed_documents_count(es_client, index_name)['count']
    if is_run_indexing:     
        ## ====> Model
        embed_model_name = os.environ.get('EMBED_MODEL')

        print("Documents vectorization: ...")
        vectorized_documents = map_progress(
            f=lambda document: embed_document(
                ollama_client, document, embed_model_name),
            seq=documents,
            max_workers=1,
        )

        ## ====> Indexing...
        print("Documents indexing in es: ...")
        map_progress(
            f=lambda document: index_document(
                es_client, index_name, document, timeout=60),
            seq=vectorized_documents,
            max_workers=1,
        )

        print(f"""Successfully indexed {
              get_indexed_documents_count(es_client, index_name)['count'] - indexed_docs_count
        }""")
    else:
        print("No document-indexing will take place.")

    print(f"Index {index_name} has {indexed_docs_count} documents")


def check_for_new_data(bucket_dir):
    """
    """
    state_file_path = Path(bucket_dir) / "bucket_state.json"
    new_dirs = []
    
    # Load existing state if it exists, otherwise initialize an empty state
    if state_file_path.exists():
        with open(state_file_path, 'r') as f:
            state = json.load(f)
    else:
        state = {"tracked_directories": []}
    
    # List directories in the bucket directory
    directories = [d for d in os.listdir(bucket_dir) if os.path.isdir(Path(bucket_dir) / d)]
    
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
    else:
        print("No new directories found.")
        return None


def update_bucket_state(bucket_dir, new_dirs=[]):
    """
    """
    state_file_path = Path(bucket_dir) / "bucket_state.json"
        
    if state_file_path.exists():
        with open(state_file_path, 'r') as f:
            state = json.load(f)
    else:
        state = {"tracked_directories": []}

    state["tracked_directories"] += new_dirs
    with open(state_file_path, 'w') as f:
        json.dump(state, f, indent=4)

    print("Updated Bucket state for newly indexed documents.")