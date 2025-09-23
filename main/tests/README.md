# Test Suite Documentation

This folder contains all test scripts for the HA Momentum Trading system.

## 🧪 Test Files Overview

### Historical Data Ingestion Tests
- **`testTvDatafeed.py`** - Comprehensive TvDatafeed integration test
- **`testHistoricalIngestion.py`** - Historical data ingestion pipeline test  
- **`testAlphaVantage.py`** - Legacy Alpha Vantage API test (for reference)

### Database Tests
- **`testOHLCVStorage.py`** - OHLCV data storage and retrieval test
- **`screenerDatabaseTest.py`** - Screener results database test

### Screener Tests  
- **`screenerTest.py`** - PMH/RTH screener functionality test

## 🚀 Running Tests

### From Tests Directory
```bash
cd main/tests

# Test TvDatafeed integration (recommended)
python testTvDatafeed.py

# Test historical data ingestion pipeline
python testHistoricalIngestion.py

# Test OHLCV database operations
python testOHLCVStorage.py

# Test screener functionality
python screenerTest.py
```

### From Root Directory
```bash
# Run individual tests
python main/tests/testTvDatafeed.py
python main/tests/testHistoricalIngestion.py
```

## ✅ What Gets Tested

### TvDatafeed Integration (`testTvDatafeed.py`)
- ✅ TvDatafeed initialization (no login required)
- ✅ Data fetching for multiple asset classes:
  - US Stocks (AAPL, MSFT, TSLA)
  - Crypto (BTCUSDT)
  - Multiple timeframes (1m, 5m, 15m)
- ✅ **Extended hours data** (pre-market & after-hours)
- ✅ Database integration with TimescaleDB
- ✅ Technical indicators calculation
- ✅ Data deduplication

### Historical Ingestion (`testHistoricalIngestion.py`)
- ✅ Complete ingestion pipeline
- ✅ Data format conversion
- ✅ Database storage and retrieval
- ✅ Error handling

### Key Features Verified
- 🕐 **Extended Hours**: Data includes pre-market (4:00-9:30 AM) and after-hours (4:00-8:00 PM EST)
- 📊 **Multi-Asset**: Stocks, crypto, forex, commodities
- ⚡ **High Performance**: Up to 5000 bars per request
- 🔄 **Deduplication**: Prevents duplicate data storage
- 📈 **Technical Indicators**: SMA, EMA, RSI, MACD, Bollinger Bands

## 🎯 Test Results Example

```
📊 Data fetch results: 3/3 successful
✅ AAPL 1m: 94 records (16:16 to 18:14) - Extended hours data!
✅ AAPL 5m: 71 records (12:20 to 18:10) - Includes after-hours
✅ BTCUSDT 15m: 48 records - 24/7 crypto data
```

## 🔧 Troubleshooting

### Import Errors
All test files use relative imports from the `main/src` directory:
```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
```

### Database Connection Issues  
Make sure TimescaleDB is running:
```bash
docker start timescaledb  # or start Docker Desktop
```

### TvDatafeed Limitations
- No login: Some data may be limited
- With login: Full access to TradingView data
- Rate limiting: Built into the library

## 📚 Next Steps
1. Run `testTvDatafeed.py` to verify complete system
2. Check your TimescaleDB for stored data
3. Explore different symbols and timeframes
4. Consider adding TradingView login for enhanced access