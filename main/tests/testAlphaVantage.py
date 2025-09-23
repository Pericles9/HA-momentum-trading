"""
Simple test script for Alpha Vantage API integration
This script helps you test the Alpha Vantage API setup
"""
import sys
import os

# Add the src directory to path for imports (from tests folder)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ingestion.hist import HistoricalDataIngestion

def test_alpha_vantage_setup():
    """Test Alpha Vantage API setup and basic functionality"""
    
    print("🚀 Testing Alpha Vantage API Setup")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ALPHA_VANTAGE_API_KEY')
    if not api_key:
        print("❌ ALPHA_VANTAGE_API_KEY environment variable not found")
        print("\n💡 To get started:")
        print("1. Get a free API key at: https://www.alphavantage.co/support/#api-key")
        print("2. Set the environment variable:")
        print("   Windows PowerShell: $env:ALPHA_VANTAGE_API_KEY='your_api_key_here'")
        print("   Windows CMD: set ALPHA_VANTAGE_API_KEY=your_api_key_here")
        print("3. Or add it to your .env file")
        return False
    
    print(f"✅ Found API key: {api_key[:8]}...")
    
    # Test 1: Initialize the ingestion system
    print("\n1️⃣ Initializing Alpha Vantage API...")
    try:
        ingestion = HistoricalDataIngestion()
        if not ingestion.initialized:
            print("❌ Failed to initialize Alpha Vantage API")
            return False
        print("✅ Alpha Vantage API initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing Alpha Vantage API: {e}")
        return False
    
    # Test 2: Fetch sample data (just a small amount to test)
    print("\n2️⃣ Testing data fetch (1min data for AAPL)...")
    try:
        data = ingestion.get_historical_data(
            symbol="AAPL",
            lookback_hours=2,  # Just 2 hours to test
            interval="1min"
        )
        
        if data is None or data.empty:
            print("❌ No data received")
            return False
        
        print(f"✅ Successfully fetched {len(data)} records")
        print(f"📊 Columns: {list(data.columns)}")
        print(f"📅 Date range: {data['timestamp'].min()} to {data['timestamp'].max()}")
        
        # Show sample data
        print(f"\n📈 Sample data (first 3 rows):")
        print(data.head(3)[['timestamp', 'open_price', 'high_price', 'low_price', 'close_price', 'volume']])
        
        return True
        
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_rate_limit_info():
    """Show information about Alpha Vantage rate limits"""
    print("\n📊 Alpha Vantage Rate Limits (Free Tier):")
    print("• 5 API calls per minute")
    print("• 500 API calls per day")
    print("• Intraday data: Up to 30 days of history")
    print("• Real-time and historical data available")
    print("\n💡 Premium tiers available for higher limits")

if __name__ == "__main__":
    success = test_alpha_vantage_setup()
    
    if success:
        print("\n🎉 Alpha Vantage API test successful!")
        show_rate_limit_info()
        print("\n✅ You can now use the historical data ingestion system")
    else:
        print("\n💥 Alpha Vantage API test failed. Please check the setup steps above.")
        show_rate_limit_info()