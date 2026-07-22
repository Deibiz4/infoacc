import gspread
import json
import os
import datetime
import sys

# Configure stdout/stderr encoding for Windows console compatibility
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass


# --- Configuration ---
SHEET_ID = "1e7xTeS-LMsKgapBLxVTayS6rqcHUgqjyx8-0EWlqG38"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')

# Signal files from different modules
SIGNAL_SOURCES = {
    "Stocks": os.path.join(BASE_DIR, "data", "signals.json"),
    "Crypto": os.path.join(BASE_DIR, "infocryptos", "data", "signals.json"),
    "Forex": os.path.join(BASE_DIR, "infofx", "data", "signals.json")
}

def update_history():
    print("LOG: Starting History Consolidation...")
    
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ Error: {CREDENTIALS_FILE} not found.")
        return False

    try:
        # Authenticate
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_key(SHEET_ID)
        
        # Ensure "Historial" tab exists
        try:
            worksheet = sh.worksheet("Historial")
            print("OK: Found 'Historial' tab.")
        except gspread.WorksheetNotFound:
            print("WARN: 'Historial' tab not found, creating it...")
            worksheet = sh.add_worksheet(title="Historial", rows=1000, cols=10)
            # Add Header
            header = ["ID", "Fecha", "Mercado", "Símbolo", "Tipo", "Entrada", "Stop Loss", "Target", "Contexto", "Notas"]
            worksheet.append_row(header)
            worksheet.format('A1:J1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.8, 'green': 0.8, 'blue': 0.8}})

        # Fetch existing IDs to prevent duplicates
        existing_ids = set(worksheet.col_values(1))
        
        new_rows = []
        
        for market_name, file_path in SIGNAL_SOURCES.items():
            if not os.path.exists(file_path):
                print(f"WARN: File not found for {market_name}: {file_path}")
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                signals = json.load(f)
                
            for s in signals:
                sig_id = s.get("id")
                if sig_id and sig_id not in existing_ids:
                    # Date | Market | Symbol | Type | Entry | SL | TP | Context | Notes
                    row = [
                        sig_id,
                        s.get("date"),
                        market_name,
                        s.get("ticker"),
                        s.get("type"),
                        s.get("entry_price"),
                        s.get("stop_loss"),
                        s.get("target_price"),
                        s.get("context"),
                        s.get("notes")
                    ]
                    new_rows.append(row)
                    existing_ids.add(sig_id)

        if new_rows:
            print(f"LOG: Appending {len(new_rows)} new signals to history...")
            # Use value_input_option='USER_ENTERED' to preserve formatting/number types
            worksheet.append_rows(new_rows, value_input_option='USER_ENTERED')
            print("OK: History updated successfully!")
        else:
            print("INFO: No new signals to add.")
            
        return True

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error updating history: {e}")
        return False

if __name__ == "__main__":
    update_history()
