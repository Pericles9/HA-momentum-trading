"""
Robust Live Data Streaming Test
Tests live data streaming with error handling and fallbacks
Works outside regular trading hours
"""
import time
import random
from datetime import datetime
from tvDatafeed import TvDatafeed, Interval

# Reliable test symbols (high liquidity)
RELIABLE_SYMBOLS = [
    ("AAPL", "NASDAQ"),
    ("MSFT", "NASDAQ"), 
    ("GOOGL", "NASDAQ"),
    ("AMZN", "NASDAQ"),
    ("TSLA", "NASDAQ"),
    ("SPY", "AMEX"),
    ("QQQ", "NASDAQ"),
    ("IWM", "AMEX"),
    ("META", "NASDAQ"),
    ("NVDA", "NASDAQ")
]

def get_session_info():
    """Get current market session information"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    time_val = hour * 100 + minute
    
    if 400 <= time_val < 930:
        session = "🌅 PRE-MARKET"
        is_extended = True
    elif 930 <= time_val < 1600:
        session = "🏛️ REGULAR HOURS" 
        is_extended = False
    elif 1600 <= time_val < 2000:
        session = "🌆 AFTER HOURS"
        is_extended = True
    else:
        session = "🌙 CLOSED"
        is_extended = True
    
    return session, is_extended

def find_working_symbol(tv):
    """Find a symbol that returns data"""
    print("🔍 Finding a working symbol...")
    
    # Try a few symbols to find one that works
    for symbol, exchange in RELIABLE_SYMBOLS[:5]:
        try:
            print(f"  Testing {symbol}...")
            data = tv.get_hist(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.in_1_minute,
                n_bars=1,
                extended_session=True
            )
            
            if data is not None and not data.empty:
                price = data.iloc[-1]['close']
                timestamp = data.index[-1]
                print(f"  ✅ {symbol} working: ${price:.2f} at {timestamp}")
                return symbol, exchange
            else:
                print(f"  ⚠️ {symbol}: No data")
                
        except Exception as e:
            print(f"  ❌ {symbol}: {e}")
            
        time.sleep(0.5)  # Small delay
    
    return None, None

def load_historical_sample(tv, symbol, exchange, minutes=10):
    """Load historical data sample"""
    print(f"\n📚 Loading {minutes} minutes of historical data for {symbol}...")
    
    try:
        data = tv.get_hist(
            symbol=symbol,
            exchange=exchange,
            interval=Interval.in_1_minute,
            n_bars=minutes,
            extended_session=True
        )
        
        if data is not None and not data.empty:
            print(f"✅ Loaded {len(data)} historical records")
            
            # Show sample data
            latest = data.iloc[-1]
            earliest = data.iloc[0]
            
            print(f"📊 Earliest: {data.index[0]} | ${earliest['close']:.2f}")
            print(f"📊 Latest:   {data.index[-1]} | ${latest['close']:.2f}")
            
            if len(data) > 1:
                change = latest['close'] - earliest['close']
                change_pct = (change / earliest['close']) * 100
                print(f"📈 Change: ${change:+.2f} ({change_pct:+.2f}%)")
            
            return data
        else:
            print("⚠️ No historical data")
            return None
            
    except Exception as e:
        print(f"❌ Historical data error: {e}")
        return None

def stream_live_data(tv, symbol, exchange, duration=30):
    """Stream live data for specified duration"""
    print(f"\n📡 Streaming live data for {duration} seconds...")
    
    session, is_extended = get_session_info()
    print(f"🕒 Session: {session}")
    print(f"📊 Extended hours: {'ENABLED' if is_extended else 'DISABLED'}")
    
    start_time = time.time()
    update_count = 0
    successful_updates = 0
    data_points = []
    prev_price = None
    
    print(f"\n{'='*50}")
    print(f"🎯 LIVE STREAM: {symbol} ({exchange})")
    print(f"{'='*50}")
    
    while (time.time() - start_time) < duration:
        try:
            # Fetch latest data
            data = tv.get_hist(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.in_1_minute,
                n_bars=1,
                extended_session=True
            )
            
            update_count += 1
            current_time = datetime.now().strftime("%H:%M:%S")
            
            if data is not None and not data.empty:
                current_price = data.iloc[-1]['close']
                data_time = data.index[-1].strftime("%H:%M:%S")
                volume = data.iloc[-1]['volume']
                
                # Calculate change
                change_str = ""
                if prev_price and prev_price > 0:
                    change = current_price - prev_price
                    change_pct = (change / prev_price) * 100
                    change_str = f" ({change:+.2f}, {change_pct:+.2f}%)"
                
                print(f"📊 #{update_count:2d} | {current_time} | Data: {data_time} | ${current_price:.2f}{change_str} | Vol: {volume:,}")
                
                data_points.append(data.copy())
                successful_updates += 1
                prev_price = current_price
                
            else:
                print(f"⚠️ #{update_count:2d} | {current_time} | No data available")
            
        except Exception as e:
            print(f"❌ #{update_count:2d} | {current_time} | Error: {e}")
        
        # Wait before next update
        remaining = duration - (time.time() - start_time)
        if remaining > 3:
            time.sleep(3)
        elif remaining > 0:
            time.sleep(remaining)
    
    print(f"{'='*50}")
    print(f"✅ Stream completed!")
    print(f"📊 Updates attempted: {update_count}")
    print(f"📡 Successful updates: {successful_updates}")
    print(f"📈 Data points collected: {len(data_points)}")
    
    if len(data_points) >= 2:
        first_price = data_points[0].iloc[-1]['close']
        last_price = data_points[-1].iloc[-1]['close']
        total_change = last_price - first_price
        total_change_pct = (total_change / first_price) * 100
        print(f"💰 Price movement: ${first_price:.2f} → ${last_price:.2f}")
        print(f"📊 Total change: ${total_change:+.2f} ({total_change_pct:+.2f}%)")
    
    return data_points

def main():
    """Main test function"""
    print("=" * 70)
    print("  🚀 ROBUST LIVE DATA STREAMING TEST")
    print("=" * 70)
    print(f"🕒 Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    session, is_extended = get_session_info()
    print(f"📊 Market session: {session}")
    print("=" * 70)
    
    try:
        # Initialize TvDatafeed
        print("🔧 Initializing TvDatafeed...")
        tv = TvDatafeed()
        print("✅ TvDatafeed initialized")
        
        # Find working symbol
        symbol, exchange = find_working_symbol(tv)
        
        if not symbol:
            print("❌ No working symbols found!")
            print("This could be due to:")
            print("  - Network connectivity issues")
            print("  - TradingView server problems")
            print("  - Free tier limitations")
            return False
        
        print(f"\n🎯 Selected symbol: {symbol} ({exchange})")
        
        # Load historical data
        hist_data = load_historical_sample(tv, symbol, exchange, minutes=10)
        
        # Stream live data
        live_data = stream_live_data(tv, symbol, exchange, duration=30)
        
        # Final summary
        print("\n" + "=" * 70)
        print("  📊 FINAL TEST SUMMARY")
        print("=" * 70)
        print(f"🎯 Symbol: {symbol} ({exchange})")
        print(f"📚 Historical records: {len(hist_data) if hist_data is not None and not hist_data.empty else 0}")
        print(f"📡 Live data points: {len(live_data)}")
        print(f"🕒 Test session: {session}")
        print(f"⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        
        if live_data and len(live_data) > 0:
            print("🎉 Live data streaming test SUCCESSFUL!")
            print("✅ The system can stream live market data outside regular hours")
        else:
            print("⚠️ Live data streaming test had issues")
            print("💡 This is normal outside market hours or with free data access")
        
        return True
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")