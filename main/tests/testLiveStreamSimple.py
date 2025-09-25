"""
Simple Live Data Test - No Database Required
Tests TvDatafeed with hardcoded tickers for 20 minutes
Saves data to CSV files instead of database
"""
import time
import pandas as pd
from datetime import datetime, timedelta
from tvDatafeed import TvDatafeed, Interval

# Hardcoded test tickers
TEST_TICKERS = ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]

def get_session_info():
    """Get current market session information"""
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    time_val = hour * 100 + minute
    
    if 400 <= time_val < 930:
        return "🌅 PRE-MARKET", True
    elif 930 <= time_val < 1600:
        return "🏛️ REGULAR HOURS", False
    elif 1600 <= time_val < 2000:
        return "🌆 AFTER HOURS", True
    else:
        return "🌙 CLOSED", True

def find_working_ticker(tv):
    """Find a ticker that has available data"""
    print("🔍 Testing tickers for data availability...")
    
    for ticker in TEST_TICKERS:
        try:
            print(f"  Testing {ticker}...")
            data = tv.get_hist(
                symbol=ticker,
                exchange="NASDAQ",
                interval=Interval.in_1_minute,
                n_bars=1,
                extended_session=True
            )
            
            if data is not None and not data.empty:
                price = data.iloc[-1]['close']
                timestamp = data.index[-1]
                print(f"  ✅ {ticker} working: ${price:.2f} at {timestamp}")
                return ticker
            else:
                print(f"  ⚠️ {ticker}: No data")
                
        except Exception as e:
            print(f"  ❌ {ticker}: Error - {e}")
        
        time.sleep(0.5)
    
    return None

def load_historical_data(tv, ticker, minutes=20):
    """Load historical data"""
    print(f"\n📚 Loading {minutes} minutes of historical data for {ticker}...")
    
    try:
        data = tv.get_hist(
            symbol=ticker,
            exchange="NASDAQ",
            interval=Interval.in_1_minute,
            n_bars=minutes,
            extended_session=True
        )
        
        if data is not None and not data.empty:
            print(f"✅ Loaded {len(data)} historical records")
            
            # Save to CSV
            filename = f"{ticker}_historical_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            data.to_csv(filename)
            print(f"💾 Saved historical data to {filename}")
            
            # Show sample
            latest = data.iloc[-1]
            earliest = data.iloc[0]
            print(f"📊 Time range: {data.index[0]} to {data.index[-1]}")
            print(f"📊 Price range: ${earliest['close']:.2f} to ${latest['close']:.2f}")
            
            return data, filename
        else:
            print("⚠️ No historical data retrieved")
            return None, None
            
    except Exception as e:
        print(f"❌ Historical data error: {e}")
        return None, None

def stream_live_data(tv, ticker, duration_minutes=20):
    """Stream live data and save to CSV"""
    print(f"\n📡 Starting live data stream for {duration_minutes} minutes...")
    
    session, is_extended = get_session_info()
    print(f"🕒 Session: {session}")
    print(f"📊 Extended hours: {'ENABLED' if is_extended else 'DISABLED'}")
    
    start_time = time.time()
    duration_seconds = duration_minutes * 60
    update_interval = 10  # seconds
    
    live_data_points = []
    csv_filename = f"{ticker}_live_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    print(f"\n{'='*60}")
    print(f"🎯 LIVE STREAM: {ticker}")
    print(f"💾 Saving to: {csv_filename}")
    print(f"{'='*60}")
    
    update_count = 0
    
    try:
        while (time.time() - start_time) < duration_seconds:
            try:
                # Fetch latest data
                data = tv.get_hist(
                    symbol=ticker,
                    exchange="NASDAQ",
                    interval=Interval.in_1_minute,
                    n_bars=1,
                    extended_session=True
                )
                
                update_count += 1
                current_time = datetime.now()
                
                if data is not None and not data.empty:
                    # Add metadata
                    data_with_meta = data.copy()
                    data_with_meta['symbol'] = ticker
                    data_with_meta['fetch_time'] = current_time
                    data_with_meta['update_number'] = update_count
                    
                    live_data_points.append(data_with_meta)
                    
                    # Log the update
                    row = data.iloc[-1]
                    data_time = data.index[-1].strftime("%H:%M:%S")
                    price = row['close']
                    volume = row['volume']
                    
                    print(f"📊 #{update_count:2d} | {current_time.strftime('%H:%M:%S')} | "
                          f"Data: {data_time} | ${price:.2f} | Vol: {volume:,}")
                    
                    # Save to CSV incrementally
                    if len(live_data_points) == 1:
                        # First save - create file with headers
                        data_with_meta.to_csv(csv_filename)
                    else:
                        # Append to existing file
                        data_with_meta.to_csv(csv_filename, mode='a', header=False)
                
                else:
                    print(f"⚠️ #{update_count:2d} | {current_time.strftime('%H:%M:%S')} | No data available")
                
            except Exception as e:
                print(f"❌ #{update_count+1:2d} | {current_time.strftime('%H:%M:%S')} | Error: {e}")
            
            # Progress update
            elapsed = time.time() - start_time
            remaining = duration_seconds - elapsed
            progress = (elapsed / duration_seconds) * 100
            
            if update_count % 5 == 0:  # Every 5 updates
                print(f"⏳ Progress: {progress:.1f}% | Remaining: {remaining/60:.1f} min | Updates: {update_count}")
            
            # Wait for next update
            if remaining > update_interval:
                time.sleep(update_interval)
            elif remaining > 0:
                time.sleep(remaining)
            else:
                break
    
    except KeyboardInterrupt:
        print(f"\n🛑 Stream interrupted by user after {update_count} updates")
    
    # Final summary
    elapsed_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"✅ Live streaming completed!")
    print(f"📊 Updates attempted: {update_count}")
    print(f"📡 Data points collected: {len(live_data_points)}")
    print(f"⏰ Actual duration: {elapsed_time/60:.2f} minutes")
    print(f"💾 Data saved to: {csv_filename}")
    
    if len(live_data_points) >= 2:
        first_price = live_data_points[0].iloc[-1]['close']
        last_price = live_data_points[-1].iloc[-1]['close']
        change = last_price - first_price
        change_pct = (change / first_price) * 100
        print(f"📈 Price movement: ${first_price:.2f} → ${last_price:.2f}")
        print(f"📊 Total change: ${change:+.2f} ({change_pct:+.2f}%)")
    
    print(f"{'='*60}")
    
    return live_data_points, csv_filename

def main():
    """Main test function"""
    print("=" * 80)
    print("  🧪 20-MINUTE LIVE DATA TEST (CSV MODE)")
    print("=" * 80)
    print("  This test will:")
    print("  1. Test hardcoded tickers (AAPL, MSFT, GOOGL, TSLA, NVDA)")
    print("  2. Load 20 minutes of historical data")
    print("  3. Stream live data for 20 minutes")
    print("  4. Save all data to CSV files")
    print("  5. Work during extended hours")
    print("=" * 80)
    
    try:
        # Initialize TvDatafeed
        print("🔧 Initializing TvDatafeed...")
        tv = TvDatafeed()
        print("✅ TvDatafeed initialized")
        
        # Find working ticker
        ticker = find_working_ticker(tv)
        if not ticker:
            print("❌ No working tickers found!")
            return False
        
        print(f"\n🎯 Selected ticker: {ticker}")
        
        # Load historical data
        hist_data, hist_file = load_historical_data(tv, ticker, minutes=20)
        
        # Brief pause
        print(f"\n⏳ Starting 20-minute live stream in 5 seconds...")
        print(f"💡 This will take 20 minutes - press Ctrl+C to stop early")
        time.sleep(5)
        
        # Stream live data
        live_data, live_file = stream_live_data(tv, ticker, duration_minutes=20)
        
        # Final summary
        print(f"\n🎉 TEST COMPLETED!")
        print(f"🎯 Ticker: {ticker}")
        print(f"📚 Historical records: {len(hist_data) if hist_data is not None else 0}")
        print(f"📡 Live updates: {len(live_data)}")
        if hist_file:
            print(f"💾 Historical data: {hist_file}")
        if live_file:
            print(f"💾 Live data: {live_file}")
        
        return True
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
        return True
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)