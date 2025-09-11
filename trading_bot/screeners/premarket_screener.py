"""
Premarket screener using Selenium to scrape Nasdaq pre-market movers.
Returns a list of tickers for the top N pre-market stocks.
"""
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import time

def get_top_premarket_tickers(chromedriver_path, num_rows=3, headless=True):
    """
    Launches a Selenium Chrome browser, navigates to the Nasdaq pre-market screener,
    clicks the 'Most Advanced' button, scrapes the top N rows of the table, and returns a list of tickers.
    Args:
        chromedriver_path (str): Path to the ChromeDriver executable.
        num_rows (int): Number of top rows to extract tickers from.
        headless (bool): Whether to run Chrome in headless mode.
    Returns:
        List[str]: List of ticker symbols from the first cell of each row.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get("https://www.nasdaq.com/market-activity/pre-market")
        time.sleep(2)
        try:
            most_advanced = driver.find_element(By.XPATH, "//button[text()='Most Advanced']")
            most_advanced.click()
            time.sleep(1)
        except Exception:
            pass
        table = driver.find_element(By.XPATH, "/html/body/div[2]/div/main/div[2]/article/div[2]/div/div[3]/div[1]/div[3]/table")
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        data = []
        for row in rows[:num_rows]:
            try:
                cells = row.find_elements(By.XPATH, ".//th | .//td")
                row_data = []
                for cell in cells:
                    link = cell.find_elements(By.TAG_NAME, "a")
                    if link:
                        row_data.append(link[0].text.strip())
                    else:
                        row_data.append(cell.text.strip())
                while len(row_data) < 5:
                    row_data.append("")
                data.append(row_data[:5])
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        tickers = [row[0] for row in data if row and row[0]]
        return tickers
    finally:
        driver.quit()

# Example usage:
# chromedriver_path = r"C:\\Users\\cleem\\Downloads\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe"
# tickers = get_top_premarket_tickers(chromedriver_path, num_rows=3, headless=True)
# print(tickers)