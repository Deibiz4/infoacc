import os
import datetime
import locale
from bs4 import BeautifulSoup

# Configure locale for Spanish dates
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except:
        print("⚠️ Warning: Spanish locale not found. Dates might be in English.")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.join(BASE_DIR, 'index.html')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')

def get_latest_report():
    """Find the most recent HTML report file."""
    files = [f for f in os.listdir(REPORTS_DIR) if f.startswith('daily_market_report_') and f.endswith('.html')]
    if not files:
        return None
    
    # Sort by date (filename contains date YYYY_MM_DD)
    files.sort(reverse=True)
    return files[0]

def update_hub():
    print("🌐 Updating Web Hub (index.html)...")
    
    if not os.path.exists(INDEX_PATH):
        print(f"❌ Error: {INDEX_PATH} not found.")
        return False

    latest_report_file = get_latest_report()
    if not latest_report_file:
         print("⚠️ No reports found to update index.")
         return False
         
    print(f"📄 Latest Report Found: {latest_report_file}")

    # Parse Date from Filename
    # daily_market_report_2026_02_16.html
    try:
        date_str = latest_report_file.replace('daily_market_report_', '').replace('.html', '')
        report_date = datetime.datetime.strptime(date_str, "%Y_%m_%d")
        formatted_date = report_date.strftime("%d de %B, %Y").title() # "16 De Febrero, 2026"
    except Exception as e:
        print(f"⚠️ Error parsing date: {e}")
        formatted_date = datetime.datetime.now().strftime("%Y-%m-%d")

    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    latest_card = None
    
    # --- 1. Archive Previous Latest Report ---
    # Find the CURRENT "Latest Report" card by ID
    latest_card = soup.find('a', id='latest-report-stock')
            
    if latest_card:
        
        if latest_card and 'daily_market_report' in latest_card['href']:
            old_href = latest_card['href']
            old_title = latest_card.find('span', class_='report-title').text.strip()
            old_date_text = latest_card.find('span', class_='report-date').text.strip()
            
            # Check if this old report is already in the archive to avoid dupes
            archive_list = soup.find('ul', id='archive-stock')
            if archive_list:
                existing_links = [a['href'] for a in archive_list.find_all('a')]
                
                # Only archive if it's NOT the same as the NEW report we are about to set
                # and NOT already in archive
                new_href_relative = f"reports/{latest_report_file}"
                
                if old_href != new_href_relative and old_href not in existing_links:
                    print(f"📦 Archiving previous report: {old_href}")
                    
                    new_item = soup.new_tag('li', attrs={'class': 'archive-item'})
                    
                    link = soup.new_tag('a', href=old_href)
                    
                    date_span = soup.new_tag('span', attrs={'class': 'archive-date'})
                    date_span.string = old_date_text
                    
                    link.append(date_span)
                    link.append(f" {old_title}") # Simple text append for title part
                    
                    new_item.append(link)
                    
                    # Prepend to list
                    archive_list.insert(0, new_item)

    # --- 2. Update Latest Report Section ---
    if latest_card:
        # Update Href
        latest_card['href'] = f"reports/{latest_report_file}"
        
        # Update Date
        date_elem = latest_card.find('span', class_='report-date')
        if date_elem: date_elem.string = formatted_date
        
        # Update Title (Static for now, or extract from Report content if we wanted strictly)
        title_elem = latest_card.find('span', class_='report-title')
        if title_elem: title_elem.string = "Informe Diario - Market Scan & Value"
        
        # Update Summary
        summary_elem = latest_card.find('span', class_='report-summary')
        if summary_elem: 
            summary_elem.string = "Análisis actualizado con datos reales de mercado. Oportunidades Value (RSI) y Momentum detectadas por el escáner."
    else:
        print("⚠️ Warning: Could not find 'Latest Report' card to update.")

    # Save changes
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        f.write(str(soup))
        
    print("✅ Web Hub (index.html) updated successfully.")
    return True

if __name__ == "__main__":
    update_hub()
