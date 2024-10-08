"""
This module provides a utility function for mapping a function
over a sequence with progress tracking using ThreadPoolExecutor
and tqdm for progress visualization.
"""

from concurrent.futures import ThreadPoolExecutor

from tqdm.auto import tqdm


def map_progress(f, seq, max_workers=1, verbose=True):
    """
    Map a function over a sequence with progress tracking.

    Args:
        f (callable): The function to apply to each element in the
            sequence.
        seq (iterable): The sequence of elements to process.
        max_workers (int, optional): The maximum number of threads
            to use. Default is 1.
        verbose (bool): Whether to log progress

    Returns:
        list: A list of results from applying the function to each
        element in the sequence.
    """
    pool = ThreadPoolExecutor(max_workers=max_workers)

    results = []
    seq_len = len(seq)

    with tqdm(total=seq_len) as progress:
        for i, el in enumerate(seq):
            future = pool.submit(f, el)
            future.add_done_callback(lambda p: progress.update())
            results.append(future.result())

            if (i % (max(seq_len, 20) // 20) == 0) and verbose:
                print(f"{len(results)}/{seq_len} items processed so far...")

        if verbose:
            print(f"{len(results)}/{seq_len} items processed.")

    return results
