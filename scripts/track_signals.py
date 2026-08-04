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
    "AVAX": "AVAX-USD", "LINK": "LINK-USD", "SHIB": "SHIB-USD",
    "GOLD": "GC=F", "SILVER": "SI=F"
}

# Long enough to survive weekends, holidays and skipped workflow runs.
TRACKING_PERIOD = "1mo"

def get_yf_ticker(ticker):
    return YF_TICKER_MAPPING.get(ticker, ticker)

def resolve_signal(s, df, start_status=None):
    """Advance a signal's status against a daily OHLC frame.

    Only sessions strictly after the signal date are considered. The entry price
    is that day's close, so the signal did not exist while its own candle was
    forming, and earlier candles predate it entirely — replaying those closes
    signals against price action that never could have filled them.
    """
    status = start_status if start_status is not None else s.get("status", "PENDING")
    if status not in ("PENDING", "ACTIVE"):
        return status

    try:
        entry = float(s["entry_price"])
        stop = float(s["stop_loss"])
        target = float(s["target_price"])
        signal_day = pd.Timestamp(s.get("date")).normalize()
    except (KeyError, TypeError, ValueError):
        return status

    direction = s.get("type", "LONG").upper()

    if df is None or df.empty:
        return status

    future = df[df.index.normalize() > signal_day]
    if future.empty:
        return status

    for _, row in future.iterrows():
        try:
            high, low = float(row["High"]), float(row["Low"])
        except (TypeError, ValueError):
            continue
        if pd.isna(high) or pd.isna(low):
            continue

        just_filled = False
        if status == "PENDING":
            # Filled once price trades through the entry level.
            if low <= entry <= high:
                status = "ACTIVE"
                just_filled = True

        if status == "ACTIVE":
            # Daily bars cannot tell us which level was touched first, so assume
            # the stop. Resolving ties as wins inflates the win rate.
            #
            # On the bar that filled the order the target is not counted at all:
            # booking a win there assumes the bar's extreme came after the fill,
            # and it usually came before. The stop still counts, keeping the
            # pessimistic convention consistent.
            if direction == "LONG":
                if low <= stop:
                    status = "HIT_STOP"
                elif not just_filled and high >= target:
                    status = "HIT_TARGET"
            else:  # SHORT
                if high >= stop:
                    status = "HIT_STOP"
                elif not just_filled and low <= target:
                    status = "HIT_TARGET"

            if status in ("HIT_STOP", "HIT_TARGET"):
                break

    return status

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
        data = yf.download(tickers_to_query, period=TRACKING_PERIOD, progress=False)
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

        yf_ticker = get_yf_ticker(s.get("ticker"))

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

        new_status = resolve_signal(s, df)
        if new_status != s.get("status"):
            changes_made = True
        s["status"] = new_status
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
