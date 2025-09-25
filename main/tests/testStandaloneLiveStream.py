"""
Standalone Live Data Test Script
Simple test that picks a random ticker and streams live data for 1 minute
Works outside regular trading hours with extended session data
No database dependencies - logs everything to terminal
"""
import time
import random
from datetime import datetime, timedelta
import pandas as pd

# Test if TvDatafeed is available
try:
    from tvDatafeed import TvDatafeed, Interval
    TVDATAFEED_AVAILABLE = True
    print("✅ TvDatafeed imported successfully")
except ImportError:
    print("❌ TvDatafeed not available. Install with:")
    print("pip install --upgrade --no-cache-dir git+https://github.com/rongardF/tvdatafeed.git")
    exit(1)

# Popular tickers for testing
TEST_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", 
    "META", "NVDA", "NFLX", "AMD", "CRM",
    "UBER", "PYPL", "ADBE", "INTC", "BA"
]

def get_session_type(dt=None):
    """Determine current market session"""
    if dt is None:
        dt = datetime.now()
    
    hour = dt.hour
    minute = dt.minute
    time_val = hour * 100 + minute
    
    if 400 <= time_val < 930:
        return "🌅 PRE-MARKET"
    elif 930 <= time_val < 1600:
        return "🏛️ REGULAR HOURS"
    elif 1600 <= time_val < 2000:
        return "🌆 AFTER HOURS"
    else:
        return "🌙 CLOSED"

def format_data_point(data, symbol, update_num, prev_close=None):
    """Format a data point for logging"""
    if data is None or data.empty:
        return "No data available"
    
    row = data.iloc[-1]
    timestamp = data.index[-1]
    
    # Format timestamp
    if hasattr(timestamp, 'strftime'):
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    else:
        time_str = str(timestamp)
    
    # Basic OHLCV data
    open_price = row.get('open', 0)
    high_price = row.get('high', 0)
    low_price = row.get('low', 0)
    close_price = row.get('close', 0)
    volume = row.get('volume', 0)
    
    # Calculate change if previous close available
    change_str = ""
    if prev_close and prev_close > 0 and close_price > 0:
        change = close_price - prev_close
        change_pct = (change / prev_close) * 100
        change_str = f" | Change: ${change:+.2f} ({change_pct:+.2f}%)"
    
    # Session type
    session = get_session_type(timestamp if hasattr(timestamp, 'hour') else datetime.now())
    
    output = f"""
📡 LIVE UPDATE #{update_num} - {symbol}
{'=' * 60}
🕒 Market Time: {time_str}
🕐 Fetch Time:  {datetime.now().strftime('%H:%M:%S')}
{session}

💰 PRICE DATA:
   Open:  ${open_price:.2f}
   High:  ${high_price:.2f}  
   Low:   ${low_price:.2f}
   Close: ${close_price:.2f}{change_str}

📊 Volume: {volume:,}
{'=' * 60}
"""
    return output

def test_historical_data(tv, symbol, minutes=20):
    """Test loading historical data"""
    print(f"\n📚 Loading {minutes} minutes of historical data for {symbol}...")
    
    try:
        # Get historical data
        hist_data = tv.get_hist(
            symbol=symbol,
            exchange="NASDAQ",
            interval=Interval.in_1_minute,
            n_bars=minutes,
            extended_session=True
        )
        
        if hist_data is not None and not hist_data.empty:
            print(f"✅ Successfully loaded {len(hist_data)} historical data points")
            
            # Show first few and last few records
            print("\n📊 HISTORICAL DATA SAMPLE (First 3 records):")
            print("-" * 80)
            for i, (timestamp, row) in enumerate(hist_data.head(3).iterrows()):
                time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                print(f"  {i+1}. {time_str} | O:{row['open']:.2f} H:{row['high']:.2f} L:{row['low']:.2f} C:{row['close']:.2f} | Vol:{row['volume']:,}")
            
            if len(hist_data) > 6:
                print("  ...")
                print("\n📊 HISTORICAL DATA SAMPLE (Last 3 records):")
                print("-" * 80)
                for i, (timestamp, row) in enumerate(hist_data.tail(3).iterrows()):
                    time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"  {len(hist_data)-2+i}. {time_str} | O:{row['open']:.2f} H:{row['high']:.2f} L:{row['low']:.2f} C:{row['close']:.2f} | Vol:{row['volume']:,}")
            
            return hist_data
        else:
            print("⚠️ No historical data retrieved")
            return None
            
    except Exception as e:
        print(f"❌ Error loading historical data: {e}")
        return None

def test_live_streaming(tv, symbol, duration_seconds=60):
    """Test live data streaming"""
    print(f"\n📡 Starting live data stream for {duration_seconds} seconds...")
    print(f"🕒 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Symbol: {symbol}")
    print(f"⚙️ Extended hours: ENABLED")
    print(f"📊 Session: {get_session_type()}")
    
    start_time = time.time()
    update_interval = 5  # seconds between updates
    update_count = 0
    live_data_points = []
    
    try:
        while (time.time() - start_time) < duration_seconds:
            elapsed = time.time() - start_time
            remaining = duration_seconds - elapsed
            
            try:
                # Fetch latest data
                data = tv.get_hist(
                    symbol=symbol,
                    exchange="NASDAQ", 
                    interval=Interval.in_1_minute,
                    n_bars=1,
                    extended_session=True
                )
                
                update_count += 1
                
                if data is not None and not data.empty:
                    # Get previous close for change calculation
                    prev_close = None
                    if live_data_points:
                        prev_close = live_data_points[-1].iloc[-1].get('close', 0)
                    
                    # Log the data point
                    output = format_data_point(data, symbol, update_count, prev_close)
                    print(output)
                    
                    # Store data point
                    live_data_points.append(data.copy())
                    
                else:
                    print(f"\n📊 UPDATE #{update_count} - No new data available")
                    print(f"🕒 Time: {datetime.now().strftime('%H:%M:%S')} | Session: {get_session_type()}")
                
            except Exception as fetch_error:
                print(f"\n⚠️ UPDATE #{update_count} - Fetch error: {fetch_error}")
            
            # Wait before next update (if time remaining)
            if remaining > update_interval:
                print(f"⏳ Waiting {update_interval}s... ({remaining:.0f}s remaining)")
                time.sleep(update_interval)
            elif remaining > 0:
                time.sleep(remaining)
            else:
                break
        
        # Summary
        print(f"\n✅ Live streaming completed!")
        print(f"📊 Total updates attempted: {update_count}")
        print(f"📡 Data points received: {len(live_data_points)}")
        
        if len(live_data_points) >= 2:
            first_close = live_data_points[0].iloc[-1].get('close', 0)
            last_close = live_data_points[-1].iloc[-1].get('close', 0)
            
            if first_close > 0:
                total_change = last_close - first_close
                total_change_pct = (total_change / first_close) * 100
                print(f"📈 Price movement: ${first_close:.2f} → ${last_close:.2f}")
                print(f"📊 Total change: ${total_change:+.2f} ({total_change_pct:+.2f}%)")
        
        return live_data_points
        
    except Exception as e:
        print(f"❌ Live streaming error: {e}")
        return live_data_points

def main():
    """Main test function"""
    print("=" * 80)
    print("  🧪 STANDALONE LIVE DATA STREAM TEST")
    print("=" * 80)
    print("  📋 This test will:")
    print("    1. Initialize TvDatafeed connection")
    print("    2. Pick a random ticker")
    print("    3. Load 20 minutes of historical data")
    print("    4. Stream live data for 60 seconds")
    print("    5. Log all data to terminal")
    print("    6. Work outside regular trading hours")
    print("=" * 80)
    
    # Initialize TvDatafeed
    print("\n🔧 Initializing TvDatafeed...")
    try:
        tv = TvDatafeed()
        print("✅ TvDatafeed initialized successfully")
    except Exception as e:
        print(f"❌ TvDatafeed initialization failed: {e}")
        return False
    
    # Select random ticker
    symbol = random.choice(TEST_TICKERS)
    print(f"\n🎲 Randomly selected ticker: {symbol}")
    print(f"🕒 Test start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 Current session: {get_session_type()}")
    
    try:
        # Test historical data loading
        hist_data = test_historical_data(tv, symbol, minutes=20)
        
        # Brief pause
        print("\n⏳ Starting live stream in 3 seconds...")
        time.sleep(3)
        
        # Test live streaming
        live_data = test_live_streaming(tv, symbol, duration_seconds=60)
        
        # Final summary
        print("\n" + "=" * 80)
        print("  📊 FINAL TEST SUMMARY")  
        print("=" * 80)
        print(f"  🎯 Symbol: {symbol}")
        print(f"  📚 Historical records: {len(hist_data) if hist_data is not None else 0}")
        print(f"  📡 Live data points: {len(live_data) if live_data else 0}")
        print(f"  🕒 Session during test: {get_session_type()}")
        print(f"  ⏰ Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        print("\n🎉 Test completed successfully!")
        return True
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)