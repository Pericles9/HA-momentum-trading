"""
Test script for historical data ingestion using TvDatafeed
"""
import sys
import os
import pandas as pd

# Add the src directory to path for imports (from tests folder)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ingestion.hist import HistoricalDataIngestion
from DB.connection import test_connection
from DB.operations import DatabaseOperations

def test_historical_ingestion():
    """Test the TvDatafeed historical data ingestion system"""
    
    print("🚀 Testing TvDatafeed Historical Data Ingestion System")
    print("=" * 60)
    
    # Test 1: Database Connection
    print("\n1️⃣ Testing database connection...")
    if not test_connection():
        print("❌ Database connection failed. Please check your TimescaleDB setup.")
        return False
    
    # Test 2: Initialize data ingestion
    print("\n2️⃣ Initializing TvDatafeed data ingestion...")
    ingestion = HistoricalDataIngestion()
    
    if not ingestion.initialized:
        print("❌ Failed to initialize TvDatafeed data ingestion")
        return False
    
    # Test 3: Fetch sample data with extended hours
    print("\n3️⃣ Fetching sample historical data with extended hours...")
    symbol = "AAPL"
    exchange = "NASDAQ"
    lookback_hours = 3  # Get 3 hours of data
    
    data = ingestion.get_historical_data(
        symbol=symbol,
        exchange=exchange,
        lookback_hours=lookback_hours,
        interval="5m"  # 5-minute intervals
    )
    
    if data is None or data.empty:
        print(f"❌ Failed to fetch data for {symbol}")
        return False
    
    print(f"✅ Fetched {len(data)} records for {symbol}")
    print(f"📊 Data columns: {list(data.columns)}")
    print(f"📅 Data range: {data['timestamp'].min()} to {data['timestamp'].max()}")
    
    # Test 4: Store data in database
    print("\n4️⃣ Testing database storage...")
    try:
        db_ops = DatabaseOperations()
        
        # Convert data to the format expected by insert_ohlcv_data
        records = []
        for _, row in data.iterrows():
            record = {
                'timestamp': row['timestamp'],
                'open': float(row['open_price']),
                'high': float(row['high_price']),
                'low': float(row['low_price']),
                'close': float(row['close_price']),
                'volume': int(row['volume']) if pd.notna(row['volume']) else 0,
            }
            records.append(record)
        
        # Store the OHLCV data
        success = db_ops.insert_ohlcv_data(
            symbol=symbol,
            timeframe="5m",  # 5-minute timeframe
            ohlcv_data=records
        )
        
        if success:
            print(f"✅ Successfully stored {len(data)} records in database")
            
            # Test retrieval
            print("\n5️⃣ Testing data retrieval...")
            
            retrieved_data = db_ops.get_ohlcv_data(
                symbol=symbol,
                timeframe="5m",
                days=1  # Get data from the last day
            )
            
            if retrieved_data is not None and not retrieved_data.empty:
                print(f"✅ Successfully retrieved {len(retrieved_data)} records from database")
                print(f"📊 Retrieved data shape: {retrieved_data.shape}")
                return True
            else:
                print("❌ Failed to retrieve data from database")
                return False
        else:
            print("❌ Failed to store data in database")
            return False
            
    except Exception as e:
        print(f"❌ Database operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_historical_ingestion()
    
    if success:
        print("\n🎉 All tests passed! Historical data ingestion system is working correctly.")
    else:
        print("\n💥 Some tests failed. Please check the error messages above.")