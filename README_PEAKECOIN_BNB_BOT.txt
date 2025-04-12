# 🪙 PeakeCoin BNB Bot

A lightweight trading bot for automating trades on the [Hive Engine](https://hive-engine.com), specifically for the `SWAP.BNB` token. This project was built to help automate simple buy/sell orders using the Hive blockchain via the `beem` Python library.

---

## 📌 Features

- Automatically places buy/sell orders at configurable spreads
- Pulls live orderbook data from Hive Engine
- Secure Hive blockchain transactions using custom JSON
- Adjustable trade amount and delay between orders
- Optional FTP integration for logs or remote backups

---

## 📁 File Overview

| File | Purpose |
|------|---------|
| `peakecoin_bnb_bot.py` | Main trading loop for SWAP.BNB |
| `place_order.py` | Places orders on Hive Engine via signed blockchain transactions |
| `fetch_market.py` | Pulls market/orderbook data from Hive Engine |
| `ftp_upload.py` | Uploads files (e.g., logs or bot scripts) to GeoCities via FTP |

---

## ⚙️ Setup

### 1. Clone the Repo
```bash
git clone https://github.com/PaulMoon410/peakecoin_bnb_bot.git
cd peakecoin_bnb_bot
```

### 2. Install Dependencies
```bash
pip install beem requests
```

### 3. Configure Hive Credentials
Open `place_order.py` and replace:
```python
HIVE_POSTING_KEY = "your_private_posting_key_here"
```
> ⚠️ Never share your private key! Use environment variables or encrypted configs in production.

---

## 🚀 Running the Bot

```bash
python peakecoin_bnb_bot.py
```

The bot will:
- Fetch current top bid/ask for `SWAP.BNB`
- Calculate buy/sell prices based on a 3% spread
- Place orders using available balance
- Sleep for 60 seconds and repeat

---

## 🔧 Optional: FTP Upload

To upload logs or scripts remotely via FTP:

1. Edit `ftp_upload.py` and set:
   - `FTP_HOST`
   - `FTP_USER`
   - `FTP_PASS`

2. Use this helper:
```python
from ftp_upload import upload_to_ftp
upload_to_ftp("trade_log.txt", "trade_log.txt")
```

---

## 📜 License

MIT License. Do what you want, just don’t blame me if it breaks.

---

## 🤝 Contribute

Want to help expand this bot? Submit a pull request or fork it and make your own mods.

---

## 📫 Contact

Made by [@paulmoon410](https://github.com/PaulMoon410)

Follow the project on Hive: [`@peakecoin`](https://ecency.com/@peakecoin)
