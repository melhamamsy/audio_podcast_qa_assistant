"""
This module provides functions to calculate relevance metrics for 
search results.
It includes functions to calculate the relevance of search results 
against ground truth data, as well as hit rate and 
mean reciprocal rank (MRR) metrics.
"""


def retrieve_relevance(question_dict, search_func, **search_func_keys):
    """
    Calculate the relevance of search results by comparing them to the ground truth.

    Args:
        question_dict (dict): A dictionary containing information about the question,
                              including 'episode_id', 'chunk_id', and other relevant fields.
        search_func (callable): The search function to use for retrieving documents.
                                This function should accept keyword arguments.
        search_func_keys (dict): Key-value pairs where:
            - The keys represent the arguments required by the search function.
            - The values represent the corresponding fields in `question_dict` to extract
            and pass to `search_func`.

    Returns:
        list: A list of booleans indicating whether each document in the search results
              matches the ground truth `(episode_id, chunk_id)`.

    Example:
        If `search_func_keys = {"query": "text"}`, the function will extract
        `question_dict["text"]` and pass it as `query=<value>` to `search_func`.
    """

    search_args = {key: question_dict.get(val) for key, val in search_func_keys.items()}
    ground_truth = (question_dict["episode_id"], question_dict["chunk_id"])
    return [
        (doc["id"], doc["chunk_id"]) == ground_truth
        for doc in search_func(**search_args)
    ]


def hit_rate(relevance_total):
    """
    Calculate the hit rate from relevance results.

    Args:
        relevance_total (list): A list of lists where each inner
        list contains boolean values indicating relevance of
        search results.

    Returns:
        float: The hit rate, calculated as the proportion of queries
        with at least one relevant result.
    """
    cnt = 0

    for line in relevance_total:
        if True in line:
            cnt = cnt + 1

    return cnt / len(relevance_total)


def mrr(relevance_total):
    """
    Calculate the mean reciprocal rank (MRR) from relevance results.

    Args:
        relevance_total (list): A list of lists where each inner
        list contains boolean values indicating relevance of
        search results.

    Returns:
        float: The mean reciprocal rank, calculated as the average
        of reciprocal ranks of the first relevant result for each
        query.
    """
    total_score = 0.0

    for line in relevance_total:
        for rank, _ in enumerate(line):
            if line[rank] is True:
                total_score = total_score + 1 / (rank + 1)

    return total_score / len(relevance_total)
