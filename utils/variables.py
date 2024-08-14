"""
"""

import os
from utils.utils import conf, initialize_env_variables
from utils.elasticsearch import create_elasticsearch_client
from utils.ollama import create_ollama_client
from utils.openai import create_openai_client

initialize_env_variables()

CONF = conf()

PROJECT_DIR = os.getenv(f'PROJECT{CONF}_DIR')

CACHE_DIR = os.path.join(PROJECT_DIR, "hf_cache")

ES_CLIENT = create_elasticsearch_client(
    host=os.getenv(f'ELASTIC{CONF}_HOST'),
    port=os.getenv('ELASTIC_PORT'),
)

OLLAMA_CLIENT = create_ollama_client(
    ollama_host=os.getenv(f'OLLAMA{CONF}_HOST'),
    ollama_port=os.getenv('OLLAMA_PORT'),
)

OPENAI_CLIENT = create_openai_client(

)

INDEX_NAME = os.getenv('ES_INDEX_NAME')

INDEX_SETTINGS_PATH = os.path.join(
    PROJECT_DIR, 
    "config/elasticsearch/index_settings.json"
)

QA_PROMPT_TEMPLATE_PATH = os.path.join(
    PROJECT_DIR,
    'prompts/podcast_qa.txt',
)

EVAL_PROMPT_TEMPLATE_PATH = os.path.join(
    PROJECT_DIR,
    'prompts/llm_as_a_judge.txt',
)

EXPECTED_MAPPING = [
    'id', 'chunk_id', 'channel', 'channel_id', 'title',
    'categories', 'tags', 'text', 'text_vector'
]

WORK_POOL_NAME = os.getenv('WORK_POOL_NAME')
