"""
This module checks if a specified Prefect work pool exists.
It lists all available work pools and compares against an environment variable.
Passes 'true' of 'false' to stdout
"""

import asyncio
import io
import os
import sys

from prefect.client import get_client, PrefectClient


async def list_work_pools():
    """
    Asynchronously retrieve a list of all Prefect work pool names.

    Returns:
        list: A list of work pool names.
    """
    async with get_client() as client:
        client: PrefectClient
        work_pools = await client.read_work_pools()
    return [work_pool.name for work_pool in work_pools]


# Capture stdout in a variable
if __name__ == "__main__":
    # Create a StringIO object to capture the output
    captured_output = io.StringIO()
    sys.stdout = captured_output  # Redirect stdout to the StringIO object

    # Run your async function and print the result
    result = asyncio.run(list_work_pools())
    print(result)

    # Reset stdout to its original value
    sys.stdout = sys.__stdout__

    # Get the captured output as a string
    output_as_string = captured_output.getvalue()

    # Print or use the captured output
    if os.getenv("WORK_POOL_NAME") in result:
        print("true")
    else:
        print("false")
