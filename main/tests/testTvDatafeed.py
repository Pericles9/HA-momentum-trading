"""
Test script for TvDatafeed integration
This script tests the TvDatafeed-based historical data ingestion
"""
import sys
import os

# Add the src directory to path for imports (from tests folder)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ingestion.hist import HistoricalDataIngestion
from DB.connection import test_connection

def test_tvdatafeed_basic():
    """Test basic TvDatafeed functionality"""
    
    print("🚀 Testing TvDatafeed Basic Functionality")
    print("=" * 50)
    
    # Test 1: Initialize TvDatafeed
    print("\n1️⃣ Initializing TvDatafeed...")
    ingestion = HistoricalDataIngestion()
    
    if not ingestion.initialized:
        print("❌ Failed to initialize TvDatafeed")
        return False
    
    # Test 2: Search for symbols
    print("\n2️⃣ Testing symbol search...")
    apple_results = ingestion.search_symbol("AAPL", "NASDAQ")
    if apple_results:
        print("✅ Symbol search working")
    else:
        print("⚠️ Symbol search returned no results (this may be normal)")
    
    # Test 3: Fetch sample data for different intervals
    print("\n3️⃣ Testing data fetch for different intervals...")
    
    test_cases = [
        {"symbol": "AAPL", "exchange": "NASDAQ", "interval": "1m", "hours": 2},
        {"symbol": "AAPL", "exchange": "NASDAQ", "interval": "5m", "hours": 6},
        {"symbol": "BTCUSDT", "exchange": "BINANCE", "interval": "15m", "hours": 12},
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test 3.{i}: {test_case['symbol']} on {test_case['exchange']} ({test_case['interval']})")
        
        try:
            data = ingestion.get_historical_data(
                symbol=test_case['symbol'],
                exchange=test_case['exchange'],
                lookback_hours=test_case['hours'],
                interval=test_case['interval']
            )
            
            if data is not None and not data.empty:
                print(f"    ✅ Got {len(data)} records")
                print(f"    📅 Range: {data['timestamp'].min()} to {data['timestamp'].max()}")
                print(f"    💰 Price range: ${data['close_price'].min():.2f} - ${data['close_price'].max():.2f}")
                success_count += 1
            else:
                print(f"    ❌ No data received")
                
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    print(f"\n📊 Data fetch results: {success_count}/{len(test_cases)} successful")
    
    return success_count > 0

def test_tvdatafeed_with_database():
    """Test TvDatafeed with database integration"""
    
    print("\n" + "=" * 60)
    print("🚀 Testing TvDatafeed with Database Integration")
    print("=" * 60)
    
    # Test 1: Database connection
    print("\n1️⃣ Testing database connection...")
    if not test_connection():
        print("❌ Database connection failed. Please check your TimescaleDB setup.")
        print("💡 Make sure Docker is running and TimescaleDB container is started")
        return False
    
    # Test 2: Full ingestion pipeline
    print("\n2️⃣ Testing full ingestion pipeline...")
    ingestion = HistoricalDataIngestion()
    
    if not ingestion.initialized:
        print("❌ Failed to initialize TvDatafeed")
        return False
    
    # Test with a reliable symbol
    symbol = "AAPL"
    exchange = "NASDAQ"
    
    success = ingestion.ingest_historical_data(
        symbol=symbol,
        exchange=exchange,
        lookback_hours=3,  # 3 hours of data
        interval="5m",     # 5-minute intervals
        add_indicators=True,
        update_mode="append"
    )
    
    if success:
        print(f"✅ Successfully ingested data for {symbol}")
        return True
    else:
        print(f"❌ Failed to ingest data for {symbol}")
        return False

def show_usage_examples():
    """Show usage examples for different markets"""
    
    print("\n" + "=" * 60)
    print("💡 TvDatafeed Usage Examples")
    print("=" * 60)
    
    examples = [
        {"title": "US Stocks", "symbols": [
            "AAPL (NASDAQ) - Apple Inc",
            "MSFT (NASDAQ) - Microsoft",
            "TSLA (NASDAQ) - Tesla",
            "SPY (NYSE) - S&P 500 ETF"
        ]},
        {"title": "Crypto", "symbols": [
            "BTCUSDT (BINANCE) - Bitcoin",
            "ETHUSDT (BINANCE) - Ethereum", 
            "ADAUSDT (BINANCE) - Cardano"
        ]},
        {"title": "Forex", "symbols": [
            "EURUSD (FOREX) - Euro/USD",
            "GBPUSD (FOREX) - Pound/USD",
            "USDJPY (FOREX) - USD/Yen"
        ]},
        {"title": "Commodities", "symbols": [
            "GOLD (COMEX) - Gold Futures",
            "CRUDE (NYMEX) - Crude Oil"
        ]}
    ]
    
    for category in examples:
        print(f"\n📊 {category['title']}:")
        for symbol in category['symbols']:
            print(f"  • {symbol}")
    
    print(f"\n🕐 Supported Intervals:")
    intervals = ['1m', '3m', '5m', '15m', '30m', '45m', '1h', '2h', '3h', '4h', '1D', '1W', '1M']
    for interval in intervals:
        print(f"  • {interval}")

if __name__ == "__main__":
    print("🎯 TvDatafeed Integration Test Suite")
    print("=" * 60)
    
    # Run basic tests
    basic_success = test_tvdatafeed_basic()
    
    if basic_success:
        # Run database tests if basic tests pass
        db_success = test_tvdatafeed_with_database()
        
        if db_success:
            print("\n🎉 All tests passed! TvDatafeed integration is working correctly.")
        else:
            print("\n⚠️ Basic functionality works, but database integration failed.")
            print("   Check your TimescaleDB connection and try again.")
    else:
        print("\n💥 Basic TvDatafeed tests failed.")
        print("   This might be due to network issues or TradingView access limits.")
    
    # Show usage examples regardless of test results
    show_usage_examples()
    
    print(f"\n📚 Next steps:")
    print("  1. Try the examples above with: python -c \"from main.src.ingestion.hist import HistoricalDataIngestion; ...\"")
    print("  2. Run the main ingestion: python main/src/ingestion/hist.py")
    print("  3. Check your database for stored data")