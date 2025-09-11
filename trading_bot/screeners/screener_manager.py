import datetime
from .premarket_screener import get_top_premarket_tickers
from .market_screener import get_top_market_tickers
from .stock import Stock

class ScreenerManager:
    """
    Manages running the appropriate screener and maintaining a list of Stock objects
    that have appeared and met criteria.
    """
    def __init__(self, chromedriver_path, num_rows=10, headless=True):
        self.chromedriver_path = chromedriver_path
        self.num_rows = num_rows
        self.headless = headless
        self.stocks = []  # List[Stock]
        self.tickers_seen = set()  # To avoid duplicates

    def is_premarket(self):
        """
        Returns True if current time is premarket (e.g., before 9:30am US Eastern).
        Adjust timezone logic as needed for your use case.
        """
        now = datetime.datetime.now()
        # Assume local time is US Eastern; adjust if needed
        return now.hour < 9 or (now.hour == 9 and now.minute < 30)

    def run(self):
        """
        Runs the appropriate screener and updates the stock list.
        """
        if self.is_premarket():
            results = get_top_premarket_tickers(self.chromedriver_path, self.num_rows, self.headless)
        else:
            results = get_top_market_tickers(self.chromedriver_path, self.num_rows, self.headless)

        for ticker, change, volume in results:
            if ticker not in self.tickers_seen:
                stock = Stock(ticker, change, volume)
                self.stocks.append(stock)
                self.tickers_seen.add(ticker)

    def get_stocks(self):
        """
        Returns the current list of Stock objects.
        """
        return self.stocks

# Example usage:
# chromedriver_path = r"C:\\Users\\cleem\\Downloads\\chromedriver-win64\\chromedriver-win64\\chromedriver.exe"
# manager = ScreenerManager(chromedriver_path, num_rows=5, headless=True)
# manager.run()
# print(manager.get_stocks())