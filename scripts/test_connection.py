import os
import requests
import base64
from dotenv import load_dotenv

load_dotenv()

def test_connection(subdomain):
    username = os.getenv("WP_USERNAME")
    password = os.getenv("WP_APP_PASSWORD")
    base_url = f"https://{subdomain}.av-kantei.com"
    api_url = f"{base_url}/wp-json/wp/v2/users/me"

    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded}"
    }

    try:
        print(f"Testing connection to {base_url}...")
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code == 200:
            user_data = response.json()
            print(f"Success! Connected to {subdomain}")
            print(f"User ID: {user_data.get('id')}")
            print(f"Username: {user_data.get('slug')}")
            print(f"Display Name: {user_data.get('name')}")
            print(f"Roles: {user_data.get('roles')}")
        else:
            print(f"Failed: {response.status_code} {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_connection("sd01-chichi")
