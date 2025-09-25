"""
Quick TvDatafeed Connection Test
Tests basic connectivity and available data
"""
from tvDatafeed import TvDatafeed, Interval
import time
from datetime import datetime

def test_basic_connection():
    """Test basic TvDatafeed functionality"""
    print("🔧 Testing TvDatafeed basic connection...")
    
    try:
        tv = TvDatafeed()
        print("✅ TvDatafeed initialized")
        
        # Test with popular symbols and different exchanges
        test_symbols = [
            ("AAPL", "NASDAQ"),
            ("MSFT", "NASDAQ"), 
            ("SPY", "AMEX"),
            ("QQQ", "NASDAQ"),
            ("TSLA", "NASDAQ")
        ]
        
        for symbol, exchange in test_symbols:
            print(f"\n📊 Testing {symbol} ({exchange})...")
            try:
                # Try to get just 1 bar of recent data
                data = tv.get_hist(
                    symbol=symbol,
                    exchange=exchange,
                    interval=Interval.in_1_minute,
                    n_bars=1,
                    extended_session=True
                )
                
                if data is not None and not data.empty:
                    latest = data.iloc[-1]
                    timestamp = data.index[-1]
                    print(f"✅ {symbol}: ${latest['close']:.2f} at {timestamp}")
                    return True  # Success! Found working data
                else:
                    print(f"⚠️ {symbol}: No data returned")
                    
            except Exception as e:
                print(f"❌ {symbol}: Error - {e}")
            
            # Small delay between requests
            time.sleep(1)
        
        print("\n⚠️ No working symbols found - may be connection/access issues")
        return False
        
    except Exception as e:
        print(f"❌ TvDatafeed initialization failed: {e}")
        return False

def test_intervals():
    """Test different time intervals"""
    print("\n📊 Available intervals:")
    intervals = [
        'in_1_minute', 'in_3_minute', 'in_5_minute', 'in_15_minute', 
        'in_30_minute', 'in_1_hour', 'in_4_hour', 'in_daily'
    ]
    
    for interval_name in intervals:
        if hasattr(Interval, interval_name):
            print(f"  ✅ {interval_name}")
        else:
            print(f"  ❌ {interval_name}")

def main():
    print("=" * 60)
    print("  🧪 QUICK TVDATAFEED TEST")
    print("=" * 60)
    print(f"🕒 Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Test intervals
    test_intervals()
    
    # Test connection
    success = test_basic_connection()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ TvDatafeed is working!")
    else:
        print("⚠️ TvDatafeed connection issues - may be:")
        print("  - Network/internet issues")
        print("  - TradingView server issues") 
        print("  - Free tier limitations")
        print("  - After hours data limitations")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    main()