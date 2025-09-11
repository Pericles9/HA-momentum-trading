"""
Heikin Ashi and custom indicator calculations.
"""
import pandas as pd

class HeikinAshi:
    @staticmethod
    def calculate(df):
        """
        Converts a DataFrame of OHLCV data to Heikin Ashi candles.
        Expects columns: open, high, low, close, volume. Returns a new DataFrame.
        """
        ha = pd.DataFrame(index=df.index)
        ha["ha_close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
        ha["ha_open"] = 0.0
        ha["ha_open"].iloc[0] = (df["open"].iloc[0] + df["close"].iloc[0]) / 2
        for i in range(1, len(df)):
            ha["ha_open"].iloc[i] = (ha["ha_open"].iloc[i-1] + ha["ha_close"].iloc[i-1]) / 2
        ha["ha_high"] = df[["high"]].join(ha[["ha_open", "ha_close"]]).max(axis=1)
        ha["ha_low"] = df[["low"]].join(ha[["ha_open", "ha_close"]]).min(axis=1)
        ha["volume"] = df["volume"]
        return ha
