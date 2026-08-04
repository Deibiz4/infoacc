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

# Risk concentration limits. These tickers are heavily correlated, so an
# unbounded scan opens dozens of near-identical bets at once (28 in one day in
# July 2026) and the book becomes a single directional wager on the index.
MAX_OPEN_POSITIONS = 10      # total PENDING + ACTIVE at any time
MAX_NEW_SIGNALS_PER_RUN = 4  # new entries admitted per scan

def calculate_indicators(df):
    """Calculate RSI, SMAs, ATR, and Volume Avg."""
    if len(df) < 200:
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
    
    # Avg Volume
    df['Vol_Avg'] = df['Volume'].rolling(window=20).mean()
    
    return df

def generate_signal(ticker, df):
    """Generate high-probability trading signals with ATR risk management & 200 SMA trend filtering."""
    if df.empty or len(df) < 200:
        return None
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    price = float(last_row['Close'])
    volume = float(last_row['Volume'])
    vol_avg = float(last_row['Vol_Avg'])
    rsi = float(last_row['RSI'])
    rsi_prev = float(prev_row['RSI'])
    sma50 = float(last_row['SMA_50'])
    sma200 = float(last_row['SMA_200'])
    atr = float(last_row['ATR']) if not pd.isna(last_row['ATR']) and last_row['ATR'] > 0 else price * 0.02
    
    signal = {
        "id": f"{datetime.datetime.now().strftime('%Y%m%d')}_{ticker}",
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "ticker": ticker,
        "entry_price": round(price, 2),
        "status": "PENDING",
        "notes": ""
    }
    
    high_volume = volume > (vol_avg * 1.15)
    
    # ---- LONG STRATEGIES (MUST BE ABOVE 200 SMA) ----
    if price > sma200:
        # 1. RSI Value Oversold Rebound (Price > 200 SMA & RSI < 33 & RSI Turning Up)
        if rsi < 33 and rsi > rsi_prev:
            stop_dist = max(1.5 * atr, price * 0.02)
            target_dist = stop_dist * 2.5
            signal["type"] = "LONG"
            signal["context"] = "VALUE_OVERSOLD"
            signal["stop_loss"] = round(price - stop_dist, 2)
            signal["target_price"] = round(price + target_dist, 2)
            signal["notes"] = f"Bullish trend value rebound above 200-SMA. RSI Oversold ({rsi:.1f}) turning up. Risk-Reward 1:2.5 (ATR: ${atr:.2f})."
            return signal

        # 2. SMA 50 Volume Breakout (Trading WITH 200 SMA Bullish Trend)
        elif price > sma50 and prev_row['Close'] <= prev_row['SMA_50'] and high_volume:
            stop_dist = max(1.5 * atr, price * 0.025)
            target_dist = stop_dist * 2.66
            signal["type"] = "LONG"
            signal["context"] = "MOMENTUM_BREAKOUT"
            signal["stop_loss"] = round(price - stop_dist, 2)
            signal["target_price"] = round(price + target_dist, 2)
            signal["notes"] = f"SMA 50 High-Volume Breakout above 200 SMA. Volume +{((volume/vol_avg)-1)*100:.0f}% vs avg. Risk-Reward 1:2.66."
            return signal

        # 3. Pullback to SMA 50 in Confirmed Uptrend
        elif price > sma50 and price <= sma50 * 1.018 and rsi > 42 and rsi < 58:
            stop_dist = max(1.4 * atr, (price - sma50) + 1.2 * atr)
            target_dist = stop_dist * 2.5
            signal["type"] = "LONG"
            signal["context"] = "TREND_PULLBACK"
            signal["stop_loss"] = round(price - stop_dist, 2)
            signal["target_price"] = round(price + target_dist, 2)
            signal["notes"] = f"Healthy pullback to 50-SMA support in 200-SMA uptrend. Risk-Reward 1:2.5."
            return signal

    # ---- SHORT STRATEGIES (MUST BE BELOW 200 SMA) ----
    elif price < sma200:
        # 4. RSI Overbought Rejection in Downtrend (Price < 200 SMA & RSI > 67 & RSI Turning Down)
        if rsi > 67 and rsi < rsi_prev:
            stop_dist = max(1.5 * atr, price * 0.02)
            target_dist = stop_dist * 2.5
            signal["type"] = "SHORT"
            signal["context"] = "OVERBOUGHT_REJECTION"
            signal["stop_loss"] = round(price + stop_dist, 2)
            signal["target_price"] = round(price - target_dist, 2)
            signal["notes"] = f"Bearish mean-reversion short rejection below 200-SMA. RSI Overbought ({rsi:.1f}) turning down. Risk-Reward 1:2.5."
            return signal

        # 5. SMA 50 Volume Breakdown (Trading WITH 200 SMA Bearish Trend)
        elif price < sma50 and prev_row['Close'] >= prev_row['SMA_50'] and high_volume:
            stop_dist = max(1.5 * atr, price * 0.025)
            target_dist = stop_dist * 2.66
            signal["type"] = "SHORT"
            signal["context"] = "BREAKDOWN_SHORT"
            signal["stop_loss"] = round(price + stop_dist, 2)
            signal["target_price"] = round(price - target_dist, 2)
            signal["notes"] = f"SMA 50 High-Volume Breakdown below 200 SMA. Volume +{((volume/vol_avg)-1)*100:.0f}% vs avg. Risk-Reward 1:2.66."
            return signal

    return None

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
    room = max(0, MAX_OPEN_POSITIONS - open_positions)
    allowed = min(room, MAX_NEW_SIGNALS_PER_RUN)

    if len(new_signals) <= allowed:
        return new_signals

    ranked = sorted(new_signals, key=signal_rr, reverse=True)
    dropped = len(new_signals) - allowed
    print(
        f"🛑 Risk limit: {open_positions} open, keeping {allowed} of "
        f"{len(new_signals)} new signals (dropped {dropped} by reward/risk)."
    )
    return ranked[:allowed]

def scan_market():
    print(f"Scanning {len(TICKERS)} tickers...")
    
    # Load existing signals to keep history/active state and prevent duplicates
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    existing_signals = []
    blocked_tickers = set()
    if os.path.exists(SIGNALS_FILE):
        try:
            with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
                existing_signals = json.load(f)
                # A ticker is blocked if it has an open position OR was already
                # signalled today. Without the second condition a signal closed
                # by the tracker earlier in the day gets re-emitted on the next
                # run, duplicating the same trade in the P&L.
                blocked_tickers = {
                    s.get("ticker") for s in existing_signals
                    if s.get("status") in ["PENDING", "ACTIVE"] or s.get("date") == today
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
            last_row = df.iloc[-1]
            
            # 1. Generate Signal Logic (Only if ticker has no open or same-day signal)
            if ticker in blocked_tickers:
                print(f"⏭️ Skipping {ticker}: open position or already signalled today.")
            else:
                sig = generate_signal(ticker, df)
                if sig:
                    new_signals.append(sig)
            
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
            print(f"Error processing {ticker}: {e}")
            continue

    # Apply concentration limits before committing. Best reward/risk first, so
    # the cap keeps the strongest setups rather than whichever ticker the loop
    # happened to reach first.
    new_signals = apply_risk_limits(new_signals, existing_signals)

    # Combine existing and new signals
    combined_signals = existing_signals + new_signals
    print(f"Found {len(new_signals)} new signals. Total historical/active signals: {len(combined_signals)}")
    with open(SIGNALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(combined_signals, f, indent=4)
        
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
        
    print(f"Exported Market Scan to {CSV_FILE}")

if __name__ == "__main__":
    scan_market()
