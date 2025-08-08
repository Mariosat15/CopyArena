from datetime import datetime, timedelta

# Optional imports for data processing (only needed for real MT5)
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    pd = None
    np = None
    PANDAS_AVAILABLE = False
import asyncio
import json
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass
from sqlalchemy.orm import Session
import os
import platform

# Conditional MT5 import - use mock for cloud deployment
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("MT5 library loaded successfully - Windows environment detected")
except ImportError:
    from mt5_mock import mock_mt5 as mt5, MockAccountInfo, MockTradePosition
    MT5_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.info("MT5 library not available - using mock for cloud deployment")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MT5TradeInfo:
    ticket: int
    symbol: str
    trade_type: str  # BUY or SELL
    volume: float
    open_price: float
    close_price: float
    open_time: datetime
    close_time: datetime
    profit: float
    swap: float
    commission: float
    comment: str
    magic: int
    is_open: bool

@dataclass
class MT5AccountInfo:
    login: int
    server: str
    name: str
    company: str
    currency: str
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float

class MT5Bridge:
    def __init__(self, user_id: int = None):
        self.user_id = user_id
        self.connected = False
        self.account_info = None
        self.active_trades = {}
        self.last_update = None
        self.login = None
        self.password = None
        self.server = None
        self._connection_lock = asyncio.Lock()
        
    async def connect(self, login: int = None, password: str = None, server: str = None) -> bool:
        """Connect to MT5 terminal with user isolation"""
        async with self._connection_lock:
            try:
                # Store user credentials for reconnection
                if login and password and server:
                    self.login = login
                    self.password = password
                    self.server = server
                
                # Handle cloud deployment (mock MT5)
                if not MT5_AVAILABLE:
                    logger.info(f"User {self.user_id}: Using mock MT5 for cloud deployment")
                    if not mt5.initialize():
                        logger.error(f"User {self.user_id}: Failed to initialize mock MT5")
                        return False
                    
                    # Mock login
                    if login and password and server:
                        if not mt5.login(login, password, server):
                            logger.error(f"User {self.user_id}: Failed to login to mock MT5")
                            return False
                        logger.info(f"User {self.user_id}: Successfully connected to mock MT5 account {login}")
                    
                    self.connected = True
                    return True
                
                # Initialize real MT5 connection (Windows)
                if not mt5.initialize():
                    logger.error(f"User {self.user_id}: Failed to initialize MT5")
                    return False
                
                # If this user has credentials, ensure we're connected to their account
                if self.login and self.password and self.server:
                    # Check if we're already connected to this user's account
                    current_account = mt5.account_info()
                    if current_account and current_account.login == self.login:
                        logger.info(f"User {self.user_id}: Already connected to correct MT5 account {self.login}")
                    else:
                        # Need to switch to this user's account
                        logger.info(f"User {self.user_id}: Switching to MT5 account {self.login}")
                        if not mt5.login(self.login, password=self.password, server=self.server):
                            logger.error(f"User {self.user_id}: Failed to login to MT5 account {self.login}")
                            mt5.shutdown()
                            return False
                        logger.info(f"User {self.user_id}: Successfully logged in to MT5 account {self.login}")
                else:
                    # NO FALLBACK - Users must provide their own credentials for isolation
                    logger.error(f"User {self.user_id}: No credentials provided - cannot connect to MT5")
                    logger.error(f"User {self.user_id}: Each user must provide their own MT5 account credentials")
                    return False
                
                self.connected = True
                self.account_info = await self._get_account_info()
                logger.info(f"User {self.user_id}: MT5 Bridge connected successfully")
                return True
                
            except Exception as e:
                logger.error(f"User {self.user_id}: Error connecting to MT5: {e}")
                return False
    
    async def _ensure_user_connection(self):
        """Ensure we're connected to this user's specific account before any operation"""
        if not self.connected:
            return False
            
        if self.login and self.password and self.server:
            current_account = mt5.account_info()
            if not current_account or current_account.login != self.login:
                logger.info(f"User {self.user_id}: Reconnecting to correct account {self.login}")
                return await self.connect(self.login, self.password, self.server)
        
        return True

    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info(f"User {self.user_id}: MT5 Bridge disconnected")
    
    async def _get_account_info(self) -> Optional[MT5AccountInfo]:
        """Get account information"""
        if not await self._ensure_user_connection():
            return None
            
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return None
                
            return MT5AccountInfo(
                login=account_info.login,
                server=account_info.server,
                name=account_info.name,
                company=account_info.company,
                currency=account_info.currency,
                balance=account_info.balance,
                equity=account_info.equity,
                margin=account_info.margin,
                free_margin=account_info.margin_free,
                margin_level=account_info.margin_level,
                profit=account_info.profit
            )
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def get_open_positions(self) -> List[MT5TradeInfo]:
        """Get all open positions"""
        if not self.connected:
            logger.warning("Not connected to MT5, cannot get positions")
            return []
            
        try:
            positions = mt5.positions_get()
            if positions is None:
                logger.info("No open positions found")
                return []
            
            logger.info(f"Found {len(positions)} open positions")
            trades = []
            for pos in positions:
                trade = MT5TradeInfo(
                    ticket=pos.ticket,
                    symbol=pos.symbol,
                    trade_type="BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                    volume=pos.volume,
                    open_price=pos.price_open,
                    close_price=pos.price_current,
                    open_time=datetime.fromtimestamp(pos.time),
                    close_time=datetime.now(),
                    profit=pos.profit,
                    swap=getattr(pos, 'swap', 0.0),
                    commission=getattr(pos, 'commission', 0.0),
                    comment=getattr(pos, 'comment', ''),
                    magic=getattr(pos, 'magic', 0),
                    is_open=True
                )
                trades.append(trade)
                logger.info(f"Position: {pos.symbol} {trade.trade_type} {pos.volume} lots, profit: {pos.profit}")
            
            return trades
            
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            return []
    
    def get_trade_history(self, days: int = 30) -> List[MT5TradeInfo]:
        """Get trade history for specified number of days"""
        if not self.connected:
            logger.warning("Not connected to MT5, cannot get trade history")
            return []
            
        try:
            # Get history for the last N days
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            logger.info(f"Getting trade history from {from_date} to {to_date}")
            deals = mt5.history_deals_get(from_date, to_date)
            if deals is None:
                logger.info("No trade history found")
                return []
            
            logger.info(f"Found {len(deals)} deals in history")
            trades = []
            for deal in deals:
                if deal.entry == mt5.DEAL_ENTRY_OUT:  # Only closed trades
                    trade = MT5TradeInfo(
                        ticket=deal.ticket,
                        symbol=deal.symbol,
                        trade_type="BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL",
                        volume=deal.volume,
                        open_price=deal.price,
                        close_price=deal.price,
                        open_time=datetime.fromtimestamp(deal.time),
                        close_time=datetime.fromtimestamp(deal.time),
                        profit=deal.profit,
                        swap=getattr(deal, 'swap', 0.0),
                        commission=getattr(deal, 'commission', 0.0),
                        comment=getattr(deal, 'comment', ''),
                        magic=getattr(deal, 'magic', 0),
                        is_open=False
                    )
                    trades.append(trade)
                    logger.info(f"History: {deal.symbol} {trade.trade_type} {deal.volume} lots, profit: {deal.profit}")
            
            logger.info(f"Processed {len(trades)} closed trades from history")
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        """Get symbol information and current price"""
        if not self.connected:
            return None
            
        try:
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return None
            
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return None
            
            return {
                "symbol": symbol,
                "bid": tick.bid,
                "ask": tick.ask,
                "spread": tick.ask - tick.bid,
                "digits": symbol_info.digits,
                "point": symbol_info.point,
                "trade_mode": symbol_info.trade_mode,
                "volume_min": symbol_info.volume_min,
                "volume_max": symbol_info.volume_max,
                "volume_step": symbol_info.volume_step,
                "margin_initial": symbol_info.margin_initial,
                "currency_base": symbol_info.currency_base,
                "currency_profit": symbol_info.currency_profit,
                "currency_margin": symbol_info.currency_margin,
                "last_update": datetime.fromtimestamp(tick.time)
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return None
    
    async def sync_trades_to_database(self, user_id: int, db_session=None):
        """Sync MT5 trades to database"""
        if not await self._ensure_user_connection():
            logger.warning(f"User {user_id}: MT5 not connected correctly, cannot sync trades")
            return
        
        # Import session from models
        if not db_session:
            from models import SessionLocal
            db = SessionLocal()
        else:
            db = db_session
        try:
            # Import models from separate file
            from models import Trade
            
            # Get all trades from MT5
            open_positions = self.get_open_positions()
            historical_trades = self.get_trade_history(days=30)
            all_trades = open_positions + historical_trades
            
            # Get current tickets from MT5
            mt5_tickets = {str(trade.ticket) for trade in all_trades}
            
            # Get all database trades for this user
            db_trades = db.query(Trade).filter(Trade.user_id == user_id).all()
            
            new_trades = []
            updated_trades = []
            removed_trades = []
            
            for mt5_trade in all_trades:
                # Check if trade already exists in database
                existing_trade = db.query(Trade).filter(
                    Trade.ticket == str(mt5_trade.ticket),
                    Trade.user_id == user_id
                ).first()
                
                if not existing_trade:
                    # Create new trade record
                    db_trade = Trade(
                        user_id=user_id,
                        ticket=str(mt5_trade.ticket),
                        symbol=mt5_trade.symbol,
                        trade_type=mt5_trade.trade_type,
                        volume=mt5_trade.volume,
                        open_price=mt5_trade.open_price,
                        close_price=mt5_trade.close_price if not mt5_trade.is_open else None,
                        open_time=mt5_trade.open_time,
                        close_time=mt5_trade.close_time if not mt5_trade.is_open else None,
                        profit=mt5_trade.profit,
                        is_open=mt5_trade.is_open
                    )
                    db.add(db_trade)
                    new_trades.append(db_trade)
                else:
                    # Check if trade has changed
                    has_changed = False
                    old_profit = existing_trade.profit
                    old_is_open = existing_trade.is_open
                    
                    if mt5_trade.is_open:
                        # Update open position data
                        if existing_trade.close_price != mt5_trade.close_price or existing_trade.profit != mt5_trade.profit:
                            existing_trade.close_price = mt5_trade.close_price
                            existing_trade.profit = mt5_trade.profit
                            has_changed = True
                    else:
                        # Trade was closed
                        if existing_trade.is_open or existing_trade.profit != mt5_trade.profit:
                            existing_trade.close_price = mt5_trade.close_price
                            existing_trade.close_time = mt5_trade.close_time
                            existing_trade.profit = mt5_trade.profit
                            existing_trade.is_open = False
                            has_changed = True
                    
                    if has_changed:
                        updated_trades.append((existing_trade, old_profit, old_is_open))
            
            # Handle trades that no longer exist in MT5 (cleanup old/duplicate trades)
            for db_trade in db_trades:
                if db_trade.ticket not in mt5_tickets:
                    # This trade is in database but not in MT5 anymore
                    if db_trade.is_open:
                        # If it was marked as open but doesn't exist in MT5, mark as closed
                        logger.info(f"Closing orphaned trade {db_trade.ticket} - not found in MT5")
                        old_profit = db_trade.profit
                        db_trade.is_open = False
                        db_trade.close_time = datetime.now()
                        removed_trades.append((db_trade, old_profit, True))
            
            db.commit()
            logger.info(f"Synced {len(all_trades)} trades to database for user {user_id} (New: {len(new_trades)}, Updated: {len(updated_trades)}, Cleaned: {len(removed_trades)})")
            
            # Send WebSocket notifications for individual trade updates
            try:
                from websocket_manager import manager
                import asyncio
                
                # Send notifications for new trades
                for trade in new_trades:
                    trade_data = {
                        "type": "trade_new",
                        "data": {
                            "id": trade.id,
                            "ticket": trade.ticket,
                            "symbol": trade.symbol,
                            "trade_type": trade.trade_type,
                            "volume": trade.volume,
                            "open_price": trade.open_price,
                            "close_price": trade.close_price,
                            "open_time": trade.open_time.isoformat() if trade.open_time else None,
                            "close_time": trade.close_time.isoformat() if trade.close_time else None,
                            "profit": trade.profit,
                            "is_open": trade.is_open
                        }
                    }
                    asyncio.create_task(manager.send_user_message(trade_data, user_id))
                
                # Send notifications for updated trades
                for trade, old_profit, old_is_open in updated_trades:
                    # Determine update type
                    if old_is_open and not trade.is_open:
                        update_type = "trade_closed"
                        message = f"{trade.symbol} trade closed: {'+' if trade.profit >= 0 else ''}${trade.profit:.2f}"
                    else:
                        update_type = "trade_updated"
                        profit_change = trade.profit - old_profit
                        message = f"{trade.symbol} P&L update: {'+' if profit_change >= 0 else ''}${profit_change:.2f}"
                    
                    trade_data = {
                        "type": update_type,
                        "data": {
                            "id": trade.id,
                            "ticket": trade.ticket,
                            "symbol": trade.symbol,
                            "trade_type": trade.trade_type,
                            "volume": trade.volume,
                            "open_price": trade.open_price,
                            "close_price": trade.close_price,
                            "open_time": trade.open_time.isoformat() if trade.open_time else None,
                            "close_time": trade.close_time.isoformat() if trade.close_time else None,
                            "profit": trade.profit,
                            "is_open": trade.is_open,
                            "old_profit": old_profit,
                            "old_is_open": old_is_open,
                            "message": message
                        }
                    }
                    asyncio.create_task(manager.send_user_message(trade_data, user_id))
                
                # Send notifications for cleaned up trades
                for trade, old_profit, old_is_open in removed_trades:
                    trade_data = {
                        "type": "trade_closed",
                        "data": {
                            "id": trade.id,
                            "ticket": trade.ticket,
                            "symbol": trade.symbol,
                            "trade_type": trade.trade_type,
                            "volume": trade.volume,
                            "open_price": trade.open_price,
                            "close_price": trade.close_price,
                            "open_time": trade.open_time.isoformat() if trade.open_time else None,
                            "close_time": trade.close_time.isoformat() if trade.close_time else None,
                            "profit": trade.profit,
                            "is_open": False,
                            "old_profit": old_profit,
                            "old_is_open": old_is_open,
                            "message": f"{trade.symbol} trade cleaned up - no longer in MT5"
                        }
                    }
                    asyncio.create_task(manager.send_user_message(trade_data, user_id))
                
                # Send overall sync notification if there were changes
                if new_trades or updated_trades or removed_trades:
                    sync_data = {
                        "type": "trades_synced",
                        "data": {
                            "new_trades": len(new_trades),
                            "updated_trades": len(updated_trades),
                            "removed_trades": len(removed_trades),
                            "total_trades": len(all_trades),
                            "message": f"Updated: {len(new_trades)} new, {len(updated_trades)} changed, {len(removed_trades)} cleaned"
                        }
                    }
                    asyncio.create_task(manager.send_user_message(sync_data, user_id))
                    
            except Exception as e:
                logger.error(f"Error sending WebSocket notifications: {e}")
            
        except Exception as e:
            logger.error(f"Error syncing trades to database: {e}")
            db.rollback()
        finally:
            if not db_session:  # Only close if we created the session
                db.close()
    
    async def monitor_account(self, user_id: int, callback=None):
        """Monitor account for real-time updates"""
        if not await self._ensure_user_connection():
            logger.warning(f"User {user_id}: Cannot start monitoring, MT5 not connected correctly")
            return
        
        logger.info(f"Starting account monitoring for user {user_id}")
        
        # Update connection status in database
        await self._update_connection_status(user_id, True)
        
        while self.connected:
            try:
                # Ensure we're still connected to the correct user account
                if not await self._ensure_user_connection():
                    logger.error(f"User {user_id}: Lost connection to correct MT5 account, stopping monitoring")
                    break
                
                # Update account info
                current_account_info = await self._get_account_info()
                
                # Sync trades to database
                await self.sync_trades_to_database(user_id)
                
                # Send WebSocket account update
                try:
                    from websocket_manager import manager
                    if current_account_info:
                        account_data = {
                            "type": "account_update",
                            "data": {
                                "balance": current_account_info.balance,
                                "equity": current_account_info.equity,
                                "margin": current_account_info.margin,
                                "free_margin": current_account_info.free_margin,
                                "margin_level": current_account_info.margin_level,
                                "currency": current_account_info.currency,
                                "timestamp": datetime.now().isoformat()
                            }
                        }
                        await manager.send_user_message(account_data, user_id)
                        
                        # Send margin level warning if needed
                        if current_account_info.margin_level <= 150:
                            if current_account_info.margin_level <= 50:
                                severity = "critical"
                            elif current_account_info.margin_level <= 100:
                                severity = "high"
                            else:
                                severity = "warning"
                                
                            margin_warning = {
                                "type": "margin_warning",
                                "data": {
                                    "margin_level": current_account_info.margin_level,
                                    "severity": severity,
                                    "message": f"Margin Level: {current_account_info.margin_level:.1f}%",
                                    "timestamp": datetime.now().isoformat()
                                }
                            }
                            await manager.send_user_message(margin_warning, user_id)
                            
                except Exception as e:
                    logger.error(f"Error sending account WebSocket update: {e}")
                
                # Call callback with updates if provided
                if callback:
                    await callback({
                        "type": "account_update",
                        "user_id": user_id,
                        "account_info": current_account_info.__dict__ if current_account_info else None,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Wait before next update
                await asyncio.sleep(1)  # Update every 1 second for real-time response
                
            except Exception as e:
                logger.error(f"Error in account monitoring: {e}")
                await asyncio.sleep(10)  # Wait longer on error
        
        # Update connection status when monitoring stops
        await self._update_connection_status(user_id, False)
    
    async def _update_connection_status(self, user_id: int, is_connected: bool):
        """Update connection status in database"""
        try:
            from models import SessionLocal, MT5Connection
            db = SessionLocal()
            
            connection = db.query(MT5Connection).filter(MT5Connection.user_id == user_id).first()
            if connection:
                connection.is_connected = is_connected
                connection.last_sync = datetime.utcnow()
                db.commit()
                logger.info(f"Updated MT5 connection status for user {user_id}: {'connected' if is_connected else 'disconnected'}")
            
            db.close()
        except Exception as e:
            logger.error(f"Error updating connection status: {e}")

# Per-user MT5 bridge instances
user_mt5_bridges = {}  # user_id -> MT5Bridge instance

def get_user_mt5_bridge(user_id: int) -> MT5Bridge:
    """Get or create MT5Bridge instance for a specific user"""
    if user_id not in user_mt5_bridges:
        user_mt5_bridges[user_id] = MT5Bridge(user_id=user_id)
        logger.info(f"Created new MT5Bridge instance for user {user_id}")
    return user_mt5_bridges[user_id]

async def start_mt5_monitoring(user_id: int, login: int = None, password: str = None, server: str = None):
    """Start MT5 monitoring for a user"""
    user_bridge = get_user_mt5_bridge(user_id)
    if await user_bridge.connect(login, password, server):
        await user_bridge.monitor_account(user_id)
    else:
        logger.error(f"Failed to start MT5 monitoring for user {user_id}")

def stop_mt5_monitoring(user_id: int = None):
    """Stop MT5 monitoring for a specific user or all users"""
    if user_id:
        if user_id in user_mt5_bridges:
            user_mt5_bridges[user_id].disconnect()
            del user_mt5_bridges[user_id]
            logger.info(f"Stopped MT5 monitoring for user {user_id}")
    else:
        # Stop all
        for bridge in user_mt5_bridges.values():
            bridge.disconnect()
        user_mt5_bridges.clear()
        logger.info("Stopped MT5 monitoring for all users") 