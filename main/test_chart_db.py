"""
Chart Viewer Database Connection Test
Tests the database connection and data availability for the chart viewer
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from src.DB.operations import DatabaseOperations
    print("✅ DatabaseOperations imported successfully")
except ImportError as e:
    print(f"❌ Failed to import DatabaseOperations: {e}")
    sys.exit(1)

def test_database_connection():
    """Test basic database connection"""
    try:
        db_ops = DatabaseOperations()
        print("✅ Database connection established")
        return db_ops
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def test_execute_query_method(db_ops):
    """Test the execute_query method"""
    try:
        # Simple test query
        result = db_ops.execute_query("SELECT 1 as test")
        if result:
            print("✅ execute_query method works")
            print(f"   Test result: {result}")
        else:
            print("❌ execute_query returned None")
        return True
    except Exception as e:
        print(f"❌ execute_query method failed: {e}")
        return False

def test_ohlcv_table(db_ops):
    """Test OHLCV table access"""
    try:
        # Check if table exists and has data
        result = db_ops.execute_query("SELECT COUNT(*) FROM ohlcv_data")
        if result:
            count = result[0][0]
            print(f"✅ ohlcv_data table has {count} records")
            
            if count > 0:
                # Get sample data
                sample = db_ops.execute_query("SELECT * FROM ohlcv_data LIMIT 3")
                if sample:
                    print("📊 Sample data:")
                    for row in sample:
                        print(f"   {row}")
                
                # Get available symbols
                symbols = db_ops.execute_query("""
                    SELECT symbol, COUNT(*) as records, MAX(timestamp) as last_update 
                    FROM ohlcv_data 
                    GROUP BY symbol 
                    ORDER BY MAX(timestamp) DESC
                """)
                if symbols:
                    print(f"📈 Available symbols ({len(symbols)}):")
                    for symbol_row in symbols:
                        symbol, count, last_update = symbol_row
                        print(f"   {symbol}: {count} records, last: {last_update}")
            else:
                print("⚠️ No data in ohlcv_data table")
        else:
            print("❌ Could not query ohlcv_data table")
            
    except Exception as e:
        print(f"❌ OHLCV table test failed: {e}")

def main():
    """Main test function"""
    print("🔧 Chart Viewer Database Connection Test")
    print("=" * 50)
    
    # Test 1: Database connection
    db_ops = test_database_connection()
    if not db_ops:
        return
    
    # Test 2: execute_query method
    if not test_execute_query_method(db_ops):
        return
    
    # Test 3: OHLCV data
    test_ohlcv_table(db_ops)
    
    print("=" * 50)
    print("🎯 Test completed! Chart viewer should now work.")
    
    # Close database connection
    try:
        db_ops.session.close()
        print("✅ Database connection closed")
    except:
        pass

if __name__ == "__main__":
    main()