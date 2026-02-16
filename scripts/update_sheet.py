import gspread
import csv
import os
import time

# --- Configuration ---
# Sheet ID from user: 
# https://docs.google.com/spreadsheets/d/1e7xTeS-LMsKgapBLxVTayS6rqcHUgqjyx8-0EWlqG38/edit?gid=0#gid=0
SHEET_ID = "1e7xTeS-LMsKgapBLxVTayS6rqcHUgqjyx8-0EWlqG38" 

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'credentials.json')
CSV_FILE = os.path.join(BASE_DIR, 'data', 'market_scan.csv')

def update_google_sheet():
    print("☁️ Connecting to Google Sheets...")
    
    if not os.path.exists(CREDENTIALS_FILE):
        print("❌ Error: credentials.json not found.")
        return False
        
    try:
        # Authenticate
        gc = gspread.service_account(filename=CREDENTIALS_FILE)
        
        # Open Sheet
        try:
             sh = gc.open_by_key(SHEET_ID)
        except Exception:
             print("⚠️ open_by_key failed, trying open_by_url...")
             sh = gc.open_by_url(f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
             
        worksheet = sh.sheet1 # Default first sheet
        
        print(f"✅ Connected to: {sh.title}")
        
        # Read CSV Data
        if not os.path.exists(CSV_FILE):
             print(f"❌ Error: {CSV_FILE} not found. Run market scanner first.")
             return False
             
        with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=';')
            csv_data = list(reader)
            
        if not csv_data:
            print("⚠️ CSV is empty.")
            return False

        # Prepare Data for Sheets
        # gspread expects a list of lists.
        # Check matching columns. The CSV has formulas starting with "="
        # gspread generally handles formulas correctly if input as raw string.
        
        # Clear existing content (optional, or just overwrite range)
        print("🧹 Clearing old data...")
        worksheet.clear()
        
        # Update
        print(f"📝 Writing {len(csv_data)} rows to sheet...")
        # value_input_option='USER_ENTERED' forces Sheets to parse formulas
        worksheet.update(range_name='A2', values=csv_data[1:], value_input_option='USER_ENTERED')
        
        # Write header separately (optional, but good for safety)
        worksheet.update(range_name='A1', values=[csv_data[0]], value_input_option='RAW')
        
        # Optional: Format Header
        worksheet.format('A1:N1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})
        
        print("✅ Google Sheet Updated Successfully!")
        return True
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error updating sheet: {e}")
        return False

if __name__ == "__main__":
    update_google_sheet()
