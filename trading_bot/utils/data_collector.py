"""
Module for collecting and injecting market data from Polygon.io.
Handles fetching raw OHLCV data and saving to disk.
"""
import requests
import pandas as pd
import os

class PolygonDataCollector:
    def __init__(self, api_key, save_dir="data/raw"):
        self.api_key = api_key
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)

    def fetch_ohlcv(self, symbol, multiplier=1, timespan="minute", from_date=None, to_date=None, limit=50000):
        """
        Fetches OHLCV bars from Polygon.io for a given symbol and date range.
        Returns a pandas DataFrame.
        """
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{multiplier}/{timespan}/{from_date}/{to_date}"
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": limit,
            "apiKey": self.api_key
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if "results" not in data:
            raise ValueError("No results in Polygon.io response")
        df = pd.DataFrame(data["results"])
        # Polygon columns: t (timestamp), o, h, l, c, v, n, vw
        df = df.rename(columns={"t": "timestamp", "o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"})
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("datetime", inplace=True)
        return df[["open", "high", "low", "close", "volume"]]

    def save_to_csv(self, df, symbol, filename=None):
        """
        Saves a DataFrame to CSV in the raw data directory.
        """
        if filename is None:
            filename = f"{symbol}.csv"
        path = os.path.join(self.save_dir, filename)
        df.to_csv(path)
        return path

    def load_from_csv(self, symbol, filename=None):
        """
        Loads a DataFrame from CSV in the raw data directory.
        """
        if filename is None:
            filename = f"{symbol}.csv"
        path = os.path.join(self.save_dir, filename)
        return pd.read_csv(path, index_col="datetime", parse_dates=["datetime"])