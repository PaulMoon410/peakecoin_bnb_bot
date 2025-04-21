import time
from fetch_market import get_orderbook_top
from place_order import place_order, HIVE_ACCOUNT

TOKEN = "SWAP.BNB"
SPREAD = 0.01  # 3% above/below for placing orders
TRADE_QTY = 0.001
SLEEP_TIME = 60  # seconds

def trading_bot():
    while True:
        book = get_orderbook_top(TOKEN)
        if not book:
            print("❌ Failed to fetch orderbook.")
            time.sleep(SLEEP_TIME)
            continue

        buy_price = book["highestBid"] * (1 - SPREAD)
        sell_price = book["lowestAsk"] * (1 + SPREAD)

        print(f"🟢 Market Price: {(book['highestBid'] + book['lowestAsk']) / 2} | Buy: {buy_price} | Sell: {sell_price}")

        print(f"⚡ Placing BUY order: {TRADE_QTY} {TOKEN} at {buy_price}")
        place_order(HIVE_ACCOUNT, TOKEN, buy_price, TRADE_QTY, "buy")

        print(f"⚡ Placing SELL order: {TRADE_QTY} {TOKEN} at {sell_price}")
        place_order(HIVE_ACCOUNT, TOKEN, sell_price, TRADE_QTY, "sell")

        time.sleep(SLEEP_TIME)

if __name__ == "__main__":
    trading_bot()
