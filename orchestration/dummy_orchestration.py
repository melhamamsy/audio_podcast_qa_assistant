from prefect import task, flow
import os
import json
from pathlib import Path

# Task 1: Check if bucket directory contains new data (directories only) and update state
def check_for_new_data(bucket_dir):
    state_file_path = Path(bucket_dir) / "bucket_state.json"
    new_dirs = []
    
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
            new_dirs.append(directory)
            print(f"New directory found: {directory}")
    
    if new_data:
        return new_dirs
    else:
        print("No new directories found.")
        return None

# Task 2: Run if new directories are found
def update_bucket_state(bucket_dir, new_dirs=[]):
    state_file_path = Path(bucket_dir) / "bucket_state.json"
        
    if new_dirs:
        if state_file_path.exists():
            with open(state_file_path, 'r') as f:
                state = json.load(f)
        else:
            state = {"tracked_directories": []}

        state["tracked_directories"] += new_dirs
        with open(state_file_path, 'w') as f:
            json.dump(state, f, indent=4)

        print("Updated Bucket state for newly indexed documents.")

# Flow definition using the flow decorator
@flow(log_prints=True)
def check_and_process_flow(bucket_dir):

    new_dirs = task(check_for_new_data, log_prints=True)(bucket_dir)
        
    # Process new data if the check_for_new_data task succeeded
    if new_dirs:
        print(new_dirs) ## setup_es deployment call should be here

    task(update_bucket_state, log_prints=True)(bucket_dir, new_dirs)

# Run the flow
if __name__ == "__main__":
    check_and_process_flow("/mnt/workspace/__ing/llming/DTC/audio_podcast_qa_assistant/bucket")
