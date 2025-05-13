# peake_ltc.py
import time
import datetime
import json
import os
from fetch_market import get_orderbook_top
from place_order import place_order, get_open_orders, cancel_order, get_balance  # ✅ Uses external module with PEK gas logic

# 🔐 Hive account
HIVE_ACCOUNT = "peakecoin"
TOKEN = "SWAP.LTC"
QTY = 0.0001
TICK = 0.001
DELAY = 60  # seconds between cycles

last_gas_time = 0
GAS_INTERVAL = 3600  # seconds (1 hour)

def maybe_buy_gas(account_name):
    global last_gas_time
    now = time.time()
    if now - last_gas_time > GAS_INTERVAL:
        print("Placing PEK gas order (hourly)...")
        from place_order import place_order, GAS_TOKEN, GAS_PRICE, GAS_AMOUNT
        place_order(account_name, GAS_TOKEN, GAS_PRICE, GAS_AMOUNT, order_type="buy")
        last_gas_time = now
    else:
        print("Skipping PEK gas order (not time yet).")

def smart_trade(account_name, token, quantity):
    print(f"\n--- Starting smart trade for {token} ---")
    # Fetch open orders for this token
    print("Step 1: Fetching open orders for token...")
    open_orders = get_open_orders(account_name, token)
    num_open_orders = len(open_orders) if open_orders else 0
    print(f"Open orders for {token}: {num_open_orders}")

    # Fetch all open orders for the account (all tokens)
    print("Step 2: Fetching all open orders for account...")
    all_open_orders = get_open_orders(account_name)
    total_open_orders = len(all_open_orders) if all_open_orders else 0
    print(f"Total open orders (all tokens): {total_open_orders}")

    # Warn and skip if at or above order limit
    if num_open_orders >= 198 or total_open_orders >= 198:
        print(f"[WARN] Too many open orders ({num_open_orders} for {token}, {total_open_orders} total). Hive Engine will ignore new orders. Skipping new order placement.")
        maybe_buy_gas(account_name)
        print(f"--- Smart trade for {token} complete (skipped due to order limit) ---\n")
        return

    # Separate buy and sell orders
    buy_orders = [o for o in open_orders if o.get('type') == 'buy']
    sell_orders = [o for o in open_orders if o.get('type') == 'sell']
    print(f"Buy orders: {len(buy_orders)} | Sell orders: {len(sell_orders)}")
    print("Step 3: Skipping all cancel logic. Only placing new orders...")
    market = get_orderbook_top(token)
    if not market:
        print("Failed to fetch market data.")
        return
    bid = market["highestBid"]
    ask = market["lowestAsk"]
    # Use a difference of 0.00000001 (TICK) between buy and sell
    buy_price = round(bid + 0.00000001, 8)
    sell_price = round(max(ask - 0.00000001, buy_price + 0.00000001), 8)

    # Only place a buy order if not already present at this price and it won't cross with own sell
    own_min_sell = min([float(o['price']) for o in sell_orders], default=None)
    if own_min_sell is not None and buy_price >= own_min_sell:
        print(f"[SKIP] Buy price {buy_price} would cross with own sell at {own_min_sell}, not placing buy.")
    elif any(abs(float(o['price']) - buy_price) < 1e-8 for o in buy_orders):
        print(f"[SKIP] Already have a BUY order at {buy_price}, not placing duplicate.")
    else:
        print(f"Step 4: Placing buy order at {buy_price}")
        place_order(account_name, token, buy_price, quantity, order_type="buy")

    # Only place a sell order if not already present at this price and it won't cross with own buy
    own_max_buy = max([float(o['price']) for o in buy_orders], default=None)
    if own_max_buy is not None and sell_price <= own_max_buy:
        print(f"[SKIP] Sell price {sell_price} would cross with own buy at {own_max_buy}, not placing sell.")
    elif any(abs(float(o['price']) - sell_price) < 1e-8 for o in sell_orders):
        print(f"[SKIP] Already have a SELL order at {sell_price}, not placing duplicate.")
    else:
        print(f"Step 5: Placing sell order at {sell_price}")
        place_order(account_name, token, sell_price, quantity, order_type="sell")

    maybe_buy_gas(account_name)
    print(f"--- Smart trade for {token} complete ---\n")

if __name__ == "__main__":
    while True:
        try:
            smart_trade(HIVE_ACCOUNT, TOKEN, QTY)
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}")
        time.sleep(DELAY)
