import gspread
import os

SHEET_ID = "1e7xTeS-LMsKgapBLxVTayS6rqcHUgqjyx8-0EWlqG38"
CREDENTIALS_FILE = "credentials.json"

def list_worksheets():
    if not os.path.exists(CREDENTIALS_FILE):
        print("❌ Error: credentials.json not found.")
        return
    
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_key(SHEET_ID)
        print(f"✅ Connected to Spreadsheet: {sh.title}")
        print("Worksheets found:")
        for ws in sh.worksheets():
            print(f"- {ws.title} (ID: {ws.id})")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_worksheets()
