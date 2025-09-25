================================================================================
  🎯 HA MOMENTUM TRADING SYSTEM
================================================================================
  📊 Dynamic Screening & Watchlist4. Use '--console-only' mode for testing and setup
5. Monitor live data streams with 'live' command
6. Adjust live data settings for optimal performance
7. Use 'stop-live'/'start-live' to manage streaming during high volatilityManagement
  📈 Historical Data Ingestion with Extended Hours
  📡 Live Data Collection with TvDatafeed
  🎮 Interactive Console Interface
  ⚙️ Runtime Configuration Management
  🐳 Automatic Database Management
================================================================================

## 📁 PROJECT STRUCTURE
main/
├── main.py                 # Main orchestration system
├── config.json            # Configuration file (auto-generated)
├── momentum_trading.log    # System log file
├── setup_database.py      # Database initialization
├── src/
│   ├── DB/
│   │   ├── connection.py   # TimescaleDB connection
│   │   ├── models.py       # Database models
│   │   └── operations.py   # Database operations
│   ├── ingestion/
│   │   ├── hist.py         # Historical data ingestion (tvdatafeed)
│   │   └── live.py         # Live data collection (placeholder)
│   └── screener/
│       ├── PMH.py          # Pre-market screener (Selenium-based)
│       └── RTH.py          # Regular hours screener (Selenium-based)
└── tests/
    ├── README.md           # Test documentation
    ├── screenerTest.py     # Screener functionality tests
    ├── testTvDatafeed.py   # TvDatafeed integration tests
    ├── testHistoricalIngestion.py  # Historical data tests
    └── testOHLCVStorage.py # Database storage tests

## 🚀 QUICK START

### 1. Setup Environment
launch venv:
.\.venv\Scripts\Activate.ps1

### 2. Start System (Database Auto-Start)
cd main
python main.py

⚡ NEW: The system now automatically:
- Checks if Docker is running
- Starts TimescaleDB container if needed
- Creates new container if it doesn't exist
- Waits for database to be ready
- Tests connection before proceeding

### 3. Manual Database Setup (Optional)
If you prefer manual setup:
docker run -d --name timescaledb -e POSTGRES_PASSWORD=password123 -p 5433:5432 timescale/timescaledb:latest-pg14

## 🛑 HOW TO STOP THE SYSTEM
- Press Ctrl+C in the terminal
- Or type 'quit' or 'exit' in the console interface

## 🎮 CONSOLE COMMANDS

### System Control:
- status          - Show system status and watchlist
- pause           - Pause screening (keeps system running)
- resume          - Resume screening
- screen          - Force immediate screen update
- quit/exit       - Stop the system

### Watchlist Management:
- watchlist       - Show current watchlist
- clear           - Clear entire watchlist
- add <SYMBOL>    - Manually add a symbol (e.g., add AAPL)
- remove <SYMBOL> - Remove a symbol (e.g., remove MSFT)

### Configuration:
- config          - Show all configuration settings
- set <key>=<val> - Update configuration (e.g., set screening_interval_minutes=2)
- save            - Save current config to file

### Database Management:
- db              - Check database and Docker status
- restart-db      - Restart TimescaleDB container

### Live Data Management:
- live            - Show live data streaming status
- start-live      - Start live data collection
- stop-live       - Stop live data collection

### Help:
- help            - Show all available commands

### Configuration Examples:
set screening_interval_minutes=2      # Screen every 2 minutes instead of 1
set max_watchlist_size=25             # Limit watchlist to 25 stocks
set historical_lookback_days=2        # Get 2 days of historical data
set log_level=DEBUG                   # More detailed logging
set live_data_enabled=false          # Disable live data collection
set live_update_interval=10           # Update live data every 10 seconds
set live_data_batch_size=15           # Limit to 15 symbols for live streaming

## 🚀 STARTUP OPTIONS

### Basic Usage:
python main.py                        # Normal mode with console interface

### Advanced Options:
python main.py --interval 2           # Screen every 2 minutes
python main.py --max-watchlist 25     # Limit to 25 stocks
python main.py --lookback-days 2      # 2 days historical data
python main.py --log-level DEBUG      # Debug logging
python main.py --console-only         # Console mode (no auto-screening)
python main.py --no-console           # Background mode (no console)
python main.py --config custom.json   # Use custom config file

### Help:
python main.py --help                 # Show all command line options

## ⚙️ CONFIGURATION FILE (config.json)

The system automatically creates and manages a config.json file with the following settings:

{
    "screening_interval_minutes": 1,        # How often to screen (minutes)
    "max_watchlist_size": 50,               # Maximum symbols in watchlist
    "min_volume_threshold": 1000000,        # Minimum volume filter
    "historical_lookback_days": 1,          # Days of historical data
    "data_interval": "1m",                  # Data resolution (1m, 5m, etc.)
    "include_extended_hours": true,         # Include pre/post market data
    "premarket_start": "04:00",             # Pre-market start time
    "premarket_end": "09:30",               # Pre-market end time
    "market_open": "09:30",                 # Regular market open
    "market_close": "16:00",                # Regular market close
    "afterhours_end": "20:00",              # After-hours end time
    "log_level": "INFO",                    # Logging level
    "console_output": true,                 # Console logging
    "paper_trading": true,                  # Paper trading mode
    "max_position_size": 10000.0,           # Max position size
    "live_data_enabled": true,              # Enable live data streaming
    "live_update_interval": 5,              # Live data update interval (seconds)
    "live_data_batch_size": 25              # Max symbols for live streaming
}

## 🔄 SYSTEM WORKFLOW

### Time-Based Screening:
- Pre-market (4:00-9:30 AM): Uses PMH screener for pre-market movers
- Market hours (9:30 AM-4:00 PM): Uses RTH screener for regular hours gainers
- After-hours (4:00-8:00 PM): Continues with RTH screener
- Closed: No screening performed

### Data Collection:
1. System screens stocks every minute (configurable)
2. Updates watchlist with new momentum stocks
3. Fetches historical 1-minute data (back to 4am previous day) for new symbols
4. ⚡ NEW: Starts live data streams for all watchlist symbols
5. Streams real-time 1-minute OHLCV data with extended hours
6. Automatically stops streams for symbols removed from watchlist
7. Stores all data in TimescaleDB with timestamps and indicators
8. Manages connection health and reconnections automatically

### Database Schema:
- screener_results: Stores screening results and criteria
- ohlcv_data: Stores OHLC + Volume data with indicators
- trading_signals: For future trading signal storage

## 🧪 TESTING

### Test Scripts Location: `main/tests/`

### Core System Tests:
- `screenerTest.py` - Tests PMH/RTH screeners with Selenium
- `screenerDatabaseTest.py` - Tests screener database operations
- `testHistoricalIngestion.py` - Tests historical data ingestion
- `testLiveDataIngestion.py` - Tests live data ingestion system
- `testOHLCVStorage.py` - Tests OHLCV data storage
- `testAlphaVantage.py` - Tests Alpha Vantage integration
- `testTvDatafeed.py` - Tests TvDatafeed integration

### Live Data Streaming Tests:
- `robustLiveStreamTest.py` - **Main live stream test** (30 second stream with error handling)
- `testStandaloneLiveStream.py` - Comprehensive 60 second test (standalone)
- `quickTvTest.py` - Quick TvDatafeed connection test

### Running Tests:
```bash
cd main/tests

# Quick tests:
python quickTvTest.py                  # Test TvDatafeed connection
python robustLiveStreamTest.py         # Test live streaming (30s)

# Full system tests:
python testLiveDataIngestion.py        # Test live data streaming system
python testHistoricalIngestion.py      # Test historical data ingestion
python testOHLCVStorage.py            # Test database storage
python screenerTest.py                # Test screener functionality
```

### Test Features:
- ✅ Works outside regular trading hours (extended session data)
- ✅ Real-time data streaming with connection error handling
- ✅ Database integration testing
- ✅ Screener automation testing
- ✅ Historical data backfill testing

## 📊 DATABASES & APIs

### TimescaleDB (PostgreSQL Extension):
- Host: localhost:5433
- Database: momentum_trading
- User: postgres
- Password: password123

### Data Sources:
- TvDatafeed: Historical and live market data with extended hours
- Pre-market screener: https://stockanalysis.com/markets/pre-market/
- Regular hours screener: https://stockanalysis.com/markets/gainers/

### API Keys:
alpha vantage api key: 5YFOJ4IOA13XY4HB

## 📝 LOGS

The system creates detailed logs in:
- momentum_trading.log (in main/ directory)
- Console output (real-time)

Log levels: DEBUG, INFO, WARNING, ERROR

## 🔧 DEPENDENCIES

Key packages (installed in venv):
- pandas: Data manipulation
- sqlalchemy: Database ORM
- psycopg2: PostgreSQL adapter
- selenium: Web scraping for screeners
- webdriver-manager: Automatic Chrome driver management
- schedule: Task scheduling
- docker: Container management for auto-database startup
- tvdatafeed: Market data (installed from GitHub)
- python-dotenv: Environment variables

## 🚧 UPCOMING FEATURES

- Advanced trading signal generation
- Position management and portfolio tracking
- Real-time alerts and notifications
- Web dashboard interface
- Strategy backtesting framework
- Multi-timeframe analysis
- Risk management tools

## 💡 USAGE TIPS

1. Start with default settings, then adjust via console commands
2. Use 'status' command to monitor system health
3. Monitor logs for any data ingestion issues  
4. Use 'pause' during market volatility to prevent over-screening
5. Manually add/remove symbols as needed with add/remove commands
6. Save configuration changes with 'save' command
7. Use '--console-only' mode for testing and setup

## 🐛 TROUBLESHOOTING

1. Database Connection Issues:
   ⚡ NEW: System now auto-manages database!
   - Use 'db' command to check status
   - Use 'restart-db' command to restart container
   - System automatically starts TimescaleDB if needed
   - Fallback: Ensure TimescaleDB container is running manually: docker ps
   - Check port 5433 is available
   - Verify password: password123

2. Docker Issues:
   - Ensure Docker Desktop is installed and running
   - Check Docker daemon: docker info
   - Windows: Ensure Docker Desktop is started
   - WSL2 backend recommended for Windows

3. Screener Issues:
   - Chrome driver automatically managed by webdriver-manager
   - Check internet connection for web scraping
   - Verify website URLs in PMH.py and RTH.py

4. TvDatafeed Issues:
   - Ensure package installed from GitHub source
   - Check TradingView credentials if needed
   - Monitor rate limiting

5. Virtual Environment:
   - Always activate venv before running: .\.venv\Scripts\Activate.ps1
   - Install packages in venv, not system Python

================================================================================