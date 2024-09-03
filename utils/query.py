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

from exceptions.exceptions import QueryTypeWrongValueError, WrongPomptParams
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


def elastic_search_text(query, title_query=None, boost=None, size=5):
    """
    Perform a text-based search using Elasticsearch.

    Args:
        query (str): The main query string to search for.
        title_query (str, Optional): An optional title filter to narrow the search.
        boost (float, Optional): An optional boost to the qeury
        size (int): Number of documents to retrieve, Default is 5.

    Returns:
        list: A list of search results matching the query.
    """
    search_query = {
        "_source": ["text", "title", "tags", "chunk_id", "id"],
        "size": size,
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

    if boost:
        search_query["query"]["bool"]["must"]["multi_match"]["boost"] = boost

    responses = ES_CLIENT.search(
        index=INDEX_NAME,
        body=search_query,
    )

    return [
        {"_id": hit["_id"], "_score": hit["_score"], **hit["_source"]}
        for hit in responses["hits"]["hits"]
    ]


def elastic_search_knn(query_vector, title_query=None, boost=None, size=5):
    """
    Perform a K-Nearest Neighbors (KNN) search using Elasticsearch.

    Args:
        query_vector (list): The query vector for similarity search.
        title_query (str, Optional): An optional title filter to narrow the search.
        boost (float, Optional): An optional boost to the qeury
        size (int): Number of documents to retrieve, Default is 5.

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

    if boost:
        knn["boost"] = boost

    search_query = {
        "knn": knn,
        "size": size,
        "_source": ["text", "title", "tags", "chunk_id", "id"],
    }

    responses = ES_CLIENT.search(
        index=INDEX_NAME,
        body=search_query,
    )

    return [
        {"_id": hit["_id"], "_score": hit["_score"], **hit["_source"]}
        for hit in responses["hits"]["hits"]
    ]


def compute_rrf(rank, k=60):
    """
    Compute the Reciprocal Rank Fusion (RRF) score for a given document rank.

    The RRF score is calculated as 1 / (k + rank), where 'k' is a tunable
    parameter that defines how much emphasis is placed on lower-ranked results.

    Parameters:
    ----------
    rank : int
        The rank of the document (1-based index).
    k : int, optional
        The constant used to adjust the impact of the rank in the RRF calculation.
        Default is 60.

    Returns:
    -------
    float
        The reciprocal relevance score for the document.
    """
    return 1 / (k + rank)


def compute_documents_rrf(k, *results_args):
    """
    Calculate the RRF scores for documents from multiple result sets.

    This function computes the cumulative RRF score for each document
    across multiple ranked result sets.

    Parameters:
    ----------
    k : int
        The constant used in the RRF calculation.
    *results_args : list of list of dict
        Each argument is a list of results, where each result is a dictionary
        representing a document with an '_id' key. The rank is derived from the
        index within each result list.

    Returns:
    -------
    list of tuple
        A list of tuples where each tuple contains a document ID and its
        cumulative RRF score, sorted in descending order by score.
    """
    rrf_scores = {}
    for results in results_args:
        for rank, hit in enumerate(results):
            doc_id = hit["_id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + compute_rrf(rank + 1, k)

    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)


def elastic_search_hybrid_rrf(
    query, query_vector, k=60, title_query=None, vector_boost=None
):
    """
    Perform a hybrid search using Elasticsearch by combining text-based and
    vector-based search results, then re-ranking them using RRF.

    Parameters:
    ----------
    query : str
        The text query used for the traditional keyword search.
    query_vector : list or ndarray
        The vector representing the query, used for the k-NN (vector) search.
    k : int, optional
        The constant used in the RRF calculation. Default is 60.
    title_query : str, optional
        An additional query for targeting specific fields like titles.
    vector_boost : float, optional
        The weight assigned to the vector-based search results relative to
        the text-based results. Must be a float between 0 and 1. If None,
        both text and vector search are given equal weight (0.5).

    Returns:
    -------
    list of dict
        A list of the top-K documents, sorted by their RRF score. Each document
        contains its original content plus an additional key 'rrf_score'
        indicating its RRF score.

    Raises:
    -------
    AssertionError
        If vector_boost is provided but is not a float between 0 and 1.
    """
    assert vector_boost is None or (
        isinstance(vector_boost, (float, int)) and 0 <= vector_boost <= 1
    ), (
        f"Incorrect value '{vector_boost}' for vector_boost, "
        "must be a float or int between [0, 1] or None"
    )

    if vector_boost:
        text_boost = 1 - vector_boost
    else:
        vector_boost = text_boost = 0.5

    knn_results = elastic_search_knn(
        query_vector, title_query=title_query, boost=vector_boost, size=10
    )
    keyword_results = elastic_search_text(
        query, title_query=title_query, boost=text_boost, size=10
    )

    results = knn_results + keyword_results
    result_ids = [doc["_id"] for doc in results]

    rrf_scores = compute_documents_rrf(k, knn_results, keyword_results)

    # Get top-K documents by the score
    final_results = []
    for doc_id, rrf_score in rrf_scores[:5]:
        doc = results[result_ids.index(doc_id)]
        doc["rrf_score"] = rrf_score
        final_results.append(doc)

    return final_results


def elastic_search_hybrid_rrf_qr(
    query, query_rewriting_results, k=60, title_query=None, vector_boost=None
):
    """
    Performs a hybrid search using the original query and rewritten results,
    applying Reciprocal Rank Fusion (RRF) to rank and merge the results.

    The function takes the original query and its rewritten variations,
    conducts a hybrid search for each, and then applies RRF to combine and
    rank the results. The top `k` results based on the RRF score are returned.

    Parameters:
    -----------
    query : str
        The original query string.
    query_rewriting_results : list of str
        A list of rewritten queries derived from the original query.
    k : int, optional
        The number of top results to return after applying RRF, default is 60.
    title_query : str, optional
        An additional query parameter for title-based search, default is None.
    vector_boost : float, optional
        A boost value for vector-based search results, default is None.

    Returns:
    --------
    list of dict
        A list of the top `k` search results, each containing the RRF score.
    """
    results = [
        elastic_search_hybrid_rrf(
            query=query,
            query_vector=get_embedding(OLLAMA_CLIENT, query),
            k=k,
            title_query=title_query,
            vector_boost=vector_boost,
        )
        for query in query_rewriting_results + [query]
    ]
    flattened_results = flatten_list_of_lists(results)
    result_ids = [doc["_id"] for doc in flattened_results]
    rrf_results = compute_documents_rrf(k, *results)

    final_results = []
    for doc_id, rrf_score in rrf_results[:5]:
        doc = flattened_results[result_ids.index(doc_id)]
        doc["rrf_score"] = rrf_score
        final_results.append(doc)

    return final_results


def llm(prompt, model_choice="ollama/gemma:2b"):
    """
    Generate a response using a language model.

    Args:
        prompt (str): The prompt to be passed to the language model.
        model_choice (str, optional): The model to use for generating the response.
                                      Defaults to "ollama/gemma:2b".

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
    """
    Perform a search based on the specified search type.

    This function supports different search methods, including vector-based,
    text-based, and hybrid approaches. It returns results based on the selected
    search type.

    Parameters:
    ----------
    query : str
        The main search query to be processed.
    title_query : str
        An optional query to target specific fields like titles.
    search_type : str
        The type of search to perform. It must be one of the following:
        - "Vector": Performs a k-NN (vector-based) search using the query embedding.
        - "Text": Performs a traditional keyword search.
        - "Hybrid": Combines the results of both vector-based and text-based searches,
          re-ranking the documents using Reciprocal Rank Fusion (RRF).

    Returns:
    -------
    list of dict
        A list of search results. Each result is a dictionary containing the relevant
        information about a document.

    Raises:
    -------
    QueryTypeWrongValueError
        If `search_type` is not one of "Text", "Vector", or "Hybrid".
    """
    if search_type == "Vector":
        query_vector = get_embedding(
            client=OLLAMA_CLIENT,
            text=query,
            model_name=os.getenv("EMBED_MODEL", "nomic-embed-text"),
        )
        return elastic_search_knn(query_vector, title_query)

    if search_type == "Text":
        return elastic_search_text(query, title_query)

    if search_type == "Hybrid":
        query_vector = get_embedding(
            client=OLLAMA_CLIENT,
            text=query,
            model_name=os.getenv("EMBED_MODEL", "nomic-embed-text"),
        )
        return elastic_search_hybrid_rrf(query, query_vector, title_query=title_query)

    raise QueryTypeWrongValueError(
        "`search_type` must be either 'Text', 'Vector', or 'Hybrid'"
    )


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
        search_type (str): The type of search to perform ("Text", "Vector", or "Hybrid").

    Returns:
        dict: The generated answer and related metadata.
    """
    search_results = get_search_results(query, title_query, search_type)
    tags, titles = process_search_results(search_results)

    context = build_context(search_results)
    answer, tokens, response_time = generate_answer(query, context, model_choice)

    eval_model = os.getenv("EVAL_MODEL", "ollama/gemma:2b")
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
