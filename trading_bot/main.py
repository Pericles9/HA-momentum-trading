"""
Entry point for running the trading bot.
Initializes config, data feeds, strategies, and order execution.
"""

import time
import datetime
from screeners.screener_manager import ScreenerManager

def main():
    """
    Runs the screener manager every 3 minutes between 7am and 3pm.
    """
    # Set your chromedriver path here
    chromedriver_path = r"C:\\Users\\cleem\\Downloads\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe"
    manager = ScreenerManager(chromedriver_path, num_rows=10, headless=True)

    start_time = datetime.time(7, 0)
    end_time = datetime.time(15, 0)

    print("[INFO] Bot started. Waiting for 7:00am...")
    while True:
        now = datetime.datetime.now().time()
        if now >= start_time:
            break
        time.sleep(30)

    print("[INFO] Screening started.")
    while True:
        now = datetime.datetime.now().time()
        if now >= end_time:
            print("[INFO] Screening ended at 3:00pm.")
            break
        print(f"[INFO] Running screener at {datetime.datetime.now().strftime('%H:%M:%S')}")
        manager.run()
        print(f"[INFO] Stocks found so far: {manager.get_stocks()}")
        time.sleep(180)  # 3 minutes

if __name__ == "__main__":
    main()
