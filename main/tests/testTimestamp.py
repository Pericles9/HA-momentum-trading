"""
Quick test to check timestamp formatting from TvDatafeed
"""
from tvDatafeed import TvDatafeed, Interval
from datetime import datetime

def test_timestamp_format():
    """Test what format TvDatafeed returns for timestamps"""
    print("🔧 Testing timestamp format from TvDatafeed...")
    
    try:
        tv = TvDatafeed()
        print("✅ TvDatafeed initialized")
        
        # Get sample data
        data = tv.get_hist(
            symbol="AAPL",
            exchange="NASDAQ",
            interval=Interval.in_1_minute,
            n_bars=1,
            extended_session=True
        )
        
        if data is not None and not data.empty:
            row = data.iloc[-1]
            timestamp = data.index[-1]
            
            print(f"📊 Data shape: {data.shape}")
            print(f"📅 Timestamp type: {type(timestamp)}")
            print(f"📅 Timestamp value: {timestamp}")
            print(f"📅 Timestamp repr: {repr(timestamp)}")
            
            # Try converting to datetime
            if hasattr(timestamp, 'to_pydatetime'):
                converted = timestamp.to_pydatetime()
                print(f"📅 Converted type: {type(converted)}")
                print(f"📅 Converted value: {converted}")
            
            # Check row data
            print(f"💰 Row data types:")
            for col in data.columns:
                print(f"  {col}: {type(row[col])} = {row[col]}")
                
            return True
        else:
            print("⚠️ No data returned")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_timestamp_format()