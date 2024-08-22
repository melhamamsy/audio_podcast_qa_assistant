"""
This module provides utility functions for interacting with Prefect deployments.
The utilities include functions to:
    1. Retrieve a deployment ID by its name and associated flow name.
    2. Create and trigger a deployment run with specified parameters.
    3. Monitor task status until done

These functions simplify managing and automating Prefect workflows programmatically.
"""

import time

from prefect.client import get_client
from prefect.states import StateType


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


async def monitor_run_status(run_id: str):
    """
    Monitor the status of a Prefect run until it is terminated.

    Parameters:
        run_id (str): The ID of the Prefect run to monitor.

    Returns:
        None: Prints 1 if the run completes successfully,
              prints 2 if the run fails or is canceled.

    The function continuously checks the status of the given `run_id` until
    it reaches a terminal state (COMPLETED, FAILED, or CANCELLED). It then
    prints 1 for successful completion and 2 otherwise.
    """
    async with get_client() as client:
        while True:
            flow_run = await client.read_flow_run(run_id)
            state = flow_run.state

            if state.type in {
                StateType.COMPLETED,
                StateType.FAILED,
                StateType.CANCELLED,
            }:
                return state.type

            # Wait for a few seconds before checking again
            print(f"Waiting for run with run_id '{run_id}' to finish...")
            time.sleep(5)
