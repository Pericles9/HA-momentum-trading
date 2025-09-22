import sys
import os
import pandas as pd

# Add the screener directory to sys.path
screener_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'screener'))
sys.path.append(screener_path)

from main.src.screener.PMH import fetch_table_to_df as fetch_pmh
from main.src.screener.RTH import fetch_table_to_df as fetch_rth

# Test PMH screener
df_pmh = fetch_pmh()
print("\nPMH Screener DataFrame:\n", df_pmh)
assert isinstance(df_pmh, pd.DataFrame)
assert not df_pmh.empty, "PMH screener returned an empty DataFrame"

# Test RTH screener
df_rth = fetch_rth()
print("\nRTH Screener DataFrame:\n", df_rth)
assert isinstance(df_rth, pd.DataFrame)
assert not df_rth.empty, "RTH screener returned an empty DataFrame"