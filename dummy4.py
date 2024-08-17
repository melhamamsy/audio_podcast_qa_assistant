import requests

# Grafana server URL and credentials
grafana_url = "http://localhost:3000"
username = "admin"  # typically the default admin username
password = "admin"

# The ID of the API key you want to delete (you get this from the list API)
api_key_id = 1  # Replace with the actual key ID you want to delete

# API endpoint for deleting the API key
url = f"{grafana_url}/api/auth/keys/{api_key_id}"

# Headers with basic authentication
headers = {
    "Content-Type": "application/json"
}

# Make the DELETE request to delete the API key
response = requests.delete(url, headers=headers, auth=(username, password))

# Check if the request was successful
if response.status_code == 200:
    print(f"API Key with ID {api_key_id} successfully deleted.")
else:
    print(f"Failed to delete API key. Status code: {response.status_code}")
    print(response.json())
