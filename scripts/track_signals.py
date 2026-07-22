import os
import json
import datetime
import yfinance as yf
import pandas as pd
import sys

# Configure stdout/stderr encoding for Windows console compatibility
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SIGNAL_FILES = {
    "Stocks": os.path.join(BASE_DIR, "data", "signals.json"),
    "Crypto": os.path.join(BASE_DIR, "infocryptos", "data", "signals.json"),
    "Forex": os.path.join(BASE_DIR, "infofx", "data", "signals.json")
}

# Mapping back clean tickers to yfinance tickers if needed
YF_TICKER_MAPPING = {
    # Forex
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X", 
    "USDCHF": "USDCHF=X", "AUDUSD": "AUDUSD=X", "USDCAD": "USDCAD=X", 
    "NZDUSD": "NZDUSD=X", "EURGBP": "EURGBP=X", "EURJPY": "EURJPY=X", 
    "GBPJPY": "GBPJPY=X", "GC": "GC=F", "SI": "SI=F",
    # Crypto
    "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD",
    "AVAX": "AVAX-USD", "LINK": "LINK-USD", "SHIB": "SHIB-USD"
}

def get_yf_ticker(ticker):
    return YF_TICKER_MAPPING.get(ticker, ticker)

def track_market_signals(market_name, file_path):
    if not os.path.exists(file_path):
        print(f"INFO: No signals file for {market_name} yet.")
        return

    print(f"📊 Tracking active signals for {market_name}...")
    with open(file_path, 'r', encoding='utf-8') as f:
        try:
            signals = json.load(f)
        except json.JSONDecodeError:
            print(f"⚠️ Error reading JSON from {file_path}, resetting database.")
            signals = []

    active_or_pending = [s for s in signals if s.get("status") in ["PENDING", "ACTIVE"]]
    if not active_or_pending:
        print(f"✅ No active or pending signals to track in {market_name}.")
        return

    # Download recent 5 days of data for the active tickers
    tickers_to_query = list(set(get_yf_ticker(s.get("ticker")) for s in active_or_pending))
    print(f"☁️ Fetching market data from yfinance for: {tickers_to_query}")
    
    try:
        # Download data
        data = yf.download(tickers_to_query, period="5d", progress=False)
        if data.empty:
            print("⚠️ yfinance returned empty data.")
            return
    except Exception as e:
        print(f"❌ Error fetching tracking data from yfinance: {e}")
        return

    updated_signals = []
    changes_made = False

    for s in signals:
        if s.get("status") not in ["PENDING", "ACTIVE"]:
            updated_signals.append(s)
            continue

        ticker = s.get("ticker")
        yf_ticker = get_yf_ticker(ticker)
        entry = s.get("entry_price")
        target = s.get("target_price")
        stop = s.get("stop_loss")
        direction = s.get("type", "LONG").upper()

        # Handle multi-index data vs single ticker data from yfinance
        try:
            if len(tickers_to_query) == 1:
                df = data.copy()
            else:
                df = data.xs(yf_ticker, level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data[yf_ticker]
        except Exception:
            # Ticker data not found in download result
            updated_signals.append(s)
            continue

        if df.empty:
            updated_signals.append(s)
            continue

        # Get High, Low and Close prices
        high_prices = df['High'].tolist()
        low_prices = df['Low'].tolist()
        close_prices = df['Close'].tolist()

        status = s.get("status", "PENDING")

        # Track price crossings
        for high, low, close in zip(high_prices, low_prices, close_prices):
            if status == "PENDING":
                # For LONG: Triggered if Low <= Entry <= High
                # For SHORT: Triggered if Low <= Entry <= High
                # If price crossed or touched entry, we move to ACTIVE
                if low <= entry <= high:
                    status = "ACTIVE"
                    changes_made = True

            if status == "ACTIVE":
                if direction == "LONG":
                    # Target hit
                    if high >= target:
                        status = "HIT_TARGET"
                        changes_made = True
                        break
                    # Stop hit
                    elif low <= stop:
                        status = "HIT_STOP"
                        changes_made = True
                        break
                else:  # SHORT
                    # Target hit (price went down to target)
                    if low <= target:
                        status = "HIT_TARGET"
                        changes_made = True
                        break
                    # Stop hit (price went up to stop)
                    if high >= stop:
                        status = "HIT_STOP"
                        changes_made = True
                        break

        s["status"] = status
        updated_signals.append(s)

    if changes_made:
        print(f"💾 Saving tracked signal updates to {file_path}...")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(updated_signals, f, indent=4)
    else:
        print(f"✅ No status changes detected for {market_name}.")

def main():
    print("=== STARTING GLOBAL SIGNAL TRACKING ===")
    for market, path in SIGNAL_FILES.items():
        track_market_signals(market, path)
    print("=== SIGNAL TRACKING COMPLETED ===")

if __name__ == "__main__":
    main()
