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

# File Paths (Relative to script execution)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SIGNALS_FILE = os.path.join(DATA_DIR, 'signals.json')
CSV_FILE = os.path.join(DATA_DIR, 'market_scan.csv')

def calculate_indicators(df):
    """Calculate RSI, SMAs, and Volume Avg."""
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
    
    signal = {
        "id": f"{datetime.datetime.now().strftime('%Y%m%d')}_{ticker}",
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "ticker": ticker.replace("-USD", ""),
        "entry_price": round(price, 4),
        "status": "PENDING",
        "notes": ""
    }
    
    # Strategies (Bidirectional for Crypto)

    # ---- LONG STRATEGIES ----

    # 1. RSI Oversold (Value Play)
    if rsi < 35: # Crypto runs hotter/colder
        signal["type"] = "LONG"
        signal["context"] = "VALUE_OVERSOLD"
        signal["target_price"] = round(price * 1.08, 4)
        signal["stop_loss"] = round(price * 0.95, 4)
        signal["notes"] = f"RSI Oversold ({rsi:.1f}). Dip buy opportunity."
        return signal

    # 2. Momentum / Breakout
    elif price > sma50 and rsi > 55 and rsi < 75:
        signal["type"] = "LONG"
        signal["context"] = "MOMENTUM_TREND"
        signal["target_price"] = round(price * 1.10, 4)
        signal["stop_loss"] = round(sma50 * 0.98, 4)
        signal["notes"] = "Above SMA 50 with strong momentum."
        return signal

    # ---- SHORT STRATEGIES ----

    # 3. RSI Overbought (Mean Reversion Short)
    elif rsi > 75: # Higher threshold for crypto's natural volatility
        signal["type"] = "SHORT"
        signal["context"] = "OVERBOUGHT_REJECTION"
        signal["target_price"] = round(price * 0.92, 4)  # target: -8%
        signal["stop_loss"] = round(price * 1.05, 4)     # stop: +5%
        signal["notes"] = f"RSI Overbought ({rsi:.1f}). Mean reversion short opportunity."
        return signal

    # 4. SMA 50 Breakdown (Bearish Momentum)
    elif price < sma50 and rsi < 45:
        signal["type"] = "SHORT"
        signal["context"] = "BREAKDOWN_SHORT"
        signal["target_price"] = round(price * 0.90, 4)  # target: -10%
        signal["stop_loss"] = round(sma50 * 1.02, 4)     # stop: just above SMA50
        signal["notes"] = "Below SMA 50 with bearish pressure. Short momentum."
        return signal

    return None

def scan_market():
    print(f"Scanning {len(TICKERS)} tickers...")
    
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
            if clean_ticker in active_or_pending_tickers:
                print(f"⏭️ Skipping {clean_ticker}: Already has an active or pending signal.")
            else:
                sig = generate_signal(ticker, df)
                if sig:
                    new_signals.append(sig)
            
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
