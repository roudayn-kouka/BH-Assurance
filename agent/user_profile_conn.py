import requests

BASE_URL = "http://localhost:8083"

def fetch_new_user():
    """
    Sends a GET request to /user/random and returns the parsed JSON data.
    """
    url = f"{BASE_URL}/user/random"
    try:
        response = requests.get(url, timeout=5)  # set timeout to avoid hanging
        response.raise_for_status()  # raise an exception for 4xx/5xx errors
        data = response.json()  # parse JSON response
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching random user: {e}")
        return None
    

def fetch_existing_user(user_id):
    """
    Sends a GET request to /user/id and returns the parsed JSON data.
    """
    url = f"{BASE_URL}/user/id/{user_id}"
    try:
        response = requests.get(url, timeout=5)  # set timeout to avoid hanging
        response.raise_for_status()  # raise an exception for 4xx/5xx errors
        data = response.json()  # parse JSON response
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching existing user: {e}")
        return None
        
# Example usage
if __name__ == "__main__":
    user_data = fetch_new_user()
    if user_data:
        print("Random user data:")
        print(user_data)
