"""
This module initializes various configurations and environment variables for the project.
It sets up clients for Elasticsearch, Ollama, and OpenAI, and configures paths for
project directories, cache, prompt templates, and Grafana and PostgreSQL settings.

The main configurations are loaded dynamically based on the environment (setup mode or not),
allowing seamless switching between different setups.
"""

import os

from utils.elasticsearch import create_elasticsearch_client
from utils.ollama import create_ollama_client
from utils.openai import create_openai_client
from utils.utils import conf, initialize_env_variables

initialize_env_variables()

CONF = conf()

PROJECT_DIR = os.getenv(f"PROJECT{CONF}_DIR")

CACHE_DIR = os.path.join(PROJECT_DIR, "hf_cache")

ES_CLIENT = create_elasticsearch_client(
    host=os.getenv(f"ELASTIC{CONF}_HOST"),
    port=os.getenv("ELASTIC_PORT"),
)

OLLAMA_CLIENT = create_ollama_client(
    ollama_host=os.getenv(f"OLLAMA{CONF}_HOST"),
    ollama_port=os.getenv("OLLAMA_PORT"),
)

OPENAI_CLIENT = create_openai_client()

INDEX_NAME = os.getenv("ES_INDEX_NAME")

INDEX_SETTINGS_PATH = os.path.join(
    PROJECT_DIR, "config/elasticsearch/index_settings.json"
)

QA_PROMPT_TEMPLATE_PATH = os.path.join(
    PROJECT_DIR,
    "prompts/podcast_qa.txt",
)

EVAL_PROMPT_TEMPLATE_PATH = os.path.join(
    PROJECT_DIR,
    "prompts/llm_as_a_judge.txt",
)

EXPECTED_MAPPING = [
    "id",
    "chunk_id",
    "channel",
    "channel_id",
    "title",
    "categories",
    "tags",
    "text",
    "text_vector",
]

WORK_POOL_NAME = os.getenv("WORK_POOL_NAME")

GRAFANA_HOST = os.getenv("GRAFANA_SETUP_HOST")
GRAFANA_PORT = os.getenv("GRAFANA_PORT")
GRAFANA_URL = f"http://{GRAFANA_HOST}:{GRAFANA_PORT}"
GRAFANA_ADMIN_USER = os.getenv("GRAFANA_ADMIN_USER")
GRAFANA_ADMIN_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD")
GRAFANA_ADMIN_TOKEN = os.getenv("GRAFANA_ADMIN_TOKEN")

POSTGRES_HOST = os.getenv(f"POSTGRES{CONF}_HOST")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB = os.getenv("POSTGRES_DB")
