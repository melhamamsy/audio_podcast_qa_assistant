from prefect.client import get_client
import asyncio

async def list_deployments():
    async with get_client() as client:
        deployments = await client.read_deployments()

    return [deployment.name for deployment in deployments]

# To run the async function in a synchronous context
if __name__ == "__main__":
    print(asyncio.run(list_deployments()))
