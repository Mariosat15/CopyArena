import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import json
from typing import List, Dict, Optional, Any
import logging
from dataclasses import dataclass
from sqlalchemy.orm import Session

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
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.active_trades = {}
        self.last_update = None
        
    async def connect(self, login: int = None, password: str = None, server: str = None) -> bool:
        """Connect to MT5 terminal"""
        try:
            # Initialize MT5 connection
            if not mt5.initialize():
                logger.error("Failed to initialize MT5")
                return False
            
            # If credentials provided, login to specific account
            if login and password and server:
                if not mt5.login(login, password=password, server=server):
                    logger.error(f"Failed to login to MT5 account {login}")
                    mt5.shutdown()
                    return False
                logger.info(f"Successfully logged in to MT5 account {login}")
            else:
                # Try to connect to already logged in account
                account_info = mt5.account_info()
                if account_info is None:
                    logger.warning("No account logged in MT5 terminal")
                    # Don't return False here, keep connection for terminal status
                else:
                    logger.info(f"Connected to existing MT5 account {account_info.login}")
            
            self.connected = True
            self.account_info = self._get_account_info()
            logger.info("MT5 Bridge connected successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to MT5: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("MT5 Bridge disconnected")
    
    def _get_account_info(self) -> Optional[MT5AccountInfo]:
        """Get account information"""
        if not self.connected:
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
        if not self.connected:
            logger.warning("MT5 not connected, cannot sync trades")
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
                else:
                    # Update existing trade (for open positions)
                    if mt5_trade.is_open:
                        existing_trade.close_price = mt5_trade.close_price
                        existing_trade.profit = mt5_trade.profit
                    else:
                        existing_trade.close_price = mt5_trade.close_price
                        existing_trade.close_time = mt5_trade.close_time
                        existing_trade.profit = mt5_trade.profit
                        existing_trade.is_open = False
            
            db.commit()
            logger.info(f"Synced {len(all_trades)} trades to database for user {user_id}")
            
            # Send WebSocket notification about trade sync
            try:
                from websocket_manager import manager
                import asyncio
                
                # Send trade sync notification
                sync_data = {
                    "type": "trades_synced",
                    "data": {
                        "trades_count": len(all_trades),
                        "message": f"Synced {len(all_trades)} trades from MT5"
                    }
                }
                
                # Send notification (this will work in background task context)
                asyncio.create_task(manager.send_user_message(sync_data, user_id))
                    
            except Exception as e:
                logger.error(f"Error sending WebSocket notification: {e}")
            
        except Exception as e:
            logger.error(f"Error syncing trades to database: {e}")
            db.rollback()
        finally:
            if not db_session:  # Only close if we created the session
                db.close()
    
    async def monitor_account(self, user_id: int, callback=None):
        """Monitor account for real-time updates"""
        if not self.connected:
            return
        
        logger.info(f"Starting account monitoring for user {user_id}")
        
        # Update connection status in database
        await self._update_connection_status(user_id, True)
        
        while self.connected:
            try:
                # Update account info
                current_account_info = self._get_account_info()
                
                # Sync trades to database
                await self.sync_trades_to_database(user_id)
                
                # Call callback with updates if provided
                if callback:
                    await callback({
                        "type": "account_update",
                        "user_id": user_id,
                        "account_info": current_account_info.__dict__ if current_account_info else None,
                        "timestamp": datetime.now().isoformat()
                    })
                
                # Wait before next update
                await asyncio.sleep(5)  # Update every 5 seconds
                
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

# Global MT5 bridge instance
mt5_bridge = MT5Bridge()

async def start_mt5_monitoring(user_id: int, login: int = None, password: str = None, server: str = None):
    """Start MT5 monitoring for a user"""
    if await mt5_bridge.connect(login, password, server):
        await mt5_bridge.monitor_account(user_id)
    else:
        logger.error("Failed to start MT5 monitoring")

def stop_mt5_monitoring():
    """Stop MT5 monitoring"""
    mt5_bridge.disconnect() 