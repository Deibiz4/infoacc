import schedule
import time
import logging
from daily_workflow import run_workflow

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def job():
    logging.info("⏳ Starting scheduled job...")
    try:
        run_workflow()
    except Exception as e:
        logging.error(f"❌ Job failed: {e}")

# Schedule the job every day at 08:30
schedule.every().monday.at("08:30").do(job)
schedule.every().tuesday.at("08:30").do(job)
schedule.every().wednesday.at("08:30").do(job)
schedule.every().thursday.at("08:30").do(job)
schedule.every().friday.at("08:30").do(job)

logging.info("🚀 Worker started. Waiting for 08:30 AM (Mon-Fri)...")

while True:
    schedule.run_pending()
    time.sleep(60)
