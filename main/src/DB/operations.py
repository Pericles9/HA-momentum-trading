"""
Database operations for TimescaleDB
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text, desc

from .connection import engine, SessionLocal, get_db
from .models import ScreenerResult, OHLCVData, TradingSignals


class DatabaseOperations:
    """
    Class to handle database operations
    """
    
    def __init__(self):
        self.session = SessionLocal()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
    
    def setup_timescaledb(self):
        """
        Setup TimescaleDB hypertables for time-series data
        """
        try:
            # Create TimescaleDB extension if not exists
            self.session.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))
            
            # Convert tables to hypertables
            hypertable_queries = [
                "SELECT create_hypertable('screener_results', 'timestamp', if_not_exists => TRUE);",
                "SELECT create_hypertable('ohlcv_data', 'timestamp', if_not_exists => TRUE);",
                "SELECT create_hypertable('trading_signals', 'timestamp', if_not_exists => TRUE);"
            ]
            
            for query in hypertable_queries:
                try:
                    self.session.execute(text(query))
                except Exception as e:
                    print(f"Hypertable creation warning: {e}")
            
            self.session.commit()
            print("TimescaleDB hypertables setup completed successfully!")
            
        except Exception as e:
            self.session.rollback()
            print(f"TimescaleDB setup error: {e}")
    
    def execute_query(self, query: str, params=None):
        """
        Execute a raw SQL query and return results
        
        Args:
            query: SQL query string
            params: Query parameters (tuple, list, or dict)
            
        Returns:
            List of tuples with query results, or None if error
        """
        try:
            if params:
                # Handle different parameter styles
                if isinstance(params, (tuple, list)):
                    # Convert %s style to numbered parameters for SQLAlchemy
                    if '%s' in query:
                        # Replace %s with :1, :2, etc.
                        param_dict = {}
                        parts = query.split('%s')
                        new_query = parts[0]
                        for i, param in enumerate(params):
                            param_name = f"param_{i}"
                            param_dict[param_name] = param
                            new_query += f":{param_name}"
                            if i + 1 < len(parts):
                                new_query += parts[i + 1]
                        result = self.session.execute(text(new_query), param_dict)
                    else:
                        # Assume named parameters
                        result = self.session.execute(text(query), dict(enumerate(params)))
                else:
                    # Dict parameters
                    result = self.session.execute(text(query), params)
            else:
                result = self.session.execute(text(query))
            
            # Return all rows as list of tuples
            return result.fetchall()
            
        except Exception as e:
            print(f"Error executing query: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            self.session.rollback()
            return None
    
    def insert_screener_results(self, df: pd.DataFrame, screener_type: str) -> bool:
        """
        Insert screener results from DataFrame
        
        Args:
            df: DataFrame with screener results
            screener_type: 'PMH' or 'RTH'
        
        Returns:
            bool: Success status
        """
        try:
            timestamp = datetime.utcnow()
            
            for index, row in df.iterrows():
                screener_result = ScreenerResult(
                    timestamp=timestamp,
                    screener_type=screener_type,
                    symbol=str(row.get('Symbol', '')),
                    name=str(row.get('Name', '')),
                    change_percent=self._safe_float(row.get('Change %')),
                    price=self._safe_float(row.get('Price')),
                    volume=self._safe_int(row.get('Volume')),
                    market_cap=str(row.get('Market Cap', '')),
                    rank=int(row.get('#', index + 1))
                )
                self.session.add(screener_result)
            
            self.session.commit()
            print(f"Successfully inserted {len(df)} {screener_type} screener results")
            return True
            
        except Exception as e:
            self.session.rollback()
            print(f"Error inserting screener results: {e}")
            return False
    
    def insert_ohlcv_data(self, symbol: str, timeframe: str, ohlcv_data: List[Dict]) -> bool:
        """
        Insert OHLCV data with indicators
        
        Args:
            symbol: Stock symbol
            timeframe: Time frame ('1m', '10m', etc.)
            ohlcv_data: List of OHLCV dictionaries
        
        Returns:
            bool: Success status
        """
        try:
            for data in ohlcv_data:
                ohlcv_record = OHLCVData(
                    timestamp=data['timestamp'],
                    symbol=symbol,
                    timeframe=timeframe,
                    open_price=data['open'],
                    high_price=data['high'],
                    low_price=data['low'],
                    close_price=data['close'],
                    volume=data['volume'],
                    # Indicators (optional)
                    sma_20=data.get('sma_20'),
                    sma_50=data.get('sma_50'),
                    ema_12=data.get('ema_12'),
                    ema_26=data.get('ema_26'),
                    rsi=data.get('rsi'),
                    macd=data.get('macd'),
                    macd_signal=data.get('macd_signal'),
                    macd_histogram=data.get('macd_histogram'),
                    bollinger_upper=data.get('bollinger_upper'),
                    bollinger_middle=data.get('bollinger_middle'),
                    bollinger_lower=data.get('bollinger_lower')
                )
                self.session.add(ohlcv_record)
            
            self.session.commit()
            print(f"Successfully inserted {len(ohlcv_data)} OHLCV records for {symbol}")
            return True
            
        except Exception as e:
            self.session.rollback()
            print(f"Error inserting OHLCV data: {e}")
            return False
    
    def get_latest_screener_results(self, screener_type: str, limit: int = 100) -> pd.DataFrame:
        """
        Get latest screener results
        
        Args:
            screener_type: 'PMH' or 'RTH'
            limit: Number of results to return
        
        Returns:
            pd.DataFrame: Screener results
        """
        try:
            query = self.session.query(ScreenerResult).filter(
                ScreenerResult.screener_type == screener_type
            ).order_by(desc(ScreenerResult.timestamp)).limit(limit)
            
            results = query.all()
            
            # Convert to DataFrame
            data = []
            for result in results:
                data.append({
                    'timestamp': result.timestamp,
                    'symbol': result.symbol,
                    'name': result.name,
                    'change_percent': result.change_percent,
                    'price': result.price,
                    'volume': result.volume,
                    'market_cap': result.market_cap,
                    'rank': result.rank
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            print(f"Error getting screener results: {e}")
            return pd.DataFrame()
    
    def get_ohlcv_data(self, symbol: str, timeframe: str, days: int = 30) -> pd.DataFrame:
        """
        Get OHLCV data for a symbol
        
        Args:
            symbol: Stock symbol
            timeframe: Time frame
            days: Number of days to retrieve
        
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = text("""
                SELECT * FROM ohlcv_data 
                WHERE symbol = :symbol 
                AND timeframe = :timeframe 
                AND timestamp >= :cutoff_date
                ORDER BY timestamp DESC
            """)
            
            result = self.session.execute(query, {
                'symbol': symbol,
                'timeframe': timeframe,
                'cutoff_date': cutoff_date
            })
            
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            return pd.DataFrame(data)
            
        except Exception as e:
            print(f"Error getting OHLCV data: {e}")
            return pd.DataFrame()
    
    def get_latest_ohlcv_data(self, symbol: str, limit: int = 1) -> pd.DataFrame:
        """
        Get the latest OHLCV data for a symbol
        
        Args:
            symbol: Stock symbol
            limit: Number of latest records to retrieve
        
        Returns:
            pd.DataFrame: Latest OHLCV data with timestamp as index
        """
        try:
            query = text("""
                SELECT timestamp, open_price as open, high_price as high, low_price as low, close_price as close, volume, symbol, timeframe
                FROM ohlcv_data 
                WHERE symbol = :symbol 
                ORDER BY timestamp DESC
                LIMIT :limit
            """)
            
            result = self.session.execute(query, {
                'symbol': symbol,
                'limit': limit
            })
            
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            if data:
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                return df.sort_index()
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error getting latest OHLCV data: {e}")
            return pd.DataFrame()
    
    def cleanup_old_live_data(self, cutoff_time: datetime):
        """
        Clean up old live data to manage storage
        
        Args:
            cutoff_time: Delete data older than this timestamp
        """
        try:
            query = text("""
                DELETE FROM ohlcv_data 
                WHERE timestamp < :cutoff_time
                AND ingestion_timestamp IS NOT NULL
            """)
            
            result = self.session.execute(query, {'cutoff_time': cutoff_time})
            self.session.commit()
            
            print(f"Cleaned up {result.rowcount} old live data records")
            
        except Exception as e:
            print(f"Error cleaning up old data: {e}")
            self.session.rollback()
    
    @staticmethod
    def _safe_float(value) -> Optional[float]:
        """Convert value to float safely"""
        try:
            if pd.isna(value) or value == '' or value is None:
                return None
            # Remove % sign and other characters
            if isinstance(value, str):
                value = value.replace('%', '').replace(',', '').replace('$', '')
            return float(value)
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _safe_int(value) -> Optional[int]:
        """Convert value to int safely"""
        try:
            if pd.isna(value) or value == '' or value is None:
                return None
            # Remove commas and other characters
            if isinstance(value, str):
                value = value.replace(',', '')
            return int(float(value))
        except (ValueError, TypeError):
            return None