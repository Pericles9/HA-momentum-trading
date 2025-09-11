class Stock:
    """
    Represents a stock found by a screener, with ticker, change, and volume.
    You can extend this class with more attributes as needed.
    """
    def __init__(self, ticker, change, volume):
        self.ticker = ticker
        self.change = change
        self.volume = volume

    def __repr__(self):
        return f"Stock(ticker={self.ticker}, change={self.change}, volume={self.volume})"