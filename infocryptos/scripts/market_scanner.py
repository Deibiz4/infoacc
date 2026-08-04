import yfinance as yf
import pandas as pd
import json
import os
import datetime
import time

# --- Configuration ---
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
SIGNALS_FILE = os.path.join(DATA_DIR, 'signals.json')
# --- CONFIGURATION (CRYPTO) ---
TICKERS = [
    "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
    "ADA-USD", "DOGE-USD", "AVAX-USD", "DOT-USD", "LINK-USD",
    "TRX-USD", "NEAR-USD", "SHIB-USD", "LTC-USD", "BCH-USD"
]
MAX_HISTORY = "1y"

# Risk concentration limits. Crypto is the most correlated universe here — most
# alts track BTC — so the caps are tighter than for stocks.
MAX_OPEN_POSITIONS = 5       # per entry mode
MAX_NEW_SIGNALS_PER_RUN = 2  # per entry mode

PRICE_DECIMALS = 4

# File Paths (Relative to script execution)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SIGNALS_FILE = os.path.join(DATA_DIR, 'signals.json')
CSV_FILE = os.path.join(DATA_DIR, 'market_scan.csv')

def calculate_indicators(df):
    """Calculate RSI, SMAs, and ATR."""
    if len(df) < 50:
        return df # Not enough data
    
    # SMAs
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50)
    
    # ATR (14)
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    return df

def generate_signal(ticker, df):
    """Generate trading signal based on ATR risk management & 200 SMA trend filtering."""
    if df.empty or len(df) < 50:
        return None
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    price = float(last_row['Close'])
    rsi = float(last_row['RSI'])
    rsi_prev = float(prev_row['RSI'])
    sma50 = float(last_row['SMA_50']) if not pd.isna(last_row['SMA_50']) else price
    sma200 = float(last_row['SMA_200']) if not pd.isna(last_row['SMA_200']) else sma50
    atr = float(last_row['ATR']) if not pd.isna(last_row['ATR']) and last_row['ATR'] > 0 else price * 0.04
    
    signal = {
        "id": f"{datetime.datetime.now().strftime('%Y%m%d')}_{ticker}",
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "ticker": ticker.replace("-USD", ""),
        "entry_price": round(price, 4),
        "status": "PENDING",
        "notes": ""
    }
    
    # ---- LONG STRATEGIES (MUST BE ABOVE 200 SMA OR 50 SMA) ----
    if price > sma200 or price > sma50:
        # 1. RSI Oversold Rebound in Bullish Context
        if rsi < 36 and rsi > rsi_prev:
            stop_dist = max(1.8 * atr, price * 0.04)
            target_dist = stop_dist * 2.5
            signal["type"] = "LONG"
            signal["context"] = "VALUE_OVERSOLD"
            signal["stop_loss"] = round(price - stop_dist, 4)
            signal["target_price"] = round(price + target_dist, 4)
            signal["notes"] = f"Crypto bullish dip rebound. RSI ({rsi:.1f}) turning up. Risk-Reward 1:2.5 (ATR: ${atr:.4g})."
            return signal

        # 2. Strong Momentum Trend
        elif price > sma50 and rsi > 54 and rsi < 72 and prev_row['RSI'] <= 54:
            stop_dist = max(1.6 * atr, price * 0.035)
            target_dist = stop_dist * 2.6
            signal["type"] = "LONG"
            signal["context"] = "MOMENTUM_TREND"
            signal["stop_loss"] = round(price - stop_dist, 4)
            signal["target_price"] = round(price + target_dist, 4)
            signal["notes"] = f"Bullish momentum breakout above 50-SMA. Risk-Reward 1:2.6."
            return signal

    # ---- SHORT STRATEGIES (MUST BE BELOW 200 SMA OR 50 SMA) ----
    if price < sma200 or price < sma50:
        # 3. RSI Overbought Rejection in Bearish Context
        if rsi > 68 and rsi < rsi_prev:
            stop_dist = max(1.8 * atr, price * 0.04)
            target_dist = stop_dist * 2.5
            signal["type"] = "SHORT"
            signal["context"] = "OVERBOUGHT_REJECTION"
            signal["stop_loss"] = round(price + stop_dist, 4)
            signal["target_price"] = round(price - target_dist, 4)
            signal["notes"] = f"Crypto overbought short rejection. RSI ({rsi:.1f}) turning down. Risk-Reward 1:2.5."
            return signal

        # 4. SMA 50 Breakdown (Bearish Momentum)
        elif price < sma50 and rsi < 44 and prev_row['RSI'] >= 44:
            stop_dist = max(1.6 * atr, price * 0.035)
            target_dist = stop_dist * 2.6
            signal["type"] = "SHORT"
            signal["context"] = "BREAKDOWN_SHORT"
            signal["stop_loss"] = round(price + stop_dist, 4)
            signal["target_price"] = round(price - target_dist, 4)
            signal["notes"] = f"Bearish momentum breakdown below 50-SMA. Risk-Reward 1:2.6."
            return signal

    return None

def signal_mode(s):
    """Entry mode of a stored signal. Signals predating modes are baseline."""
    return s.get("mode", "baseline")

def make_stop_hold(sig):
    """Derive the pullback variant of a signal, or None if it degenerates.

    Enter at the original stop instead of the setup close, one risk unit
    better, keeping the original target. Risk distance is unchanged, so
    reward/risk rises and the break-even win rate falls. Runs alongside the
    baseline signal so the two can be compared on live results. See
    scripts/backtest.py.
    """
    try:
        entry = float(sig["entry_price"])
        stop = float(sig["stop_loss"])
        target = float(sig["target_price"])
    except (KeyError, TypeError, ValueError):
        return None

    risk = abs(entry - stop)
    if risk <= abs(entry) * 0.001:
        return None

    long = sig.get("type") == "LONG"
    new_entry = stop
    new_stop = stop - risk if long else stop + risk

    if long and not (new_stop < new_entry < target):
        return None
    if not long and not (new_stop > new_entry > target):
        return None

    variant = dict(sig)
    variant["id"] = f"{sig['id']}_SH"
    variant["mode"] = "stop_hold"
    variant["entry_price"] = round(new_entry, PRICE_DECIMALS)
    variant["stop_loss"] = round(new_stop, PRICE_DECIMALS)
    variant["target_price"] = round(target, PRICE_DECIMALS)
    variant["notes"] = (
        f"Pullback entry at the baseline stop ({new_entry:.4g}), original target "
        f"held. Paired with {sig['id']}."
    )
    return variant

def signal_rr(s):
    """Reward/risk of a candidate signal, 0 if undefined."""
    try:
        risk = abs(float(s["entry_price"]) - float(s["stop_loss"]))
        return abs(float(s["target_price"]) - float(s["entry_price"])) / risk if risk else 0.0
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return 0.0

def apply_risk_limits(new_signals, existing_signals):
    """Trim a scan's candidates down to the concentration limits."""
    open_positions = sum(
        1 for s in existing_signals if s.get("status") in ("PENDING", "ACTIVE")
    )
    allowed = min(max(0, MAX_OPEN_POSITIONS - open_positions), MAX_NEW_SIGNALS_PER_RUN)

    if len(new_signals) <= allowed:
        return new_signals

    ranked = sorted(new_signals, key=signal_rr, reverse=True)
    print(
        f"🛑 Risk limit: {open_positions} open, keeping {allowed} of "
        f"{len(new_signals)} new signals (dropped {len(new_signals) - allowed} by reward/risk)."
    )
    return ranked[:allowed]

def scan_market():
    print(f"Scanning {len(TICKERS)} tickers...")
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Load existing signals to keep history/active state and prevent duplicates
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    existing_signals = []
    # Blocking is per entry mode: the baseline and the pullback variant of the
    # same setup are different trades and must not shut each other out.
    blocked = {"baseline": set(), "stop_hold": set()}
    if os.path.exists(SIGNALS_FILE):
        try:
            with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
                existing_signals = json.load(f)
                # A ticker is blocked if it has an open position OR was already
                # signalled today. Without the second condition a signal closed
                # by the tracker earlier in the day gets re-emitted on the next
                # run, duplicating the same trade in the P&L.
                for s in existing_signals:
                    if s.get("status") in ["PENDING", "ACTIVE"] or s.get("date") == today:
                        blocked.setdefault(signal_mode(s), set()).add(s.get("ticker"))
        except Exception as e:
            print(f"⚠️ Error loading existing signals: {e}")
            existing_signals = []

    candidates = {"baseline": [], "stop_hold": []}
    market_data_rows = []
    
    # Bulk download for speed
    data = yf.download(TICKERS, period="1y", group_by='ticker', progress=True)
    
    for ticker in TICKERS:
        try:
            df = data[ticker].copy()
            
            if df.empty:
                continue
                
            # Calc Indicators
            df = calculate_indicators(df)
            
            # 1. Generate Signal Logic (Only if ticker has no active/pending signal)
            clean_ticker = ticker.replace("-USD", "")
            sig = generate_signal(ticker, df) if (
                clean_ticker not in blocked["baseline"]
                or clean_ticker not in blocked["stop_hold"]
            ) else None
            if sig:
                sig["mode"] = "baseline"
                if clean_ticker not in blocked["baseline"]:
                    candidates["baseline"].append(sig)
                variant = make_stop_hold(sig)
                if variant and clean_ticker not in blocked["stop_hold"]:
                    candidates["stop_hold"].append(variant)
            elif clean_ticker in blocked["baseline"] and clean_ticker in blocked["stop_hold"]:
                print(f"⏭️ Skipping {clean_ticker}: open position or already signalled today.")
            
            # 2. Prepare CSV Row (Google Sheets formula)
            # Use "CURRENCY:BTCUSD" for Google Finance
            sheet_ticker = f"CURRENCY:{clean_ticker}USD"
            
            # Adapted Columns for Crypto
            # Ticker | Price | 24h Change | 7d Trend | Market Cap | Volume | Sentiment
            
            last_price = round(df.iloc[-1]['Close'], 2)
            change_pct = round((df.iloc[-1]['Close'] / df.iloc[-2]['Close'] - 1), 4) if len(df) > 1 else 0
            
            csv_row = [
                clean_ticker,
                f'=GOOGLEFINANCE("{sheet_ticker}")',
                change_pct, # Static fallback
                f'=SPARKLINE(GOOGLEFINANCE("{sheet_ticker}"; "price"; HOY()-7; HOY()))',
                f'=GOOGLEFINANCE("{sheet_ticker}"; "marketcap")',
                f'=GOOGLEFINANCE("{sheet_ticker}"; "volume")',
                f'=IF("{sheet_ticker}" <> ""; "Bull"; "Bear")' # Simplified logic
            ]
            
            market_data_rows.append(csv_row)
            
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue

    # Each mode is capped against its own book.
    new_signals = []
    for mode, cands in candidates.items():
        if not cands:
            continue
        book = [s for s in existing_signals if signal_mode(s) == mode]
        admitted = apply_risk_limits(cands, book)
        print(f"   {mode}: {len(admitted)} admitted of {len(cands)} candidates.")
        new_signals.extend(admitted)

    # Combine existing and new signals
    combined_signals = existing_signals + new_signals
    print(f"Found {len(new_signals)} new signals. Total historical/active signals: {len(combined_signals)}")
    with open(SIGNALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(combined_signals, f, indent=4)
        
    # Save CSV for Sheets
    headers = [
        "Coin", "Price", "24h Change", "7d Trend", "Market Cap", "Volume", "Sentiment"
    ]
    
    import csv
    with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        writer.writerows(market_data_rows)
        
    print(f"Exported Market Scan to {CSV_FILE}")

if __name__ == "__main__":
    scan_market()
