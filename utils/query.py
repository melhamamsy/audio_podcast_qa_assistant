"""
This module provides functions for searching and generating
prompts using various models. It includes functions to search
using MinSearch or Elasticsearch, build context from search
results, construct prompts from templates, and generate
responses using language models.
"""

import os
import json
import time

from exceptions.exceptions import WrongPomptParams
from utils.utils import (find_parameters, 
                         is_sublist, parse_json_response)
from utils.elasticsearch import create_elasticsearch_client
from utils.ollama import (create_ollama_client,
                          get_embedding)
from utils.openai import create_openai_client


## Create clients 
ES_CLIENT = create_elasticsearch_client(
    host=os.getenv('ELASTIC_HOST'),
    port=os.getenv('ELASTIC_PORT'),
)
OLLAMA_CLIENT = create_ollama_client(
    ollama_host=os.getenv('OLLAMA_HOST'),
    ollama_port=os.getenv('OLLAMA_PORT'),
)
OPENAI_CLIENT = create_openai_client()


INDEX_NAME = os.getenv('ES_INDEX_NAME')
PROJECT_DIR = os.getenv('PROJECT_DIR')
QA_PROMPT_TEMPLATE_PATH = os.path.join(
    PROJECT_DIR,
    'prompts/course_qa.txt',
)
EVAL_PROMPT_TEMPLATE_PATH = os.path.join(
    PROJECT_DIR,
    'prompts/llm_as_a_judge.txt',
)


def build_context(search_results):
    """
    Build context from search results.

    Args:
        search_results (list): List of search results.

    Returns:
        str: A formatted string of the search results.
    """
    context = ""

    for doc in search_results:
        context = (
            context
            + f"section: {doc['section']}\nquestion: {doc['question']}\nanswer: {doc['text']}\n\n"
        )

    return context


def build_prompt(prompt_template_path, **document_dict):
    """
    Build a prompt from a template and document dictionary.

    Args:
        prompt_template_path (str): Path to the prompt template.
        document_dict (dict): Dictionary of document parameters.

    Returns:
        str: The formatted prompt.

    Raises:
        WrongPomptParams: If the document dictionary does not
        match the expected parameters in the template.
    """
    with open(prompt_template_path, "r", encoding="utf-8") as f:
        prompt_template = f.read().strip()

    expected_params = sorted(find_parameters(prompt_template))
    provided_params = sorted(list(document_dict.keys()))

    if not is_sublist(main_list=provided_params, sublist=expected_params):
        raise WrongPomptParams(
            f"Expected presence of {expected_params}, but got {provided_params}"
        )

    prompt = prompt_template.format(**document_dict)

    return prompt


def elastic_search_text(query, course):
    """
    """
    search_query = {
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": query,
                        "fields": ["question^3", "text", "section"],
                        "type": "best_fields",
                    }
                },
                "filter": {"term": {"course": course}},
            }
        },
    }

    responses = ES_CLIENT.search(
        index=INDEX_NAME,
        body=search_query,
        size=5,
    )
    
    return [hit["_source"] for hit in responses["hits"]["hits"]]    


def elastic_search_knn(
    query_vector, course
):
    """
    """
    knn = {
        "field": "question_text_vector",
        "query_vector": query_vector,
        "k": 5,
        "num_candidates": 10_000,
        "filter": {"term": {"course": course}},
    }

    search_query = {
        "knn": knn,
        "_source": ["text", "section", "question", "course", "id"],
    }

    responses = ES_CLIENT.search(
        index=INDEX_NAME,
        body=search_query,
        size=5,
    )
    
    return [hit["_source"] for hit in responses["hits"]["hits"]]


def llm(prompt, model_choice="ollama/phi3"):
    """
    """
    start_time = time.time()

    if model_choice.startswith('ollama/'):
        client = OLLAMA_CLIENT
    elif model_choice.startswith('openai/'):
        client = OPENAI_CLIENT
    else:
        raise ValueError(f"Unknown model choice: {model_choice}")
    
    response = client.chat.completions.create(
        model=model_choice.split('/')[-1],
        messages=[{"role": "user", "content": prompt}]
    )
    answer = response.choices[0].message.content
    tokens = {
        'prompt_tokens': response.usage.prompt_tokens,
        'completion_tokens': response.usage.completion_tokens,
        'total_tokens': response.usage.total_tokens
    }

    end_time = time.time()
    response_time = end_time - start_time
    
    return answer, tokens, response_time


def evaluate_relevance(question, answer, eval_model):
    prompt = build_prompt(
        EVAL_PROMPT_TEMPLATE_PATH,
        **{'question':question, 'answer':answer}
    )

    evaluation, tokens, _ = llm(
        prompt, eval_model
    )
    
    try:
        json_eval = parse_json_response(evaluation)
        return json_eval['Relevance'], json_eval['Explanation'], tokens
    except json.JSONDecodeError:
        return "UNKNOWN", "Failed to parse evaluation", tokens


def calculate_openai_cost(model_choice, tokens):
    openai_cost = 0

    if model_choice == 'openai/gpt-3.5-turbo':
        openai_cost = (tokens['prompt_tokens'] * 0.0015 + tokens['completion_tokens'] * 0.002) / 1000
    elif model_choice in ['openai/gpt-4o', 'openai/gpt-4o-mini']:
        openai_cost = (tokens['prompt_tokens'] * 0.03 + tokens['completion_tokens'] * 0.06) / 1000

    return openai_cost


def get_answer(query, course, model_choice, search_type):
    """
    """
    if search_type == 'Vector':
        query_vector = get_embedding(
            client=OLLAMA_CLIENT, 
            text=query, 
            model_name="locusai/multi-qa-minilm-l6-cos-v1",
        )
        search_results = elastic_search_knn(query_vector, course)
    elif search_type == 'Text':
        search_results = elastic_search_text(query, course)

    context = build_context(search_results)
    document_dict = {"question": query, "context": context}

    prompt = build_prompt(
        QA_PROMPT_TEMPLATE_PATH, **document_dict
    )
    answer, tokens, response_time = llm(
        prompt=prompt,
        model_choice=model_choice,
    )
    
    eval_model = os.getenv('EVAL_MODEL', 'ollama/phi3')
    relevance, explanation, eval_tokens = evaluate_relevance(query, answer, eval_model)

    openai_cost = calculate_openai_cost(model_choice, tokens) +\
        calculate_openai_cost(eval_model, eval_tokens)
 
    return {
        'answer': answer,
        'response_time': response_time,
        'relevance': relevance,
        'relevance_explanation': explanation,
        'model_used': model_choice,
        'prompt_tokens': tokens['prompt_tokens'],
        'completion_tokens': tokens['completion_tokens'],
        'total_tokens': tokens['total_tokens'],
        'eval_prompt_tokens': eval_tokens['prompt_tokens'],
        'eval_completion_tokens': eval_tokens['completion_tokens'],
        'eval_total_tokens': eval_tokens['total_tokens'],
        'openai_cost': openai_cost,
    }
