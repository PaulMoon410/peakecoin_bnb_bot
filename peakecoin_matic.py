# peakecoin_matic_bot.py
import time
import sys
import datetime
from beem import Hive
from beem.account import Account
from beem.comment import Comment
from beem.nodelist import NodeList
from beem.transactionbuilder import TransactionBuilder
from fetch_market import get_orderbook_top, get_recent_orders
from place_order import place_order, get_open_orders, cancel_order, get_balance

# 🔐 Hive account
HIVE_ACCOUNT = "peakecoin.matic"
TOKEN = "SWAP.MATIC"
TICK = 0.00000001  # Use the correct TICK for MATIC
DELAY = 300  # seconds between cycles (5 minutes)

last_gas_time = 0
GAS_INTERVAL = 3600  # seconds (1 hour)

# Trade tracking dictionary: {order_id: {'type': 'buy'/'sell', 'price': float, 'quantity': float}}
trade_history = {}

# Daily profit tracking
profit_today = 0.0
trades_today = []
last_post_date = None

# Helper to record a trade
def record_trade(order_id, trade_type, price, quantity):
    global profit_today, trades_today
    trade_history[order_id] = {'type': trade_type, 'price': price, 'quantity': quantity}
    if trade_type == 'sell':
        # Find the best matching buy for this sell
        buys = [v for v in trade_history.values() if v['type'] == 'buy' and not v.get('matched')]
        if buys:
            best_buy = min(buys, key=lambda x: x['price'])
            profit = (price - best_buy['price']) * min(quantity, best_buy['quantity'])
            profit_today += profit
            best_buy['matched'] = True
            trades_today.append({'buy': best_buy['price'], 'sell': price, 'qty': min(quantity, best_buy['quantity']), 'profit': profit})

# Function to post daily summary to Hive
def post_daily_summary(account_name, token, profit, trades):
    try:
        nodelist = NodeList()
        nodelist.update_nodes()
        hive = Hive(node=nodelist.get_nodes())
        account = Account(account_name, blockchain_instance=hive)
        date_str = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        title = f"Daily SWAP.MATIC Trading Report - {date_str}"
        body = f"""
# Daily SWAP.MATIC Trading Report

**Date:** {date_str}
**Account:** {account_name}
**Token:** {token}

## Summary
- Total profit: {profit:.8f} {token}
- Number of trades: {len(trades)}

## Trades
"""
        for t in trades:
            body += f"- Buy: {t['buy']} | Sell: {t['sell']} | Qty: {t['qty']} | Profit: {t['profit']:.8f} {token}\n"
        body += "\n---\n*Automated post by trading bot.*"
        account.post(title, body, "hive-engine", reply_identifier=None)
        printc(f"[POSTED] Daily summary posted to Hive blog.", 'cyan')
    except Exception as e:
        printc(f"[ERROR] Failed to post daily summary: {e}", 'red')

# Check if it's a new day and post summary if so
def maybe_post_daily_summary(account_name, token):
    global last_post_date, profit_today, trades_today
    now = datetime.datetime.utcnow().date()
    if last_post_date is None or now > last_post_date:
        if trades_today:
            post_daily_summary(account_name, token, profit_today, trades_today)
        last_post_date = now
        profit_today = 0.0
        trades_today = []

# Helper to find matching buy for a sell
def find_profitable_buy(sell_price):
    # Find the highest buy price that is less than sell_price
    buys = [v for v in trade_history.values() if v['type'] == 'buy']
    if not buys:
        return None
    best_buy = max(buys, key=lambda x: x['price'])
    if sell_price > best_buy['price']:
        return best_buy
    return None

def printc(text, color):
    colors = {
        'green': '\033[92m',
        'yellow': '\033[93m',
        'red': '\033[91m',
        'cyan': '\033[96m',
        'magenta': '\033[95m',
        'reset': '\033[0m'
    }
    if sys.platform.startswith('win'):
        # On Windows, enable ANSI escape codes in terminal
        import os
        os.system('')
    print(f"{colors.get(color, '')}{text}{colors['reset']}")

def maybe_buy_gas(account_name):
    global last_gas_time
    now = time.time()
    if now - last_gas_time > GAS_INTERVAL:
        print("Placing PEK gas order (hourly)...")
        from place_order import place_order, GAS_TOKEN, GAS_AMOUNT
        GAS_PRICE = 0.00000001  # Set gas price to minimum
        place_order(account_name, GAS_TOKEN, GAS_PRICE, GAS_AMOUNT, order_type="buy")
        last_gas_time = now
    else:
        print("Skipping PEK gas order (not time yet).")

def is_market_volatile(token, window=20, threshold=0.02):
    """
    Returns True if the price volatility in the last `window` trades exceeds `threshold` (e.g., 0.02 for 2%).
    Handles None or empty results gracefully, and avoids redundant warnings.
    """
    try:
        orders = get_recent_orders(token, window)
        if not orders or not isinstance(orders, dict):
            printc("[WARN] get_recent_orders returned None or invalid dict", 'yellow')
            return False  # No data, treat as not volatile
        buy_orders = orders.get('buy', [])
        sell_orders = orders.get('sell', [])
        if buy_orders is None:
            buy_orders = []
        if sell_orders is None:
            sell_orders = []
        prices = [float(o['price']) for o in buy_orders + sell_orders if o and 'price' in o]
        if len(prices) < 2:
            if not buy_orders and not sell_orders:
                # Only print this if both lists are empty (API/data issue already logged in fetch_market)
                return False
            else:
                printc("[WARN] Not enough price data in recent orders (some trades exist, but <2 prices)", 'yellow')
                return False
        min_price = min(prices)
        max_price = max(prices)
        if min_price == 0:
            printc("[WARN] Minimum price is zero in recent orders, treating as volatile", 'yellow')
            return True  # Avoid divide by zero, treat as volatile
        volatility = (max_price - min_price) / min_price
        return volatility > threshold
    except Exception as e:
        printc(f"[ERROR] Volatility check failed: {e}", 'red')
        return False

def smart_trade(account_name, token):
    printc("\n" + "="*50, 'cyan')
    printc(f"[START] Smart trade for {token}", 'cyan')
    printc("="*50, 'cyan')
    # Volatility check
    if is_market_volatile(token, window=20, threshold=0.02):
        printc("\n[ VOLATILITY CHECK ]", 'yellow')
        printc("- Market volatility too high. Skipping this cycle.", 'yellow')
        printc("="*50 + "\n", 'yellow')
        return
    printc("\n[ BALANCE CHECK ]", 'green')
    balance = get_balance(account_name, token)
    printc(f"[GET_BALANCE] {token} for {account_name}", 'cyan')
    printc(f"- {token} balance: {balance}", 'green')
    if balance is None or balance == 0.0:
        printc(f"[WARN] {token} balance is zero or could not be fetched!", 'red')
    hive_balance = get_balance(account_name, 'HIVE')
    printc(f"[GET_BALANCE] HIVE for {account_name}", 'cyan')
    printc(f"- HIVE balance: {hive_balance}", 'green')
    if hive_balance is None or hive_balance == 0.0:
        printc(f"[WARN] HIVE balance is zero or could not be fetched!", 'red')
    rc = get_balance(account_name, 'RC')
    printc(f"[GET_BALANCE] RC for {account_name}", 'cyan')
    printc(f"- Resource Credits (RC): {rc}", 'green')
    if rc is None or rc == 0.0:
        printc(f"[WARN] RC is zero or could not be fetched!", 'red')
    MIN_RC = 1000000000  # Example: 1B RC minimum, adjust as needed
    if rc is not None:
        if rc < MIN_RC:
            printc("\n[ RC WARNING ]", 'yellow')
            printc(f"- Not enough Resource Credits (RC: {rc}). Skipping trade cycle.", 'yellow')
            printc("="*50 + "\n", 'yellow')
            return
        elif rc < MIN_RC * 2:
            printc(f"- [RC LOW] Resource Credits are low ({rc}). Consider powering up or requesting delegation.", 'yellow')
    else:
        printc("\n[ RC WARNING ]", 'yellow')
        printc("- Could not fetch Resource Credits. Proceeding with caution.", 'yellow')
    if balance > 0:
        quantity = round(balance / 10, 8)
    else:
        printc("\n[ BALANCE WARNING ]", 'red')
        printc(f"- No balance for {token}, skipping trade.", 'red')
        printc("="*50 + "\n", 'red')
        return

    open_orders = get_open_orders(account_name, token)
    num_open_orders = len(open_orders) if open_orders else 0
    all_open_orders = get_open_orders(account_name)
    total_open_orders = len(all_open_orders) if all_open_orders else 0
    printc("\n" + "-"*50, 'cyan')
    printc(f"[ORDER STATUS] \U0001F4CA Open {token} orders: {num_open_orders} | Total: {total_open_orders}", 'cyan')
    printc("-"*50, 'cyan')
    # Cancel the oldest order if at or above limit
    ORDER_LIMIT = 100
    if num_open_orders >= ORDER_LIMIT or total_open_orders >= ORDER_LIMIT:
        printc("\n[ ORDER LIMIT WARNING ]", 'yellow')
        printc(f"- Open order limit reached ({num_open_orders} for {token}, {total_open_orders} total). Cancelling oldest order...", 'yellow')
        # Find the oldest order (by _id or timestamp)
        if open_orders:
            oldest = min(open_orders, key=lambda o: o.get('timestamp', o.get('_id', 0)))
            order_id = oldest.get('_id')
            printc(f"- Oldest order object: {oldest}", 'yellow')
            # Check if the order belongs to the account
            order_account = oldest.get('account')
            if order_account != account_name:
                printc(f"- WARNING: Oldest order's account is {order_account}, but you are using {account_name} to cancel!", 'red')
            if order_id:
                printc(f"[DEBUG] Forcing cancel_order(account={account_name}, order_id={order_id})", 'magenta')
                try:
                    success, txid, error = cancel_order(account_name, order_id)
                    if success:
                        printc(f"✅ Cancelled order: {order_id} (TXID: {txid})", 'green')
                    else:
                        printc(f"❌ Failed to cancel order {order_id}: {error}", 'red')
                        if error and "invalid params" in error:
                            printc(f"Skipping retry for order {order_id} due to invalid params.", 'yellow')
                            # Do not add to pending_cancels and skip further processing for this order
                            return
                        printc(f"- cancel_order() result: success={success}, txid={txid}, error={error}", 'yellow')
                except Exception as e:
                    printc(f"[ERROR] Exception in cancel_order: {e}", 'red')
                    success = False
                    txid = None
                    error = str(e)
                # No pending_cancels logic: always retry every cycle
                # Wait and poll for order removal (up to 60s)
                max_wait = 60  # seconds
                poll_interval = 5  # seconds
                waited = 0
                while waited < max_wait:
                    open_orders_after = get_open_orders(account_name, token)
                    if not any(o.get('_id') == order_id for o in open_orders_after):
                        printc(f"✅ Order {order_id} removed from orderbook.", 'green')
                        break
                    printc(f"- Waiting for order {order_id} to be removed... ({waited+poll_interval}s)", 'yellow')
                    time.sleep(poll_interval)
                    waited += poll_interval
                else:
                    import json
                    try:
                        with open("stuck_orders.json", "a") as f:
                            f.write(json.dumps({"order_id": order_id, "timestamp": time.time()}) + "\n")
                        printc(f"❗ Stuck order {order_id} logged to stuck_orders.json", 'yellow')
                    except Exception as e:
                        printc(f"- Failed to log stuck order: {e}", 'red')
                    printc(f"❗ Order {order_id} is stuck after {max_wait}s, will retry next cycle.", 'red')
                    printc(f"  See: https://he.dtools.dev/account/{account_name} or https://hive-engine.rocks/account/{account_name}", 'red')
        else:
            printc("- No open orders found to cancel.", 'yellow')
        printc("="*50 + "\n", 'yellow')
        maybe_buy_gas(account_name)
        return

    printc("\n[ ORDERBOOK & PLACEMENT ]", 'magenta')
    buy_orders = [o for o in open_orders if o.get('type') == 'buy']
    sell_orders = [o for o in open_orders if o.get('type') == 'sell']
    market = get_orderbook_top(token)
    if not market:
        printc("- Failed to fetch market data.", 'red')
        printc("="*50 + "\n", 'red')
        return
    bid = market["highestBid"]
    ask = market["lowestAsk"]
    buy_price = round(bid + TICK, 8)
    sell_price = round(max(ask - TICK, buy_price + TICK), 8)
    own_min_sell = min([float(o['price']) for o in sell_orders], default=None)
    if own_min_sell is not None and buy_price >= own_min_sell:
        printc(f"- Buy skipped: price {buy_price} would cross with own sell at {own_min_sell}", 'yellow')
    elif any(abs(float(o['price']) - buy_price) < 1e-8 for o in buy_orders):
        printc(f"- Buy skipped: duplicate at {buy_price}", 'yellow')
    else:
        # Place buy order and record it
        printc(f"- Buy order placed: {quantity} @ {buy_price}", 'green')
        order_id = place_order(account_name, token, buy_price, quantity, order_type="buy")
        if order_id:
            record_trade(order_id, 'buy', buy_price, quantity)
    own_max_buy = max([float(o['price']) for o in buy_orders], default=None)
    if own_max_buy is not None and sell_price <= own_max_buy:
        printc(f"- Sell skipped: price {sell_price} would cross with own buy at {own_max_buy}", 'yellow')
    elif any(abs(float(o['price']) - sell_price) < 1e-8 for o in sell_orders):
        printc(f"- Sell skipped: duplicate at {sell_price}", 'yellow')
    else:
        # Only sell if it would be profitable
        profitable_buy = find_profitable_buy(sell_price)
        if profitable_buy and sell_price > profitable_buy['price']:
            printc(f"- Sell order placed: {quantity} @ {sell_price} (profit over buy at {profitable_buy['price']})", 'green')
            order_id = place_order(account_name, token, sell_price, quantity, order_type="sell")
            if order_id:
                record_trade(order_id, 'sell', sell_price, quantity)
        else:
            printc(f"- Sell skipped: no profitable buy found for sell price {sell_price}", 'yellow')
    printc("="*50 + "\n", 'magenta')
    maybe_buy_gas(account_name)
    maybe_post_daily_summary(account_name, token)

if __name__ == "__main__":
    while True:
        try:
            smart_trade(HIVE_ACCOUNT, TOKEN)
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}")
        time.sleep(DELAY)
