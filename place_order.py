import time
import requests
from beem import Hive
from beem.account import Account
from beem.transactionbuilder import TransactionBuilder
from beembase.operations import Custom_json
from beemgraphenebase.account import PrivateKey
from beem.instance import set_shared_blockchain_instance

# ✅ Replace with your Hive account + key
HIVE_ACCOUNT = "peakecoin.bnb"
HIVE_POSTING_KEY = "your_private_posting_key_here"  # 🔐 Replace with your real posting key
HIVE_NODES = ["https://api.hive.blog", "https://anyx.io"]

# ✅ Connect to Hive using direct key
hive = Hive(node=HIVE_NODES, keys=[HIVE_POSTING_KEY])
set_shared_blockchain_instance(hive)  # required for signing to work without wallet
account = Account(HIVE_ACCOUNT, blockchain_instance=hive)

def get_balance(account_name, token):
    """Fetch token balance"""
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
    r = requests.post("https://api.hive-engine.com/rpc/contracts", json=payload)
    if r.status_code == 200:
        result = r.json()
        if result["result"]:
            return float(result["result"][0]["balance"])
    return 0.0

def place_order(account_name, token, price, quantity, order_type="buy"):
    token_used = token if order_type == "sell" else "SWAP.HIVE"
    available = get_balance(account_name, token_used)

    if available <= 0:
        print(f"❗ Cannot place order — {token_used} balance is 0.")
        return False

    if available < quantity:
        print(f"⚠️ Not enough balance! Adjusting order. Available: {available}")
        quantity = max(available * 0.95, 0.0001)

    payload = {
        "contractName": "market",
        "contractAction": order_type,
        "contractPayload": {
            "symbol": token,
            "quantity": str(round(quantity, 8)),
            "price": str(round(price, 8))
        }
    }

    print(f"📝 Final Order Payload: {payload}")

    try:
        tx = TransactionBuilder(blockchain_instance=hive)
        op = Custom_json(
            required_auths=[account_name],
            required_posting_auths=[],
            id="ssc-mainnet-hive",
            json=payload
        )

        tx.appendOps([op])
        tx.sign()
        print("🔏 Transaction signed successfully!")
        tx.broadcast()
        print(f"✅ Order placed: {order_type.upper()} {quantity} {token} at {price}")
        return True

    except Exception as e:
        print(f"❌ Error broadcasting order: {e}")
        import traceback
        traceback.print_exc()
        return False

# ✅ Manual test
if __name__ == "__main__":
    place_order(HIVE_ACCOUNT, "SWAP.BNB", 0.99, 5, "buy")
