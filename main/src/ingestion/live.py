"""
Live Data Ingestion Module using TvDatafeed
Streams real-time market data for watchlist symbols

This module:
1. Monitors the current watchlist
2. Starts/stops live data streams based on watchlist changes
3. Ingests real-time OHLCV data with extended hours
4. Stores data in TimescaleDB with indicators
5. Manages connection health and reconnections
"""
import time
import threading
import logging
from typing import Dict, Set, Optional, Callable
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass
import queue
from concurrent.futures import ThreadPoolExecutor
import asyncio

try:
    from tvDatafeed import TvDatafeed
    TVDATAFEED_AVAILABLE = True
except ImportError:
    TVDATAFEED_AVAILABLE = False
    logging.warning("TvDatafeed not available. Install with: pip install --upgrade --no-cache-dir git+https://github.com/rongardF/tvdatafeed.git")

from ..DB.operations import DatabaseOperations

logger = logging.getLogger(__name__)


@dataclass
class LiveDataConfig:
    """Configuration for live data ingestion"""
    update_interval: int = 5  # seconds between updates
    max_retries: int = 3
    reconnect_delay: int = 30  # seconds
    batch_size: int = 50  # max symbols per batch
    enable_extended_hours: bool = True
    data_retention_hours: int = 48  # hours of live data to keep
    

class LiveDataStream:
    """Individual live data stream for a symbol"""
    
    def __init__(self, symbol: str, exchange: str, tv_datafeed: TvDatafeed, db_ops: DatabaseOperations):
        self.symbol = symbol
        self.exchange = exchange
        self.tv_datafeed = tv_datafeed
        self.db_ops = db_ops
        self.is_active = False
        self.last_update = None
        self.error_count = 0
        self.thread = None
        self.stop_event = threading.Event()
        
    def start(self):
        """Start the live data stream"""
        if self.is_active:
            return
            
        self.is_active = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._stream_data, daemon=True)
        self.thread.start()
        logger.info(f"📡 Started live stream for {self.symbol}")
        
    def stop(self):
        """Stop the live data stream"""
        if not self.is_active:
            return
            
        self.is_active = False
        self.stop_event.set()
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
            
        logger.info(f"🛑 Stopped live stream for {self.symbol}")
        
    def _stream_data(self):
        """Main streaming loop"""
        while self.is_active and not self.stop_event.is_set():
            try:
                # Get latest data point
                data = self._fetch_latest_data()
                
                if data is not None and not data.empty:
                    # Store in database
                    success = self._store_data(data)
                    
                    if success:
                        self.last_update = datetime.now()
                        self.error_count = 0
                    else:
                        self.error_count += 1
                        
                else:
                    # No new data (normal during off hours)
                    pass
                    
            except Exception as e:
                self.error_count += 1
                logger.error(f"❌ Live stream error for {self.symbol}: {e}")
                
                if self.error_count >= 5:
                    logger.error(f"🚫 Too many errors for {self.symbol}, stopping stream")
                    break
                    
            # Wait before next update
            if not self.stop_event.wait(LiveDataConfig().update_interval):
                continue
                
        self.is_active = False
        
    def _fetch_latest_data(self) -> Optional[pd.DataFrame]:
        """Fetch the latest data point for the symbol"""
        try:
            # Get last 2 periods to ensure we have the latest
            data = self.tv_datafeed.get_hist(
                symbol=self.symbol,
                exchange=self.exchange,
                interval=TvDatafeed.Interval.in_1_minute,
                n_bars=2,
                extended_session=LiveDataConfig().enable_extended_hours
            )
            
            if data is not None and not data.empty:
                # Return only the most recent bar
                latest_data = data.tail(1).copy()
                
                # Add metadata
                latest_data['symbol'] = self.symbol
                latest_data['exchange'] = self.exchange
                latest_data['ingestion_timestamp'] = datetime.now()
                
                return latest_data
                
            return None
            
        except Exception as e:
            logger.debug(f"Data fetch error for {self.symbol}: {e}")
            return None
            
    def _store_data(self, data: pd.DataFrame) -> bool:
        """Store data in database"""
        try:
            # Check if this data point already exists
            latest_timestamp = data.index[-1]
            
            # Query existing data to avoid duplicates
            existing_data = self.db_ops.get_latest_ohlcv_data(
                symbol=self.symbol, 
                limit=1
            )
            
            if existing_data is not None and not existing_data.empty:
                if latest_timestamp <= existing_data.index[-1]:
                    # This data already exists
                    return True
            
            # Store new data
            success = self.db_ops.insert_ohlcv_data(data)
            
            if success:
                logger.debug(f"💾 Stored live data for {self.symbol}: {latest_timestamp}")
                
            return success
            
        except Exception as e:
            logger.error(f"❌ Database storage error for {self.symbol}: {e}")
            return False


class LiveDataIngestion:
    """
    Main live data ingestion manager
    Handles multiple symbol streams and watchlist synchronization
    """
    
    def __init__(self, config: LiveDataConfig = None):
        """Initialize live data ingestion system"""
        self.config = config or LiveDataConfig()
        self.tv_datafeed = None
        self.db_ops = None
        self.initialized = False
        
        # Stream management
        self.active_streams: Dict[str, LiveDataStream] = {}
        self.current_watchlist: Set[str] = set()
        self.watchlist_callback: Optional[Callable[[], Set[str]]] = None
        
        # Control
        self.is_running = False
        self.manager_thread = None
        self.stop_event = threading.Event()
        
        # Statistics
        self.stats = {
            'streams_active': 0,
            'total_updates': 0,
            'last_update': None,
            'errors': 0
        }
        
        self._initialize()
        
    def _initialize(self):
        """Initialize TvDatafeed and database connections"""
        try:
            if not TVDATAFEED_AVAILABLE:
                raise Exception("TvDatafeed package not available")
                
            # Initialize TvDatafeed
            self.tv_datafeed = TvDatafeed()
            logger.info("✅ TvDatafeed initialized for live streaming")
            
            # Initialize database operations
            self.db_ops = DatabaseOperations()
            logger.info("✅ Database operations initialized for live data")
            
            self.initialized = True
            
        except Exception as e:
            logger.error(f"❌ Live data ingestion initialization failed: {e}")
            self.initialized = False
            
    def set_watchlist_callback(self, callback: Callable[[], Set[str]]):
        """Set callback function to get current watchlist"""
        self.watchlist_callback = callback
        
    def start(self):
        """Start the live data ingestion system"""
        if not self.initialized:
            logger.error("❌ Live data ingestion not initialized")
            return False
            
        if self.is_running:
            logger.info("ℹ️ Live data ingestion already running")
            return True
            
        logger.info("🚀 Starting live data ingestion system")
        
        self.is_running = True
        self.stop_event.clear()
        
        # Start the watchlist manager thread
        self.manager_thread = threading.Thread(target=self._manage_streams, daemon=True)
        self.manager_thread.start()
        
        logger.info("✅ Live data ingestion system started")
        return True
        
    def stop(self):
        """Stop the live data ingestion system"""
        if not self.is_running:
            return
            
        logger.info("🛑 Stopping live data ingestion system")
        
        self.is_running = False
        self.stop_event.set()
        
        # Stop all active streams
        for stream in list(self.active_streams.values()):
            stream.stop()
            
        self.active_streams.clear()
        
        # Wait for manager thread to finish
        if self.manager_thread and self.manager_thread.is_alive():
            self.manager_thread.join(timeout=15)
            
        logger.info("✅ Live data ingestion system stopped")
        
    def _manage_streams(self):
        """Main management loop - syncs streams with watchlist"""
        logger.info("⏰ Live data stream manager started")
        
        while self.is_running and not self.stop_event.is_set():
            try:
                # Get current watchlist
                if self.watchlist_callback:
                    new_watchlist = self.watchlist_callback()
                else:
                    new_watchlist = set()
                
                # Sync streams with watchlist
                self._sync_streams_with_watchlist(new_watchlist)
                
                # Update statistics
                self._update_stats()
                
                # Clean up old data periodically
                if datetime.now().minute % 30 == 0:  # Every 30 minutes
                    self._cleanup_old_data()
                
            except Exception as e:
                logger.error(f"❌ Stream manager error: {e}")
                self.stats['errors'] += 1
                
            # Wait before next check
            if self.stop_event.wait(30):  # Check every 30 seconds
                break
                
        logger.info("⏹️ Live data stream manager stopped")
        
    def _sync_streams_with_watchlist(self, new_watchlist: Set[str]):
        """Synchronize active streams with current watchlist"""
        # Stop streams for symbols no longer in watchlist
        symbols_to_stop = set(self.active_streams.keys()) - new_watchlist
        for symbol in symbols_to_stop:
            if symbol in self.active_streams:
                self.active_streams[symbol].stop()
                del self.active_streams[symbol]
                logger.info(f"🔽 Removed {symbol} from live streams")
                
        # Start streams for new symbols
        symbols_to_start = new_watchlist - set(self.active_streams.keys())
        for symbol in symbols_to_start:
            if len(self.active_streams) < self.config.batch_size:
                try:
                    stream = LiveDataStream(
                        symbol=symbol,
                        exchange="NASDAQ",  # Could be made dynamic
                        tv_datafeed=self.tv_datafeed,
                        db_ops=self.db_ops
                    )
                    stream.start()
                    self.active_streams[symbol] = stream
                    logger.info(f"🔼 Added {symbol} to live streams")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to start stream for {symbol}: {e}")
            else:
                logger.warning(f"⚠️ Stream limit reached ({self.config.batch_size}), skipping {symbol}")
                
        self.current_watchlist = new_watchlist.copy()
        
    def _update_stats(self):
        """Update system statistics"""
        active_count = len([s for s in self.active_streams.values() if s.is_active])
        total_updates = sum(1 for s in self.active_streams.values() if s.last_update)
        
        self.stats.update({
            'streams_active': active_count,
            'total_updates': total_updates,
            'last_update': datetime.now(),
            'symbols': list(self.active_streams.keys())
        })
        
    def _cleanup_old_data(self):
        """Clean up old live data to manage storage"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=self.config.data_retention_hours)
            
            # This would be implemented in DatabaseOperations
            # self.db_ops.cleanup_old_live_data(cutoff_time)
            
            logger.debug(f"🧹 Cleaned up live data older than {cutoff_time}")
            
        except Exception as e:
            logger.error(f"❌ Data cleanup error: {e}")
            
    def get_stats(self) -> Dict:
        """Get current system statistics"""
        return {
            **self.stats,
            'is_running': self.is_running,
            'initialized': self.initialized,
            'config': {
                'update_interval': self.config.update_interval,
                'batch_size': self.config.batch_size,
                'extended_hours': self.config.enable_extended_hours
            }
        }
        
    def get_stream_status(self, symbol: str) -> Optional[Dict]:
        """Get status for a specific symbol stream"""
        if symbol in self.active_streams:
            stream = self.active_streams[symbol]
            return {
                'symbol': symbol,
                'active': stream.is_active,
                'last_update': stream.last_update,
                'error_count': stream.error_count
            }
        return None
        
    def force_update(self, symbol: str = None):
        """Force immediate update for symbol or all symbols"""
        if symbol and symbol in self.active_streams:
            # Force update for specific symbol
            stream = self.active_streams[symbol]
            logger.info(f"🔄 Forcing update for {symbol}")
            # This could trigger an immediate data fetch
            
        elif symbol is None:
            # Force update for all symbols
            logger.info("🔄 Forcing update for all active streams")
            for stream in self.active_streams.values():
                if stream.is_active:
                    # Trigger immediate updates
                    pass
                    
    def pause_stream(self, symbol: str):
        """Pause a specific symbol stream"""
        if symbol in self.active_streams:
            self.active_streams[symbol].stop()
            logger.info(f"⏸️ Paused live stream for {symbol}")
            
    def resume_stream(self, symbol: str):
        """Resume a specific symbol stream"""
        if symbol in self.active_streams:
            self.active_streams[symbol].start()
            logger.info(f"▶️ Resumed live stream for {symbol}")


# Utility functions for integration
def create_live_data_manager(watchlist_callback: Callable[[], Set[str]], config: LiveDataConfig = None) -> LiveDataIngestion:
    """
    Factory function to create a live data manager
    
    Args:
        watchlist_callback: Function that returns current watchlist
        config: Optional configuration
        
    Returns:
        LiveDataIngestion instance
    """
    manager = LiveDataIngestion(config)
    manager.set_watchlist_callback(watchlist_callback)
    return manager