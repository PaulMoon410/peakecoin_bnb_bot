HIVE_ENGINE_API = "https://api.hive-engine.com/rpc"

def get_market_data(token="SWAP.BNB"):
    """Fetch market data for a specific token."""
    payload = {
        "jsonrpc": "2.0",
        "method": "find",
        "params": {
            "contract": "market",
            "table": "metrics",
            "query": {"symbol": token},
            "limit": 1
        },
        "id": 1
    }
    response = requests.post(f"{HIVE_ENGINE_API}/contracts", json=payload)

    if response.status_code == 200:
        return response.json()
    else:
        print("Error fetching market data:", response.text)
        return None

# Example usage
if __name__ == "__main__":
    market_data = get_market_data("SWAP.BNB")
    print(market_data)