"""
This module provides utility functions for interacting with Prefect deployments.
The utilities include functions to:
    1. Retrieve a deployment ID by its name and associated flow name.
    2. Create and trigger a deployment run with specified parameters.

These functions simplify managing and automating Prefect workflows programmatically.
"""

from prefect.client import get_client


async def get_deployment_id_by_name(deployment_name: str, flow_name: str):
    """
    Retrieve the ID of a Prefect deployment given its deployment name and flow name.

    Args:
        deployment_name (str): The name of the deployment.
        flow_name (str): The name of the flow associated with the deployment.

    Returns:
        str or None: The deployment ID if found, otherwise None.
    """
    client = get_client()
    deployments = await client.read_deployments()  # Fetch all deployments

    for deployment in deployments:
        if (
            deployment.name == deployment_name
            and flow_name == deployment.entrypoint.split(":")[-1]
        ):
            return deployment.id

    return None


async def create_deployment_run(deployment_id: str, parameters: dict):
    """
    Create and trigger a deployment run using the given deployment ID and parameters.

    Args:
        deployment_id (str): The ID of the deployment to trigger.
        parameters (dict): The parameters to pass to the deployment run.

    Returns:
        prefect.engine.state.State: The state of the triggered flow run.
    """
    client = get_client()
    return await client.create_flow_run_from_deployment(
        deployment_id=deployment_id,
        parameters=parameters,
    )
