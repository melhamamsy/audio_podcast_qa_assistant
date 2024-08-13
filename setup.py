import os
import argparse
import pickle
from utils.utils import (
    initialize_env_variables,
    conf,
    load_podcast_data,
)
from utils.elasticsearch import (
    create_elasticsearch_client,
    remove_elasticsearch_index,
    search_elasticsearch_indecis,
    load_index_settings,
    create_elasticsearch_index,
    index_document,
    get_index_mapping,
    get_indexed_documents_count,
)
from utils.ollama import (
    create_ollama_client,
    embed_document,
)
from utils.asr import (
    create_whisper_processor_and_model,
    transcripe_and_cache_episodes,
    load_cached_episodes,
)
from utils.postgres import init_db
from utils.multithread import map_progress


# Replace with root project dir
CONF = conf()
PROJECT_DIR = os.getenv(f"PROJECT{CONF}_DIR")
CACHE_DIR = os.path.join(PROJECT_DIR, "hf_cache")
EXPECTED_MAPPING = [
    'id', 'chunk_id', 'channel', 'channel_id', 'title',
    'categories', 'tags', 'text', 'text_vector'
]


def setup_es(reindex_es=False, defacto=True):
    """Setup ElasticSearch Index.
    """
    ## ====> ElasticSearch Client
    es_host = os.environ.get(f'ELASTIC{CONF}_HOST', 'localhost')
    es_port = os.environ.get('ELASTIC_PORT', 9200)
    es_client = create_elasticsearch_client(es_host, es_port)

    ## ====> ElasticSearch Index
    index_name = os.environ.get('ES_INDEX_NAME')
    index_settings_path = os.path.join(
            PROJECT_DIR, 
            "config/elasticsearch/course_qa_id_vecs_index_settings.json"
        )
    index_settings = load_index_settings(index_settings_path)

    ## Check: if index is already created, do not recreate.
    if reindex_es:
        print("Recreating ElasticSearch Index {index_name}...")
        remove_elasticsearch_index(es_client, index_name)

    if index_name not in search_elasticsearch_indecis(es_client):
        create_elasticsearch_index(es_client, index_name, index_settings)
    ## Check: if the mapping is correct, recreate if not.
    elif sorted(
            list(get_index_mapping(es_client, index_name).keys())
        ) != sorted(EXPECTED_MAPPING):
        print(f"Incorrect Mapping of index {index_name}, recreating...")
        remove_elasticsearch_index(es_client, index_name)
        create_elasticsearch_index(es_client, index_name, index_settings)
    else:
        print(f"Index {index_name} is already created.")

    ## ====> Load Documents
    if defacto:
        path = os.path.join(PROJECT_DIR, "data/generated_document_embeddings/embeddings.pkl")
        with open(path, 'rb') as file:
            documents = pickle.load(file)
    else:
        dataset = load_podcast_data(
            name=os.getenv('PODCAST_DATASET'),
            cache_dir=CACHE_DIR,
        )

        ## ASR
        processor, model = create_whisper_processor_and_model(
            asr_model_name=os.getenv("ASR_MODEL", "openai/whisper-small"),
            cache_dir=CACHE_DIR,
        )
        transcripts_cache_dir = os.path.join(
                PROJECT_DIR, "data/generated_transcriptions")
        transcripe_and_cache_episodes(
            model=model,
            processor=processor,
            dataset=dataset,
            transcripts_cache_dir=transcripts_cache_dir,
        )
        dataset = load_cached_episodes(transcripts_cache_dir)
        
        ## CHUNKING

    if get_indexed_documents_count(es_client,index_name)['count'] != len(documents):     
        ## ====> Ollama Client
        ollama_host = os.environ.get(f'OLLAMA{CONF}_HOST', 'localhost')
        ollama_port = os.environ.get('OLLAMA_PORT', 11434)
        ollama_client = create_ollama_client(ollama_host, ollama_port)

        ## ====> Model
        embed_model_name = os.environ.get('EMBED_MODEL')

        print("Documents vectorization: ...")
        vectorized_documents = map_progress(
            f=lambda document: embed_document(
                ollama_client, document, embed_model_name),
            seq=documents,
            max_workers=6,
        )

        ## ====> Indexing...
        print("Documents indexing in es: ...")
        map_progress(
            f=lambda document: index_document(
                es_client, index_name, document, timeout=60),
            seq=vectorized_documents,
            max_workers=6,
        )
    else:
        print(f"Index {index_name} already has {len(documents)} documents")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reading control parameters.")
    parser.add_argument('--reindex_es', type=str, required=True, help='Value of reindex_es')
    parser.add_argument('--reinit_db', type=str, required=True, help='Value of reinit_db')
    parser.add_argument('--defacto', type=str, required=True, help='Value of defacto')
    args = parser.parse_args()

    reindex_es = True if args.reindex_es == "true" else False
    reinit_db = True if args.reinit_db == "true" else False
    defacto = True if args.defacto == "true" else False

    initialize_env_variables(PROJECT_DIR)
    setup_es(reindex_es, defacto)
    init_db(reinit_db)