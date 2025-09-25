"""
Quick database insertion test
"""
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from DB.connection import test_connection
from DB.operations import DatabaseOperations

def test_db_insertion():
    """Test if database insertion is working"""
    print("🔧 Testing database insertion...")
    
    # Test connection
    if not test_connection():
        print("❌ Database connection failed")
        return False
    print("✅ Database connection successful")
    
    # Test insertion
    try:
        db_ops = DatabaseOperations()
        
        # Create test data
        test_data = [{
            'timestamp': datetime.now(),
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.5,
            'volume': 1000
        }]
        
        # Try to insert
        success = db_ops.insert_ohlcv_data(
            symbol="TEST",
            timeframe="1m",
            ohlcv_data=test_data
        )
        
        if success:
            print("✅ Database insertion successful")
            
            # Try to retrieve
            latest = db_ops.get_latest_ohlcv_data(symbol="TEST", limit=1)
            if latest is not None and not latest.empty:
                print(f"✅ Data retrieval successful: {len(latest)} records")
                print(f"📊 Latest record: ${latest.iloc[0]['close']:.2f}")
            else:
                print("⚠️ Data retrieval failed")
            
        else:
            print("❌ Database insertion failed")
            
        return success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_db_insertion()