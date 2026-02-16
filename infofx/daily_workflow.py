import os
import datetime
import logging
import time
import argparse

# Configure logging
logging.basicConfig(
    filename='daily_workflow.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_fallback_html(today):
    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Mantenimiento - {today}</title>
        <style>
            body {{ font-family: sans-serif; background: #0f172a; color: #fff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .container {{ text-align: center; padding: 2rem; border: 1px solid #334155; border-radius: 1rem; background: #1e293b; }}
            h1 {{ color: #ef4444; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>⚠️ Sistema en Mantenimiento</h1>
            <p>No se han podido verificar datos concluyentes para el informe de hoy ({today}).</p>
            <p>El sistema está reintentando la conexión con los proveedores de datos.</p>
        </div>
    </body>
    </html>
    """
    
    report_filename = f"forex_market_report_{today}"
    html_path = os.path.join("reports", f"{report_filename}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logging.warning(f"⚠️ Generated Fallback HTML to {html_path}")

def run_workflow_attempt():
    # 1. Market Scanner (Real Data)
    logging.info("Step 1: Scanning Market for Real Data...")
    try:
        from scripts.market_scanner import scan_market
        scan_market() # Generates data/signals.json and data/market_scan.csv
        logging.info("✅ Market Scan completed.")
    except Exception as e:
        logging.error(f"❌ Market Scanner failed: {e}")
        return False

    # 1.5 Update Google Sheet (New Automation)
    if os.path.exists(os.path.join(BASE_DIR, 'credentials.json')):
        logging.info("Step 1.5: Updating Google Sheet...")
        try:
            from scripts.update_sheet import update_google_sheet
            update_google_sheet()
        except Exception as e:
             logging.error(f"⚠️ Google Sheet update failed: {e}")
    else:
        logging.warning("⚠️ No credentials.json found. Skipping Sheet update.")

def run_reports_and_hub():
    # 2 & 3. Report Generation (USING NEW GENERATOR)
    logging.info("Step 2 & 3: Generating Reports (MD + HTML) with Real Data...")
    try:
        from scripts.report_generator import run_generator
        run_generator("data/signals.json", "reports")
        logging.info("✅ Reports generated successfully.")
    except Exception as e:
        logging.error(f"❌ Report generation failed: {e}")
        return False

    # 4. Update Web Hub (Index.html)
    logging.info("Step 4: Updating Web Hub (index.html)...")
    try:
        from scripts.update_hub import update_hub
        update_hub()
        logging.info("✅ Web Hub updated successfully.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        logging.error(f"❌ Web Hub update failed: {e}")

    return True

def run_workflow(data_only=False):
    logging.info(f"Starting Daily Market Report Workflow (DataOnly={data_only})")
    today = datetime.datetime.now().strftime("%Y_%m_%d")
    
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        logging.info(f"🔄 Attempt {attempt}/{max_retries}...")
        try:
            # Step 1: Data Gathering (Always runs)
            if run_workflow_attempt():
                if data_only:
                    logging.info("✅ Data Phase Completed. Skipping reports as requested.")
                    return
                
                # Step 2: Report & Hub Phase
                if run_reports_and_hub():
                    logging.info("✅ Workflow Completed Successfully.")
                    return
        except Exception as e:
            logging.error(f"❌ Attempt {attempt} failed: {e}")
        
        if attempt < max_retries:
            time.sleep(5) # Wait before retry
    
    logging.error("❌ All attempts failed. Generating Fallback HTML.")
    generate_fallback_html(today)

if __name__ == "__main__":
    os.makedirs("reports", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Ensure current directory is correct for imports
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-only", action="store_true", help="Only run scanner and sheet updates")
    args = parser.parse_args()
    
    run_workflow(data_only=args.data_only)
