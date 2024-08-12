from prefect import task, flow
import os
import json
from pathlib import Path

# Task 1: Check if bucket directory contains new data (directories only) and update state
@task
def check_for_new_data(bucket_dir):
    state_file_path = Path(bucket_dir) / "bucket_state.json"
    
    # Load existing state if it exists, otherwise initialize an empty state
    if state_file_path.exists():
        with open(state_file_path, 'r') as f:
            state = json.load(f)
    else:
        state = {"tracked_directories": []}
    
    # List directories in the bucket directory
    directories = [d for d in os.listdir(bucket_dir) if os.path.isdir(Path(bucket_dir) / d)]
    
    # Check if new directories are present by comparing with tracked directories
    new_data = False
    for directory in directories:
        if directory not in state["tracked_directories"]:
            new_data = True
            state["tracked_directories"].append(directory)
            print(f"New directory found: {directory}")
    
    if new_data:
        # Update the state file with the new directories
        with open(state_file_path, 'w') as f:
            json.dump(state, f, indent=4)
        return True
    else:
        print("No new directories found.")
        return False

# Task 2: Run if new directories are found
@task
def process_new_data():
    print("Processing new data...")

# Flow definition using the flow decorator
@flow
def check_and_process_flow(bucket_dir):
    data_check = check_for_new_data(bucket_dir)
    
    # Process new data if the check_for_new_data task succeeded
    if data_check:
        process_new_data()

# Run the flow
if __name__ == "__main__":
    check_and_process_flow("bucket")
