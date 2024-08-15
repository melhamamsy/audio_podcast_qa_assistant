# from prefect.client import get_client
# import asyncio

# async def list_deployments():
#     async with get_client() as client:
#         deployments = await client.read_deployments()

#     return [deployment.name for deployment in deployments]

# async def list_work_pools():
#     async with get_client() as client:
#         work_pools = await client.read_work_pools()

#     return [work_pool.name for work_pool in work_pools]

# # To run the async function in a synchronous context
# if __name__ == "__main__":
#     print(asyncio.run(list_deployments()))
#     print(asyncio.run(list_work_pools()))

import io
import os
import sys
from prefect.client import get_client
import asyncio

async def list_work_pools():
    async with get_client() as client:
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
