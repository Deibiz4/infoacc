import gspread
import os

SHEET_ID = "1e7xTeS-LMsKgapBLxVTayS6rqcHUgqjyx8-0EWlqG38"
CREDENTIALS_FILE = "credentials.json"

def test_attributes():
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet("Forex")
        
        print("Testing attributes in Forex tab...")
        ws.update_acell('K1', '=GOOGLEFINANCE("CURRENCY:EURUSD"; "changepct")')
        ws.update_acell('L1', '=GOOGLEFINANCE("CURRENCY:EURUSD"; "high")')
        
        print("Update sent. Now reading values back...")
        import time
        time.sleep(2)
        
        print(f"K1 (changepct): {ws.acell('K1').value}")
        print(f"L1 (high): {ws.acell('L1').value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_attributes()
