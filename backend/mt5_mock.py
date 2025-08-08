"""
Mock MT5 service for cloud deployment where MetaTrader5 library is not available.
This allows the backend to run on Linux servers while maintaining API compatibility.
"""
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class MockAccountInfo:
    login: int = 12345678
    trade_mode: int = 0
    leverage: int = 100
    limit_orders: int = 200
    margin_so_mode: int = 0
    trade_allowed: bool = True
    trade_expert: bool = True
    margin_mode: int = 0
    currency_digits: int = 2
    fifo_close: bool = False
    balance: float = 10000.0
    credit: float = 0.0
    profit: float = 0.0
    equity: float = 10000.0
    margin: float = 0.0
    margin_free: float = 10000.0
    margin_level: float = 0.0
    margin_so_call: float = 50.0
    margin_so_so: float = 30.0
    margin_initial: float = 0.0
    margin_maintenance: float = 0.0
    assets: float = 0.0
    liabilities: float = 0.0
    commission_blocked: float = 0.0
    name: str = "Mock Demo Account"
    server: str = "MockServer-Demo"
    currency: str = "USD"
    company: str = "Mock Broker Ltd"

@dataclass 
class MockTradePosition:
    ticket: int
    time: int
    time_msc: int
    time_update: int
    time_update_msc: int
    type: int
    magic: int
    identifier: int
    reason: int
    volume: float
    price_open: float
    sl: float
    tp: float
    price_current: float
    swap: float
    profit: float
    symbol: str
    comment: str = ""
    external_id: str = ""

class MockMT5:
    """Mock MT5 class that simulates MetaTrader5 functionality for cloud deployment"""
    
    def __init__(self):
        self.initialized = False
        self.logged_in = False
        self.account_info_data = MockAccountInfo()
        self.positions_data: List[MockTradePosition] = []
        self.deals_data: List[Dict[str, Any]] = []
        
    def initialize(self, path: str = None, login: int = None, password: str = None, server: str = None, timeout: int = None, portable: bool = False) -> bool:
        """Mock initialize - always returns True in cloud mode"""
        logger.info("MockMT5: Initialize called - simulating success")
        self.initialized = True
        return True
        
    def login(self, login: int, password: str = "", server: str = "") -> bool:
        """Mock login - always returns True in cloud mode"""
        logger.info(f"MockMT5: Login called for account {login} - simulating success")
        self.logged_in = True
        self.account_info_data.login = login
        self.account_info_data.server = server or "MockServer-Demo"
        return True
        
    def shutdown(self) -> None:
        """Mock shutdown"""
        logger.info("MockMT5: Shutdown called")
        self.initialized = False
        self.logged_in = False
        
    def account_info(self) -> Optional[MockAccountInfo]:
        """Return mock account info"""
        if not self.logged_in:
            return None
        return self.account_info_data
        
    def positions_get(self, symbol: str = None, group: str = None, ticket: int = None) -> tuple:
        """Return mock positions"""
        if not self.logged_in:
            return tuple()
        return tuple(self.positions_data)
        
    def history_deals_get(self, date_from, date_to, group: str = "", position: int = None) -> tuple:
        """Return mock historical deals"""
        if not self.logged_in:
            return tuple()
        return tuple(self.deals_data)
        
    def last_error(self) -> tuple:
        """Return mock error info"""
        return (0, "Success")

# Global mock instance
mock_mt5 = MockMT5()

# Mock constants that match the real MT5 library
TRADE_ACTION_DEAL = 1
TRADE_ACTION_PENDING = 5
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
POSITION_TYPE_BUY = 0
POSITION_TYPE_SELL = 1 