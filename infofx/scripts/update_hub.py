import os
import datetime
import locale
from bs4 import BeautifulSoup
import sys

# Configure stdout/stderr encoding for Windows console compatibility
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    pass

# Configure locale for Spanish dates
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except:
        print("⚠️ Warning: Spanish locale not found. Dates might be in English.")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_PATH = os.path.abspath(os.path.join(BASE_DIR, '..', 'index.html'))
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
RELATIVE_REPORT_PATH = "infofx/reports"

def get_all_reports():
    """Find all HTML report files, sorted descending by date."""
    if not os.path.exists(REPORTS_DIR):
        return []
    files = [f for f in os.listdir(REPORTS_DIR) if f.startswith('forex_market_report_') and f.endswith('.html')]
    # Sort descending
    files.sort(reverse=True)
    return files

def update_hub():
    print(f"🌐 Updating Web Hub Control ({INDEX_PATH})...")
    
    if not os.path.exists(INDEX_PATH):
        print(f"❌ Error: {INDEX_PATH} not found.")
        return False

    all_reports = get_all_reports()
    if not all_reports:
         print("⚠️ No reports found to update index.")
         return False
         
    latest_report_file = all_reports[0]
    print(f"📄 Latest Report Found: {latest_report_file}")

    # Parse Date
    try:
        date_str = latest_report_file.replace('forex_market_report_', '').replace('.html', '')
        report_date = datetime.datetime.strptime(date_str, "%Y_%m_%d")
        formatted_date = report_date.strftime("%d de %B, %Y").title()
    except Exception as e:
        print(f"⚠️ Error parsing date: {e}")
        formatted_date = datetime.datetime.now().strftime("%Y-%m-%d")

    with open(INDEX_PATH, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')

    latest_card = soup.find('a', id='latest-report-forex')
            
    # --- 1. Update Card ---
    if latest_card:
        latest_card['href'] = f"{RELATIVE_REPORT_PATH}/{latest_report_file}"
        
        date_elem = latest_card.find('span', class_='report-date')
        if date_elem: date_elem.string = formatted_date
        
        title_elem = latest_card.find('span', class_='report-title')
        if title_elem: title_elem.string = "Informe Diario - Mercado Divisas"
        
        summary_elem = latest_card.find('span', class_='report-summary')
        if summary_elem: 
            summary_elem.string = "Análisis Técnico y Fundamental para pares Mayores y Cruces (Forex)."
    else:
        print("⚠️ Warning: Could not find '#latest-report-forex' in main index.")

    # --- 2. Rebuild Archive List ---
    archive_list = soup.find('ul', id='archive-forex')
    if archive_list:
        # Clear existing items
        archive_list.clear()
        
        # Populate with the rest of reports
        for report_file in all_reports[1:]:
            try:
                date_str = report_file.replace('forex_market_report_', '').replace('.html', '')
                report_date = datetime.datetime.strptime(date_str, "%Y_%m_%d")
                formatted_date = report_date.strftime("%d de %B, %Y").title()
            except Exception as e:
                formatted_date = date_str
            
            new_item = soup.new_tag('li', attrs={'class': 'archive-item'})
            link = soup.new_tag('a', href=f"{RELATIVE_REPORT_PATH}/{report_file}")
            
            date_span = soup.new_tag('span', attrs={'class': 'archive-date'})
            date_span.string = formatted_date
            
            link.append(date_span)
            link.append(f" Informe Diario - Mercado Divisas")
            new_item.append(link)
            archive_list.append(new_item)
            
        print(f"📦 Forex archive list rebuilt with {len(all_reports[1:])} reports.")

    # --- 3. Inject Signals Data to signals.html (for local file:// compatibility) ---
    signals_html_path = os.path.join(BASE_DIR, 'signals.html')
    signals_json_path = os.path.join(BASE_DIR, 'data', 'signals.json')
    if os.path.exists(signals_html_path) and os.path.exists(signals_json_path):
        try:
            with open(signals_json_path, 'r', encoding='utf-8') as sf:
                raw_json = sf.read()
            with open(signals_html_path, 'r', encoding='utf-8') as shf:
                html_content = shf.read()
            
            # Find window.SIGNALS_DATA = [...]; and replace it
            import re
            pattern = r'window\.SIGNALS_DATA\s*=\s*\[.*?\];'
            replacement = f'window.SIGNALS_DATA = {raw_json.strip()};'
            updated_html, count = re.subn(pattern, replacement, html_content, flags=re.DOTALL)
            
            if count > 0:
                with open(signals_html_path, 'w', encoding='utf-8') as shf:
                    shf.write(updated_html)
                print("💉 Injected dynamic signals database into Forex signals.html successfully.")
            else:
                print("⚠️ Pattern window.SIGNALS_DATA not found in Forex signals.html.")
        except Exception as je:
            print(f"⚠️ Error injecting data to Forex signals.html: {je}")

    # Save changes
    with open(INDEX_PATH, 'w', encoding='utf-8') as f:
        f.write(str(soup))
        
    print("✅ Forex Section updated in Main Hub.")
    return True

if __name__ == "__main__":
    update_hub()
