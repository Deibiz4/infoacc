import gspread
import os

SHEET_ID = "1e7xTeS-LMsKgapBLxVTayS6rqcHUgqjyx8-0EWlqG38"
CREDENTIALS_FILE = "credentials.json"

def test_separators():
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet("Forex")
        
        print("Testing separators in Forex tab...")
        # Test semicolon (Spanish/European)
        ws.update_acell('H1', '=GOOGLEFINANCE("CURRENCY:EURUSD"; "price")')
        # Test comma (English/Standard)
        ws.update_acell('I1', '=GOOGLEFINANCE("CURRENCY:EURUSD", "price")')
        
        print("Update sent. Now reading values back...")
        import time
        time.sleep(2) # Wait for Sheets to calculate
        
        print(f"H1 (semicolon): {ws.acell('H1').value}")
        print(f"I1 (comma): {ws.acell('I1').value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_separators()
