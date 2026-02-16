import os
import subprocess
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("master_workflow.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def run_command(command, cwd):
    """Executes a command and logs output."""
    logging.info(f"🚀 Running: {command} in {cwd}")
    try:
        result = subprocess.run(
            command, 
            cwd=cwd, 
            shell=True, 
            capture_output=True, 
            text=True,
            encoding='utf-8'
        )
        if result.returncode == 0:
            logging.info(f"SUCCESS: {command}")
            return True
        else:
            logging.error(f"FAILED: {command}")
            logging.error(result.stderr)
            return False
    except Exception as e:
        logging.error(f"❌ Exception running {command}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-only", action="store_true", help="Run only the data gathering phase")
    args = parser.parse_args()
    
    start_time = datetime.now()
    mode_str = " (DATA ONLY)" if args.data_only else ""
    logging.info(f"=== STARTING MASTER MARKET WORKFLOW{mode_str} ===")
    
    data_flag = " --data-only" if args.data_only else ""
    
    # 1. Stocks (Root)
    success_stocks = run_command(f"python daily_workflow.py{data_flag}", BASE_DIR)
    
    # 2. Crypto
    crypto_dir = os.path.join(BASE_DIR, "infocryptos")
    success_crypto = run_command(f"python daily_workflow.py{data_flag}", crypto_dir)
    
    # 3. Forex
    forex_dir = os.path.join(BASE_DIR, "infofx")
    success_forex = run_command(f"python daily_workflow.py{data_flag}", forex_dir)
    
    # 4. Consolidate History (New Tab)
    success_history = run_command("python scripts/update_history.py", BASE_DIR)
    
    end_time = datetime.now()
    duration = end_time - start_time
    
    logging.info(f"=== MASTER WORKFLOW SUMMARY{mode_str} ===")
    logging.info(f"Stocks:  {'✅' if success_stocks else '❌'}")
    logging.info(f"Crypto:  {'✅' if success_crypto else '❌'}")
    logging.info(f"Forex:   {'✅' if success_forex else '❌'}")
    logging.info(f"History: {'✅' if success_history else '❌'}")
    logging.info(f"Total Duration: {duration}")
    logging.info("===============================")

if __name__ == "__main__":
    main()
