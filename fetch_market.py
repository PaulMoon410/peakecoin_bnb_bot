import requests

def get_orderbook_top(token="SWAP.BNB"):
    payload = {
        "jsonrpc": "2.0",
        "method": "find",
        "params": {
            "contract": "market",
            "table": "buyBook",
            "query": {"symbol": token},
            "limit": 1,
            "indexes": [{"index": "priceDec", "descending": True}]
        },
        "id": 1
    }
    buy_response = requests.post("https://api.hive-engine.com/rpc/contracts", json=payload)

    payload["table"] = "sellBook"
    payload["indexes"] = [{"index": "price", "descending": False}]
    sell_response = requests.post("https://api.hive-engine.com/rpc/contracts", json=payload)

    print("📥 Buy:", buy_response.text)
    print("📤 Sell:", sell_response.text)

    if buy_response.status_code == 200 and sell_response.status_code == 200:
        buy_result = buy_response.json().get("result", [])
        sell_result = sell_response.json().get("result", [])

        highest_bid = float(buy_result[0]["price"]) if buy_result else 0
        lowest_ask = float(sell_result[0]["price"]) if sell_result else 0

        return {"highestBid": highest_bid, "lowestAsk": lowest_ask}

    return None
