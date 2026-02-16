import json
import csv
import os
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
SIGNALS_FILE = os.path.join(DATA_DIR, 'signals.json')
OUTPUT_FILE = os.path.join(DATA_DIR, 'portfolio_tracker.csv')

def load_signals():
    """Load signals from JSON file."""
    if not os.path.exists(SIGNALS_FILE):
        print(f"Error: Signals file not found at {SIGNALS_FILE}")
        return []
    
    with open(SIGNALS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def generate_csv(signals):
    """Generate CSV with Google Sheets formulas."""
    
    # Define CSV headers
    headers = [
        "ID", "Fecha", "Ticker", "Empresa (Google)", "Precio Actual (Google)", 
        "Cambio % (Google)", "Tendencia 1A (Sparkline)", "Entrada Signal", 
        "Stop Loss", "Target", "Estado", "Tipo", "Notas"
    ]
    
    # Prepare rows
    rows = []
    for signal in signals:
        ticker = signal.get('ticker')
        
        # Google Sheets Formulas (using ; as separator for European locale)
        # Note: We use local format formulas as requested
        
        # =GOOGLEFINANCE("TICKER"; "name")
        formula_name = f'=GOOGLEFINANCE("{ticker}"; "name")'
        
        # =GOOGLEFINANCE("TICKER"; "price")
        formula_price = f'=GOOGLEFINANCE("{ticker}"; "price")'
        
        # =GOOGLEFINANCE("TICKER"; "changepct")
        formula_change = f'=GOOGLEFINANCE("{ticker}"; "changepct")'
        
        # =SPARKLINE(GOOGLEFINANCE("TICKER"; "price"; HOY()-365; HOY()))
        # Using TODAY() instead of HOY() because Google Sheets functions effectively in English often, 
        # but if the user's locale is Spanish, they might need HOY(). 
        # However, standard practice for compatibility is usually English function names with ; separator.
        # But per user request/prompt examples: "HOY()". We will use HOY() as requested.
        formula_sparkline = f'=SPARKLINE(GOOGLEFINANCE("{ticker}"; "price"; HOY()-365; HOY()))'
        
        row = [
            signal.get('id'),
            signal.get('date'),
            ticker,
            formula_name,
            formula_price,
            formula_change,
            formula_sparkline,
            str(signal.get('entry_price')).replace('.', ','), # Excel/Sheets often expects comma decimal in certain locales
            str(signal.get('stop_loss')).replace('.', ','),
            str(signal.get('target_price')).replace('.', ','),
            signal.get('status'),
            signal.get('type'),
            signal.get('notes')
        ]
        rows.append(row)
        
    # Write to CSV
    # Using ; as delimiter because that's standard for regions that use comma as decimal separator
    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f, delimiter=';', quoting=csv.QUOTE_MINIMAL)
            writer.writerow(headers)
            writer.writerows(rows)
        print(f"Success: Exported {len(rows)} signals to {OUTPUT_FILE}")
    except Exception as e:
        print(f"Error writing CSV: {e}")

if __name__ == "__main__":
    print("Starting Google Sheets CSV Export...")
    signals = load_signals()
    if signals:
        generate_csv(signals)
    print("Done.")
