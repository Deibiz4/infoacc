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
    """Calculate RSI, SMAs."""
    if len(df) < 50:
        return df # Not enough data
    
    # SMS
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()
    
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['RSI'] = df['RSI'].fillna(50)
    
    return df

def generate_signal(ticker, df):
    """Generate trading signal based on technical analysis."""
    if df.empty or len(df) < 50:
        return None
        
    last_row = df.iloc[-1]
    
    price = last_row['Close']
    rsi = last_row['RSI']
    sma50 = last_row['SMA_50']
    
    clean_ticker = ticker.replace("=X", "")
    
    signal = {
        "id": f"{datetime.datetime.now().strftime('%Y%m%d')}_{clean_ticker}",
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "ticker": clean_ticker,
        "entry_price": round(price, 5),
        "status": "PENDING",
        "notes": ""
    }
    
    # Strategies (Forex)
    # 1. RSI Extremes
    if rsi < 30: 
        signal["type"] = "LONG"
        signal["context"] = "OVERSOLD_BOUNCE"
        signal["target_price"] = round(price * 1.005, 5) # Smaller targets for FX
        signal["stop_loss"] = round(price * 0.998, 5)
        signal["notes"] = f"RSI Oversold ({rsi:.1f}). Reversion play."
        return signal
    elif rsi > 70:
        signal["type"] = "SHORT"
        signal["context"] = "OVERBOUGHT_REJECTION"
        signal["target_price"] = round(price * 0.995, 5)
        signal["stop_loss"] = round(price * 1.002, 5)
        signal["notes"] = f"RSI Overbought ({rsi:.1f}). Reversion play."
        return signal
        
    # 2. Trend Following
    elif price > sma50 and rsi > 55 and rsi < 65:
        signal["type"] = "LONG"
        signal["context"] = "TREND_CONTINUATION"
        signal["target_price"] = round(price * 1.008, 5)
        signal["stop_loss"] = round(sma50, 5)
        signal["notes"] = "Above SMA 50 with steady momentum."
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
