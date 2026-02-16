import gspread
import os

SHEET_ID = "1e7xTeS-LMsKgapBLxVTayS6rqcHUgqjyx8-0EWlqG38"
CREDENTIALS_FILE = "credentials.json"

def check_all_tabs():
    try:
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        sh = gc.open_by_key(SHEET_ID)
        for ws in sh.worksheets():
            print(f"--- {ws.title} ---")
            data = ws.get_all_values()
            if not data:
                print("[Empty]")
            else:
                for row in data[:3]:
                    print(row)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_all_tabs()
