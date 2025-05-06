import time
import requests
import json as jsonlib
import os
from nectar.hive import Hive
from nectar.account import Account
from nectar.transactionbuilder import TransactionBuilder
from nectarbase.operations import Custom_json
from nectar.instance import set_shared_blockchain_instance

# 🔐 Hive account + keys
HIVE_ACCOUNT = "Your Account"
HIVE_POSTING_KEY = "Posting Key"
HIVE_ACTIVE_KEY = "Active Key"
HIVE_NODES = ["https://api.hive.blog", "https://anyx.io"]

# 🧠 Trade history for logic
TRADE_HISTORY_FILE = "trade_history.json"
MIN_PROFIT_MARGIN = 0.015  # 1.5%

# ✅ Connect to Hive
hive = Hive(node=HIVE_NODES, keys=[HIVE_POSTING_KEY, HIVE_ACTIVE_KEY])
set_shared_blockchain_instance(hive)
account = Account(HIVE_ACCOUNT, blockchain_instance=hive)


def load_trade_history():
    if os.path.exists(TRADE_HISTORY_FILE):
        with open(TRADE_HISTORY_FILE, "r") as f:
            return jsonlib.load(f)
    return {}

def save_trade_history(data):
    with open(TRADE_HISTORY_FILE, "w") as f:
        jsonlib.dump(data, f, indent=2)

def update_trade_history(token, action, price):
    history = load_trade_history()
    if token not in history:
        history[token] = {}
    history[token][action] = price
    save_trade_history(history)

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

    # 🧠 Loss prevention logic
    history = load_trade_history()
    if order_type == "sell":
        last_buy = history.get(token, {}).get("buy", 0)
        min_sell_price = last_buy * (1 + MIN_PROFIT_MARGIN)
        if last_buy > 0 and price < min_sell_price:
            print(f"🚫 Skipping SELL — price {price} < min profitable price {min_sell_price}")
            return False
    elif order_type == "buy":
        last_sell = history.get(token, {}).get("sell", float("inf"))
        max_buy_price = last_sell * (1 - MIN_PROFIT_MARGIN)
        if last_sell < float("inf") and price > max_buy_price:
            print(f"🚫 Skipping BUY — price {price} > max profitable price {max_buy_price}")
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
        update_trade_history(token, order_type, price)
        return True

    except Exception as e:
        print(f"❌ Error broadcasting order: {e}")
        import traceback
        traceback.print_exc()
        return False
