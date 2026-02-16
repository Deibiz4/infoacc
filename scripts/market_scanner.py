import yfinance as yf
import pandas as pd
import json
import os
import datetime
import time

# --- Configuration ---
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
SIGNALS_FILE = os.path.join(DATA_DIR, 'signals.json')
CSV_FILE = os.path.join(DATA_DIR, 'market_scan.csv')

# Expanded Ticker List (Tech, Blue Chips, Growth)
TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
    "AMD", "INTC", "QCOM", "AVGO", "TXN", "MU", "ARM", "SMCI",
    "JPM", "BAC", "V", "MA", "AXP", "GS",
    "KO", "PEP", "MCD", "WMT", "COST", "PG", "JNJ", "PFE", "LLY",
    "XOM", "CVX", "COP", "SLB",
    "DIS", "NFLX", "SPOT", "UBER", "ABNB", "BKNG",
    "CAT", "DE", "BA", "LMT", "GE",
    "PLTR", "SOFI", "COIN", "MARA", "RIOT", "DKNG"
]

def calculate_indicators(df):
    """Calculate RSI, SMAs, and Volume Avg."""
    if len(df) < 200:
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
    
    # Avg Volume
    df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
    
    return df

def generate_signal(ticker, df):
    """Generate trading signal based on technical analysis."""
    if df.empty or len(df) < 50:
        return None
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    price = last_row['Close']
    rsi = last_row['RSI']
    sma50 = last_row['SMA_50']
    
    signal = {
        "id": f"{datetime.datetime.now().strftime('%Y%m%d')}_{ticker}",
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "ticker": ticker,
        "entry_price": round(price, 2),
        "status": "PENDING",
        "notes": ""
    }
    
    # --- Strategies ---
    
    # 1. RSI Oversold (Value Play)
    if rsi < 30:
        signal["type"] = "LONG"
        signal["context"] = "VALUE_OVERSOLD"
        signal["target_price"] = round(price * 1.05, 2)
        signal["stop_loss"] = round(price * 0.97, 2)
        signal["notes"] = f"RSI Oversold ({rsi:.1f}). Rebound potential."
        return signal
        
    # 2. SMA 50 Breakout (Momentum)
    elif price > sma50 and prev_row['Close'] <= prev_row['SMA_50']:
        signal["type"] = "LONG"
        signal["context"] = "MOMENTUM_BREAKOUT"
        signal["target_price"] = round(price * 1.08, 2)
        signal["stop_loss"] = round(price * 0.95, 2)
        signal["notes"] = "SMA 50 Breakout. Bullish momentum."
        return signal
    
    # 3. Pullback to SMA 50 (Trend Continuation)
    elif price > sma50 and price < sma50 * 1.02 and rsi > 40 and rsi < 60:
        signal["type"] = "LONG"
        signal["context"] = "TREND_PULLBACK"
        signal["target_price"] = round(price * 1.06, 2)
        signal["stop_loss"] = round(sma50 * 0.98, 2)
        signal["notes"] = "Pullback to SMA 50 support."
        return signal

    return None

def scan_market():
    print(f"🔍 Scanning {len(TICKERS)} tickers...")
    
    signals = []
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
            last_row = df.iloc[-1]
            
            # 1. Generate Signal Logic
            sig = generate_signal(ticker, df)
            if sig:
                signals.append(sig)
            
            # 2. Prepare CSV Row (Google Sheets format)
            # Ticker;Name;Price;Change%;Sparkline;Entry;Target;Stop;Date;Status;Type;Notes
            
            # Formulas
            f_name = f'=GOOGLEFINANCE("{ticker}"; "name")'
            f_price = f'=GOOGLEFINANCE("{ticker}"; "price")'
            f_change = f'=GOOGLEFINANCE("{ticker}"; "changepct")/100' # Sheets expects % format
            f_spark = f'=SPARKLINE(GOOGLEFINANCE("{ticker}"; "price"; HOY()-30; HOY()))'
            
            # Real Data for CSV (Static fallback or hybrid)
            # User wants: Ticker, Name, Price, Var%, Trend(30d), SMA50, Range 6M, Position, MarketCap, EPS, PE, Beta, Sector, Industry
            
            # Using the formulae requested by user
            # Ticker	Nombre	Precio	Var %	Tendencia (30d)	SMA 50 (Medio)	Rango 6 Meses	Donde esta hoy?	Market Cap	EPS (Beneficio/Acción)	P/E (PER)	Beta	Sector	Industria

            csv_row = [
                ticker,
                # Formulas (ensure semicolon for Spanish locale)
                f'=GOOGLEFINANCE("{ticker}"; "name")',
                f'=GOOGLEFINANCE("{ticker}")', # Simplified price as requested for FX, good for consistency
                f'=GOOGLEFINANCE("{ticker}"; "changepct")', # Removed /100 if they format as % in sheet, or keep it if they prefer
                f'=SPARKLINE(GOOGLEFINANCE("{ticker}"; "price"; HOY()-30; HOY()))',
                f'=PROMEDIO(INDEX(GOOGLEFINANCE("{ticker}"; "price"; HOY()-80; HOY());;2))',
                f'=SPARKLINE({{GOOGLEFINANCE("{ticker}";"price"); MIN(INDEX(GOOGLEFINANCE("{ticker}"; "price"; HOY()-180; HOY());;2)); MAX(INDEX(GOOGLEFINANCE("{ticker}"; "price"; HOY()-180; HOY());;2))}};{{"charttype"\\"bar";"max"\\MAX(INDEX(GOOGLEFINANCE("{ticker}"; "price"; HOY()-180; HOY());;2));"min"\\MIN(INDEX(GOOGLEFINANCE("{ticker}"; "price"; HOY()-180; HOY());;2));"color1"\\"blue"}})',
                f'=SI(GOOGLEFINANCE("{ticker}"; "price") > PROMEDIO(MAX(INDEX(GOOGLEFINANCE("{ticker}"; "price"; HOY()-180; HOY());;2)); MIN(INDEX(GOOGLEFINANCE("{ticker}"; "price"; HOY()-180; HOY());;2))); "Zona Alta"; "Zona Baja")',
                f'=GOOGLEFINANCE("{ticker}"; "marketcap")',
                f'=GOOGLEFINANCE("{ticker}"; "eps")',
                f'=GOOGLEFINANCE("{ticker}"; "pe")',
                f'=GOOGLEFINANCE("{ticker}"; "beta")',
                f'=IFERROR(INDEX(IMPORTXML("https://finance.yahoo.com/quote/"&"{ticker}","//span[text()=\'Sector(s)\']/following-sibling::span");1);"-")',
                f'=IFERROR(INDEX(IMPORTXML("https://finance.yahoo.com/quote/"&"{ticker}","//span[text()=\'Industry\']/following-sibling::span");1);"-")'
            ]
            
            market_data_rows.append(csv_row)
            
        except Exception as e:
            print(f"⚠️ Error processing {ticker}: {e}")
            continue

    # Save Signals JSON
    print(f"✅ Found {len(signals)} signals.")
    with open(SIGNALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(signals, f, indent=4)
        
    # Save CSV for Sheets
    headers = [
        "Ticker", "Nombre", "Precio", "Var %", "Tendencia (30d)", "SMA 50 (Medio)", 
        "Rango 6 Meses", "Donde esta hoy?", "Market Cap", "EPS", "P/E", "Beta", "Sector", "Industria"
    ]
    
    import csv
    with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)
        writer.writerow(headers)
        writer.writerows(market_data_rows)
        
    print(f"✅ Exported Market Scan to {CSV_FILE}")

if __name__ == "__main__":
    scan_market()
