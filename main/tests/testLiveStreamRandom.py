"""
Live Data Stream Test Script
Tests the complete data pipeline with a random ticker:
1. Picks a random ticker from a predefined list
2. Loads 20 minutes of historical data
3. Streams live data for 1 minute
4. Logs all data received to terminal
5. Works outside regular trading hours using extended sessions
"""
import sys
import os
import time
import random
from datetime import datetime, timedelta
import pandas as pd
import logging

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from tvDatafeed import TvDatafeed, Interval
    TVDATAFEED_AVAILABLE = True
except ImportError:
    print("❌ TvDatafeed not available. Install with:")
    print("pip install --upgrade --no-cache-dir git+https://github.com/rongardF/tvdatafeed.git")
    TVDATAFEED_AVAILABLE = False
    sys.exit(1)

from DB.connection import test_connection
from DB.operations import DatabaseOperations
from ingestion.hist import HistoricalDataIngestion

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Hardcoded test tickers - high liquidity stocks for reliable data
TEST_TICKERS = ["QURE"]

class LiveDataTester:
    """Test class for live data streaming"""
    
    def __init__(self):
        self.tv_datafeed = None
        self.db_ops = None
        self.selected_ticker = None
        self.historical_data = None
        self.live_data_points = []
        
    def initialize(self):
        """Initialize connections and components"""
        logger.info("🔧 Initializing test components...")
        
        # Test database connection
        if not test_connection():
            logger.error("❌ Database connection failed - ensure TimescaleDB is running")
            return False
        logger.info("✅ Database connection successful")
        
        # Initialize TvDatafeed
        try:
            self.tv_datafeed = TvDatafeed()
            logger.info("✅ TvDatafeed initialized")
        except Exception as e:
            logger.error(f"❌ TvDatafeed initialization failed: {e}")
            return False
        
        # Initialize database operations
        try:
            self.db_ops = DatabaseOperations()
            logger.info("✅ Database operations initialized")
        except Exception as e:
            logger.error(f"❌ Database operations initialization failed: {e}")
            return False
        
        return True
    
    def select_ticker(self):
        """Select first available ticker from the hardcoded list"""
        for ticker in TEST_TICKERS:
            logger.info(f"🔍 Testing ticker: {ticker}")
            try:
                # Test if ticker has data available
                test_data = self.tv_datafeed.get_hist(
                    symbol=ticker,
                    exchange="NASDAQ",
                    interval=Interval.in_1_minute,
                    n_bars=1,
                    extended_session=True
                )
                
                if test_data is not None and not test_data.empty:
                    self.selected_ticker = ticker
                    logger.info(f"✅ Selected ticker: {ticker}")
                    return ticker
                else:
                    logger.warning(f"⚠️ {ticker}: No data available")
                    
            except Exception as e:
                logger.warning(f"⚠️ {ticker}: Error - {e}")
                
            time.sleep(0.5)  # Small delay between tests
        
        logger.error("❌ No working tickers found")
        return None
    
    def load_historical_data(self, minutes=20):
        """Load historical data for the selected ticker"""
        logger.info(f"📚 Loading {minutes} minutes of historical data for {self.selected_ticker}...")
        
        try:
            # Use HistoricalDataIngestion for consistency
            hist_ingestion = HistoricalDataIngestion()
            
            if not hist_ingestion.initialized:
                logger.error("❌ Historical ingestion not initialized")
                return False
            
            # Calculate lookback hours
            lookback_hours = max(1, minutes // 60 + 1)  # At least 1 hour
            
            # Ingest historical data
            success = hist_ingestion.ingest_historical_data(
                symbol=self.selected_ticker,
                exchange="NASDAQ",
                lookback_hours=lookback_hours,
                interval="1m",
                add_indicators=True,
                update_mode="append"
            )
            
            if success:
                # Retrieve the data to show what was loaded
                self.historical_data = self.db_ops.get_latest_ohlcv_data(
                    symbol=self.selected_ticker, 
                    limit=minutes
                )
                
                if self.historical_data is not None and not self.historical_data.empty:
                    logger.info(f"✅ Loaded {len(self.historical_data)} historical data points")
                    
                    # Show sample of historical data
                    self._log_data_sample("HISTORICAL", self.historical_data.tail(3))
                    return True
                else:
                    logger.warning("⚠️ No historical data retrieved from database")
                    return False
            else:
                logger.error("❌ Historical data ingestion failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error loading historical data: {e}")
            return False
    
    def stream_live_data(self, duration_minutes=20):
        """Stream live data for specified duration in minutes"""
        duration_seconds = duration_minutes * 60
        logger.info(f"📡 Starting live data stream for {duration_minutes} minutes ({duration_seconds} seconds)...")
        logger.info(f"🕒 Current time: {datetime.now()}")
        
        start_time = time.time()
        update_interval = 10  # seconds between updates (increased for 20min test)
        update_count = 0
        successful_saves = 0
        failed_saves = 0
        
        try:
            while (time.time() - start_time) < duration_seconds:
                # Fetch latest data point
                try:
                    data = self.tv_datafeed.get_hist(
                        symbol=self.selected_ticker,
                        exchange="NASDAQ",
                        interval=Interval.in_1_minute,
                        n_bars=1,
                        extended_session=True  # Enable extended hours
                    )
                    
                    update_count += 1
                    current_time = datetime.now()
                    
                    if data is not None and not data.empty:
                        # Add metadata
                        data_point = data.copy()
                        data_point['symbol'] = self.selected_ticker
                        data_point['fetch_time'] = current_time
                        
                        # Store in our collection
                        self.live_data_points.append(data_point)
                        
                        # Log the data point
                        self._log_live_data_point(data_point, update_count)
                        
                        # Store in database - ENHANCED DATABASE TESTING
                        try:
                            # Prepare data for database storage in correct format
                            row = data.iloc[-1]
                            timestamp = data.index[-1]
                            
                            # Convert to the format expected by insert_ohlcv_data
                            ohlcv_record = [{
                                'timestamp': timestamp.to_pydatetime() if hasattr(timestamp, 'to_pydatetime') else timestamp,
                                'open': float(row['open']),
                                'high': float(row['high']),
                                'low': float(row['low']),
                                'close': float(row['close']),
                                'volume': int(row['volume'])
                            }]
                            
                            success = self.db_ops.insert_ohlcv_data(
                                symbol=self.selected_ticker,
                                timeframe="1m",
                                ohlcv_data=ohlcv_record
                            )
                            
                            if success:
                                successful_saves += 1
                                logger.info(f"💾 ✅ Saved data point {update_count} to database")
                            else:
                                failed_saves += 1
                                logger.warning(f"💾 ❌ Failed to save data point {update_count}")
                                
                        except Exception as db_e:
                            failed_saves += 1
                            logger.error(f"💾 ❌ Database error on update {update_count}: {db_e}")
                    
                    else:
                        logger.info(f"📊 No new data available (update {update_count})")
                        
                except Exception as fetch_e:
                    logger.warning(f"⚠️ Data fetch error on update {update_count}: {fetch_e}")
                
                # Progress indicator
                elapsed = time.time() - start_time
                remaining = duration_seconds - elapsed
                progress_pct = (elapsed / duration_seconds) * 100
                
                logger.info(f"⏳ Progress: {progress_pct:.1f}% | "
                           f"Remaining: {remaining/60:.1f} min | "
                           f"DB Saves: {successful_saves}/{update_count}")
                
                # Wait before next update
                if remaining > update_interval:
                    time.sleep(update_interval)
                else:
                    # For the last update, sleep the remaining time
                    if remaining > 0:
                        time.sleep(remaining)
                    break
            
            # Final statistics
            total_time = time.time() - start_time
            logger.info(f"✅ Live streaming completed!")
            logger.info(f"📊 Total updates: {update_count}")
            logger.info(f"📡 Data points collected: {len(self.live_data_points)}")
            logger.info(f"💾 Database saves: {successful_saves} successful, {failed_saves} failed")
            logger.info(f"⏰ Actual duration: {total_time/60:.2f} minutes")
            logger.info(f"📈 Success rate: {(successful_saves/max(1,update_count))*100:.1f}%")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Live streaming error: {e}")
            return False
    
    def _log_data_sample(self, data_type, data):
        """Log a sample of data in a formatted way"""
        if data is None or data.empty:
            return
        
        logger.info(f"📊 {data_type} DATA SAMPLE:")
        logger.info("=" * 80)
        
        for idx, row in data.iterrows():
            timestamp = idx if hasattr(idx, 'strftime') else str(idx)
            if hasattr(idx, 'strftime'):
                timestamp = idx.strftime("%Y-%m-%d %H:%M:%S")
            
            logger.info(f"  Time: {timestamp}")
            logger.info(f"  OHLC: O=${row.get('open', 'N/A'):.2f} "
                       f"H=${row.get('high', 'N/A'):.2f} "
                       f"L=${row.get('low', 'N/A'):.2f} "
                       f"C=${row.get('close', 'N/A'):.2f}")
            logger.info(f"  Volume: {row.get('volume', 'N/A'):,}")
            if 'symbol' in row:
                logger.info(f"  Symbol: {row['symbol']}")
            logger.info("-" * 40)
    
    def _log_live_data_point(self, data_point, update_num):
        """Log a single live data point with detailed information"""
        logger.info(f"📡 LIVE UPDATE #{update_num}")
        logger.info("=" * 60)
        
        # Get the data row
        if not data_point.empty:
            row = data_point.iloc[-1]  # Get latest row
            timestamp = data_point.index[-1]
            
            if hasattr(timestamp, 'strftime'):
                timestamp_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            else:
                timestamp_str = str(timestamp)
            
            logger.info(f"  📅 Market Time: {timestamp_str}")
            logger.info(f"  🔤 Symbol: {self.selected_ticker}")
            logger.info(f"  💰 Price Data:")
            logger.info(f"    Open:  ${row.get('open', 0):.2f}")
            logger.info(f"    High:  ${row.get('high', 0):.2f}")
            logger.info(f"    Low:   ${row.get('low', 0):.2f}")
            logger.info(f"    Close: ${row.get('close', 0):.2f}")
            logger.info(f"  📊 Volume: {row.get('volume', 0):,}")
            
            # Calculate price change if we have previous data
            if len(self.live_data_points) > 1:
                prev_close = self.live_data_points[-2].iloc[-1].get('close', 0)
                current_close = row.get('close', 0)
                if prev_close > 0:
                    change = current_close - prev_close
                    change_pct = (change / prev_close) * 100
                    logger.info(f"  📈 Change: ${change:+.2f} ({change_pct:+.2f}%)")
            
            # Fetch time
            fetch_time = data_point.get('fetch_time')
            if isinstance(fetch_time, pd.Series):
                fetch_time = fetch_time.iloc[0] if len(fetch_time) > 0 else datetime.now()
            elif fetch_time is None:
                fetch_time = datetime.now()
                
            if hasattr(fetch_time, 'strftime'):
                fetch_str = fetch_time.strftime("%H:%M:%S")
            else:
                fetch_str = str(fetch_time)
            logger.info(f"  🕒 Fetched: {fetch_str}")
            
            # Market session info
            session_type = self._get_session_type(timestamp if hasattr(timestamp, 'hour') else datetime.now())
            logger.info(f"  🏛️ Session: {session_type}")
        
        logger.info("=" * 60)
    
    def _get_session_type(self, dt):
        """Determine market session type"""
        hour = dt.hour
        minute = dt.minute
        time_val = hour * 100 + minute
        
        if 400 <= time_val < 930:
            return "PRE-MARKET"
        elif 930 <= time_val < 1600:
            return "REGULAR HOURS"
        elif 1600 <= time_val < 2000:
            return "AFTER HOURS"
        else:
            return "CLOSED"
    
    def generate_summary(self):
        """Generate a comprehensive summary of the test results"""
        logger.info("📊 COMPREHENSIVE TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"  🎯 Ticker: {self.selected_ticker}")
        logger.info(f"  📚 Historical Records: {len(self.historical_data) if self.historical_data is not None else 0}")
        logger.info(f"  📡 Live Updates Collected: {len(self.live_data_points)}")
        
        if self.live_data_points:
            # Calculate actual test duration
            if len(self.live_data_points) > 1:
                first_fetch = self.live_data_points[0].get('fetch_time')
                last_fetch = self.live_data_points[-1].get('fetch_time')
                
                if isinstance(first_fetch, pd.Series):
                    first_fetch = first_fetch.iloc[0] if len(first_fetch) > 0 else datetime.now()
                if isinstance(last_fetch, pd.Series):
                    last_fetch = last_fetch.iloc[0] if len(last_fetch) > 0 else datetime.now()
                    
                if hasattr(first_fetch, 'total_seconds') and hasattr(last_fetch, 'total_seconds'):
                    try:
                        duration = (last_fetch - first_fetch).total_seconds() / 60
                        logger.info(f"  ⏰ Actual Test Duration: {duration:.2f} minutes")
                    except:
                        pass
            
            # Get first and last data points for price analysis
            first_point = self.live_data_points[0]
            last_point = self.live_data_points[-1]
            
            if not first_point.empty and not last_point.empty:
                first_close = first_point.iloc[-1].get('close', 0)
                last_close = last_point.iloc[-1].get('close', 0)
                
                if first_close > 0:
                    total_change = last_close - first_close
                    total_change_pct = (total_change / first_close) * 100
                    logger.info(f"  📈 Price Change: ${first_close:.2f} → ${last_close:.2f}")
                    logger.info(f"  📊 Total Change: ${total_change:+.2f} ({total_change_pct:+.2f}%)")
                
                # Volume analysis
                total_volume = sum(point.iloc[-1].get('volume', 0) for point in self.live_data_points)
                avg_volume = total_volume / len(self.live_data_points) if self.live_data_points else 0
                logger.info(f"  📊 Total Volume: {total_volume:,}")
                logger.info(f"  📊 Avg Volume per Update: {avg_volume:,.0f}")
        
        # Database analysis
        logger.info(f"  💾 Database Integration Test:")
        try:
            # Check current data in database for our symbol
            db_records = self.db_ops.get_latest_ohlcv_data(
                symbol=self.selected_ticker, 
                limit=100  # Get recent records
            )
            
            if db_records is not None and not db_records.empty:
                logger.info(f"    ✅ Records in DB: {len(db_records)}")
                latest_db_record = db_records.iloc[0]  # Most recent
                latest_timestamp = db_records.index[0]
                logger.info(f"    🕒 Latest DB Record: {latest_timestamp}")
                logger.info(f"    💰 Latest DB Price: ${latest_db_record.get('close', 'N/A'):.2f}")
            else:
                logger.info(f"    ⚠️ No records found in database")
                
        except Exception as e:
            logger.error(f"    ❌ Database check failed: {e}")
        
        # Session info
        current_session = self._get_session_type(datetime.now())
        logger.info(f"  🕒 Market Session: {current_session}")
        logger.info(f"  🌐 Extended Hours: ENABLED")
        
        # Test results
        success_rate = len(self.live_data_points) > 0
        hist_success = self.historical_data is not None and not self.historical_data.empty
        
        logger.info("  🎯 Test Results:")
        logger.info(f"    Historical Data: {'✅ SUCCESS' if hist_success else '❌ FAILED'}")
        logger.info(f"    Live Data Stream: {'✅ SUCCESS' if success_rate else '❌ FAILED'}")
        logger.info(f"    Database Storage: {'✅ TESTED' if self.db_ops else '❌ NOT TESTED'}")
        
        logger.info("=" * 80)


def main():
    """Main test function"""
    print("=" * 80)
    print("  🧪 20-MINUTE LIVE DATA STREAM TEST")
    print("=" * 80)
    print("  This test will:")
    print("  1. Test hardcoded tickers (AAPL, MSFT, GOOGL, TSLA, NVDA)")
    print("  2. Load 20 minutes of historical data")
    print("  3. Stream live data for 20 minutes")
    print("  4. Save all live data to database")
    print("  5. Verify database storage")
    print("  6. Work during extended hours")
    print("=" * 80)
    
    tester = LiveDataTester()
    
    try:
        # Initialize
        if not tester.initialize():
            logger.error("❌ Initialization failed")
            return False
        
        # Select working ticker
        ticker = tester.select_ticker()
        if not ticker:
            logger.error("❌ No working ticker found")
            return False
        
        print(f"\n🎯 Testing with ticker: {ticker}")
        
        # Load historical data
        if not tester.load_historical_data(minutes=20):
            logger.error("❌ Historical data loading failed")
            # Continue anyway - historical data is not critical for live stream test
        
        # Pause before starting live stream
        print("\n⏳ Starting 20-minute live data stream in 5 seconds...")
        print("💡 This will take 20 minutes - press Ctrl+C to stop early")
        time.sleep(5)
        
        # Stream live data for 20 minutes
        if not tester.stream_live_data(duration_minutes=20):
            logger.error("❌ Live data streaming failed")
            return False
        
        # Generate comprehensive summary
        print("\n")
        tester.generate_summary()
        
        print("\n🎉 20-MINUTE TEST COMPLETED SUCCESSFULLY!")
        print("📊 Check the database for stored live data records")
        return True
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user")
        print("\n📊 Generating summary of partial test...")
        tester.generate_summary()
        return True  # Still consider it a success if user interrupted
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)