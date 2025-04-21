import time
import requests
import json as jsonlib 
from nectar.hive import Hive
from beem import Hive 
from nectar.account import Account
from nectar.transactionbuilder import TransactionBuilder
from nectarbase.operations import Custom_json
from nectar.instance import set_shared_blockchain_instance

# 🔐 Hive account + keys
HIVE_ACCOUNT = "peakecoin.bnb"
HIVE_POSTING_KEY = "5JZWDTJvCkxz2rPXW9qEajMZoKegt9V4nXCcY7WD1LRC7tRbXB6"
HIVE_ACTIVE_KEY = "5JgXLzFB8fsH64WPWD9fzC4sJQyxSXhn4ykqXrakCnJaSfDjNuL"
HIVE_NODES = ["https://api.hive.blog", "https://anyx.io"]

# ✅ Connect to Hive
hive = Hive(node=HIVE_NODES, keys=[HIVE_POSTING_KEY, HIVE_ACTIVE_KEY])
set_shared_blockchain_instance(hive)
account = Account(HIVE_ACCOUNT, blockchain_instance=hive)


def get_balance(account_name, token):
    payload = {
        "jsonrpc": "2.0",
        "method": "find",
        "params": {
            "contract": "tokens",
            "table": "balances",
            "query": {"account": account_name, "symbol": token},
        },
        "id": 1,
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

    if available < quantity:
        print(f"⚠️ Not enough balance! Adjusting order. Available: {available}")
        quantity = max(available * 0.95, 0.00001)

    if quantity <= 0:
        print(f"🚫 Skipping order — quantity too small: {quantity}")
        return False

    payload = {
        "contractName": "market",
        "contractAction": order_type,
        "contractPayload": {
            "symbol": token,
            "quantity": str(round(quantity, 8)),
            "price": str(round(price, 6)),
        },
    }

    print(f"📝 Final Order Payload: {payload}")

    try:
        tx = TransactionBuilder(blockchain_instance=hive)
        op = Custom_json(
            required_auths=[account_name],
            required_posting_auths=[],
            id="ssc-mainnet-hive",
            json=jsonlib.dumps(payload),
        )
        tx.appendOps([op])
        tx.appendSigner(account_name, "active")

        print("🔐 Loaded public keys in wallet:", hive.wallet.getPublicKeys())
        print("🔑 Required signing key (active):", account["active"]["key_auths"][0][0])

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



