"""
Test script for Live Data Ingestion
Tests the TvDatafeed live streaming functionality
"""
import sys
import os
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ingestion.live import LiveDataIngestion, LiveDataConfig, create_live_data_manager
from DB.connection import test_connection

def test_watchlist_callback():
    """Mock watchlist callback for testing"""
    # Return a small test watchlist
    return {"AAPL", "MSFT", "GOOGL"}

def test_live_data_ingestion():
    """Test live data ingestion functionality"""
    print("=" * 60)
    print("  🧪 TESTING LIVE DATA INGESTION")
    print("=" * 60)
    
    # Test database connection
    print("1. Testing database connection...")
    if not test_connection():
        print("❌ Database connection failed - ensure TimescaleDB is running")
        return False
    print("✅ Database connection successful")
    
    # Test live data manager initialization
    print("\n2. Testing live data manager initialization...")
    try:
        config = LiveDataConfig(
            update_interval=10,  # 10 seconds for testing
            batch_size=3,
            enable_extended_hours=True
        )
        
        manager = create_live_data_manager(
            watchlist_callback=test_watchlist_callback,
            config=config
        )
        
        if manager.initialized:
            print("✅ Live data manager initialized successfully")
        else:
            print("❌ Live data manager initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing live data manager: {e}")
        return False
    
    # Test starting live data collection
    print("\n3. Testing live data collection startup...")
    try:
        success = manager.start()
        if success:
            print("✅ Live data collection started")
        else:
            print("❌ Failed to start live data collection")
            return False
            
    except Exception as e:
        print(f"❌ Error starting live data collection: {e}")
        return False
    
    # Let it run for a short time
    print("\n4. Running live data collection for 30 seconds...")
    print("   (Check logs for stream activity)")
    
    for i in range(6):  # 6 * 5 seconds = 30 seconds
        time.sleep(5)
        stats = manager.get_stats()
        print(f"   Status: {stats['streams_active']} active streams, "
              f"{stats['total_updates']} updates, "
              f"Last: {stats['last_update']}")
    
    # Test statistics
    print("\n5. Checking final statistics...")
    final_stats = manager.get_stats()
    print(f"   Active Streams: {final_stats['streams_active']}")
    print(f"   Total Updates: {final_stats['total_updates']}")
    print(f"   Is Running: {final_stats['is_running']}")
    print(f"   Symbols: {final_stats.get('symbols', [])}")
    
    # Test stopping
    print("\n6. Testing live data collection shutdown...")
    try:
        manager.stop()
        print("✅ Live data collection stopped successfully")
        
    except Exception as e:
        print(f"❌ Error stopping live data collection: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("  ✅ LIVE DATA INGESTION TEST COMPLETED")
    print("=" * 60)
    
    return True

def test_individual_components():
    """Test individual components"""
    print("\n🔧 Testing individual components...")
    
    # Test LiveDataConfig
    config = LiveDataConfig()
    print(f"✅ Default config: interval={config.update_interval}s, batch={config.batch_size}")
    
    # Test direct LiveDataIngestion
    try:
        ingestion = LiveDataIngestion(config)
        print(f"✅ Direct ingestion init: {ingestion.initialized}")
        
        if ingestion.initialized:
            # Test stats
            stats = ingestion.get_stats()
            print(f"✅ Stats accessible: {len(stats)} fields")
            
    except Exception as e:
        print(f"❌ Direct ingestion test failed: {e}")

if __name__ == "__main__":
    try:
        # Test individual components first
        test_individual_components()
        
        # Run main test
        success = test_live_data_ingestion()
        
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed!")
            
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()