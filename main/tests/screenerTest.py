import sys
import os
import pandas as pd

# Add the src directory to sys.path to enable imports
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.append(src_path)

from screener.PMH import fetch_table_to_df as fetch_pmh
from screener.RTH import fetch_table_to_df as fetch_rth

def test_pmh_screener():
    """Test PMH screener functionality"""
    print("🔍 Testing PMH screener...")
    try:
        df_pmh = fetch_pmh()
        print(f"✅ PMH Screener: Retrieved {len(df_pmh)} results")
        print(f"Columns: {list(df_pmh.columns)}")
        print(f"Sample data:\n{df_pmh.head()}")
        
        assert isinstance(df_pmh, pd.DataFrame), "PMH screener should return a DataFrame"
        assert not df_pmh.empty, "PMH screener returned an empty DataFrame"
        
        return df_pmh
        
    except Exception as e:
        print(f"❌ PMH screener failed: {e}")
        raise


def test_rth_screener():
    """Test RTH screener functionality"""
    print("\n🔍 Testing RTH screener...")
    try:
        df_rth = fetch_rth()
        print(f"✅ RTH Screener: Retrieved {len(df_rth)} results")
        print(f"Columns: {list(df_rth.columns)}")
        print(f"Sample data:\n{df_rth.head()}")
        
        assert isinstance(df_rth, pd.DataFrame), "RTH screener should return a DataFrame"
        assert not df_rth.empty, "RTH screener returned an empty DataFrame"
        
        return df_rth
        
    except Exception as e:
        print(f"❌ RTH screener failed: {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("  Screener Functionality Test")
    print("=" * 60)
    
    # Test PMH screener
    df_pmh = test_pmh_screener()
    
    # Test RTH screener  
    df_rth = test_rth_screener()
    
    print(f"\n🎉 All tests passed!")
    print(f"📊 PMH results: {len(df_pmh)} stocks")
    print(f"📊 RTH results: {len(df_rth)} stocks")