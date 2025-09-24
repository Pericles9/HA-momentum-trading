import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def fetch_table_to_df(
    url: str = "https://stockanalysis.com/markets/premarket/gainers/",
    table_xpath: str = '//*[@id="main-table"]/tbody'
) -> pd.DataFrame:
    """
    Uses Selenium to pull table data from a website and returns it as a pandas DataFrame.
    Args:
        url (str): The URL of the website.
        table_xpath (str): The XPath to locate the table.
    Returns:
        pd.DataFrame: DataFrame containing table data.
    """
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Use webdriver-manager to automatically manage ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        driver.get(url)
        table = driver.find_element(By.XPATH, table_xpath)
        rows = table.find_elements(By.TAG_NAME, "tr")
        data = []
        for row in rows:
            cols = row.find_elements(By.TAG_NAME, "td")
            if cols:
                data.append([col.text for col in cols])
        driver.quit()
        
        # Example columns, adjust as needed
        columns = ["#", "Symbol", "Name", "Change %", "Price", "Volume", "Market Cap"]
        df = pd.DataFrame(data, columns=columns)
        return df
        
    except Exception as e:
        print(f"Error in PMH screener: {e}")
        return pd.DataFrame()  # Return empty DataFrame on error