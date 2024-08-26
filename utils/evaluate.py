"""
This module provides functions to calculate relevance metrics for 
search results.
It includes functions to calculate the relevance of search results 
against ground truth data, as well as hit rate and 
mean reciprocal rank (MRR) metrics.
"""


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
