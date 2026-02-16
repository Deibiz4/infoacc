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
INDEX_PATH = os.path.join(BASE_DIR, '..', 'index.html')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
# The path relative to the PARENT index.html
RELATIVE_REPORT_PATH = "infofx/reports"

def get_latest_report():
    """Find the most recent HTML report file."""
    files = [f for f in os.listdir(REPORTS_DIR) if f.startswith('forex_market_report_') and f.endswith('.html')]
    if not files:
        return None
    
    # Sort by date (filename contains date YYYY_MM_DD)
    files.sort(reverse=True)
    return files[0]

def update_hub():
    print(f"🌐 Updating Web Hub Control ({INDEX_PATH})...")
    
    if not os.path.exists(INDEX_PATH):
        print(f"❌ Error: {INDEX_PATH} not found.")
        return False

    latest_report_file = get_latest_report()
    if not latest_report_file:
         print("⚠️ No reports found to update index.")
         return False
         
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

    # --- Find Forex Section ---
    latest_card = soup.find('a', id='latest-report-forex')
            
    if latest_card:
        # Check if archiving is needed
        # If the link currently points to a DIFFERENT crypto report, archieve it?
        # The main hub archive usually mixes everything or we might want separate archives.
        # For now, let's just update the "Latest" card. 
        # If we want to add to the shared archive list, we can.
        
        old_href = latest_card.get('href', '#')
        old_title = latest_card.find('span', class_='report-title').text.strip()
        old_date_text = latest_card.find('span', class_='report-date').text.strip()
        
        new_href = f"{RELATIVE_REPORT_PATH}/{latest_report_file}"
        
        # Archive logic (Shared List)
        archive_list = soup.find('ul', id='archive-forex')
        if archive_list and 'forex_market_report' in old_href and old_href != new_href:
             existing_links = [a['href'] for a in archive_list.find_all('a')]
             if old_href not in existing_links:
                print(f"📦 Archiving previous forex report: {old_href}")
                new_item = soup.new_tag('li', attrs={'class': 'archive-item'})
                link = soup.new_tag('a', href=old_href)
                date_span = soup.new_tag('span', attrs={'class': 'archive-date'})
                date_span.string = old_date_text
                link.append(date_span)
                link.append(f" {old_title}")
                new_item.append(link)
                archive_list.insert(0, new_item)

        # Update Card
        latest_card['href'] = new_href
        
        date_elem = latest_card.find('span', class_='report-date')
        if date_elem: date_elem.string = formatted_date
        
        title_elem = latest_card.find('span', class_='report-title')
        if title_elem: title_elem.string = "Informe Diario - Mercado Divisas"
        
        summary_elem = latest_card.find('span', class_='report-summary')
        if summary_elem: 
            summary_elem.string = "Análisis Técnico y Fundamental para pares Mayores y Cruces (Forex)."
            
        print("✅ Forex Section updated in Main Hub.")
        
        with open(INDEX_PATH, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        return True
    else:
        print("⚠️ Warning: Could not find '#latest-report-crypto' in main index.")
        return False

if __name__ == "__main__":
    update_hub()
