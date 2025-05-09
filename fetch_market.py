import requests

def get_orderbook_top(token="SWAP.LTC"):
    # Pull top buy orders (usually works correctly with sorting)
    buy_payload = {
        "jsonrpc": "2.0",
        "method": "find",
        "params": {
            "contract": "market",
            "table": "buyBook",
            "query": {"symbol": token},
            "limit": 1000,
            "indexes": [{"index": "priceDec", "descending": True}]
        },
        "id": 1
    }

    # Pull up to 1000 sell orders to ensure we capture the true lowest ask
    sell_payload = {
        "jsonrpc": "2.0",
        "method": "find",
        "params": {
            "contract": "market",
            "table": "sellBook",
            "query": {"symbol": token},
            "limit": 1000,
            "indexes": [{"index": "price", "descending": False}]
        },
        "id": 2
    }

    # Request both buy and sell books
    buy_response = requests.post("https://api.hive-engine.com/rpc/contracts", json=buy_payload)
    sell_response = requests.post("https://api.hive-engine.com/rpc/contracts", json=sell_payload)

    # Log raw responses (optional for debugging)
    print("📥 Buy:", buy_response.text)
    print("📤 Sell:", sell_response.text)

    if buy_response.status_code == 200 and sell_response.status_code == 200:
        buy_result = buy_response.json().get("result", [])
        sell_result = sell_response.json().get("result", [])

        # Use the highest priced buy order (top bid)
        highest_bid = float(buy_result[0]["price"]) if buy_result else 0

        # Use the true lowest sell price found in the result
        valid_asks = [float(order["price"]) for order in sell_result if float(order["price"]) > 0]
        lowest_ask = min(valid_asks) if valid_asks else 0

        return {"highestBid": highest_bid, "lowestAsk": lowest_ask}

    return None
