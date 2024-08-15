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
                         check_for_new_data,
                         update_bucket_state,
                         )
from utils.variables import (PROJECT_DIR, CACHE_DIR,
                             ES_CLIENT, OLLAMA_CLIENT,
                             INDEX_NAME, WORK_POOL_NAME
                             )
from utils.postgres import init_db
from prefect import task, flow
from prefect.deployments import Deployment
from prefect.client.schemas.schedules import CronSchedule


def parse_cli_args():
    """
    """
    parser = argparse.ArgumentParser(description="Reading control parameters.")
    parser.add_argument('--reindex_es', type=str, required=False, help='Value of reindex_es')
    parser.add_argument('--reinit_db', type=str, required=False, help='Value of reinit_db')
    parser.add_argument('--defacto', type=str, required=False, help='Value of defacto')
    parser.add_argument('--reinit_prefect', type=str, required=False, help='Value of reinit_prefect')
    args = parser.parse_args()

    assert args.reindex_es in ["true", "false", None],\
        "'reindex_es' must be either 'true', 'false', or left blank"
    assert args.reinit_db in ["true", "false", None],\
        "'reinit_db' must be either 'true', 'false', or left blank"
    assert args.defacto in ["true", "false", None],\
        "'defacto' must be either 'true', 'false', or left blank"
    assert args.reinit_prefect in ["true", "false", None],\
        "'reinit_prefect' must be either 'true', 'false', or left blank"

    reindex_es = True if args.reindex_es == "true" else False
    reinit_db = True if args.reinit_db == "true" else False
    defacto = False if args.defacto == "false" else True
    reinit_prefect = True if args.reinit_prefect == "true" else False


    return reindex_es, reinit_db, defacto, reinit_prefect


@flow(name="setup_es" ,log_prints=True)
def setup_es(reindex_es=False, defacto=True, new_episodes_dirs=None):
    """Setup ElasticSearch Index.
    """

    ## ============> Initialize ES
    task(init_es, log_prints=True)(reindex_es=reindex_es)
    print_log("============> Initialize ES: Done.")


    ## ============> Loading Podcasts
    dataset = task(load_podcast_data, log_prints=True)(
        new_episodes_dirs=new_episodes_dirs,
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
    is_run_indexing = bool(new_episodes_dirs or reindex_es)
    _ = index_documents_es(
        OLLAMA_CLIENT, ES_CLIENT, INDEX_NAME, documents, is_run_indexing)
    print_log("============> Indexing Documents in ES: Done.")


@flow(name="init_db" ,log_prints=True)
def init_df_flow(reinit_db):
    task(init_db, log_prints=True)(reinit_db)


@flow(name="process_new_episodes" ,log_prints=True)
def process_new_episodes(bucket_dir):

    new_dirs = task(check_for_new_data, log_prints=True)(bucket_dir)
        
    # Process new data if the check_for_new_data task succeeded
    if new_dirs:
        params = {
            "reindex_es": False,
            "defacto": False,
            "new_episodes_dirs": new_dirs,
        }

        # Run the flow with parameters
        setup_es.run(parameters=params)

        task(update_bucket_state, log_prints=True)(bucket_dir, new_dirs)
    else:
        print("Found no new episodes, nothing to do...")


if __name__ == "__main__":
    """
    """
    reindex_es, reinit_db, defacto, reinit_prefect = parse_cli_args()
    
    # Creating deployments for the flows
    if reinit_prefect:
        print_log(
            "Re-deploying prefect flows ...")

        deployment_setup_es = Deployment.build_from_flow(
            flow=setup_es,
            name="ad-hoc",
            work_pool_name=WORK_POOL_NAME,
            parameters={"reindex_es": reindex_es, "defacto": defacto},
        )

        deployment_init_db = Deployment.build_from_flow(
            flow=init_df_flow,
            name="ad-hoc",
            work_pool_name=WORK_POOL_NAME,
            parameters={"reinit_db": reinit_db},
        )

        deployment_process_new_episodes = Deployment.build_from_flow(
            flow=process_new_episodes,
            name="midnight-every-sunday",
            work_pool_name=WORK_POOL_NAME,
            parameters={
                "bucket_dir": os.path.join(PROJECT_DIR, "bucket")
            },
            schedules = [CronSchedule(cron="0 0 * * 0")],
        )

        # Apply the deployments
        deployment_setup_es.apply()
        deployment_init_db.apply()
        deployment_process_new_episodes.apply()
    else:
        print("'reinit_prefect' is set to 'False', no need to redeploy ...")
