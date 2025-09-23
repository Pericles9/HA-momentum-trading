"""
Database setup script for TimescaleDB
Run this script to initialize the database and create tables
"""
import sys
import os

# Add the src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from DB.connection import engine, test_connection, create_tables
from DB.models import Base
from DB.operations import DatabaseOperations


def setup_database():
    """
    Complete database setup process
    """
    print("🚀 Starting TimescaleDB setup...")
    
    # Test connection
    print("📡 Testing database connection...")
    if not test_connection():
        print("❌ Database connection failed. Please check your .env configuration.")
        print("Make sure TimescaleDB is running and credentials are correct.")
        return False
    
    print("✅ Database connection successful!")
    
    # Create tables
    print("📋 Creating database tables...")
    try:
        create_tables()
        print("✅ Tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    # Setup TimescaleDB hypertables
    print("⚡ Setting up TimescaleDB hypertables...")
    try:
        with DatabaseOperations() as db_ops:
            db_ops.setup_timescaledb()
        print("✅ TimescaleDB hypertables setup completed!")
    except Exception as e:
        print(f"❌ Error setting up hypertables: {e}")
        return False
    
    print("🎉 Database setup completed successfully!")
    print("\n📊 Your database is ready for:")
    print("  • Screener results storage")
    print("  • OHLCV data with indicators")
    print("  • Trading signals")
    print("  • Time-series analytics")
    
    return True


def test_database_operations():
    """
    Test basic database operations
    """
    print("\n🧪 Testing database operations...")
    
    try:
        with DatabaseOperations() as db_ops:
            # Test getting screener results (should be empty initially)
            pmh_results = db_ops.get_latest_screener_results('PMH', limit=10)
            rth_results = db_ops.get_latest_screener_results('RTH', limit=10)
            
            print(f"✅ Retrieved {len(pmh_results)} PMH results")
            print(f"✅ Retrieved {len(rth_results)} RTH results")
            
        print("✅ Database operations test passed!")
        
    except Exception as e:
        print(f"❌ Database operations test failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("=" * 50)
    print("  TimescaleDB Setup for Momentum Trading")
    print("=" * 50)
    
    success = setup_database()
    
    if success:
        test_database_operations()
        print("\n🚀 Ready to start storing your trading data!")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)