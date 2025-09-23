"""
Historical data ingestion using TvDatafeed (TradingView data)
Fetches intraday OHLCV data and stores it in TimescaleDB
"""
import sys
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from tvDatafeed import TvDatafeed, Interval
import time

# Add the src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from DB.operations import DatabaseOperations
from DB.connection import test_connection


class HistoricalDataIngestion:
    """
    Historical data ingestion system using TvDatafeed (TradingView)
    """
    
    def __init__(self, username: str = None, password: str = None):
        """
        Initialize the TvDatafeed data ingestion system
        
        Args:
            username: TradingView username (optional, can work without login)
            password: TradingView password (optional, can work without login)
        """
        try:
            # Initialize TvDatafeed
            if username and password:
                print("🔐 Initializing TvDatafeed with login credentials...")
                self.tv = TvDatafeed(username, password)
                self.logged_in = True
            else:
                print("🔓 Initializing TvDatafeed without login (some data may be limited)...")
                self.tv = TvDatafeed()
                self.logged_in = False
            
            self.initialized = True
            
            # Test the connection by trying to get a small amount of data
            test_data = self.tv.get_hist(symbol='AAPL', exchange='NASDAQ', interval=Interval.in_daily, n_bars=1)
            if test_data is not None and not test_data.empty:
                print("✅ TvDatafeed initialized successfully")
            else:
                raise Exception("Failed to fetch test data")
            
        except Exception as e:
            print(f"❌ Failed to initialize TvDatafeed: {e}")
            self.tv = None
            self.initialized = False
            self.logged_in = False
    
    def get_historical_data(
        self, 
        symbol: str,
        exchange: str = "NASDAQ", 
        lookback_hours: int = 24,
        interval: str = "1m"
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical intraday data from TradingView
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            exchange: Exchange name (e.g., 'NASDAQ', 'NYSE', 'BINANCE')
            lookback_hours: Hours to look back from now (for filtering recent data)
            interval: Data interval ('1m', '3m', '5m', '15m', '30m', '45m', '1h', '2h', '3h', '4h', '1D', '1W', '1M')
        
        Returns:
            pd.DataFrame: OHLCV data or None if failed
        """
        if not self.initialized:
            print("❌ TvDatafeed not initialized")
            return None
        
        try:
            print(f"📊 Fetching {symbol} data from {exchange} with {interval} interval...")
            
            # Map interval strings to TvDatafeed Interval enum
            interval_mapping = {
                '1m': Interval.in_1_minute,
                '3m': Interval.in_3_minute,
                '5m': Interval.in_5_minute,
                '15m': Interval.in_15_minute,
                '30m': Interval.in_30_minute,
                '45m': Interval.in_45_minute,
                '1h': Interval.in_1_hour,
                '2h': Interval.in_2_hour,
                '3h': Interval.in_3_hour,
                '4h': Interval.in_4_hour,
                '1D': Interval.in_daily,
                '1W': Interval.in_weekly,
                '1M': Interval.in_monthly
            }
            
            if interval not in interval_mapping:
                print(f"❌ Unsupported interval: {interval}")
                print(f"Supported intervals: {list(interval_mapping.keys())}")
                return None
            
            tv_interval = interval_mapping[interval]
            
            # Calculate number of bars needed based on lookback hours
            # TvDatafeed can fetch up to 5000 bars
            if interval in ['1m']:
                # 1 minute: 60 bars per hour
                n_bars = min(lookback_hours * 60, 5000)
            elif interval in ['3m']:
                # 3 minutes: 20 bars per hour
                n_bars = min(lookback_hours * 20, 5000)
            elif interval in ['5m']:
                # 5 minutes: 12 bars per hour  
                n_bars = min(lookback_hours * 12, 5000)
            elif interval in ['15m']:
                # 15 minutes: 4 bars per hour
                n_bars = min(lookback_hours * 4, 5000)
            elif interval in ['30m']:
                # 30 minutes: 2 bars per hour
                n_bars = min(lookback_hours * 2, 5000)
            elif interval in ['45m']:
                # 45 minutes: ~1.33 bars per hour
                n_bars = min(int(lookback_hours * 1.33), 5000)
            elif interval in ['1h']:
                # 1 hour: 1 bar per hour
                n_bars = min(lookback_hours, 5000)
            elif interval in ['2h']:
                # 2 hours: 0.5 bars per hour
                n_bars = min(int(lookback_hours * 0.5), 5000)
            elif interval in ['3h']:
                # 3 hours: ~0.33 bars per hour
                n_bars = min(int(lookback_hours * 0.33), 5000)
            elif interval in ['4h']:
                # 4 hours: 0.25 bars per hour
                n_bars = min(int(lookback_hours * 0.25), 5000)
            else:
                # For daily/weekly/monthly, just get reasonable amount
                n_bars = min(lookback_hours // 24, 1000)  # Convert hours to days
            
            # Ensure we get at least some data
            n_bars = max(n_bars, 10)
            
            print(f"� Requesting {n_bars} bars of {interval} data...")
            
            # Fetch data from TradingView with extended hours
            data = self.tv.get_hist(
                symbol=symbol,
                exchange=exchange,
                interval=tv_interval,
                n_bars=n_bars,
                extended_session=True  # Include pre-market and after-hours data
            )
            
            if data is None or data.empty:
                print(f"❌ No data received for {symbol} on {exchange}")
                print("💡 Try different exchange or symbol format")
                return None
            
            print(f"🔍 Raw data shape: {data.shape}")
            print(f"🔍 Raw columns: {list(data.columns)}")
            
            # TvDatafeed returns data with datetime as index
            # Reset index to make datetime a column
            data = data.reset_index()
            
            # Rename columns to match our database schema
            # TvDatafeed columns: open, high, low, close, volume
            column_mapping = {
                'datetime': 'timestamp',
                'open': 'open_price',
                'high': 'high_price', 
                'low': 'low_price',
                'close': 'close_price',
                'volume': 'volume'
            }
            
            data = data.rename(columns=column_mapping)
            
            # Ensure we have the required columns
            required_cols = ['timestamp', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                print(f"❌ Missing required columns: {missing_cols}")
                print(f"Available columns: {list(data.columns)}")
                return None
            
            # Convert data types
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            
            # Convert price columns to float
            for col in ['open_price', 'high_price', 'low_price', 'close_price']:
                data[col] = pd.to_numeric(data[col], errors='coerce')
            
            # Convert volume to int (handle NaN values and non-numeric data)
            try:
                data['volume'] = pd.to_numeric(data['volume'], errors='coerce').fillna(0).astype('Int64')
            except (TypeError, ValueError):
                # If volume data is in scientific notation or other format, handle it
                data['volume'] = data['volume'].apply(lambda x: int(float(x)) if pd.notna(x) and str(x).replace('.', '').replace('e', '').replace('-', '').replace('+', '').isdigit() else 0)
            
            # Filter data to the requested time window
            if lookback_hours > 0:
                end_time = datetime.now()
                start_time = end_time - timedelta(hours=lookback_hours)
                data = data[data['timestamp'] >= start_time]
            
            # Sort by timestamp (oldest first)
            data = data.sort_values('timestamp').reset_index(drop=True)
            
            # Remove any NaN values in price columns
            data = data.dropna(subset=['open_price', 'high_price', 'low_price', 'close_price'])
            
            print(f"✅ Fetched {len(data)} records for {symbol}")
            if not data.empty:
                print(f"📅 Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
            
            return data
            
        except Exception as e:
            print(f"❌ Error fetching data for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def search_symbol(self, search_text: str, exchange: str = None) -> List[Dict]:
        """
        Search for symbols on TradingView
        
        Args:
            search_text: Text to search for (e.g., 'APPLE', 'BITCOIN')
            exchange: Optional exchange to filter results
        
        Returns:
            List of matching symbols with their details
        """
        if not self.initialized:
            print("❌ TvDatafeed not initialized")
            return []
        
        try:
            print(f"🔍 Searching for '{search_text}'" + (f" on {exchange}" if exchange else ""))
            
            # Use TvDatafeed's search functionality
            if exchange:
                results = self.tv.search_symbol(search_text, exchange)
            else:
                results = self.tv.search_symbol(search_text)
            
            if results:
                print(f"✅ Found {len(results)} matching symbols:")
                for i, result in enumerate(results[:10]):  # Show first 10 results
                    print(f"  {i+1}. {result}")
            else:
                print("❌ No symbols found")
            
            return results or []
            
        except Exception as e:
            print(f"❌ Error searching symbols: {e}")
            return []
    
    def add_basic_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Add basic technical indicators to the data
        
        Args:
            data: DataFrame with OHLCV data
        
        Returns:
            DataFrame with added indicators
        """
        try:
            df = data.copy()
            
            # Simple Moving Averages
            df['sma_20'] = df['close_price'].rolling(window=20).mean()
            df['sma_50'] = df['close_price'].rolling(window=50).mean()
            
            # Exponential Moving Averages
            df['ema_12'] = df['close_price'].ewm(span=12).mean()
            df['ema_26'] = df['close_price'].ewm(span=26).mean()
            
            # RSI calculation
            delta = df['close_price'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['macd_signal'] = df['macd'].ewm(span=9).mean()
            df['macd_histogram'] = df['macd'] - df['macd_signal']
            
            # Bollinger Bands
            bb_period = 20
            bb_std = 2
            df['bollinger_middle'] = df['close_price'].rolling(window=bb_period).mean()
            bb_std_dev = df['close_price'].rolling(window=bb_period).std()
            df['bollinger_upper'] = df['bollinger_middle'] + (bb_std_dev * bb_std)
            df['bollinger_lower'] = df['bollinger_middle'] - (bb_std_dev * bb_std)
            
            print(f"✅ Added technical indicators to {len(df)} records")
            return df
            
        except Exception as e:
            print(f"❌ Error adding indicators: {e}")
            return data
    
    def check_existing_data(self, symbol: str, timeframe: str = "1m") -> Optional[datetime]:
        """
        Check if symbol already exists in database and return the latest timestamp
        
        Args:
            symbol: Stock symbol
            timeframe: Data timeframe
        
        Returns:
            Latest timestamp for the symbol or None if no data exists
        """
        try:
            with DatabaseOperations() as db_ops:
                # Get recent data to check latest timestamp
                existing_data = db_ops.get_ohlcv_data(symbol, timeframe, days=1)
                
                if existing_data.empty:
                    print(f"📊 No existing data found for {symbol}")
                    return None
                
                latest_timestamp = existing_data['timestamp'].max()
                print(f"📅 Latest data for {symbol}: {latest_timestamp}")
                return pd.to_datetime(latest_timestamp)
                
        except Exception as e:
            print(f"❌ Error checking existing data: {e}")
            return None
    
    def store_data(
        self, 
        symbol: str, 
        data: pd.DataFrame, 
        timeframe: str = "1m",
        update_mode: str = "append"
    ) -> bool:
        """
        Store OHLCV data in the database
        
        Args:
            symbol: Stock symbol
            data: DataFrame with OHLCV data and indicators
            timeframe: Data timeframe
            update_mode: 'append' to add new data, 'replace' to replace all data
        
        Returns:
            Success status
        """
        try:
            if data.empty:
                print("❌ No data to store")
                return False
            
            # Check for existing data
            latest_existing = self.check_existing_data(symbol, timeframe)
            
            if update_mode == "append" and latest_existing is not None:
                # Ensure both timestamps are timezone-aware or naive for comparison
                if latest_existing.tz is not None and data['timestamp'].dt.tz is None:
                    # Make data timezone-aware to match existing data
                    data['timestamp'] = data['timestamp'].dt.tz_localize('UTC')
                elif latest_existing.tz is None and data['timestamp'].dt.tz is not None:
                    # Make latest_existing timezone-aware
                    latest_existing = latest_existing.tz_localize('UTC')
                
                # Filter out data that already exists (avoid duplicates)
                new_data = data[data['timestamp'] > latest_existing]
                
                if new_data.empty:
                    print(f"✅ No new data to add for {symbol}")
                    return True
                
                print(f"📊 Appending {len(new_data)} new records for {symbol}")
                data_to_store = new_data
            else:
                print(f"📊 Storing {len(data)} records for {symbol}")
                data_to_store = data
            
            # Convert DataFrame to list of dictionaries for database insertion
            records = []
            for _, row in data_to_store.iterrows():
                record = {
                    'timestamp': row['timestamp'],
                    'open': float(row['open_price']),
                    'high': float(row['high_price']),
                    'low': float(row['low_price']),
                    'close': float(row['close_price']),
                    'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
                }
                
                # Add indicators if they exist
                indicator_cols = ['sma_20', 'sma_50', 'ema_12', 'ema_26', 'rsi', 
                                'macd', 'macd_signal', 'macd_histogram',
                                'bollinger_upper', 'bollinger_middle', 'bollinger_lower']
                
                for col in indicator_cols:
                    if col in row and pd.notna(row[col]):
                        record[col] = float(row[col])
                
                records.append(record)
            
            # Store in database
            with DatabaseOperations() as db_ops:
                success = db_ops.insert_ohlcv_data(symbol, timeframe, records)
                
                if success:
                    print(f"✅ Successfully stored {len(records)} records for {symbol}")
                    return True
                else:
                    print(f"❌ Failed to store data for {symbol}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error storing data: {e}")
            return False
    
    def ingest_historical_data(
        self,
        symbol: str,
        exchange: str = "NASDAQ",
        lookback_hours: int = 24,
        interval: str = "1m",
        add_indicators: bool = True,
        update_mode: str = "append"
    ) -> bool:
        """
        Complete historical data ingestion pipeline using TvDatafeed
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            exchange: Exchange name (e.g., 'NASDAQ', 'NYSE', 'BINANCE')
            lookback_hours: Hours to look back from now (for filtering recent data)
            interval: Data interval ('1m', '5m', '15m', '30m', '1h', '1D')
            add_indicators: Whether to calculate technical indicators
            update_mode: 'append' to add new data, 'replace' to replace all
        
        Returns:
            Success status
        """
        print(f"🚀 Starting historical data ingestion for {symbol}")
        print(f"📊 Parameters: {exchange} exchange, {lookback_hours}h lookback, {interval} interval")
        
        # Test database connection
        if not test_connection():
            print("❌ Database connection failed")
            return False
        
        # Fetch historical data
        data = self.get_historical_data(symbol, exchange, lookback_hours, interval)
        if data is None or data.empty:
            return False
        
        # Add technical indicators
        if add_indicators:
            data = self.add_basic_indicators(data)
        
        # Store data in database
        success = self.store_data(symbol, data, interval, update_mode)
        
        if success:
            print(f"🎉 Historical data ingestion completed for {symbol}")
        else:
            print(f"❌ Historical data ingestion failed for {symbol}")
        
        return success


def main():
    """
    Example usage of the TvDatafeed historical data ingestion system
    """
    print("=" * 60)
    print("  TvDatafeed Historical Data Ingestion System")
    print("=" * 60)
    
    # Initialize the ingestion system
    # You can optionally provide TradingView credentials for better access
    # ingestion = HistoricalDataIngestion(username="your_tv_username", password="your_tv_password")
    ingestion = HistoricalDataIngestion()  # No login required
    
    if not ingestion.initialized:
        print("❌ Failed to initialize TvDatafeed")
        return
    
    # Example: Ingest data for various symbols and timeframes
    test_configs = [
        {'symbol': 'AAPL', 'exchange': 'NASDAQ', 'hours': 6, 'interval': '1m'},
        {'symbol': 'MSFT', 'exchange': 'NASDAQ', 'hours': 12, 'interval': '5m'},
        {'symbol': 'TSLA', 'exchange': 'NASDAQ', 'hours': 24, 'interval': '15m'},
    ]
    
    for config in test_configs:
        print(f"\n{'='*50}")
        success = ingestion.ingest_historical_data(
            symbol=config['symbol'],
            exchange=config['exchange'],
            lookback_hours=config['hours'],
            interval=config['interval'],
            add_indicators=True,
            update_mode="append"
        )
        
        if success:
            print(f"✅ {config['symbol']} ({config['interval']}) ingestion completed")
        else:
            print(f"❌ {config['symbol']} ({config['interval']}) ingestion failed")
        
        # Small delay between requests
        print("⏳ Brief pause...")
        time.sleep(1)
    
    print(f"\n🎉 Historical data ingestion process completed!")
    print("💡 You can also try crypto symbols with BINANCE exchange:")
    print("   - BTCUSDT, ETHUSDT, ADAUSDT with exchange='BINANCE'")


if __name__ == "__main__":
    main()
