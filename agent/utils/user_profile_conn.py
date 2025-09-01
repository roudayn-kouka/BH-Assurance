import requests
import random
from typing import Optional, Dict, Any

BASE_URL = "http://localhost:8083"

# Available endpoints with their strategies
ENDPOINTS = {
    "recommend_pm": {
        "url": "/recommend_pm/",
        "strategy": "product_recommendation",
        "description": "Product recommendations for professional clients (PM)"
    },
    "recommend_pp": {
        "url": "/recommend_pp/",
        "strategy": "product_recommendation", 
        "description": "Product recommendations for individual clients (PP)"
    },
    "facture_pm": {
        "url": "/facture_pm/",
        "strategy": "payment_reminder",
        "description": "Invoice data for professional clients (PM)"
    },
    "facture_pp": {
        "url": "/facture_pp/",
        "strategy": "payment_reminder",
        "description": "Invoice data for individual clients (PP)"
    },
    "renouvellement_pm": {
        "url": "/renouvellement_pm/",
        "strategy": "contract_renewal",
        "description": "Contract renewal for professional clients (PM)"
    },
    "renouvellement_pp": {
        "url": "/renouvellement_pp/",
        "strategy": "contract_renewal",
        "description": "Contract renewal for individual clients (PP)"
    }
}

def fetch_endpoint_data(endpoint_key: str) -> Optional[Dict[str, Any]]:
    """
    Fetch data from a specific endpoint.
    
    Args:
        endpoint_key: Key from ENDPOINTS dict (e.g., 'recommend_pm', 'facture_pm')
        
    Returns:
        Dict containing the API response data, or None if error
    """
    if endpoint_key not in ENDPOINTS:
        print(f"Unknown endpoint: {endpoint_key}")
        return None
        
    endpoint_config = ENDPOINTS[endpoint_key]
    url = f"{BASE_URL}{endpoint_config['url']}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Add metadata about the endpoint strategy
        data["endpoint_strategy"] = endpoint_config["strategy"]
        data["endpoint_description"] = endpoint_config["description"]
        data["endpoint_key"] = endpoint_key
        
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from {endpoint_key}: {e}")
        return None

def fetch_new_user() -> Optional[Dict[str, Any]]:
    """
    Fetch data from a random endpoint to simulate getting a new user.
    This replaces the old /user/random endpoint.
    """
    # Randomly select an endpoint to simulate different user scenarios
    endpoint_key = random.choice(list(ENDPOINTS.keys()))
    print(f"[INFO] Fetching random user data from endpoint: {endpoint_key}")
    
    return fetch_endpoint_data(endpoint_key)

def fetch_existing_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    For compatibility with existing code. Since we don't have user-specific endpoints,
    we'll use the first available recommendation endpoint.
    
    Args:
        user_id: The user ID (will be logged but not used for API call)
        
    Returns:
        Dict containing user data from a recommendation endpoint
    """
    print(f"[INFO] Fetching existing user data for user_id: {user_id}")
    # Use recommend_pm as default for existing users
    return fetch_endpoint_data("recommend_pm")

def fetch_strategy_data(strategy: str) -> Optional[Dict[str, Any]]:
    """
    Fetch data for a specific strategy type.
    
    Args:
        strategy: Strategy type ('product_recommendation', 'payment_reminder', 'contract_renewal')
        
    Returns:
        Dict containing data for the requested strategy
    """
    # Find endpoints matching the strategy
    matching_endpoints = [
        key for key, config in ENDPOINTS.items() 
        if config["strategy"] == strategy
    ]
    
    if not matching_endpoints:
        print(f"No endpoints found for strategy: {strategy}")
        return None
        
    # Randomly select from matching endpoints
    endpoint_key = random.choice(matching_endpoints)
    print(f"[INFO] Fetching {strategy} data from endpoint: {endpoint_key}")
    
    return fetch_endpoint_data(endpoint_key)

def get_available_strategies() -> Dict[str, list]:
    """
    Get all available strategies and their corresponding endpoints.
    
    Returns:
        Dict mapping strategy names to lists of endpoint keys
    """
    strategies = {}
    for endpoint_key, config in ENDPOINTS.items():
        strategy = config["strategy"]
        if strategy not in strategies:
            strategies[strategy] = []
        strategies[strategy].append(endpoint_key)
    
    return strategies
        
# Example usage
if __name__ == "__main__":
    user_data = fetch_new_user()
    if user_data:
        print("Random user data:")
        print(user_data)
