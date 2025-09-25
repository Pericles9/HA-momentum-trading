"""
Test database insertion with real TvDatafeed data
"""
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from tvDatafeed import TvDatafeed, Interval
from DB.connection import test_connection
from DB.operations import DatabaseOperations

def test_real_data_insertion():
    """Test database insertion with real TvDatafeed data"""
    print("🔧 Testing database insertion with real TvDatafeed data...")
    
    # Test connection
    if not test_connection():
        print("❌ Database connection failed")
        return False
    print("✅ Database connection successful")
    
    try:
        # Initialize TvDatafeed
        tv = TvDatafeed()
        print("✅ TvDatafeed initialized")
        
        # Get real data
        data = tv.get_hist(
            symbol="AAPL",
            exchange="NASDAQ", 
            interval=Interval.in_1_minute,
            n_bars=1,
            extended_session=True
        )
        
        if data is None or data.empty:
            print("❌ No data from TvDatafeed")
            return False
        
        print(f"✅ Got data: {data.shape}")
        
        # Extract data
        row = data.iloc[-1]
        timestamp = data.index[-1]
        
        print(f"📅 Raw timestamp: {timestamp} (type: {type(timestamp)})")
        
        # Format for database
        ohlcv_record = [{
            'timestamp': timestamp.to_pydatetime() if hasattr(timestamp, 'to_pydatetime') else timestamp,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': int(row['volume'])
        }]
        
        print(f"📊 Formatted record: {ohlcv_record[0]}")
        
        # Insert into database
        db_ops = DatabaseOperations()
        success = db_ops.insert_ohlcv_data(
            symbol="AAPL",
            timeframe="1m",
            ohlcv_data=ohlcv_record
        )
        
        if success:
            print("✅ Database insertion successful!")
            
            # Verify
            latest = db_ops.get_latest_ohlcv_data(symbol="AAPL", limit=1)
            if latest is not None and not latest.empty:
                print(f"✅ Verification successful: ${latest.iloc[0]['close']:.2f}")
                return True
            else:
                print("⚠️ Verification failed")
                return False
        else:
            print("❌ Database insertion failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_data_insertion()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")