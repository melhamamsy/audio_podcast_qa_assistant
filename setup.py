import os
import argparse
from utils.utils import print_log
from utils.tasks import (load_podcast_data,
                         create_whisper_processor_and_model,
                         transcripe_and_cache_episodes,
                         load_cached_episodes,
                         chunk_episodes,
                         init_es,
                         index_documents_es,
                         )
from utils.variables import (PROJECT_DIR, CACHE_DIR,
                             ES_CLIENT, OLLAMA_CLIENT,
                             INDEX_NAME
                             )
from utils.postgres import init_db
from prefect import task, flow


def parse_cli_args():
    """
    """
    parser = argparse.ArgumentParser(description="Reading control parameters.")
    parser.add_argument('--reindex_es', type=str, required=False, help='Value of reindex_es')
    parser.add_argument('--reinit_db', type=str, required=False, help='Value of reinit_db')
    parser.add_argument('--defacto', type=str, required=False, help='Value of defacto')
    args = parser.parse_args()

    assert args.reindex_es in ["true", "false", None],\
        "'reindex_es' must be either 'true', 'false', or left blank"
    assert args.reinit_db in ["true", "false", None],\
        "'reinit_db' must be either 'true', 'false', or left blank"
    assert args.defacto in ["true", "false", None],\
        "'defacto' must be either 'true', 'false', or left blank"

    reindex_es = True if args.reindex_es == "true" else False
    reinit_db = True if args.reinit_db == "true" else False
    defacto = False if args.defacto == "false" else True


    return reindex_es, reinit_db, defacto

@flow(log_prints=True)
def setup_es(reindex_es=False, defacto=True):
    """Setup ElasticSearch Index.
    """

    ## ============> Initialize ES
    task(init_es, log_prints=True)(reindex_es=reindex_es)
    print_log("============> Initialize ES: Done.")


    ## ============> Loading Podcasts
    dataset = task(load_podcast_data, log_prints=True)(
        name=os.getenv('PODCAST_DATASET'),
        cache_dir=CACHE_DIR,
        defacto=defacto,
        )
    print_log("============> Loading Podcasts: Done.")
    

    ## ============> Performing ASR
    processor, model = task(create_whisper_processor_and_model, log_prints=True)(
        asr_model_name=os.getenv("ASR_MODEL", "openai/whisper-small"),
        cache_dir=CACHE_DIR,
        defacto=defacto,
        )
    print_log("============> Whisper Model & Processor Creation: Done.")
    
    transcripts_cache_dir = os.path.join(PROJECT_DIR,
                                         "data/generated_transcriptions")
    _ = task(transcripe_and_cache_episodes, log_prints=True)(
        model=model,
        processor=processor,
        dataset=dataset,
        transcripts_cache_dir=transcripts_cache_dir,
        defacto=defacto,
        )
    print_log("============> Performing ASR: Done.")
    

    ## ============> CHUNKING
    dataset = task(load_cached_episodes, log_prints=True)(
        transcripts_cache_dir=transcripts_cache_dir,
        defacto=defacto,
        )
    print_log("============> Loading Transcriped Documents: Done.")

    documents = task(chunk_episodes, log_prints=True)(
        dataset=dataset,
        defacto=defacto,
        )
    print_log("============> Loading Chunking Documents: Done.")


    ## > Indexing documents in ES
    _ = index_documents_es(OLLAMA_CLIENT, ES_CLIENT, INDEX_NAME, documents)
    print_log("============> Indexing Documents in ES: Done.")


if __name__ == "__main__":
    reindex_es, reinit_db, defacto = parse_cli_args()
    
    setup_es(reindex_es, defacto)

    flow(init_db, log_prints=True)(reinit_db)