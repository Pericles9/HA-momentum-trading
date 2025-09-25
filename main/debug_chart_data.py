"""
Debug Chart Viewer Data Issues
Investigate why the chart viewer can't find data for existing tickers
"""

import sys
import os
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.DB.operations import DatabaseOperations

def debug_ticker_data():
    """Debug ticker data retrieval"""
    try:
        db_ops = DatabaseOperations()
        print("🔧 Debugging Chart Viewer Data Issues")
        print("=" * 50)
        
        # 1. Check what tickers exist
        print("1️⃣ Checking available tickers...")
        ticker_query = """
            SELECT 
                symbol,
                COUNT(*) as record_count,
                MIN(timestamp) as first_record,
                MAX(timestamp) as last_record
            FROM ohlcv_data 
            GROUP BY symbol 
            ORDER BY MAX(timestamp) DESC
        """
        
        tickers = db_ops.execute_query(ticker_query)
        if tickers:
            print(f"   Found {len(tickers)} tickers:")
            for row in tickers:
                symbol, count, first, last = row
                print(f"   📊 {symbol}: {count} records ({first} to {last})")
                
            # 2. Test data retrieval for first ticker
            if tickers:
                test_symbol = tickers[0][0]  # Get first ticker symbol
                print(f"\n2️⃣ Testing data retrieval for '{test_symbol}'...")
                
                # Test with different parameter styles
                days_back = 1
                start_date = datetime.now() - timedelta(days=days_back)
                print(f"   Looking for data since: {start_date}")
                
                # Method 1: SQLAlchemy style (what our execute_query expects)
                query1 = """
                    SELECT timestamp, open_price, high_price, low_price, close_price, volume
                    FROM ohlcv_data 
                    WHERE symbol = :symbol AND timestamp >= :start_date
                    ORDER BY timestamp ASC LIMIT 5
                """
                
                print("   Testing SQLAlchemy-style parameters...")
                result1 = db_ops.execute_query(query1, {'symbol': test_symbol, 'start_date': start_date})
                if result1:
                    print(f"   ✅ Found {len(result1)} records with SQLAlchemy style")
                    for row in result1[:3]:  # Show first 3
                        print(f"      {row}")
                else:
                    print("   ❌ No results with SQLAlchemy style")
                
                # Method 2: Test what chart viewer is trying to do
                print("   Testing chart viewer query style...")
                query2 = """
                    SELECT timestamp, open_price, high_price, low_price, close_price, volume
                    FROM ohlcv_data 
                    WHERE symbol = %s AND timestamp >= %s
                    ORDER BY timestamp ASC LIMIT 5
                """
                
                try:
                    result2 = db_ops.execute_query(query2, (test_symbol, start_date))
                    if result2:
                        print(f"   ✅ Found {len(result2)} records with tuple style")
                    else:
                        print("   ❌ No results with tuple style")
                except Exception as e:
                    print(f"   ❌ Error with tuple style: {e}")
                
                # Method 3: Test without date filter
                print("   Testing without date filter...")
                query3 = """
                    SELECT timestamp, open_price, high_price, low_price, close_price, volume
                    FROM ohlcv_data 
                    WHERE symbol = :symbol
                    ORDER BY timestamp DESC LIMIT 5
                """
                
                result3 = db_ops.execute_query(query3, {'symbol': test_symbol})
                if result3:
                    print(f"   ✅ Found {len(result3)} total records for {test_symbol}")
                    print("   📈 Most recent records:")
                    for row in result3:
                        print(f"      {row[0]} | O:{row[1]} H:{row[2]} L:{row[3]} C:{row[4]} V:{row[5]}")
                else:
                    print(f"   ❌ No records found for {test_symbol}")
        else:
            print("   ❌ No tickers found in database")
            
        # 3. Test the exact query the chart viewer uses
        print("\n3️⃣ Testing exact chart viewer scenario...")
        if tickers:
            test_symbol = tickers[0][0]
            days_back = 1
            start_date = datetime.now() - timedelta(days=days_back)
            
            # This is exactly what the chart viewer does
            query = """
                SELECT timestamp, open_price, high_price, low_price, close_price, volume
                FROM ohlcv_data 
                WHERE symbol = %s AND timestamp >= %s
                ORDER BY timestamp ASC
            """
            
            print(f"   Symbol: {test_symbol}")
            print(f"   Start Date: {start_date}")
            print(f"   Query: {query}")
            
            try:
                result = db_ops.execute_query(query, (test_symbol, start_date))
                if result:
                    print(f"   ✅ Chart viewer query would work: {len(result)} records")
                else:
                    print("   ❌ Chart viewer query returns no results")
                    
                    # Try with a much longer time range
                    long_start = datetime.now() - timedelta(days=30)
                    result_long = db_ops.execute_query(query, (test_symbol, long_start))
                    if result_long:
                        print(f"   ℹ️ But found {len(result_long)} records in last 30 days")
                        oldest = min(row[0] for row in result_long)
                        newest = max(row[0] for row in result_long)
                        print(f"   📅 Data range: {oldest} to {newest}")
                    
            except Exception as e:
                print(f"   ❌ Chart viewer query failed: {e}")
        
        print("=" * 50)
        print("🎯 Debug completed!")
        
        db_ops.session.close()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")

if __name__ == "__main__":
    debug_ticker_data()