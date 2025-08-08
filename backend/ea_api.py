"""
Expert Advisor API Endpoints
Handles connections from MQL5 Expert Advisors
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import logging
from datetime import datetime
import json

from models import User, Trade, MT5Connection, SessionLocal, get_db
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mt5", tags=["MT5 Expert Advisor"])

# Data models for EA communication
class AccountInfo(BaseModel):
    login: int
    balance: float
    equity: float
    margin: float
    free_margin: float
    margin_level: float
    profit: float
    currency: str

class Position(BaseModel):
    ticket: int
    symbol: str
    type: int  # 0=BUY, 1=SELL
    volume: float
    price_open: float
    price_current: float
    sl: float
    tp: float
    profit: float
    swap: float
    comment: str
    time_open: int

class EARegistration(BaseModel):
    login: int
    server: str
    company: str
    name: str
    currency: str
    leverage: int
    ea_version: str
    mt5_build: int
    timestamp: int

class EASyncData(BaseModel):
    account: AccountInfo
    positions: List[Position]
    timestamp: int
    sync_count: int

# In-memory storage for active EA connections
active_ea_connections: Dict[str, Dict] = {}

def get_user_from_api_key(api_key: str, db: Session) -> User:
    """Get user from API key"""
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    user = db.query(User).filter(User.api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user

@router.get("/ping")
async def ping(request: Request, db: Session = Depends(get_db)):
    """Test connection from EA"""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        user = get_user_from_api_key(api_key, db)
        return {"status": "connected", "user_id": user.id, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"Ping failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

@router.post("/register")
async def register_ea(
    registration: EARegistration, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """Register EA and MT5 account info"""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        user = get_user_from_api_key(api_key, db)
        
        # Update or create MT5 connection record
        mt5_connection = db.query(MT5Connection).filter(
            MT5Connection.user_id == user.id
        ).first()
        
        if not mt5_connection:
            mt5_connection = MT5Connection(
                user_id=user.id,
                login=registration.login,
                server=registration.server,
                is_connected=True
            )
            db.add(mt5_connection)
        else:
            mt5_connection.login = registration.login
            mt5_connection.server = registration.server
            mt5_connection.is_connected = True
            mt5_connection.last_connection = datetime.now()
        
        # Store connection info
        active_ea_connections[api_key] = {
            "user_id": user.id,
            "login": registration.login,
            "server": registration.server,
            "company": registration.company,
            "name": registration.name,
            "currency": registration.currency,
            "leverage": registration.leverage,
            "ea_version": registration.ea_version,
            "mt5_build": registration.mt5_build,
            "connected_at": datetime.now(),
            "last_sync": None
        }
        
        db.commit()
        
        logger.info(f"EA registered for user {user.id}: {registration.login}@{registration.server}")
        
        return {
            "status": "registered",
            "user_id": user.id,
            "message": f"MT5 account {registration.login} registered successfully"
        }
        
    except Exception as e:
        logger.error(f"EA registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/sync")
async def sync_data(
    sync_data: EASyncData, 
    request: Request, 
    db: Session = Depends(get_db)
):
    """Receive account and position data from EA"""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        user = get_user_from_api_key(api_key, db)
        
        # Update connection info
        if api_key in active_ea_connections:
            active_ea_connections[api_key]["last_sync"] = datetime.now()
        
        # Process account info
        await process_account_info(user.id, sync_data.account, db)
        
        # Process positions
        await process_positions(user.id, sync_data.positions, db)
        
        # Update sync count
        mt5_connection = db.query(MT5Connection).filter(
            MT5Connection.user_id == user.id
        ).first()
        
        if mt5_connection:
            mt5_connection.last_sync = datetime.now()
            db.commit()
        
        logger.info(f"Sync #{sync_data.sync_count} completed for user {user.id}")
        
        # Return any copy trading signals (future feature)
        response = {
            "status": "synced",
            "timestamp": datetime.now().isoformat(),
            "copy_signals": []  # Placeholder for copy trading
        }
        
        return response
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail="Sync failed")

@router.post("/disconnect")
async def disconnect_ea(request: Request, db: Session = Depends(get_db)):
    """Handle EA disconnection"""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    try:
        user = get_user_from_api_key(api_key, db)
        
        # Update connection status
        mt5_connection = db.query(MT5Connection).filter(
            MT5Connection.user_id == user.id
        ).first()
        
        if mt5_connection:
            mt5_connection.is_connected = False
            mt5_connection.last_disconnection = datetime.now()
            db.commit()
        
        # Remove from active connections
        if api_key in active_ea_connections:
            del active_ea_connections[api_key]
        
        logger.info(f"EA disconnected for user {user.id}")
        
        return {"status": "disconnected"}
        
    except Exception as e:
        logger.error(f"Disconnect failed: {e}")
        raise HTTPException(status_code=500, detail="Disconnect failed")

async def process_account_info(user_id: int, account: AccountInfo, db: Session):
    """Process account information from EA"""
    try:
        # Update MT5Connection with account info
        mt5_connection = db.query(MT5Connection).filter(
            MT5Connection.user_id == user_id
        ).first()
        
        if mt5_connection:
            # Store account info as JSON for now
            account_data = {
                "login": account.login,
                "balance": account.balance,
                "equity": account.equity,
                "margin": account.margin,
                "free_margin": account.free_margin,
                "margin_level": account.margin_level,
                "profit": account.profit,
                "currency": account.currency,
                "updated_at": datetime.now().isoformat()
            }
            
            # You might want to create a separate AccountInfo table for this
            # For now, storing in MT5Connection
            mt5_connection.account_info = json.dumps(account_data)
            db.commit()
            
        logger.debug(f"Account info processed for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to process account info: {e}")

async def process_positions(user_id: int, positions: List[Position], db: Session):
    """Process positions from EA"""
    try:
        # Get existing positions for this user
        existing_trades = db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.status == "open"
        ).all()
        
        existing_tickets = {trade.mt5_ticket: trade for trade in existing_trades}
        received_tickets = {pos.ticket for pos in positions}
        
        # Process each position
        for position in positions:
            if position.ticket in existing_tickets:
                # Update existing trade
                trade = existing_tickets[position.ticket]
                trade.current_price = position.price_current
                trade.profit = position.profit
                trade.swap = position.swap
                trade.updated_at = datetime.now()
            else:
                # Create new trade
                trade = Trade(
                    user_id=user_id,
                    mt5_ticket=position.ticket,
                    symbol=position.symbol,
                    trade_type="BUY" if position.type == 0 else "SELL",
                    volume=position.volume,
                    open_price=position.price_open,
                    current_price=position.price_current,
                    stop_loss=position.sl if position.sl > 0 else None,
                    take_profit=position.tp if position.tp > 0 else None,
                    profit=position.profit,
                    swap=position.swap,
                    comment=position.comment,
                    status="open",
                    open_time=datetime.fromtimestamp(position.time_open),
                    created_at=datetime.now()
                )
                db.add(trade)
        
        # Close trades that are no longer in positions
        for ticket, trade in existing_tickets.items():
            if ticket not in received_tickets:
                trade.status = "closed"
                trade.close_time = datetime.now()
                trade.close_price = trade.current_price
        
        db.commit()
        logger.debug(f"Processed {len(positions)} positions for user {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to process positions: {e}")

@router.get("/connections")
async def get_active_connections():
    """Get active EA connections (admin endpoint)"""
    return {
        "active_connections": len(active_ea_connections),
        "connections": [
            {
                "user_id": conn["user_id"],
                "login": conn["login"],
                "server": conn["server"],
                "company": conn["company"],
                "connected_at": conn["connected_at"].isoformat(),
                "last_sync": conn["last_sync"].isoformat() if conn["last_sync"] else None
            }
            for conn in active_ea_connections.values()
        ]
    } 