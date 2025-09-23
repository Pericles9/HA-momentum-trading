"""
Database models for TimescaleDB
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .connection import Base


class ScreenerResult(Base):
    """
    Table to store screener results over time
    """
    __tablename__ = 'screener_results'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    screener_type = Column(String(10), nullable=False)  # 'PMH' or 'RTH'
    symbol = Column(String(10), nullable=False)
    name = Column(String(100))
    change_percent = Column(Float)
    price = Column(Float)
    volume = Column(Integer)
    market_cap = Column(String(20))
    rank = Column(Integer)  # Position in the screener results
    
    # Create indexes for efficient querying
    __table_args__ = (
        Index('idx_screener_timestamp', 'timestamp'),
        Index('idx_screener_symbol', 'symbol'),
        Index('idx_screener_type', 'screener_type'),
        Index('idx_screener_symbol_timestamp', 'symbol', 'timestamp'),
    )


class OHLCVData(Base):
    """
    Table to store OHLCV data with indicators
    """
    __tablename__ = 'ohlcv_data'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    symbol = Column(String(10), nullable=False)
    timeframe = Column(String(5), nullable=False)  # '1m', '10m', etc.
    
    # OHLCV data
    open_price = Column(Float, nullable=False)
    high_price = Column(Float, nullable=False)
    low_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    
    # Technical indicators (optional, can be NULL)
    sma_20 = Column(Float)
    sma_50 = Column(Float)
    ema_12 = Column(Float)
    ema_26 = Column(Float)
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_histogram = Column(Float)
    bollinger_upper = Column(Float)
    bollinger_middle = Column(Float)
    bollinger_lower = Column(Float)
    
    # Create indexes for efficient querying
    __table_args__ = (
        Index('idx_ohlcv_timestamp', 'timestamp'),
        Index('idx_ohlcv_symbol', 'symbol'),
        Index('idx_ohlcv_timeframe', 'timeframe'),
        Index('idx_ohlcv_symbol_timeframe', 'symbol', 'timeframe'),
        Index('idx_ohlcv_symbol_timeframe_timestamp', 'symbol', 'timeframe', 'timestamp'),
    )


class TradingSignals(Base):
    """
    Table to store trading signals generated from analysis
    """
    __tablename__ = 'trading_signals'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    symbol = Column(String(10), nullable=False)
    signal_type = Column(String(10), nullable=False)  # 'BUY', 'SELL', 'HOLD'
    confidence = Column(Float)  # 0.0 to 1.0
    strategy_name = Column(String(50), nullable=False)
    timeframe = Column(String(5), nullable=False)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    notes = Column(Text)
    
    # Create indexes
    __table_args__ = (
        Index('idx_signals_timestamp', 'timestamp'),
        Index('idx_signals_symbol', 'symbol'),
        Index('idx_signals_type', 'signal_type'),
        Index('idx_signals_strategy', 'strategy_name'),
    )