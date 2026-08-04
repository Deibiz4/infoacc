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
TRACKING_PERIOD = "3mo"

# Sessions an unfilled signal waits for its entry before being written off. The
# pullback variant only fills about 40% of the time, and without an expiry the
# rest would hold concentration slots forever. Backtested across 5, 10, 20, 40
# and unlimited; results were stable, so this is not a tuned number.
EXPIRY_SESSIONS = 10

# Hourly bars are used to decide outcomes when available. Yahoo caps intraday
# history at 730 days, which comfortably covers any open signal given the
# expiry above. Falls back to daily bars per ticker when intraday is missing.
INTRADAY_PERIOD = "60d"
INTRADAY_INTERVAL = "60m"


def fetch_intraday(tickers):
    """Hourly bars per ticker; empty dict if the download fails entirely."""
    try:
        raw = yf.download(tickers, period=INTRADAY_PERIOD,
                          interval=INTRADAY_INTERVAL, group_by="ticker",
                          progress=False, auto_adjust=False)
    except Exception as e:
        print(f"⚠️ Intraday download failed, falling back to daily bars: {e}")
        return {}
    if raw is None or raw.empty:
        return {}

    frames = {}
    for t in tickers:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                level = 0 if t in raw.columns.get_level_values(0) else 1
                df = raw.xs(t, level=level, axis=1)
            else:
                df = raw
            df = df.dropna(subset=["High", "Low"])
        except Exception:
            continue
        if df.empty:
            continue
        if getattr(df.index, "tz", None) is not None:
            df = df.copy()
            df.index = df.index.tz_localize(None)
        frames[t] = df
    return frames

def get_yf_ticker(ticker):
    return YF_TICKER_MAPPING.get(ticker, ticker)

def resolve_intraday(s, bars, start_status=None, expiry=EXPIRY_SESSIONS):
    """Resolve a signal against hourly bars, in chronological order.

    A daily bar hides the order of events: when price touches both the stop and
    the target in one session, the daily engine has to guess, and guesses the
    stop. Hourly bars remove most of that guessing — whichever level price
    actually reached first decides. Ambiguity survives only inside a single
    hour, where the stop is still assumed.
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

    long = s.get("type", "LONG").upper() == "LONG"
    future = bars[bars.index.normalize() > signal_day]
    if future.empty:
        return status

    seen_days = set()
    for ts, high, low in zip(future.index, future["High"].to_numpy(),
                             future["Low"].to_numpy()):
        if pd.isna(high) or pd.isna(low):
            continue
        high, low = float(high), float(low)
        seen_days.add(ts.date())

        if status == "PENDING":
            if low <= entry <= high:
                status = "ACTIVE"
            elif expiry and len(seen_days) > expiry:
                return "EXPIRED"

        if status == "ACTIVE":
            if long:
                if low <= stop:
                    return "HIT_STOP"
                if high >= target:
                    return "HIT_TARGET"
            else:
                if high >= stop:
                    return "HIT_STOP"
                if low <= target:
                    return "HIT_TARGET"

    return status


def resolve_signal(s, df, start_status=None, expiry=EXPIRY_SESSIONS):
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

    sessions = 0
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

        # Only sessions the signal actually waited unfilled count towards expiry.
        sessions += 1
        if expiry and status == "PENDING" and sessions >= expiry:
            return "EXPIRED"

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

    hourly = fetch_intraday(tickers_to_query)
    print(f"🕐 Hourly bars available for {len(hourly)}/{len(tickers_to_query)} tickers; "
          f"the rest resolve on daily bars.")

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

        # Prefer hourly bars: they show which level price reached first, so the
        # outcome is observed rather than assumed.
        bars = hourly.get(yf_ticker)
        if bars is not None and not bars.empty:
            new_status = resolve_intraday(s, bars)
        else:
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
