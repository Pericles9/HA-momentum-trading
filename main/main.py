"""
Main Application - HA Momentum Trading System
Orchestrates screening, watchlist management, and data collection

This system:
1. Screens stocks based on time of day (PMH/RTH)
2. Updates watchlists every minute
3. Fetches historical data for watchlist stocks
4. Begins live data collection
"""
import sys
import os
import time
import schedule
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Set
import threading
import logging
from dataclasses import dataclass, field
import argparse
import json
from pathlib import Path
import subprocess

# Try to import docker, handle gracefully if not available
try:
    import docker
    from docker.errors import DockerException, NotFound, APIError
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Docker package not available. Install with: pip install docker")

# Add src to path for imports
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

# Import screener functions
from src.screener.PMH import fetch_table_to_df as pmh_screen
from src.screener.RTH import fetch_table_to_df as rth_screen
from src.ingestion.hist import HistoricalDataIngestion
from src.ingestion.live import LiveDataIngestion, LiveDataConfig, create_live_data_manager
from src.DB.connection import test_connection
from src.DB.operations import DatabaseOperations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('momentum_trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def check_docker_available() -> bool:
    """Check if Docker is available and running"""
    try:
        # Check if docker command is available
        result = subprocess.run(['docker', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return False
        
        # Check if Docker daemon is running
        result = subprocess.run(['docker', 'info'], 
                              capture_output=True, text=True, timeout=10)
        return result.returncode == 0
        
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


def check_timescaledb_container() -> Dict[str, any]:
    """
    Check TimescaleDB container status
    
    Returns:
        Dict with container info: {'exists': bool, 'running': bool, 'name': str, 'ports': str}
    """
    container_info = {
        'exists': False,
        'running': False,
        'name': 'timescaledb',
        'ports': '5433:5432',
        'image': 'timescale/timescaledb:latest-pg14'
    }
    
    try:
        if DOCKER_AVAILABLE:
            # Use docker-py library if available
            client = docker.from_env()
            try:
                container = client.containers.get('timescaledb')
                container_info['exists'] = True
                container_info['running'] = container.status == 'running'
                return container_info
            except NotFound:
                return container_info
        else:
            # Fall back to subprocess calls
            result = subprocess.run(['docker', 'ps', '-a', '--filter', 'name=timescaledb', '--format', '{{.Names}}\t{{.Status}}'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'timescaledb' in line:
                        container_info['exists'] = True
                        container_info['running'] = 'Up' in line
                        break
            
            return container_info
            
    except Exception as e:
        logger.warning(f"Failed to check container status: {e}")
        return container_info


def start_timescaledb_container() -> bool:
    """
    Start TimescaleDB container
    
    Returns:
        bool: True if started successfully, False otherwise
    """
    try:
        container_info = check_timescaledb_container()
        
        if container_info['running']:
            logger.info("✅ TimescaleDB container is already running")
            return True
        
        if container_info['exists']:
            # Container exists but is stopped, start it
            logger.info("🔄 Starting existing TimescaleDB container...")
            if DOCKER_AVAILABLE:
                client = docker.from_env()
                container = client.containers.get('timescaledb')
                container.start()
            else:
                result = subprocess.run(['docker', 'start', 'timescaledb'], 
                                      capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    logger.error(f"Failed to start container: {result.stderr}")
                    return False
            
            # Wait for container to be ready
            time.sleep(5)
            logger.info("✅ TimescaleDB container started")
            return True
        
        else:
            # Container doesn't exist, create and start it
            logger.info("🚀 Creating new TimescaleDB container...")
            
            docker_cmd = [
                'docker', 'run', '-d',
                '--name', 'timescaledb',
                '-e', 'POSTGRES_PASSWORD=password123',
                '-p', '5433:5432',
                'timescale/timescaledb:latest-pg14'
            ]
            
            result = subprocess.run(docker_cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("✅ TimescaleDB container created and started")
                # Wait for database to be ready
                logger.info("⏳ Waiting for database to initialize (30 seconds)...")
                time.sleep(30)
                return True
            else:
                logger.error(f"❌ Failed to create container: {result.stderr}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Error managing TimescaleDB container: {e}")
        return False


def ensure_database_ready() -> bool:
    """
    Ensure database and dependencies are running
    
    Returns:
        bool: True if database is ready, False otherwise
    """
    logger.info("🔍 Checking database dependencies...")
    
    # Check if Docker is available
    if not check_docker_available():
        logger.error("❌ Docker is not available or not running")
        logger.info("💡 Please install Docker and ensure it's running")
        return False
    
    logger.info("✅ Docker is available")
    
    # Check and start TimescaleDB container
    if not start_timescaledb_container():
        logger.error("❌ Failed to start TimescaleDB container")
        return False
    
    # Test database connection with retries
    logger.info("🔌 Testing database connection...")
    max_retries = 6  # 60 seconds total (6 * 10 seconds)
    
    for attempt in range(max_retries):
        if test_connection():
            logger.info("✅ Database connection successful")
            return True
        
        if attempt < max_retries - 1:
            logger.info(f"⏳ Database not ready yet, retrying in 10 seconds... ({attempt + 1}/{max_retries})")
            time.sleep(10)
    
    logger.error("❌ Database connection failed after all retries")
    return False


@dataclass
class SystemConfig:
    """System configuration that can be modified at runtime"""
    # Screening settings
    screening_interval_minutes: int = 1
    max_watchlist_size: int = 50
    min_volume_threshold: int = 1000000
    
    # Historical data settings
    historical_lookback_days: int = 1
    data_interval: str = "1m"
    include_extended_hours: bool = True
    
    # Market timing (can be adjusted for different time zones)
    premarket_start: str = "04:00"
    premarket_end: str = "09:30"
    market_open: str = "09:30"
    market_close: str = "16:00"
    afterhours_end: str = "20:00"
    
    # Logging settings
    log_level: str = "INFO"
    console_output: bool = True
    
    # Trading settings (for future use)
    paper_trading: bool = True
    max_position_size: float = 10000.0
    
    # Live data settings
    live_data_enabled: bool = True
    live_update_interval: int = 5  # seconds
    live_data_batch_size: int = 25  # max symbols for live streaming
    
    def save_to_file(self, filepath: str = "config.json"):
        """Save configuration to JSON file"""
        config_dict = {
            'screening_interval_minutes': self.screening_interval_minutes,
            'max_watchlist_size': self.max_watchlist_size,
            'min_volume_threshold': self.min_volume_threshold,
            'historical_lookback_days': self.historical_lookback_days,
            'data_interval': self.data_interval,
            'include_extended_hours': self.include_extended_hours,
            'premarket_start': self.premarket_start,
            'premarket_end': self.premarket_end,
            'market_open': self.market_open,
            'market_close': self.market_close,
            'afterhours_end': self.afterhours_end,
            'log_level': self.log_level,
            'console_output': self.console_output,
            'paper_trading': self.paper_trading,
            'max_position_size': self.max_position_size,
            'live_data_enabled': self.live_data_enabled,
            'live_update_interval': self.live_update_interval,
            'live_data_batch_size': self.live_data_batch_size
        }
        
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=4)
        logger.info(f"💾 Configuration saved to {filepath}")
    
    @classmethod
    def load_from_file(cls, filepath: str = "config.json"):
        """Load configuration from JSON file"""
        if not Path(filepath).exists():
            logger.info(f"📄 No config file found at {filepath}, using defaults")
            return cls()
        
        try:
            with open(filepath, 'r') as f:
                config_dict = json.load(f)
            
            logger.info(f"📄 Configuration loaded from {filepath}")
            return cls(**config_dict)
        except Exception as e:
            logger.error(f"❌ Failed to load config from {filepath}: {e}")
            return cls()


@dataclass
class MarketSession:
    """Market session timing configuration"""
    premarket_start: str = "04:00"    # 4:00 AM EST
    premarket_end: str = "09:30"      # 9:30 AM EST  
    market_open: str = "09:30"        # 9:30 AM EST
    market_close: str = "16:00"       # 4:00 PM EST
    afterhours_end: str = "20:00"     # 8:00 PM EST


class MomentumTradingSystem:
    """
    Main momentum trading system orchestrator
    """
    
    def __init__(self, config: SystemConfig = None):
        """Initialize the momentum trading system"""
        logger.info("🚀 Initializing HA Momentum Trading System")
        
        # Configuration
        self.config = config or SystemConfig()
        
        # Market timing
        self.market_session = MarketSession(
            premarket_start=self.config.premarket_start,
            premarket_end=self.config.premarket_end,
            market_open=self.config.market_open,
            market_close=self.config.market_close,
            afterhours_end=self.config.afterhours_end
        )
        
        # Components
        self.historical_ingestion = None
        self.db_ops = None
        self.live_data_manager = None
        
        # State management
        self.current_watchlist: Set[str] = set()
        self.previous_watchlist: Set[str] = set()
        self.last_screen_time = None
        self.system_running = False
        self.pause_screening = False
        
        # Threading
        self.screening_thread = None
        self.data_collection_threads = {}
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            # Ensure database dependencies are running
            logger.info("🏗️ Initializing system components...")
            
            if not ensure_database_ready():
                raise Exception("Database dependencies not ready")
            
            # Screeners are functions, no initialization needed
            logger.info("✅ Screeners available")
            
            # Initialize historical data ingestion
            self.historical_ingestion = HistoricalDataIngestion()
            if not self.historical_ingestion.initialized:
                raise Exception("TvDatafeed initialization failed")
            logger.info("✅ TvDatafeed initialized")
            
            # Initialize database operations
            self.db_ops = DatabaseOperations()
            logger.info("✅ Database operations initialized")
            
            # Initialize live data manager if enabled
            if self.config.live_data_enabled:
                live_config = LiveDataConfig(
                    update_interval=self.config.live_update_interval,
                    batch_size=self.config.live_data_batch_size,
                    enable_extended_hours=self.config.include_extended_hours
                )
                
                self.live_data_manager = create_live_data_manager(
                    watchlist_callback=self.get_current_watchlist,
                    config=live_config
                )
                logger.info("✅ Live data manager initialized")
            else:
                logger.info("ℹ️ Live data collection disabled in configuration")
            
        except Exception as e:
            logger.error(f"❌ Component initialization failed: {e}")
            raise
    
    def get_current_watchlist(self) -> Set[str]:
        """Get current watchlist (used by live data manager)"""
        return self.current_watchlist.copy()
    
    def get_current_market_state(self) -> str:
        """
        Determine current market state based on time
        
        Returns:
            'premarket', 'market_hours', 'afterhours', or 'closed'
        """
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        
        # Check if it's a weekday (Monday=0, Sunday=6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return 'closed'
        
        if self.market_session.premarket_start <= current_time < self.market_session.premarket_end:
            return 'premarket'
        elif self.market_session.market_open <= current_time < self.market_session.market_close:
            return 'market_hours'
        elif self.market_session.market_close <= current_time < self.market_session.afterhours_end:
            return 'afterhours'
        else:
            return 'closed'
    
    def run_screen(self) -> List[str]:
        """
        Run the appropriate screen based on current market state
        
        Returns:
            List of symbols that passed the screen
        """
        market_state = self.get_current_market_state()
        logger.info(f"📊 Running screen for market state: {market_state}")
        
        try:
            if market_state == 'premarket':
                # Run pre-market momentum screen
                logger.info("📊 Running pre-market screen...")
                df_results = pmh_screen()
                screener_type = "PMH"
                
            elif market_state == 'market_hours':
                # Run regular trading hours screen
                logger.info("📊 Running regular trading hours screen...")
                df_results = rth_screen()
                screener_type = "RTH"
                
            elif market_state == 'afterhours':
                # Continue with RTH screen during after hours
                logger.info("📊 Running after-hours screen...")
                df_results = rth_screen()
                screener_type = "RTH (After Hours)"
                
            else:
                # Market closed
                logger.info("📴 Market is closed, no screening performed")
                return []
            
            # Extract symbols from DataFrame results
            symbols = []
            if df_results is not None and not df_results.empty:
                # Get symbols from the 'Symbol' column
                if 'Symbol' in df_results.columns:
                    symbols = df_results['Symbol'].tolist()
                    # Clean symbols (remove any empty or invalid entries)
                    symbols = [str(s).strip().upper() for s in symbols if s and str(s).strip()]
                    # Filter out non-stock symbols (optional - remove if you want all)
                    symbols = [s for s in symbols if len(s) <= 5 and s.isalpha()]
            
            logger.info(f"✅ {screener_type} screen completed: {len(symbols)} symbols found")
            if symbols:
                logger.info(f"📋 Screened symbols: {', '.join(symbols[:10])}" + 
                           (f" (+{len(symbols)-10} more)" if len(symbols) > 10 else ""))
            
            # Store screen results in database
            self._store_screen_results(symbols, screener_type)
            
            return symbols
            
        except Exception as e:
            logger.error(f"❌ Screening failed: {e}")
            return []
    
    def _store_screen_results(self, symbols: List[str], screener_type: str):
        """Store screening results in database"""
        try:
            # Create DataFrame for database storage
            if symbols:
                timestamp = datetime.now()
                results_data = []
                
                for symbol in symbols:
                    results_data.append({
                        'timestamp': timestamp,
                        'symbol': symbol,
                        'screener_type': screener_type,
                        'criteria_met': 'momentum_criteria',
                        'score': 1.0
                    })
                
                df_results = pd.DataFrame(results_data)
                
                with DatabaseOperations() as db_ops:
                    success = db_ops.insert_screener_results(df_results, screener_type)
                    
                if success:
                    logger.info(f"✅ Stored {len(symbols)} {screener_type} screen results")
                else:
                    logger.warning(f"⚠️ Failed to store {screener_type} screen results")
            else:
                logger.info(f"📝 No {screener_type} results to store")
            
        except Exception as e:
            logger.error(f"❌ Failed to store screen results: {e}")
    
    def update_watchlist(self):
        """Update the current watchlist based on screening results"""
        if self.pause_screening:
            logger.info("⏸️ Screening paused, skipping watchlist update")
            return
            
        try:
            # Store previous watchlist
            self.previous_watchlist = self.current_watchlist.copy()
            
            # Run screen and get new symbols
            new_symbols = self.run_screen()
            
            # Apply max watchlist size limit
            if len(new_symbols) > self.config.max_watchlist_size:
                logger.info(f"⚠️ Limiting watchlist to {self.config.max_watchlist_size} symbols (found {len(new_symbols)})")
                new_symbols = new_symbols[:self.config.max_watchlist_size]
            
            self.current_watchlist = set(new_symbols)
            
            # Calculate changes
            added_symbols = self.current_watchlist - self.previous_watchlist
            removed_symbols = self.previous_watchlist - self.current_watchlist
            
            # Log changes
            if added_symbols:
                logger.info(f"📈 Added to watchlist: {', '.join(added_symbols)}")
            if removed_symbols:
                logger.info(f"📉 Removed from watchlist: {', '.join(removed_symbols)}")
            
            # Update historical data for new symbols
            if added_symbols:
                self._fetch_historical_data_for_new_symbols(added_symbols)
            
            self.last_screen_time = datetime.now()
            logger.info(f"🎯 Watchlist updated: {len(self.current_watchlist)} symbols")
            
        except Exception as e:
            logger.error(f"❌ Watchlist update failed: {e}")
    
    def _fetch_historical_data_for_new_symbols(self, symbols: Set[str]):
        """Fetch historical data for newly added symbols"""
        logger.info(f"📚 Fetching historical data for {len(symbols)} new symbols...")
        
        # Calculate lookback to 4am previous trading day
        now = datetime.now()
        if now.weekday() == 0:  # Monday
            # Go back to Friday 4am
            days_back = 3
        else:
            # Go back to previous day 4am
            days_back = self.config.historical_lookback_days
        
        target_time = now.replace(hour=4, minute=0, second=0, microsecond=0) - timedelta(days=days_back)
        lookback_hours = int((now - target_time).total_seconds() / 3600)
        
        logger.info(f"📅 Fetching data back to: {target_time} ({lookback_hours} hours)")
        
        for symbol in symbols:
            try:
                success = self.historical_ingestion.ingest_historical_data(
                    symbol=symbol,
                    exchange="NASDAQ",  # Could be made dynamic
                    lookback_hours=lookback_hours,
                    interval=self.config.data_interval,
                    add_indicators=True,
                    update_mode="append"
                )
                
                if success:
                    logger.info(f"✅ Historical data ingested for {symbol}")
                else:
                    logger.warning(f"⚠️ Historical data ingestion failed for {symbol}")
                    
            except Exception as e:
                logger.error(f"❌ Historical data ingestion error for {symbol}: {e}")
    
    def start_live_data_collection(self):
        """Start live data collection for watchlist symbols"""
        if self.live_data_manager and self.config.live_data_enabled:
            success = self.live_data_manager.start()
            if success:
                logger.info("📡 Live data collection started")
            else:
                logger.error("❌ Failed to start live data collection")
        else:
            logger.info("💡 Live data collection disabled or not available")
    
    def start_system(self):
        """Start the momentum trading system"""
        logger.info("🎬 Starting HA Momentum Trading System")
        
        try:
            # Initial watchlist update
            logger.info("📊 Running initial screen...")
            self.update_watchlist()
            
            # Schedule watchlist updates every minute
            schedule.every(self.config.screening_interval_minutes).minutes.do(self.update_watchlist)
            
            # Start live data collection
            self.start_live_data_collection()
            
            self.system_running = True
            logger.info("✅ System started successfully")
            
            # Main event loop
            self._run_scheduler()
            
        except KeyboardInterrupt:
            logger.info("🛑 System shutdown requested")
            self.stop_system()
        except Exception as e:
            logger.error(f"❌ System error: {e}")
            self.stop_system()
    
    def _run_scheduler(self):
        """Run the scheduling loop"""
        logger.info("⏰ Scheduler started - watchlist will update every minute")
        
        try:
            while self.system_running:
                schedule.run_pending()
                time.sleep(1)  # Check every second
                
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler interrupted")
    
    def stop_system(self):
        """Stop the momentum trading system"""
        logger.info("🛑 Stopping HA Momentum Trading System")
        
        self.system_running = False
        
        # Stop any running threads
        for thread in self.data_collection_threads.values():
            if thread.is_alive():
                thread.join(timeout=5)
        
        # Close database connections
        if self.db_ops:
            self.db_ops.session.close()
        
        # Stop live data collection
        if self.live_data_manager:
            self.live_data_manager.stop()
        
        logger.info("✅ System stopped successfully")
    
    def get_system_status(self) -> Dict:
        """Get current system status"""
        market_state = self.get_current_market_state()
        
        return {
            'system_running': self.system_running,
            'screening_paused': self.pause_screening,
            'market_state': market_state,
            'watchlist_size': len(self.current_watchlist),
            'current_watchlist': list(self.current_watchlist),
            'last_screen_time': self.last_screen_time.isoformat() if self.last_screen_time else None,
            'screening_interval': self.config.screening_interval_minutes,
            'max_watchlist_size': self.config.max_watchlist_size,
            'components_initialized': {
                'screeners': True,  # Functions are always available
                'historical_ingestion': self.historical_ingestion is not None and self.historical_ingestion.initialized,
                'database': self.db_ops is not None,
                'live_data': self.live_data_manager is not None and self.live_data_manager.initialized if self.config.live_data_enabled else False
            }
        }
    
    def pause_screening_func(self):
        """Pause the screening process"""
        self.pause_screening = True
        logger.info("⏸️ Screening paused")
    
    def resume_screening_func(self):
        """Resume the screening process"""
        self.pause_screening = False
        logger.info("▶️ Screening resumed")
    
    def update_config(self, **kwargs):
        """Update configuration parameters"""
        updated_fields = []
        
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                old_value = getattr(self.config, key)
                setattr(self.config, key, value)
                updated_fields.append(f"{key}: {old_value} -> {value}")
                
                # Special handling for scheduling interval
                if key == 'screening_interval_minutes':
                    schedule.clear()  # Clear existing schedule
                    schedule.every(value).minutes.do(self.update_watchlist)
                    logger.info(f"⏰ Screening interval updated to {value} minutes")
            else:
                logger.warning(f"⚠️ Unknown configuration parameter: {key}")
        
        if updated_fields:
            logger.info(f"⚙️ Configuration updated: {', '.join(updated_fields)}")
            self.config.save_to_file()  # Auto-save changes
        
    def force_screen_now(self):
        """Force an immediate screen update"""
        logger.info("🔄 Forcing immediate screen update...")
        self.update_watchlist()
    
    def clear_watchlist(self):
        """Clear the current watchlist"""
        old_size = len(self.current_watchlist)
        self.current_watchlist.clear()
        logger.info(f"🗑️ Watchlist cleared (removed {old_size} symbols)")
    
    def add_symbol_to_watchlist(self, symbol: str):
        """Manually add a symbol to the watchlist"""
        symbol = symbol.upper().strip()
        if symbol in self.current_watchlist:
            logger.info(f"ℹ️ {symbol} already in watchlist")
        else:
            self.current_watchlist.add(symbol)
            logger.info(f"➕ Added {symbol} to watchlist")
            # Fetch historical data for the new symbol
            self._fetch_historical_data_for_new_symbols({symbol})
    
    def remove_symbol_from_watchlist(self, symbol: str):
        """Manually remove a symbol from the watchlist"""
        symbol = symbol.upper().strip()
        if symbol in self.current_watchlist:
            self.current_watchlist.remove(symbol)
            logger.info(f"➖ Removed {symbol} from watchlist")
        else:
            logger.info(f"ℹ️ {symbol} not in watchlist")


def print_help():
    """Print available console commands"""
    print("\n" + "="*60)
    print("  📋 CONSOLE COMMANDS")
    print("="*60)
    print("  status          - Show system status")
    print("  pause           - Pause screening")
    print("  resume          - Resume screening") 
    print("  screen          - Force immediate screen")
    print("  watchlist       - Show current watchlist")
    print("  clear           - Clear watchlist")
    print("  add <SYMBOL>    - Add symbol to watchlist")
    print("  remove <SYMBOL> - Remove symbol from watchlist")
    print("  config          - Show current configuration")
    print("  set <key>=<val> - Update configuration")
    print("  save            - Save current config to file")
    print("  db              - Check database status")
    print("  restart-db      - Restart TimescaleDB container")
    print("  live            - Show live data status")
    print("  start-live      - Start live data collection")
    print("  stop-live       - Stop live data collection")
    print("  help            - Show this help")
    print("  quit/exit       - Stop the system")
    print("="*60)
    print("  Examples:")
    print("    set screening_interval_minutes=2")
    print("    set max_watchlist_size=25")
    print("    add AAPL")
    print("    remove MSFT")
    print("    db")
    print("    restart-db")
    print("="*60 + "\n")


def setup_argument_parser():
    """Setup command line argument parser"""
    parser = argparse.ArgumentParser(
        description="HA Momentum Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --interval 2 --max-watchlist 25
  python main.py --config custom_config.json
  python main.py --console-only
        """
    )
    
    parser.add_argument('--config', '-c', 
                       help='Configuration file path (default: config.json)',
                       default='config.json')
    
    parser.add_argument('--interval', '-i', type=int,
                       help='Screening interval in minutes (default: 1)')
    
    parser.add_argument('--max-watchlist', '-w', type=int,
                       help='Maximum watchlist size (default: 50)')
    
    parser.add_argument('--lookback-days', '-l', type=int,
                       help='Historical data lookback days (default: 1)')
    
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    
    parser.add_argument('--console-only', action='store_true',
                       help='Start in console-only mode (no automatic screening)')
    
    parser.add_argument('--no-console', action='store_true',
                       help='Run without console interface (background mode)')
    
    return parser


class ConsoleInterface:
    """Interactive console interface for system control"""
    
    def __init__(self, system: MomentumTradingSystem):
        self.system = system
        self.running = True
    
    def start(self):
        """Start the console interface"""
        print("\n🎮 Console interface started. Type 'help' for commands.")
        
        while self.running and self.system.system_running:
            try:
                command = input("\n> ").strip().lower()
                if not command:
                    continue
                
                self._process_command(command)
                
            except KeyboardInterrupt:
                print("\n🛑 Console interrupted. Use 'quit' to exit.")
            except EOFError:
                print("\n👋 Console session ended.")
                break
    
    def _process_command(self, command: str):
        """Process a console command"""
        parts = command.split()
        cmd = parts[0]
        
        try:
            if cmd in ['quit', 'exit', 'stop']:
                print("🛑 Stopping system...")
                self.system.stop_system()
                self.running = False
                
            elif cmd == 'help':
                print_help()
                
            elif cmd == 'status':
                status = self.system.get_system_status()
                self._print_status(status)
                
            elif cmd == 'pause':
                self.system.pause_screening = True
                print("⏸️ Screening paused")
                
            elif cmd == 'resume':
                self.system.pause_screening = False
                print("▶️ Screening resumed")
                
            elif cmd == 'screen':
                self.system.force_screen_now()
                
            elif cmd == 'watchlist':
                wl = list(self.system.current_watchlist)
                if wl:
                    print(f"📋 Watchlist ({len(wl)} symbols): {', '.join(sorted(wl))}")
                else:
                    print("📋 Watchlist is empty")
                    
            elif cmd == 'clear':
                self.system.clear_watchlist()
                
            elif cmd == 'add' and len(parts) > 1:
                symbol = parts[1].upper()
                self.system.add_symbol_to_watchlist(symbol)
                
            elif cmd == 'remove' and len(parts) > 1:
                symbol = parts[1].upper()
                self.system.remove_symbol_from_watchlist(symbol)
                
            elif cmd == 'config':
                self._print_config()
                
            elif cmd == 'set' and len(parts) > 1:
                self._handle_config_update(' '.join(parts[1:]))
                
            elif cmd == 'save':
                self.system.config.save_to_file()
                print("💾 Configuration saved")
                
            elif cmd == 'db':
                self._check_database_status()
                
            elif cmd == 'restart-db':
                self._restart_database()
                
            elif cmd == 'live':
                self._show_live_data_status()
                
            elif cmd == 'start-live':
                self._start_live_data()
                
            elif cmd == 'stop-live':
                self._stop_live_data()
                
            else:
                print(f"❓ Unknown command: '{command}'. Type 'help' for available commands.")
                
        except Exception as e:
            print(f"❌ Command error: {e}")
    
    def _print_status(self, status: Dict):
        """Print system status in a formatted way"""
        print("\n" + "="*50)
        print("  📊 SYSTEM STATUS")
        print("="*50)
        print(f"  Running: {'✅ Yes' if status['system_running'] else '❌ No'}")
        print(f"  Screening: {'⏸️ Paused' if status.get('screening_paused') else '▶️ Active'}")
        print(f"  Market State: {status['market_state'].upper()}")
        print(f"  Watchlist Size: {status['watchlist_size']}")
        print(f"  Last Screen: {status['last_screen_time'] or 'Never'}")
        print(f"  Screen Interval: {status.get('screening_interval', 'N/A')} minutes")
        print("="*50)
        
        if status['current_watchlist']:
            print(f"  📋 Watchlist: {', '.join(sorted(status['current_watchlist'][:10]))}")
            if len(status['current_watchlist']) > 10:
                print(f"       (+{len(status['current_watchlist'])-10} more)")
        print("="*50 + "\n")
    
    def _print_config(self):
        """Print current configuration"""
        config = self.system.config
        print("\n" + "="*50)
        print("  ⚙️ CONFIGURATION")
        print("="*50)
        print(f"  Screening interval: {config.screening_interval_minutes} minutes")
        print(f"  Max watchlist size: {config.max_watchlist_size}")
        print(f"  Historical lookback: {config.historical_lookback_days} days")
        print(f"  Data interval: {config.data_interval}")
        print(f"  Extended hours: {config.include_extended_hours}")
        print(f"  Log level: {config.log_level}")
        print(f"  Paper trading: {config.paper_trading}")
        print("="*50)
        print("  Market Hours:")
        print(f"    Pre-market: {config.premarket_start} - {config.premarket_end}")
        print(f"    Regular: {config.market_open} - {config.market_close}")
        print(f"    After-hours: ends at {config.afterhours_end}")
        print("="*50 + "\n")
    
    def _handle_config_update(self, update_str: str):
        """Handle configuration update command"""
        try:
            if '=' not in update_str:
                print("❓ Format: set <key>=<value>")
                return
            
            key, value = update_str.split('=', 1)
            key = key.strip()
            value = value.strip()
            
            # Type conversion based on current config
            if hasattr(self.system.config, key):
                current_val = getattr(self.system.config, key)
                if isinstance(current_val, int):
                    value = int(value)
                elif isinstance(current_val, float):
                    value = float(value)
                elif isinstance(current_val, bool):
                    value = value.lower() in ['true', '1', 'yes', 'on']
                
                self.system.update_config(**{key: value})
            else:
                print(f"❓ Unknown configuration key: {key}")
                
        except ValueError as e:
            print(f"❌ Invalid value format: {e}")
        except Exception as e:
            print(f"❌ Configuration update failed: {e}")
    
    def _check_database_status(self):
        """Check and display database status"""
        print("\n🔍 Checking database status...")
        
        # Check Docker availability
        docker_ok = check_docker_available()
        print(f"  Docker: {'✅ Available' if docker_ok else '❌ Not available'}")
        
        if not docker_ok:
            print("  💡 Please install Docker and ensure it's running")
            return
        
        # Check container status
        container_info = check_timescaledb_container()
        print(f"  TimescaleDB Container:")
        print(f"    Exists: {'✅ Yes' if container_info['exists'] else '❌ No'}")
        print(f"    Running: {'✅ Yes' if container_info['running'] else '❌ No'}")
        print(f"    Name: {container_info['name']}")
        print(f"    Ports: {container_info['ports']}")
        
        # Test database connection
        if container_info['running']:
            print("  Database Connection:")
            connection_ok = test_connection()
            print(f"    Status: {'✅ Connected' if connection_ok else '❌ Connection failed'}")
        else:
            print("  Database Connection: ⏸️ Container not running")
        
        print()
    
    def _restart_database(self):
        """Restart the TimescaleDB database"""
        print("\n🔄 Restarting TimescaleDB database...")
        
        try:
            # Stop container if running
            container_info = check_timescaledb_container()
            
            if container_info['running']:
                print("  🛑 Stopping container...")
                if DOCKER_AVAILABLE:
                    client = docker.from_env()
                    container = client.containers.get('timescaledb')
                    container.stop()
                else:
                    subprocess.run(['docker', 'stop', 'timescaledb'], 
                                 capture_output=True, timeout=30)
                
                time.sleep(3)  # Wait for clean shutdown
            
            # Start container
            if start_timescaledb_container():
                print("  ✅ Database restarted successfully")
                
                # Test connection
                print("  🔌 Testing connection...")
                if test_connection():
                    print("  ✅ Database connection verified")
                else:
                    print("  ⚠️ Database started but connection test failed")
            else:
                print("  ❌ Failed to restart database")
                
        except Exception as e:
            print(f"  ❌ Error restarting database: {e}")
        
        print()
    
    def _show_live_data_status(self):
        """Show live data collection status"""
        print("\n📡 Live Data Status")
        print("="*40)
        
        if not self.system.live_data_manager:
            print("  Status: ❌ Not initialized")
            print("  Reason: Live data disabled in configuration")
            return
        
        stats = self.system.live_data_manager.get_stats()
        
        print(f"  Status: {'✅ Running' if stats['is_running'] else '❌ Stopped'}")
        print(f"  Initialized: {'✅ Yes' if stats['initialized'] else '❌ No'}")
        print(f"  Active Streams: {stats['streams_active']}")
        print(f"  Total Updates: {stats['total_updates']}")
        print(f"  Last Update: {stats['last_update'] or 'Never'}")
        print(f"  Update Interval: {stats['config']['update_interval']} seconds")
        print(f"  Max Batch Size: {stats['config']['batch_size']}")
        print(f"  Extended Hours: {stats['config']['extended_hours']}")
        
        if 'symbols' in stats and stats['symbols']:
            symbols = stats['symbols'][:10]  # Show first 10
            remaining = len(stats['symbols']) - 10
            print(f"  Active Symbols: {', '.join(symbols)}")
            if remaining > 0:
                print(f"                  (+{remaining} more)")
        else:
            print("  Active Symbols: None")
        
        print()
    
    def _start_live_data(self):
        """Start live data collection"""
        if not self.system.live_data_manager:
            print("❌ Live data manager not available")
            return
        
        if self.system.live_data_manager.is_running:
            print("ℹ️ Live data collection is already running")
            return
        
        print("🚀 Starting live data collection...")
        success = self.system.live_data_manager.start()
        
        if success:
            print("✅ Live data collection started")
        else:
            print("❌ Failed to start live data collection")
    
    def _stop_live_data(self):
        """Stop live data collection"""
        if not self.system.live_data_manager:
            print("❌ Live data manager not available")
            return
        
        if not self.system.live_data_manager.is_running:
            print("ℹ️ Live data collection is not running")
            return
        
        print("🛑 Stopping live data collection...")
        self.system.live_data_manager.stop()
        print("✅ Live data collection stopped")


def main():
    """Main entry point"""
    # Parse command line arguments
    parser = setup_argument_parser()
    args = parser.parse_args()
    
    print("=" * 80)
    print("  🎯 HA MOMENTUM TRADING SYSTEM")
    print("=" * 80)
    print("  📊 Dynamic Screening & Watchlist Management")
    print("  📈 Historical Data Ingestion")
    print("  📡 Live Data Collection (Coming Soon)")
    print("=" * 80)
    
    try:
        # Load configuration
        config = SystemConfig.load_from_file(args.config)
        
        # Override with command line arguments
        if args.interval:
            config.screening_interval_minutes = args.interval
        if args.max_watchlist:
            config.max_watchlist_size = args.max_watchlist
        if args.lookback_days:
            config.historical_lookback_days = args.lookback_days
        if args.log_level:
            config.log_level = args.log_level
        
        # Update logging level
        logger.setLevel(getattr(logging, config.log_level))
        
        # Initialize and start the system
        system = MomentumTradingSystem(config)
        
        # Show initial status
        status = system.get_system_status()
        logger.info(f"📋 System Status: {status}")
        
        if args.console_only:
            print("\n🎮 Starting in console-only mode (no automatic screening)")
            system.pause_screening = True
            console = ConsoleInterface(system)
            console.start()
        elif args.no_console:
            print("\n🤖 Starting in background mode (no console)")
            system.start_system()
        else:
            print("\n🎮 Starting with console interface")
            # Start system in background thread
            system_thread = threading.Thread(target=system.start_system, daemon=True)
            system_thread.start()
            
            # Start console interface
            console = ConsoleInterface(system)
            console.start()
        
    except KeyboardInterrupt:
        print("\n🛑 System shutdown requested by user")
    except Exception as e:
        logger.error(f"❌ System startup failed: {e}")
        print(f"\n💥 System failed to start: {e}")
    finally:
        print("\n👋 HA Momentum Trading System shutdown complete")


if __name__ == "__main__":
    main()
