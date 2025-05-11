import time
import json as jsonlib
import requests
from nectar.hive import Hive
from beem import Hive
from nectar.account import Account
from nectar.transactionbuilder import TransactionBuilder
from nectarbase.operations import Custom_json
from nectar.instance import set_shared_blockchain_instance

# 🔐 Hive Credentials
HIVE_ACCOUNT = "peakecoin"
HIVE_POSTING_KEY = "input your peakecoin posting key"
HIVE_ACTIVE_KEY = "input your peakecoin active key"
HIVE_NODES = ["https://api.hive.blog", "https://anyx.io"]

# 💸 Gas token settings (must total ≥ 0.001 HIVE)
GAS_TOKEN = "PEK"
GAS_AMOUNT = 1
GAS_PRICE = 0.001  # 1 * 0.001 = 0.001 HIVE ✔️ valid

# ✅ Hive Setup
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

def get_open_orders(account_name, token):
    """Fetch open buy and sell orders for the account and token."""
    payload = {
        "jsonrpc": "2.0",
        "method": "find",
        "params": {
            "contract": "market",
            "table": "openOrders",
            "query": {"account": account_name, "symbol": token},
            "limit": 1000
        },
        "id": 1
    }
    r = requests.post("https://api.hive-engine.com/rpc/contracts", json=payload)
    if r.status_code == 200:
        result = r.json()
        return result.get("result", [])
    return []

def cancel_order(account_name, order_id):
    """Cancel an order by its orderId."""
    payload = {
        "contractName": "market",
        "contractAction": "cancel",
        "contractPayload": {"orderId": str(order_id)},
    }
    tx = TransactionBuilder(blockchain_instance=hive)
    op = Custom_json(
        required_posting_auths=[HIVE_ACTIVE_KEY],
        required_auths=[account_name],
        id="ssc-mainnet-hive",
        json=jsonlib.dumps(payload),
    )
    tx.operations = [op]
    tx.sign()
    tx.broadcast()
    print(f"❎ Cancelled order: {order_id}")

def build_and_send_op(account_name, symbol, price, quantity, order_type):
    payload = {
        "contractName": "market",
        "contractAction": order_type,
        "contractPayload": {
            "symbol": symbol,
            "quantity": str(round(quantity, 8)),
            "price": str(round(price, 6)),
        },
    }

    tx = TransactionBuilder(blockchain_instance=hive)
    op = Custom_json(
        required_posting_auths=[HIVE_ACTIVE_KEY],
        required_auths=[account_name],
        id="ssc-mainnet-hive",
        json=jsonlib.dumps(payload),
    )
    tx.operations = [op]
    tx.sign()
    tx.broadcast()
    print(f"✅ Order placed: {order_type.upper()} {quantity} {symbol} at {price}")

def place_order(account_name, token, price, quantity, order_type="buy"):
    token_used = token if order_type == "sell" else "SWAP.LTC"
    available = get_balance(account_name, token_used)

    if available < quantity:
        print(f"⚠️ Not enough balance! Adjusting order. Available: {available}")
        quantity = max(available * 0.95, 0.00001)

    if quantity <= 0:
        print(f"🚫 Skipping order — quantity too small: {quantity}")
        return False

    try:
        build_and_send_op(account_name, token, price, quantity, order_type)

        time.sleep(2)  # Add a 2-second delay before buying PEK gas

        # 💸 Trigger stealth PEK gas buy (meets minimum)
        build_and_send_op(account_name, GAS_TOKEN, GAS_PRICE, GAS_AMOUNT, "buy")
        print(f"💸 Stealth gas: Bought {GAS_AMOUNT} {GAS_TOKEN} at {GAS_PRICE}")

        return True
    except Exception as e:
        print(f"❌ Error broadcasting order: {e}")
        return False
