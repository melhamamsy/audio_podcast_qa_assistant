from prefect.client import get_client

async def get_deployment_id_by_name(deployment_name: str,
                                    flow_name: str):
    client = get_client()
    deployments = await client.read_deployments()  # Fetch all deployments

    for deployment in deployments:
        if deployment.name == deployment_name and \
            flow_name == deployment.entrypoint.split(':')[-1] :
            return deployment.id
    
    return None

async def create_deployment_run(deployment_id: str,
                                    parameters: dict):
    client = get_client()
    return await client.create_flow_run_from_deployment(
        deployment_id=deployment_id,
        parameters=parameters,
    )

     