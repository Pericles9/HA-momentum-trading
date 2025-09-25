"""
Simple Chart Viewer Test
Tests the chart viewer GUI with basic functionality
"""
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import tkinter as tk
    print("✅ tkinter available")
except ImportError:
    print("❌ tkinter not available")
    sys.exit(1)

try:
    import matplotlib.pyplot as plt
    print("✅ matplotlib available")
except ImportError:
    print("❌ matplotlib not available - install with: pip install matplotlib")
    sys.exit(1)

try:
    import mplfinance as mpf
    print("✅ mplfinance available - professional charts enabled")
    MPLFINANCE_AVAILABLE = True
except ImportError:
    print("⚠️ mplfinance not available - using basic charts")
    print("   Install with: pip install mplfinance")
    MPLFINANCE_AVAILABLE = False

try:
    from src.DB.operations import DatabaseOperations
    db_ops = DatabaseOperations()
    print("✅ Database connection available")
    
    # Test query
    result = db_ops.execute_query("SELECT COUNT(*) FROM ohlcv_data")
    if result:
        count = result[0][0]
        print(f"✅ Database has {count} OHLCV records")
    else:
        print("⚠️ No data in database yet")
        
except Exception as e:
    print(f"❌ Database error: {e}")

print("\n🚀 Chart Viewer should work!")
print("   Run: python chart_viewer.py")

# Optional: Start the GUI
response = input("\nStart Chart Viewer now? (y/n): ").lower().strip()
if response == 'y':
    print("🚀 Launching Chart Viewer...")
    try:
        from chart_viewer import main
        main()
    except KeyboardInterrupt:
        print("\n👋 Chart Viewer closed")
    except Exception as e:
        print(f"❌ Error running chart viewer: {e}")