"""
Example API Client for pyPortMan Backend
Use this to test the API endpoints
"""

import requests
import json

# API Base URL
BASE_URL = "http://localhost:8000"

def print_response(response, title="Response"):
    """Pretty print API response"""
    print(f"\n{title}:")
    print(f"Status: {response.status_code}")
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

def main():
    print("=" * 50)
    print("pyPortMan API Client Example")
    print("=" * 50)

    # 1. Health Check
    print("\n1. Health Check")
    response = requests.get(f"{BASE_URL}/health")
    print_response(response)

    # 2. Get all accounts
    print("\n2. Get all accounts")
    response = requests.get(f"{BASE_URL}/accounts")
    print_response(response)

    # 3. Create a new account (example)
    print("\n3. Create a new account (example)")
    account_data = {
        "name": "My Zerodha Account",
        "account_id": "YOUR_ZERODHA_USER_ID",
        "api_key": "YOUR_API_KEY",
        "api_secret": "YOUR_API_SECRET"
    }
    print("Note: Replace with your actual credentials")
    print(f"POST {BASE_URL}/accounts")
    print(json.dumps(account_data, indent=2))

    # Uncomment to actually create account:
    # response = requests.post(f"{BASE_URL}/accounts", json=account_data)
    # print_response(response)

    # 4. Get login URL for account
    print("\n4. Get login URL for account (replace {account_id})")
    print(f"GET {BASE_URL}/accounts/1/token-url")
    # response = requests.get(f"{BASE_URL}/accounts/1/token-url")
    # print_response(response)

    # 5. Get holdings
    print("\n5. Get all holdings")
    response = requests.get(f"{BASE_URL}/holdings")
    print_response(response)

    # 6. Get positions
    print("\n6. Get all positions")
    response = requests.get(f"{BASE_URL}/positions")
    print_response(response)

    # 7. Get orders
    print("\n7. Get all orders")
    response = requests.get(f"{BASE_URL}/orders")
    print_response(response)

    # 8. Get portfolio summary
    print("\n8. Get portfolio summary")
    response = requests.get(f"{BASE_URL}/stats/summary")
    print_response(response)

    # 9. Get equity curve
    print("\n9. Get equity curve (30 days)")
    response = requests.get(f"{BASE_URL}/stats/equity?days=30")
    print_response(response)

    # 10. Get allocation
    print("\n10. Get allocation breakdown")
    response = requests.get(f"{BASE_URL}/stats/allocation")
    print_response(response)

    # 11. Get top gainers
    print("\n11. Get top gainers")
    response = requests.get(f"{BASE_URL}/stats/top-gainers")
    print_response(response)

    # 12. Get top losers
    print("\n12. Get top losers")
    response = requests.get(f"{BASE_URL}/stats/top-losers")
    print_response(response)

    print("\n" + "=" * 50)
    print("API Client Example Complete")
    print("=" * 50)

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\nError: Could not connect to API server.")
        print("Make sure the server is running: uvicorn main:app --reload")
    except Exception as e:
        print(f"\nError: {e}")
