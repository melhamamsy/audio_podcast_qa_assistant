"""
This module contains setup functions for initializing and configuring various
components of the project, including ElasticSearch, database, Grafana, and
Prefect flows.
"""

import argparse
import asyncio
import os

from prefect import flow, task
from prefect.client.schemas.schedules import CronSchedule
from prefect.deployments import Deployment
from prefect.utilities.annotations import quote

from utils.postgres import init_db
from utils.prefect import create_deployment_run, get_deployment_id_by_name
from utils.tasks import (
    check_for_new_data,
    chunk_episodes,
    create_whisper_processor_and_model,
    index_documents_es,
    init_es,
    load_cached_episodes,
    load_podcast_data,
    recreate_grafana_dashboard,
    reinit_grafana_datasource,
    set_grafana_token,
    transcripe_and_cache_episodes,
    update_bucket_state,
)
from utils.utils import print_log
from utils.variables import (
    CACHE_DIR,
    ES_CLIENT,
    INDEX_NAME,
    OLLAMA_CLIENT,
    PROJECT_DIR,
    WORK_POOL_NAME,
)


def parse_cli_args():
    """
    Parses command-line arguments for controlling various setup options.

    Returns:
        tuple: A tuple containing boolean values for reindex_es, reinit_db,
               defacto, redeploy_flows, reinint_grafana, and recreate_dashboards.
    """
    parser = argparse.ArgumentParser(description="Reading control parameters.")
    parser.add_argument(
        "--reindex_es", type=str, required=False, help="Value of reindex_es"
    )
    parser.add_argument(
        "--reinit_db", type=str, required=False, help="Value of reinit_db"
    )
    parser.add_argument("--defacto", type=str, required=False, help="Value of defacto")
    parser.add_argument(
        "--redeploy_flows", type=str, required=False, help="Value of redeploy_flows"
    )
    parser.add_argument(
        "--reinint_grafana", type=str, required=False, help="Value of reinint_grafana"
    )
    parser.add_argument(
        "--recreate_dashboards",
        type=str,
        required=False,
        help="Value of recreate_dashboards",
    )
    args = parser.parse_args()

    assert args.reindex_es in [
        "true",
        "false",
        None,
    ], "'reindex_es' must be either 'true', 'false', or left blank"
    assert args.reinit_db in [
        "true",
        "false",
        None,
    ], "'reinit_db' must be either 'true', 'false', or left blank"
    assert args.defacto in [
        "true",
        "false",
        None,
    ], "'defacto' must be either 'true', 'false', or left blank"
    assert args.redeploy_flows in [
        "true",
        "false",
        None,
    ], "'redeploy_flows' must be either 'true', 'false', or left blank"
    assert args.reinint_grafana in [
        "true",
        "false",
        None,
    ], "'reinint_grafana' must be either 'true', 'false', or left blank"
    assert args.recreate_dashboards in [
        "true",
        "false",
        None,
    ], "'recreate_dashboards' must be either 'true', 'false', or left blank"

    reindex_es = args.reindex_es == "true"
    reinit_db = args.reinit_db == "true"
    defacto = args.defacto != "false"
    redeploy_flows = args.redeploy_flows == "true"
    reinint_grafana = args.reinint_grafana == "true"
    recreate_dashboards = args.recreate_dashboards == "true"

    return (
        reindex_es,
        reinit_db,
        defacto,
        redeploy_flows,
        reinint_grafana,
        recreate_dashboards,
    )


@flow(name="setup_es", log_prints=True, persist_result=False)
def setup_es(reindex_es=False, defacto=True, new_episodes_dirs=None):
    """
    Sets up the ElasticSearch index.

    Args:
        reindex_es (bool, optional): Whether to reindex ElasticSearch. Defaults
                                     to False.
        defacto (bool, optional): Whether to use the default setup. Defaults
                                  to True.
        new_episodes_dirs (list of str, optional): Directories containing new
                                                   episodes to be processed.
                                                   Defaults to None.
    """
    # Initialize ES
    task(init_es, log_prints=True)(reindex_es=reindex_es)
    print_log("============> Initialize ES: Done.")

    # Load Podcasts
    dataset = task(load_podcast_data, log_prints=True)(
        new_episodes_dirs=new_episodes_dirs,
        defacto=defacto,
    )
    print_log("============> Loading Podcasts: Done.")

    # Perform ASR
    processor, model = task(create_whisper_processor_and_model, log_prints=True)(
        asr_model_name=os.getenv("ASR_MODEL", "openai/whisper-small"),
        cache_dir=CACHE_DIR,
        defacto=defacto,
    )
    print_log("============> Whisper Model & Processor Creation: Done.")

    transcripts_cache_dir = os.path.join(PROJECT_DIR, "data/generated_transcriptions")
    _ = task(transcripe_and_cache_episodes, log_prints=True)(
        model=model,
        processor=processor,
        dataset=quote(dataset),
        transcripts_cache_dir=transcripts_cache_dir,
        defacto=defacto,
    )
    print_log("============> Performing ASR: Done.")

    # Chunking
    dataset = task(load_cached_episodes, log_prints=True)(
        transcripts_cache_dir=transcripts_cache_dir,
        defacto=defacto,
    )
    print_log("============> Loading Transcribed Documents: Done.")

    documents = task(chunk_episodes, log_prints=True)(
        dataset=quote(dataset),
        defacto=defacto,
    )
    print_log("============> Loading Chunking Documents: Done.")

    # Index documents in ES
    is_run_indexing = bool(new_episodes_dirs or reindex_es)
    _ = task(index_documents_es, log_prints=True)(
        ollama_client=OLLAMA_CLIENT,
        es_client=ES_CLIENT,
        index_name=INDEX_NAME,
        documents=quote(documents),
        is_run_indexing=is_run_indexing,
    )
    print_log("============> Indexing Documents in ES: Done.")


@flow(name="init_db", log_prints=True)
def init_df_flow(reinit_db):
    """
    Initializes the database.

    Args:
        reinit_db (bool): Whether to reinitialize the database.
    """
    task(init_db, log_prints=True)(reinit_db)


@flow(name="process_new_episodes", log_prints=True)
def process_new_episodes(bucket_dir):
    """
    Processes new episodes found in the specified bucket directory.

    Args:
        bucket_dir (str): The directory containing new episodes.
    """
    new_dirs = task(check_for_new_data, log_prints=True)(bucket_dir)

    # Process new data if the check_for_new_data task succeeded
    if new_dirs:
        params = {
            "reindex_es": False,
            "defacto": False,
            "new_episodes_dirs": new_dirs,
        }

        # Run the flow with parameters
        deployment_name = "ad-hoc"
        flow_name = "setup_es"
        deployment_id = asyncio.run(
            get_deployment_id_by_name(
                deployment_name=deployment_name,
                flow_name=flow_name,
            )
        )

        _ = asyncio.run(
            create_deployment_run(
                deployment_id=deployment_id,
                parameters=params,
            )
        )

        task(update_bucket_state, log_prints=True)(bucket_dir, new_dirs)
    else:
        print("Found no new episodes, nothing to do...")


@flow(name="setup_grafana", log_prints=True)
def setup_grafana(reinit_grafana=False, recreate_dashboards=False):
    """
    Sets up Grafana datasources and dashboards.

    Args:
        reinit_grafana (bool, optional): Whether to reinitialize the Grafana
                                         datasource. Defaults to False.
        recreate_dashboards (bool, optional): Whether to recreate the dashboards.
                                              Defaults to False.
    """
    datasource_name = os.getenv("GRAFANA_DS_NAME")
    dashboard_name = os.getenv("GRAFANA_DASHBOARD_NAME")

    task(set_grafana_token, log_prints=True)(reset_token=False)

    task(reinit_grafana_datasource, log_prints=True)(
        datasource_name=datasource_name, reinit_grafana=reinit_grafana
    )

    task(recreate_grafana_dashboard, log_prints=True)(
        dashboard_name=dashboard_name,
        datasource_name=datasource_name,
        recreate_dashboards=recreate_dashboards,
    )


if __name__ == "__main__":
    (
        reindex_es,
        reinit_db,
        defacto,
        redeploy_flows,
        reinit_grafana,
        recreate_dashboards,
    ) = parse_cli_args()

    # Creating deployments for the flows
    if redeploy_flows:
        print_log("Re-deploying prefect flows ...")

        deployment_setup_es = Deployment.build_from_flow(
            flow=setup_es,
            name="ad-hoc",
            work_pool_name=WORK_POOL_NAME,
            parameters={"reindex_es": reindex_es, "defacto": defacto},
        )
        deployment_setup_es.apply()
        print_log("Successfully deployed prefect flow setup_es/ad-hoc")

        deployment_init_db = Deployment.build_from_flow(
            flow=init_df_flow,
            name="ad-hoc",
            work_pool_name=WORK_POOL_NAME,
            parameters={"reinit_db": reinit_db},
        )
        deployment_init_db.apply()
        print_log("Successfully deployed prefect flow init_db/ad-hoc")

        deployment_setup_grafana = Deployment.build_from_flow(
            flow=setup_grafana,
            name="ad-hoc",
            work_pool_name=WORK_POOL_NAME,
            parameters={
                "reinit_grafana": reinit_grafana,
                "recreate_dashboards": recreate_dashboards,
            },
        )
        deployment_setup_grafana.apply()
        print_log("Successfully deployed prefect flow setup_grafana/ad-hoc")

        deployment_process_new_episodes = Deployment.build_from_flow(
            flow=process_new_episodes,
            name="midnight-every-sunday",
            work_pool_name=WORK_POOL_NAME,
            parameters={"bucket_dir": os.path.join(PROJECT_DIR, "bucket")},
            schedules=[CronSchedule(cron="0 0 * * 0")],
        )
        deployment_process_new_episodes.apply()
        print_log(
            "Successfully deployed prefect flow process_new_episodes/midnight-every-sunday"
        )
    else:
        print("'redeploy_flows' is set to 'False', no need to redeploy ...")
