"""
This module provides functions for searching and generating prompts using various models.
It includes functions to:
    1. Search using MinSearch or Elasticsearch.
    2. Build context from search results.
    3. Construct prompts from templates.
    4. Generate responses using language models.
    5. Evaluate relevance of responses.
    6. Calculate costs for OpenAI API usage.

These utilities facilitate generating high-quality responses and contextual
outputs by combining search, prompt engineering, and model-driven evaluation.
"""

import json
import os
import time

from exceptions.exceptions import WrongPomptParams, QueryTypeWrongValueError
from utils.ollama import get_embedding
from utils.utils import (
    find_parameters,
    flatten_list_of_lists,
    is_sublist,
    parse_json_response,
)
from utils.variables import (
    ES_CLIENT,
    EVAL_PROMPT_TEMPLATE_PATH,
    INDEX_NAME,
    OLLAMA_CLIENT,
    OPENAI_CLIENT,
    QA_PROMPT_TEMPLATE_PATH,
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
            + f"title: {doc['title']}\ntags: {doc['tags']}\nanswer: {doc['text']}\n\n"
        )

    return context


def build_prompt(prompt_template_path=None, **document_dict):
    """
    Build a prompt from a template and document dictionary.

    Args:
        prompt_template_path (str, optional): Path to the prompt template. If not provided,
                                              it defaults to QA_PROMPT_TEMPLATE_PATH.
        document_dict (dict): Dictionary of document parameters.

    Returns:
        str: The formatted prompt.

    Raises:
        WrongPomptParams: If the document dictionary does not match the expected parameters
                          in the template.
    """
    if not prompt_template_path:
        prompt_template_path = QA_PROMPT_TEMPLATE_PATH

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


def elastic_search_text(query, title_query):
    """
    Perform a text-based search using Elasticsearch.

    Args:
        query (str): The main query string to search for.
        title_query (str): An optional title filter to narrow the search.

    Returns:
        list: A list of search results matching the query.
    """
    search_query = {
        "_source": ["text", "title", "tags", "chunk_id", "id"],
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": query,
                        "fields": ["text", "title"],
                        "type": "best_fields",
                    }
                }
            }
        },
    }

    if title_query:
        search_query["query"]["bool"]["filter"] = {
            "match": {"title": {"query": title_query, "fuzziness": "AUTO"}}
        }

    responses = ES_CLIENT.search(
        index=INDEX_NAME,
        body=search_query,
        size=5,
    )

    return [hit["_source"] for hit in responses["hits"]["hits"]]


def elastic_search_knn(query_vector, title_query):
    """
    Perform a K-Nearest Neighbors (KNN) search using Elasticsearch.

    Args:
        query_vector (list): The query vector for similarity search.
        title_query (str): An optional title filter to narrow the search.

    Returns:
        list: A list of search results matching the query.
    """
    knn = {
        "field": "text_vector",
        "query_vector": query_vector,
        "k": 5,
        "num_candidates": 10_000,
    }

    if title_query:
        knn["filter"] = {
            "match": {"title": {"query": title_query, "fuzziness": "AUTO"}}
        }

    search_query = {
        "knn": knn,
        "_source": ["text", "title", "tags", "chunk_id", "id"],
    }

    responses = ES_CLIENT.search(
        index=INDEX_NAME,
        body=search_query,
        size=5,
    )

    return [hit["_source"] for hit in responses["hits"]["hits"]]


def llm(prompt, model_choice="ollama/phi3"):
    """
    Generate a response using a language model.

    Args:
        prompt (str): The prompt to be passed to the language model.
        model_choice (str, optional): The model to use for generating the response.
                                      Defaults to "ollama/phi3".

    Returns:
        tuple: The generated answer (str), token usage (dict), and response time (float).
    """
    start_time = time.time()

    if model_choice.startswith("ollama/"):
        client = OLLAMA_CLIENT
    elif model_choice.startswith("openai/"):
        client = OPENAI_CLIENT
    else:
        raise ValueError(f"Unknown model choice: {model_choice}")

    response = client.chat.completions.create(
        model=model_choice.split("/")[-1],
        messages=[{"role": "user", "content": prompt}],
    )
    answer = response.choices[0].message.content
    tokens = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens": response.usage.total_tokens,
    }

    end_time = time.time()
    response_time = end_time - start_time

    return answer, tokens, response_time


def evaluate_relevance(question, answer, eval_model):
    """
    Evaluate the relevance of a generated answer using a language model.

    Args:
        question (str): The original question.
        answer (str): The generated answer to evaluate.
        eval_model (str): The model to use for evaluating the relevance.

    Returns:
        tuple: Relevance (str), explanation (str), and token usage (dict).
    """
    prompt = build_prompt(
        EVAL_PROMPT_TEMPLATE_PATH, **{"question": question, "answer": answer}
    )

    evaluation, tokens, _ = llm(prompt, eval_model)

    try:
        json_eval = parse_json_response(evaluation)
        return json_eval["Relevance"], json_eval["Explanation"], tokens
    except json.JSONDecodeError:
        return "UNKNOWN", "Failed to parse evaluation", tokens


def calculate_openai_cost(model_choice, tokens):
    """
    Calculate the cost of using OpenAI API based on token usage.

    Args:
        model_choice (str): The model used for generating the response.
        tokens (dict): The token usage dictionary.

    Returns:
        float: The calculated cost in USD.
    """
    openai_cost = 0

    if model_choice == "openai/gpt-3.5-turbo":
        openai_cost = (
            tokens["prompt_tokens"] * 0.0015 + tokens["completion_tokens"] * 0.002
        ) / 1000
    elif model_choice in ["openai/gpt-4o", "openai/gpt-4o-mini"]:
        openai_cost = (
            tokens["prompt_tokens"] * 0.03 + tokens["completion_tokens"] * 0.06
        ) / 1000

    return openai_cost


def get_search_results(query, title_query, search_type):
    """Perform search based on the specified type."""
    if search_type == "Vector":
        query_vector = get_embedding(
            client=OLLAMA_CLIENT,
            text=query,
            model_name=os.getenv("EMBED_MODEL", "locusai/multi-qa-minilm-l6-cos-v1"),
        )
        return elastic_search_knn(query_vector, title_query)

    if search_type == "Text":
        return elastic_search_text(query, title_query)

    raise QueryTypeWrongValueError("`search_type` must be either 'Text' or 'Vector'")


def process_search_results(search_results):
    """
    Process search results to extract tags and titles.

    Args:
        search_results (list): A list of search results
            containing document data.

    Returns:
        tuple: A tuple containing formatted tags (str)
            and a set of unique titles (set).
    """
    tags = "#" + "; #".join(
        set(flatten_list_of_lists([doc["tags"] for doc in search_results]))
    )
    titles = {doc["title"] for doc in search_results}
    return tags, titles


def generate_answer(query, context, model_choice):
    """
    Generate an answer using the specified model.

    Args:
        query (str): The original question or query.
        context (str): The context built from search results.
        model_choice (str): The model to use for generating the answer.

    Returns:
        tuple: The generated answer (str), token usage (dict),
            and response time (float).
    """
    document_dict = {"question": query, "context": context}
    prompt = build_prompt(QA_PROMPT_TEMPLATE_PATH, **document_dict)
    return llm(prompt=prompt, model_choice=model_choice)


def evaluate_answer(query, answer, eval_model):
    """
    Evaluate the relevance of the answer.

    Args:
        query (str): The original question.
        answer (str): The generated answer to evaluate.
        eval_model (str): The model to use for evaluating the relevance.

    Returns:
        dict: A dictionary containing the relevance (str),
            explanation (str), and token usage (dict).
    """
    relevance, explanation, eval_tokens = evaluate_relevance(query, answer, eval_model)
    return {"relevance": relevance, "explanation": explanation, "tokens": eval_tokens}


def get_answer(query, title_query, model_choice, search_type):
    """
    Generate an answer based on a query using search results and a language model.

    Args:
        query (str): The main question or query.
        title_query (str): An optional title filter to narrow the search.
        model_choice (str): The model to use for generating the answer.
        search_type (str): The type of search to perform ("Text" or "Vector").

    Returns:
        dict: The generated answer and related metadata.
    """
    search_results = get_search_results(query, title_query, search_type)
    tags, titles = process_search_results(search_results)

    context = build_context(search_results)
    answer, tokens, response_time = generate_answer(query, context, model_choice)

    eval_model = os.getenv("EVAL_MODEL", "ollama/phi3")
    evaluation = evaluate_answer(query, answer, eval_model)

    openai_cost = calculate_openai_cost(model_choice, tokens) + calculate_openai_cost(
        eval_model, evaluation["tokens"]
    )

    return {
        "answer": answer,
        "tags": tags,
        "titles": titles,
        "response_time": response_time,
        "relevance": evaluation["relevance"],
        "relevance_explanation": evaluation["explanation"],
        "model_used": model_choice,
        "prompt_tokens": tokens["prompt_tokens"],
        "completion_tokens": tokens["completion_tokens"],
        "total_tokens": tokens["total_tokens"],
        "eval_prompt_tokens": evaluation["tokens"]["prompt_tokens"],
        "eval_completion_tokens": evaluation["tokens"]["completion_tokens"],
        "eval_total_tokens": evaluation["tokens"]["total_tokens"],
        "openai_cost": openai_cost,
    }


def openai_rephrase(episode_questions, prompt_template_path, model="gpt-4o-mini"):
    """
    Rephrase a set of questions using OpenAI.

    Args:
        episode_questions (list): A list of questions to rephrase.
        prompt_template_path (str): Path to the prompt template.
        model (str, optional): The model to use for rephrasing. Defaults to "gpt-4o-mini".

    Returns:
        list: The rephrased questions.
    """
    prompt = build_prompt(prompt_template_path, episode_questions=episode_questions)
    response = OPENAI_CLIENT.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt},
        ],
    )

    # Extract and print the response
    return parse_json_response(response.choices[0].message.content)
