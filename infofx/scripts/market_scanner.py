import yfinance as yf
import pandas as pd
import json
import os
import datetime
import time

# --- Configuration ---
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
SIGNALS_FILE = os.path.join(DATA_DIR, 'signals.json')
# --- CONFIGURATION (FOREX) ---
TICKERS = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", 
    "AUDUSD=X", "USDCAD=X", "NZDUSD=X", "EURGBP=X",
    "EURJPY=X", "GBPJPY=X", "GC=F", "SI=F"
]
MAX_HISTORY = "1y"

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
    """Generate Forex trading signal with ATR risk management & 200 SMA trend filtering."""
    if df.empty or len(df) < 50:
        return None
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    price = float(last_row['Close'])
    rsi = float(last_row['RSI'])
    rsi_prev = float(prev_row['RSI'])
    sma50 = float(last_row['SMA_50']) if not pd.isna(last_row['SMA_50']) else price
    sma200 = float(last_row['SMA_200']) if not pd.isna(last_row['SMA_200']) else sma50
    atr = float(last_row['ATR']) if not pd.isna(last_row['ATR']) and last_row['ATR'] > 0 else price * 0.005
    
    clean_ticker = ticker.replace("=X", "")
    
    signal = {
        "id": f"{datetime.datetime.now().strftime('%Y%m%d')}_{clean_ticker}",
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "ticker": clean_ticker,
        "entry_price": round(price, 5),
        "status": "PENDING",
        "notes": ""
    }
    
    # ---- LONG STRATEGIES (MUST BE ABOVE 200 SMA OR 50 SMA) ----
    if price > sma200 or price > sma50:
        # 1. RSI Oversold Bounce in Bullish Trend
        if rsi < 32 and rsi > rsi_prev:
            stop_dist = max(1.5 * atr, price * 0.003)
            target_dist = stop_dist * 2.5
            signal["type"] = "LONG"
            signal["context"] = "OVERSOLD_BOUNCE"
            signal["stop_loss"] = round(price - stop_dist, 5)
            signal["target_price"] = round(price + target_dist, 5)
            signal["notes"] = f"Forex bullish dip bounce. RSI ({rsi:.1f}) turning up. Risk-Reward 1:2.5 (ATR: {atr:.5f})."
            return signal

        # 2. Trend Continuation
        elif price > sma50 and rsi > 53 and rsi < 66 and prev_row['RSI'] <= 53:
            stop_dist = max(1.4 * atr, price * 0.0025)
            target_dist = stop_dist * 2.5
            signal["type"] = "LONG"
            signal["context"] = "TREND_CONTINUATION"
            signal["stop_loss"] = round(price - stop_dist, 5)
            signal["target_price"] = round(price + target_dist, 5)
            signal["notes"] = f"Forex trend continuation above 50-SMA. Risk-Reward 1:2.5."
            return signal

    # ---- SHORT STRATEGIES (MUST BE BELOW 200 SMA OR 50 SMA) ----
    if price < sma200 or price < sma50:
        # 3. RSI Overbought Rejection in Bearish Trend
        if rsi > 68 and rsi < rsi_prev:
            stop_dist = max(1.5 * atr, price * 0.003)
            target_dist = stop_dist * 2.5
            signal["type"] = "SHORT"
            signal["context"] = "OVERBOUGHT_REJECTION"
            signal["stop_loss"] = round(price + stop_dist, 5)
            signal["target_price"] = round(price - target_dist, 5)
            signal["notes"] = f"Forex overbought short rejection. RSI ({rsi:.1f}) turning down. Risk-Reward 1:2.5."
            return signal

        # 4. Bearish Trend Breakdown
        elif price < sma50 and rsi < 47 and prev_row['RSI'] >= 47:
            stop_dist = max(1.4 * atr, price * 0.0025)
            target_dist = stop_dist * 2.5
            signal["type"] = "SHORT"
            signal["context"] = "BREAKDOWN_SHORT"
            signal["stop_loss"] = round(price + stop_dist, 5)
            signal["target_price"] = round(price - target_dist, 5)
            signal["notes"] = f"Forex breakdown below 50-SMA. Risk-Reward 1:2.5."
            return signal

    return None

def scan_market():
    print(f"Scanning {len(TICKERS)} pairs...")
    
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

    # Load existing signals to keep history/active state and prevent duplicates
    existing_signals = []
    active_or_pending_tickers = set()
    if os.path.exists(SIGNALS_FILE):
        try:
            with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
                existing_signals = json.load(f)
                active_or_pending_tickers = {
                    s.get("ticker") for s in existing_signals 
                    if s.get("status") in ["PENDING", "ACTIVE"]
                }
        except Exception as e:
            print(f"⚠️ Error loading existing signals: {e}")
            existing_signals = []

    new_signals = []
    market_data_rows = []
    
    # Bulk download
    data = yf.download(TICKERS, period="1y", group_by='ticker', progress=True)
    
    for ticker in TICKERS:
        try:
            # Handle multi-index columns from bulk download
            if len(TICKERS) > 1:
                df = data[ticker].copy()
            else:
                df = data.copy()
            
            if df.empty:
                continue
                
            # Calc Indicators
            df = calculate_indicators(df)
            
            # Normalize ticker names
            clean_ticker = ticker.replace("=X", "")
            if ticker == "GC=F":
                clean_ticker = "GOLD"
            elif ticker == "SI=F":
                clean_ticker = "SILVER"

            # 1. Generate Signal Logic (Only if ticker has no active/pending signal)
            if clean_ticker in active_or_pending_tickers:
                print(f"⏭️ Skipping {clean_ticker}: Already has an active or pending signal.")
            else:
                sig = generate_signal(ticker, df)
                if sig:
                    new_signals.append(sig)
            
            # 2. Prepare CSV Row (Google Sheets formula)
            # Yahoo: EURUSD=X -> Google: CURRENCY:EURUSD
            # Gold: GC=F -> CURRENCY:XAUUSD
            # Silver: SI=F -> CURRENCY:XAGUSD
            
            sheet_ticker = f"CURRENCY:{clean_ticker}"
            if clean_ticker == "GOLD":
                sheet_ticker = "CURRENCY:XAUUSD"
            elif clean_ticker == "SILVER":
                sheet_ticker = "CURRENCY:XAGUSD"
            
            # Pair | Price | Change% | Sparkline | High | Low | Sentiment
            
            # Use simplified formulas as requested by user
            # Static fallbacks for attributes that Google Finance might fail to provide for currencies
            last_price = round(df.iloc[-1]['Close'], 5)
            change_pct = round((df.iloc[-1]['Close'] / df.iloc[-2]['Close'] - 1), 4) if len(df) > 1 else 0
            
            csv_row = [
                clean_ticker,
                f'=GOOGLEFINANCE("{sheet_ticker}")',
                change_pct, # Static fallback for changepct
                f'=SPARKLINE(GOOGLEFINANCE("{sheet_ticker}"; "price"; HOY()-30; HOY()))',
                f'=GOOGLEFINANCE("{sheet_ticker}"; "high")',
                f'=GOOGLEFINANCE("{sheet_ticker}"; "low")',
                f'=IF("{sheet_ticker}" <> ""; IF(INDEX(GOOGLEFINANCE("{sheet_ticker}");1) > 0; "Bull"; "Bear"); "-")'
            ]
            
            market_data_rows.append(csv_row)
            
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            continue

    # Combine existing and new signals
    combined_signals = existing_signals + new_signals
    print(f"Found {len(new_signals)} new signals. Total historical/active signals: {len(combined_signals)}")
    with open(SIGNALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(combined_signals, f, indent=4)
        
    # Save CSV for Sheets
    headers = [
        "Pair", "Price", "Change", "30d Trend", "High", "Low", "Sentiment"
    ]
    
    import csv
    with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        writer.writerows(market_data_rows)
        
    print(f"Exported Market Scan to {CSV_FILE}")

if __name__ == "__main__":
    scan_market()
