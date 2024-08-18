"""
This module provides a utility function for mapping a function
over a sequence with progress tracking using ThreadPoolExecutor
and tqdm for progress visualization.
"""

from concurrent.futures import ThreadPoolExecutor

from tqdm.auto import tqdm


def map_progress(f, seq, max_workers=1):
    """
    Map a function over a sequence with progress tracking.

    Args:
        f (callable): The function to apply to each element in the
        sequence.
        seq (iterable): The sequence of elements to process.
        max_workers (int, optional): The maximum number of threads
        to use. Default is 1.

    Returns:
        list: A list of results from applying the function to each
        element in the sequence.
    """
    pool = ThreadPoolExecutor(max_workers=max_workers)

    results = []

    with tqdm(total=len(seq)) as progress:
        futures = []

        for el in seq:
            future = pool.submit(f, el)
            future.add_done_callback(lambda p: progress.update())
            futures.append(future)

        for future in futures:
            result = future.result()
            results.append(result)

    return results
