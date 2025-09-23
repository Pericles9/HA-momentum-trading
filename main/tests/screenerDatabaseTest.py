"""
Enhanced screener test with database storage
"""
import sys
import os
import pandas as pd

# Add the src directory to sys.path to enable imports
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.append(src_path)

from screener.PMH import fetch_table_to_df as fetch_pmh
from screener.RTH import fetch_table_to_df as fetch_rth
from DB.operations import DatabaseOperations


def test_screeners_with_database():
    """
    Test screeners and store results in database
    """
    pmh_success = False
    rth_success = False
    
    print("🔍 Testing PMH screener...")
    try:
        df_pmh = fetch_pmh()
        print(f"✅ PMH Screener: Retrieved {len(df_pmh)} results")
        print(f"Columns: {list(df_pmh.columns)}")
        print(f"Sample data:\n{df_pmh.head()}")
        
        # Validate DataFrame
        if df_pmh.empty:
            print("⚠️ Warning: PMH screener returned empty DataFrame")
            return False
        
        # Store in database
        with DatabaseOperations() as db_ops:
            success = db_ops.insert_screener_results(df_pmh, 'PMH')
            if success:
                print("✅ PMH results stored in database")
                pmh_success = True
            else:
                print("❌ Failed to store PMH results")
        
    except Exception as e:
        print(f"❌ PMH screener failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*50)
    
    print("🔍 Testing RTH screener...")
    try:
        df_rth = fetch_rth()
        print(f"✅ RTH Screener: Retrieved {len(df_rth)} results")
        print(f"Columns: {list(df_rth.columns)}")
        print(f"Sample data:\n{df_rth.head()}")
        
        # Validate DataFrame
        if df_rth.empty:
            print("⚠️ Warning: RTH screener returned empty DataFrame")
            return False
        
        # Store in database
        with DatabaseOperations() as db_ops:
            success = db_ops.insert_screener_results(df_rth, 'RTH')
            if success:
                print("✅ RTH results stored in database")
                rth_success = True
            else:
                print("❌ Failed to store RTH results")
        
    except Exception as e:
        print(f"❌ RTH screener failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*50)
    
    # Test retrieving data from database
    print("📊 Testing database retrieval...")
    try:
        with DatabaseOperations() as db_ops:
            # Get latest PMH results
            pmh_db_results = db_ops.get_latest_screener_results('PMH', limit=5)
            print(f"✅ Retrieved {len(pmh_db_results)} PMH results from database")
            
            # Get latest RTH results
            rth_db_results = db_ops.get_latest_screener_results('RTH', limit=5)
            print(f"✅ Retrieved {len(rth_db_results)} RTH results from database")
            
            if not pmh_db_results.empty:
                print(f"Latest PMH results:\n{pmh_db_results.head()}")
            
            if not rth_db_results.empty:
                print(f"Latest RTH results:\n{rth_db_results.head()}")
        
    except Exception as e:
        print(f"❌ Database retrieval failed: {e}")
        import traceback
        traceback.print_exc()
    
    return pmh_success and rth_success


if __name__ == "__main__":
    print("=" * 60)
    print("  Enhanced Screener Test with Database Storage")
    print("=" * 60)
    
    success = test_screeners_with_database()
    
    if success:
        print("\n🎉 Screener test with database storage completed successfully!")
    else:
        print("\n❌ Some tests failed. Check the output above.")
        sys.exit(1)