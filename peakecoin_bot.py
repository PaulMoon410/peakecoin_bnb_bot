# peake_bot.py
import time
import datetime
from fetch_market import get_orderbook_top
from place_order import place_order  # ✅ Uses external module with PEK gas logic

# 🔐 Hive account
HIVE_ACCOUNT = "peakeoin"
TOKEN = "PEK"
QTY = 0.0001
TICK = 0.00000001
DELAY = 60  # seconds between cycles

def smart_trade(account_name, token, quantity):
    market = get_orderbook_top(token)
    if not market:
        print("⚠️ Failed to fetch market data.")
        return

    bid = market["highestBid"]
    ask = market["lowestAsk"]

    buy_price = round(bid + TICK, 8)
    sell_price = round(max(ask - TICK, buy_price + TICK), 8)

    print(f"📊 Market: Bid={bid}, Ask={ask}")
    print(f"🤖 Smart Buy: {buy_price} | Smart Sell: {sell_price}")

    place_order(account_name, token, buy_price, quantity, order_type="buy")
    place_order(account_name, token, sell_price, quantity, order_type="sell")

if __name__ == "__main__":
    while True:
        try:
            smart_trade(HIVE_ACCOUNT, TOKEN, QTY)
        except Exception as e:
            print(f"⚠️ Unexpected error: {e}")
        time.sleep(DELAY)
