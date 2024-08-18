from prefect import flow, task
from prefect.utilities.annotations import quote

@task
def my_task(x):
    print("Running my task!")
    print(x)
    return "Task completed successfully."

@flow(log_prints=True)
def my_flow():
    x = [1, 2, 3]
    result = my_task(quote(x))
    print(f"Flow finished with result: {result}")

if __name__ == "__main__":
    my_flow()

