from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import pandas as pd
import time

def get_top_market_tickers(chromedriver_path, num_rows=10, headless=True):
    """
    Launches a Selenium Chrome browser, navigates to the StockAnalysis market gainers page,
    scrapes the top N rows of the table, and returns a list of tuples (ticker, change, volume).
    Args:
        chromedriver_path (str): Path to the ChromeDriver executable.
        num_rows (int): Number of top rows to extract tickers from.
        headless (bool): Whether to run Chrome in headless mode.
    Returns:
        List[Tuple[str, str, str]]: List of (ticker, change, volume) tuples.
    """
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get("https://stockanalysis.com/markets/gainers/")
        time.sleep(2)
        table = driver.find_element(By.XPATH, "//table[contains(@class, 'table')]//tbody")
        rows = table.find_elements(By.TAG_NAME, "tr")
        data = []
        for row in rows[:num_rows]:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                row_data = [cell.text.strip() for cell in cells]
                data.append(row_data)
            except Exception as e:
                print(f"Error processing row: {e}")
                continue
        tuples = []
        for row in data:
            if len(row) > 5 and row[1] and row[3] and row[5]:
                tuples.append((row[1], row[3], row[5]))
        return tuples
    finally:
        driver.quit()

# Example usage:
#chromedriver_path = r"C:\\Users\\cleem\\Downloads\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe"
#tickers = get_top_market_tickers(chromedriver_path, num_rows=5, headless=True)
#print(tickers)