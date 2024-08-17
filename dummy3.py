import requests

# Grafana server URL and credentials
grafana_url = "http://localhost:3000"
username = "admin"  # typically the default admin username
password = "admin"

# API endpoint for listing API keys
url = f"{grafana_url}/api/auth/keys"

# Headers with basic authentication
headers = {
    "Content-Type": "application/json"
}

# Make the GET request to list the API keys
response = requests.get(url, headers=headers, auth=(username, password))

# Check if the request was successful
if response.status_code == 200:
    keys = response.json()
    if keys:
        print("Existing API Keys:")
        for key in keys:
            # print(f"Name: {key['name']}, ID: {key['id']}, Role: {key['role']}")
            print(key)
    else:
        print("No API keys found.")
else:
    print(f"Failed to retrieve API keys. Status code: {response.status_code}")
    print(response.json())
