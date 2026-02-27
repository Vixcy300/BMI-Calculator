import requests
import json

url = "http://localhost:5000/login"
data = {
    "username": "test_script",
    "password": "password123"
}

try:
    print(f"Sending POST request to {url}...")
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error: {e}")
