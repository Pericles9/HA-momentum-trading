"""
Abstract base class for trading strategies.
Defines the required interface for all strategies.
"""
from abc import ABC, abstractmethod

class BaseStrategy(ABC):
    @abstractmethod
    def generate_signals(self, data):
        """Generate trading signals based on input data."""
        pass

    @abstractmethod
    def calculate_position_size(self, balance, risk):
        """Calculate position size based on account balance and risk."""
        pass
