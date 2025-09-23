"""
Sample script to demonstrate OHLCV data insertion
This would normally be connected to a real data provider like Alpha Vantage, Yahoo Finance, etc.
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Add the src directory to sys.path to enable imports
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.append(src_path)

from DB.operations import DatabaseOperations


def generate_sample_ohlcv_data(symbol: str, timeframe: str, days: int = 7):
    """
    Generate sample OHLCV data for testing
    In production, this would fetch real data from a provider
    """
    data = []
    base_price = 100.0
    
    # Determine time interval based on timeframe
    if timeframe == '1m':
        interval = timedelta(minutes=1)
        periods_per_day = 390  # Market hours: 6.5 hours * 60 minutes
    elif timeframe == '10m':
        interval = timedelta(minutes=10)
        periods_per_day = 39  # Market hours: 6.5 hours * 6 (10-min periods)
    else:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    
    # Generate recent data (last few hours instead of days ago)
    start_time = datetime.utcnow() - timedelta(hours=days * 6)  # 6 hours per "day" of data
    current_time = start_time
    
    for _ in range(days * periods_per_day):
        # Generate realistic OHLCV data
        open_price = max(0.01, base_price + random.uniform(-2, 2))  # Ensure positive price
        high_price = open_price + random.uniform(0, 3)
        low_price = max(0.01, open_price - random.uniform(0, 2))  # Ensure positive price
        close_price = max(0.01, low_price + random.uniform(0, high_price - low_price))
        volume = random.randint(10000, 1000000)
        
        # Simple technical indicators (in practice, use proper TA libraries)
        sma_20 = base_price + random.uniform(-1, 1)
        rsi = random.uniform(30, 70)
        
        data.append({
            'timestamp': current_time,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume,
            'sma_20': round(sma_20, 2),
            'rsi': round(rsi, 2)
        })
        
        base_price = close_price  # Use close as next base
        current_time += interval
    
    return data


def test_ohlcv_storage():
    """
    Test OHLCV data storage
    """
    print("📊 Testing OHLCV data storage...")
    
    symbols = ['AAPL', 'MSFT', 'GOOGL']
    timeframes = ['1m', '10m']
    
    try:
        with DatabaseOperations() as db_ops:
            for symbol in symbols:
                for timeframe in timeframes:
                    print(f"📈 Generating sample data for {symbol} {timeframe}...")
                    
                    # Generate sample data
                    ohlcv_data = generate_sample_ohlcv_data(symbol, timeframe, days=2)
                    
                    # Insert into database
                    success = db_ops.insert_ohlcv_data(symbol, timeframe, ohlcv_data)
                    
                    if success:
                        print(f"✅ Stored {len(ohlcv_data)} {timeframe} records for {symbol}")
                    else:
                        print(f"❌ Failed to store data for {symbol} {timeframe}")
            
            print("\n📊 Testing data retrieval...")
            
            # Test data retrieval
            for symbol in symbols[:2]:  # Test first 2 symbols
                for timeframe in timeframes:
                    df = db_ops.get_ohlcv_data(symbol, timeframe, days=1)
                    print(f"📊 Retrieved {len(df)} {timeframe} records for {symbol}")
                    
                    if not df.empty:
                        print(f"Sample data for {symbol} {timeframe}:")
                        # Check actual column names and display accordingly
                        available_cols = ['timestamp']
                        price_cols = ['open_price', 'high_price', 'low_price', 'close_price'] 
                        if all(col in df.columns for col in price_cols):
                            available_cols.extend(price_cols)
                        if 'volume' in df.columns:
                            available_cols.append('volume')
                        print(df[available_cols].head(3))
                        print()
    
    except Exception as e:
        print(f"❌ OHLCV test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("  OHLCV Data Storage Test")
    print("=" * 60)
    
    test_ohlcv_storage()
    
    print("\n🎉 OHLCV test completed!")