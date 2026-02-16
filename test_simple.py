import gspread
import os

SHEET_ID = "1e7xTeS-LMsKgapBLxVTayS6rqcHUgqjyx8-0EWlqG38"
CREDENTIALS_FILE = "credentials.json"

def test_simple_formula():
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet("Forex")
        
        print("Testing simple formula in Forex tab...")
        # User suggested format
        ws.update_acell('J1', '=GOOGLEFINANCE("CURRENCY:EURUSD")')
        
        print("Update sent. Now reading value back...")
        import time
        time.sleep(2)
        
        print(f"J1 (simple): {ws.acell('J1').value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple_formula()
