import time
import requests
from beem import Hive
from beem.account import Account
from beem.transactionbuilder import TransactionBuilder
from beembase.operations import Custom_json  # ✅ Required for smart contract interaction

# ✅ Your Hive account and node setup
HIVE_ACCOUNT = "peakecoin.bnb"
HIVE_NODES = ["https://api.hive.blog", "https://anyx.io"]

# ✅ Initialize Hive client using wallet-stored key
hive = Hive(node=HIVE_NODES)
account = Account(HIVE_ACCOUNT, blockchain_instance=hive)

def get_balance(account_name, token):
    """Fetch balance of token from Hive Engine."""
    payload = {
        "jsonrpc": "2.0",
        "method": "find",
        "params": {
            "contract": "tokens",
            "table": "balances",
            "query": {"account": account_name, "symbol": token}
        },
        "id": 1
    }
    response = requests.post("https://api.hive-engine.com/rpc/contracts", json=payload)
    if response.status_code == 200:
        data = response.json()
        if data["result"]:
            return float(data["result"][0]["balance"])
    return 0.0

def place_order(account_name, token, price, quantity, order_type="buy"):
    """Places a buy/sell order on Hive Engine."""
    # ✅ Check balance and adjust quantity if needed
    available = get_balance(account_name, token if order_type == "sell" else "SWAP.HIVE")
    if available < quantity:
        print(f"⚠️ Not enough balance! Adjusting order. Available: {available} {token}")
        quantity = max(available * 0.95, 0.0001)

    # ✅ Format the payload
    order_payload = {
        "contractName": "market",
        "contractAction": order_type.lower(),
        "contractPayload": {
            "symbol": token,
            "quantity": str(round(quantity, 8)),
            "price": str(round(price, 8))
        }
    }

    print(f"📝 Adjusted Order JSON: {order_payload}")

    try:
        tx = TransactionBuilder(blockchain_instance=hive)
        op = Custom_json(
            required_auths=[account_name],
            required_posting_auths=[],
            id="ssc-mainnet-hive",
            json=order_payload
        )
        tx.appendOps([op])
        tx.sign()
        print("🔏 Transaction signed successfully!")

        tx.broadcast()
        print(f"✅ Order placed: {order_type.upper()} {quantity} {token} at {price}")
        return True

    except Exception as e:
        print(f"❌ Error placing order: {e}")
        import traceback
        traceback.print_exc()
        return False

# ✅ Run a test order if executed directly
if __name__ == "__main__":
    place_order(HIVE_ACCOUNT, "SWAP.BNB", 0.99, 5, "buy")
