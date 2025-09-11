"""
Heikin Ashi momentum strategy implementation.
Translates Pine Script logic to Python, inherits from BaseStrategy.
"""
from .base_strategy import BaseStrategy


import pandas as pd
import numpy as np

class HAMomentumStrategy(BaseStrategy):
    """
    Implements the Heikin Ashi Long Only + Strong Trend Filters strategy.
    Expects `data` as a pandas DataFrame with columns: open, high, low, close, volume, and datetime index.
    """
    def __init__(self, config=None, strategy_params=None):
        self.config = config or {}
        self.strategy_params = strategy_params or {}

    def heikin_ashi(self, df):
        ha = pd.DataFrame(index=df.index)
        ha['ha_close'] = (df['open'] + df['high'] + df['low'] + df['close']) / 4
        ha['ha_open'] = 0.0
        ha['ha_open'].iloc[0] = (df['open'].iloc[0] + df['close'].iloc[0]) / 2
        for i in range(1, len(df)):
            ha['ha_open'].iloc[i] = (ha['ha_open'].iloc[i-1] + ha['ha_close'].iloc[i-1]) / 2
        ha['ha_high'] = df[['high']].join(ha[['ha_open', 'ha_close']]).max(axis=1)
        ha['ha_low'] = df[['low']].join(ha[['ha_open', 'ha_close']]).min(axis=1)
        return ha

    def generate_signals(self, data):
        df = data.copy()
        ha = self.heikin_ashi(df)
        df = df.join(ha)

        # === Basic signals
        df['bullish_signal'] = df['ha_close'] > df['ha_open']

        # --- Previous session close filter (+30%)
        df['prev_session_close'] = df['close'].shift(1).rolling(window=1440, min_periods=1).last()  # daily close, adjust as needed
        df['price_condition'] = (df['close'] >= df['prev_session_close'] * 1.3)

        # --- ROC filter
        roc_length = self.strategy_params.get('roc_length', 5)
        roc_threshold = self.strategy_params.get('roc_threshold', 1.5)
        df['roc'] = df['close'].pct_change(periods=roc_length) * 100
        df['roc_condition'] = df['roc'] > roc_threshold

        # --- Candle size filter
        atr_period = self.strategy_params.get('atr_period', 14)
        df['tr'] = np.maximum(df['high'] - df['low'],
                              np.abs(df['high'] - df['close'].shift(1)),
                              np.abs(df['low'] - df['close'].shift(1)))
        df['atr'] = df['tr'].rolling(window=atr_period, min_periods=1).mean()
        df['min_candle_size'] = df['atr'] * 0.5
        df['candle_size'] = df['ha_high'] - df['ha_low']
        df['candle_condition'] = df['candle_size'] > df['min_candle_size']

        # --- MACD filter (1-minute, here use current timeframe for demo)
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd_line'] = ema12 - ema26
        df['signal_line'] = df['macd_line'].ewm(span=9, adjust=False).mean()
        df['macd_condition'] = df['macd_line'] > 0

        # === Strong trend filters
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        # For multi-timeframe, you would resample to 1h and calculate EMA, then align back
        # Here, we use current timeframe for simplicity
        df['trend_up'] = True  # Placeholder, can add logic for EMA cross

        # Volume filter
        df['vol_sma20'] = df['volume'].rolling(window=20, min_periods=1).mean()
        df['vol_filter'] = df['volume'] > df['vol_sma20']

        # Combine trend filters
        df['trend_condition'] = df['trend_up'] & df['vol_filter']

        # --- Final long entry condition
        df['long_condition'] = (
            df['bullish_signal'] &
            df['price_condition'] &
            df['roc_condition'] &
            df['candle_condition'] &
            df['macd_condition'] &
            df['trend_condition']
        )

        # === Exits
        df['atr_stop_loss'] = df['close'] - df['atr'] * 1.5
        df['exit_condition'] = df['ha_close'] < df['ha_open']

        return df[['long_condition', 'atr_stop_loss', 'exit_condition']]

    def calculate_position_size(self, balance, risk):
        # Example: risk is percent of balance to risk per trade
        return balance * risk
