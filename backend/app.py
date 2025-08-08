"""
CopyArena Backend API

This backend supports both:
1. Local development with real MT5 connections (Windows)
2. Cloud deployment with mock MT5 for demo purposes (Linux/Render)

In cloud mode, MT5 functionality is simulated to allow the app to run
on Linux servers where MetaTrader5 library is not available.
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import asyncio
import logging
from typing import List, Dict, Optional
from websocket_manager import manager, start_ping_task
from models import User, Trade, Follow, MT5Connection, Badge, UserBadge, SessionLocal, get_db
from sqlalchemy.orm import Session
import os
from contextlib import asynccontextmanager
import uuid

app = FastAPI(title="CopyArena API", version="1.0.0")

logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add session management imports
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import asyncio
import logging
import os
from contextlib import asynccontextmanager
import uuid
from typing import Optional

# Add session storage
user_sessions = {}  # session_id -> user_id mapping

def get_or_create_session_user(session_id: str, db: Session) -> User:
    """Get or create a user for this session"""
    if session_id in user_sessions:
        user_id = user_sessions[session_id]
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    
    # Create a new user for this session with timestamp to ensure uniqueness
    import time
    timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
    new_user = User(
        email=f"user_{session_id[:8]}_{timestamp}@copyarena.com",
        username=f"Trader_{session_id[:8]}_{timestamp}",
        hashed_password=hash_password("temp_password"),
        subscription_plan="free",
        credits=0,
        xp_points=0,
        level=1,
        is_online=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Store the session mapping
    user_sessions[session_id] = new_user.id
    
    # DO NOT start MT5 monitoring automatically - users must connect their own accounts first
    logger.info(f"Created new user {new_user.id} (session: {session_id[:8]}) - awaiting MT5 credentials")
    
    return new_user

def get_session_id_from_request(request: Request) -> str:
    """Get or create session ID from request"""
    # Try to get session from cookies
    session_id = request.cookies.get("copyarena_session")
    if not session_id:
        # Create new session
        session_id = str(uuid.uuid4())
    return session_id

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user based on session"""
    session_id = get_session_id_from_request(request)
    return get_or_create_session_user(session_id, db)

# Session management endpoint
@app.post("/api/auth/session")
async def create_session(response: Response, request: Request, db: Session = Depends(get_db)):
    """Create a new user session"""
    session_id = get_session_id_from_request(request)
    user = get_or_create_session_user(session_id, db)
    
    # Set session cookie
    response.set_cookie(
        key="copyarena_session",
        value=session_id,
        max_age=30 * 24 * 60 * 60,  # 30 days
        httponly=True,
        samesite="lax"
    )
    
    return {
        "session_id": session_id[:8],  # Shortened for display
        "user_id": user.id,
        "username": user.username,
        "message": "Session created successfully"
    }

# Pydantic models
class UserCreate(BaseModel):
    email: str
    username: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class FollowRequest(BaseModel):
    trader_id: int
    auto_copy: bool = False
    max_trade_size: float = 0.01
    risk_level: float = 1.0

class MT5ConnectionRequest(BaseModel):
    login: int
    password: str
    server: str

class MT5TradeData(BaseModel):
    ticket: str
    symbol: str
    trade_type: str
    volume: float
    open_price: float
    close_price: Optional[float] = None
    profit: float
    is_open: bool

# Helper functions

def hash_password(password: str) -> str:
    return f"hashed_{password}"  # Simplified for demo

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hashed_password == f"hashed_{plain_password}"

# Removed: ensure_user_exists - now using session-based user creation

# API Routes
@app.get("/")
async def root():
    return {"message": "CopyArena API is running!", "status": "healthy"}

@app.post("/api/auth/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Create new user
    hashed_password = hash_password(user_data.password)
    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "token": f"token_{user.id}",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "subscription_plan": user.subscription_plan,
            "credits": user.credits,
            "xp_points": user.xp_points,
            "level": user.level
        }
    }

@app.post("/api/auth/login")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "token": f"token_{user.id}",
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "subscription_plan": user.subscription_plan,
            "credits": user.credits,
            "xp_points": user.xp_points,
            "level": user.level
        }
    }

@app.get("/api/user/profile")
async def get_profile(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # User is already provided by dependency injection
    
    # Get trading stats
    trades = db.query(Trade).filter(Trade.user_id == user.id).all()
    total_trades = len(trades)
    profitable_trades = len([t for t in trades if t.profit > 0])
    win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
    total_profit = sum(t.profit for t in trades)
    
    # Get followers count
    followers_count = db.query(Follow).filter(Follow.trader_id == user.id).count()
    
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "subscription_plan": user.subscription_plan,
        "credits": user.credits,
        "xp_points": user.xp_points,
        "level": user.level,
        "avatar_url": user.avatar_url,
        "is_online": user.is_online,
        "badges": [],
        "stats": {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "total_profit": round(total_profit, 2),
            "followers_count": followers_count
        }
    }

@app.get("/api/marketplace/traders")
async def get_traders(db: Session = Depends(get_db), skip: int = 0, limit: int = 20):
    traders = db.query(User).offset(skip).limit(limit).all()
    
    result = []
    for trader in traders:
        # Get trading stats
        trades = db.query(Trade).filter(Trade.user_id == trader.id).all()
        total_trades = len(trades)
        profitable_trades = len([t for t in trades if t.profit > 0])
        win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
        total_profit = sum(t.profit for t in trades)
        
        # Get followers count
        followers_count = db.query(Follow).filter(Follow.trader_id == trader.id).count()
        
        result.append({
            "id": trader.id,
            "username": trader.username,
            "avatar_url": trader.avatar_url,
            "xp_points": trader.xp_points,
            "level": trader.level,
            "is_online": trader.is_online,
            "stats": {
                "total_trades": total_trades,
                "win_rate": round(win_rate, 2),
                "total_profit": round(total_profit, 2),
                "followers_count": followers_count
            }
        })
    
    return result

@app.get("/api/leaderboard")
async def get_leaderboard(db: Session = Depends(get_db), sort_by: str = "xp_points"):
    users = db.query(User).all()
    
    result = []
    for user in users:
        trades = db.query(Trade).filter(Trade.user_id == user.id).all()
        total_profit = sum(t.profit for t in trades)
        followers_count = db.query(Follow).filter(Follow.trader_id == user.id).count()
        
        result.append({
            "id": user.id,
            "username": user.username,
            "avatar_url": user.avatar_url,
            "xp_points": user.xp_points,
            "level": user.level,
            "is_online": user.is_online,
            "total_profit": round(total_profit, 2),
            "followers_count": followers_count
        })
    
    # Sort by requested field
    if sort_by == "total_profit":
        result.sort(key=lambda x: x["total_profit"], reverse=True)
    elif sort_by == "followers_count":
        result.sort(key=lambda x: x["followers_count"], reverse=True)
    else:
        result.sort(key=lambda x: x["xp_points"], reverse=True)
    
    return result[:50]

@app.get("/api/trades")
async def get_trades(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Get trades for current user (user provided by dependency injection)
    
    trades = db.query(Trade).filter(Trade.user_id == user.id).order_by(Trade.open_time.desc()).all()
    
    result = []
    for trade in trades:
        result.append({
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
        })
    
    return result

@app.post("/api/follow")
async def follow_trader(follow_request: FollowRequest, db: Session = Depends(get_db)):
    # Use current user as follower
    user = db.query(User).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if already following
    existing_follow = db.query(Follow).filter(
        Follow.follower_id == user.id,
        Follow.trader_id == follow_request.trader_id
    ).first()
    
    if existing_follow:
        raise HTTPException(status_code=400, detail="Already following this trader")
    
    follow = Follow(
        follower_id=user.id,
        trader_id=follow_request.trader_id,
        auto_copy=follow_request.auto_copy,
        max_trade_size=follow_request.max_trade_size,
        risk_level=follow_request.risk_level
    )
    
    db.add(follow)
    db.commit()
    
    return {"message": "Successfully following trader"}

# MT5 Connection Endpoints
@app.post("/api/mt5/connect")
async def connect_mt5(connection_data: MT5ConnectionRequest, background_tasks: BackgroundTasks, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Connect user's MT5 account"""
    # User is already provided by dependency injection
    
    # Check if connection already exists
    existing_connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    
    if existing_connection:
        # Update existing connection
        existing_connection.login = connection_data.login
        existing_connection.server = connection_data.server
        existing_connection.password_hash = hash_password(connection_data.password)  # In production, use proper encryption
        existing_connection.updated_at = datetime.utcnow()
    else:
        # Create new connection
        import uuid
        connection_token = str(uuid.uuid4())
        
        mt5_connection = MT5Connection(
            user_id=user.id,
            login=connection_data.login,
            server=connection_data.server,
            password_hash=hash_password(connection_data.password),  # In production, use proper encryption
            connection_token=connection_token
        )
        db.add(mt5_connection)
    
    db.commit()
    
    # Start MT5 monitoring in background
    try:
        from mt5_bridge import start_mt5_monitoring
        background_tasks.add_task(
            start_mt5_monitoring,
            user.id,
            connection_data.login,
            connection_data.password,
            connection_data.server
        )
    except ImportError:
        logger.warning("MT5 bridge not available")
    
    return {"message": "MT5 connection established", "status": "connecting"}

@app.get("/api/mt5/status")
async def get_mt5_status(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get MT5 connection status"""
    # User is already provided by dependency injection
    
    connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    if not connection:
        return {"connected": False, "message": "No MT5 connection configured"}
    
    return {
        "connected": connection.is_connected,
        "login": connection.login,
        "server": connection.server,
        "last_sync": connection.last_sync.isoformat() if connection.last_sync else None
    }

@app.post("/api/mt5/sync")
async def sync_mt5_trades(background_tasks: BackgroundTasks, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Manually sync MT5 trades"""
    # User is already provided by dependency injection
    
    connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    if not connection:
        raise HTTPException(status_code=400, detail="No MT5 connection configured")
    
    # Trigger sync in background
    try:
        from mt5_bridge import get_user_mt5_bridge
        # Get user-specific MT5 bridge
        user_bridge = get_user_mt5_bridge(user.id)
        # First ensure MT5 is connected
        if not user_bridge.connected:
            success = await user_bridge.connect()
            if not success:
                raise HTTPException(status_code=500, detail="Failed to connect to MT5")
        
        background_tasks.add_task(user_bridge.sync_trades_to_database, user.id, db)
    except ImportError:
        logger.warning("MT5 bridge not available")
    
    return {"message": "Trade sync initiated"}

@app.post("/api/mt5/cleanup")
async def cleanup_mt5_trades(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Clean up duplicate or orphaned trades"""
    # User is already provided by dependency injection
    
    try:
        from mt5_bridge import get_user_mt5_bridge
        
        # Get user-specific MT5 bridge
        user_bridge = get_user_mt5_bridge(user.id)
        
        # Ensure MT5 is connected
        if not user_bridge.connected:
            success = await user_bridge.connect()
            if not success:
                raise HTTPException(status_code=500, detail="Failed to connect to MT5")
        
        # Get current MT5 trades
        open_positions = user_bridge.get_open_positions()
        historical_trades = user_bridge.get_trade_history(days=30)
        all_mt5_trades = open_positions + historical_trades
        mt5_tickets = {str(trade.ticket) for trade in all_mt5_trades}
        
        # Get database trades
        db_trades = db.query(Trade).filter(Trade.user_id == user.id).all()
        
        # Find and clean up orphaned trades
        cleaned_count = 0
        for db_trade in db_trades:
            if db_trade.ticket not in mt5_tickets and db_trade.is_open:
                logger.info(f"Cleaning up orphaned trade {db_trade.ticket}")
                db_trade.is_open = False
                db_trade.close_time = datetime.utcnow()
                cleaned_count += 1
        
        db.commit()
        
        return {
            "message": f"Cleanup completed: {cleaned_count} trades cleaned",
            "cleaned_trades": cleaned_count,
            "total_mt5_trades": len(all_mt5_trades),
            "total_db_trades": len(db_trades)
        }
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {e}")

@app.get("/api/mt5/debug")
async def debug_mt5_connection(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Debug MT5 connection and get detailed status"""
    try:
        from mt5_bridge import get_user_mt5_bridge
        user_bridge = get_user_mt5_bridge(user.id)
        import MetaTrader5 as mt5
        
        # Check if MT5 is initialized
        if not mt5.initialize():
            return {
                "error": "MT5 not initialized",
                "last_error": mt5.last_error(),
                "terminal_info": None,
                "account_info": None
            }
        
        # Get terminal info
        terminal_info = mt5.terminal_info()
        account_info = mt5.account_info()
        
        result = {
            "mt5_initialized": True,
            "bridge_connected": user_bridge.connected,
            "terminal_info": {
                "name": terminal_info.name if terminal_info else None,
                "path": terminal_info.path if terminal_info else None,
                "data_path": terminal_info.data_path if terminal_info else None,
                "connected": terminal_info.connected if terminal_info else None,
            } if terminal_info else None,
            "account_info": {
                "login": account_info.login if account_info else None,
                "server": account_info.server if account_info else None,
                "balance": account_info.balance if account_info else None,
                "equity": account_info.equity if account_info else None,
                "margin": account_info.margin if account_info else None,
                "currency": account_info.currency if account_info else None,
            } if account_info else None,
            "positions_count": len(mt5.positions_get() or []),
            "last_error": mt5.last_error()
        }
        
        return result
        
    except ImportError as e:
        return {"error": f"MT5 bridge import error: {e}"}
    except Exception as e:
        return {"error": f"Debug error: {e}"}

@app.get("/api/mt5/test-trades")
async def test_mt5_trades():
    """Test endpoint to directly fetch trades from MT5"""
    try:
        from mt5_bridge import mt5_bridge
        import MetaTrader5 as mt5
        
        # Ensure MT5 is connected
        if not mt5_bridge.connected:
            logger.info("MT5 not connected, attempting to connect...")
            success = await mt5_bridge.connect()
            if not success:
                return {"error": "Failed to connect to MT5", "trades": [], "connection_attempted": True}
            logger.info("MT5 connected successfully")
        
        # Get positions directly
        positions = mt5.positions_get()
        deals = mt5.history_deals_get(datetime.now() - timedelta(days=7), datetime.now())
        
        result = {
            "positions": [],
            "recent_deals": [],
            "positions_count": len(positions) if positions else 0,
            "deals_count": len(deals) if deals else 0,
            "last_error": mt5.last_error()
        }
        
        # Process positions
        if positions:
            for pos in positions:
                result["positions"].append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": pos.volume,
                    "price_open": pos.price_open,
                    "price_current": pos.price_current,
                    "profit": pos.profit,
                    "swap": getattr(pos, 'swap', 0.0),
                    "commission": getattr(pos, 'commission', 0.0),
                    "time": datetime.fromtimestamp(pos.time).isoformat(),
                    "comment": getattr(pos, 'comment', '')
                })
        
        # Process recent deals
        if deals:
            for deal in deals[-10:]:  # Last 10 deals
                result["recent_deals"].append({
                    "ticket": deal.ticket,
                    "symbol": deal.symbol,
                    "type": "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL",
                    "volume": deal.volume,
                    "price": deal.price,
                    "profit": deal.profit,
                    "swap": getattr(deal, 'swap', 0.0),
                    "commission": getattr(deal, 'commission', 0.0),
                    "time": datetime.fromtimestamp(deal.time).isoformat(),
                    "comment": getattr(deal, 'comment', ''),
                    "entry": deal.entry
                })
        
        return result
        
    except ImportError:
        return {"error": "MT5 bridge not available"}
    except Exception as e:
        return {"error": f"Test error: {e}"}

# WebSocket Endpoints
@app.websocket("/ws/user/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket connection for real-time updates"""
    await manager.connect(websocket, user_id, "user")
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await manager.send_personal_message(
                    json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}),
                    websocket
                )
            elif message.get("type") == "subscribe":
                # Handle subscription to specific data feeds
                await manager.send_personal_message(
                    json.dumps({"type": "subscribed", "feed": message.get("feed")}),
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.websocket("/ws/mt5/{connection_token}")
async def mt5_websocket_endpoint(websocket: WebSocket, connection_token: str, db: Session = Depends(get_db)):
    """WebSocket connection for MT5 bridge updates"""
    # Verify connection token
    connection = db.query(MT5Connection).filter(MT5Connection.connection_token == connection_token).first()
    if not connection:
        await websocket.close(code=4001, reason="Invalid connection token")
        return
    
    await manager.connect(websocket, connection.user_id, "mt5")
    
    try:
        while True:
            # Receive trade data from MT5 bridge
            data = await websocket.receive_text()
            trade_data = json.loads(data)
            
            # Process trade update
            if trade_data.get("type") == "trade_update":
                # Send to user's connections
                await manager.send_trade_update(trade_data["data"], connection.user_id)
                
                # Update user online status
                user = db.query(User).filter(User.id == connection.user_id).first()
                if user:
                    user.is_online = True
                    user.last_seen = datetime.utcnow()
                    db.commit()
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # Update user offline status
        user = db.query(User).filter(User.id == connection.user_id).first()
        if user:
            user.is_online = False
            db.commit()
    except Exception as e:
        logging.error(f"MT5 WebSocket error: {e}")
        manager.disconnect(websocket)

# Enhanced data endpoints
@app.get("/api/trades/real-time")
async def get_real_time_trades(db: Session = Depends(get_db)):
    """Get real-time trades from MT5"""
    try:
        from mt5_bridge import mt5_bridge
        
        # Ensure MT5 is connected
        if not mt5_bridge.connected:
            success = await mt5_bridge.connect()
            if not success:
                logger.warning("Could not connect to MT5, falling back to database")
        
        # Get trades directly from MT5 if connected
        if mt5_bridge.connected:
            open_positions = mt5_bridge.get_open_positions()
            trade_history = mt5_bridge.get_trade_history(days=1)  # Last 24 hours
            
            all_trades = []
            
            # Process open positions
            for pos in open_positions:
                all_trades.append({
                    "id": f"open_{pos.ticket}",
                    "ticket": str(pos.ticket),
                    "symbol": pos.symbol,
                    "trade_type": pos.trade_type,
                    "volume": pos.volume,
                    "open_price": pos.open_price,
                    "close_price": pos.close_price,
                    "open_time": pos.open_time.isoformat(),
                    "close_time": None,
                    "profit": pos.profit,
                    "is_open": True,
                    "duration": str(datetime.now() - pos.open_time),
                    "source": "mt5_live"
                })
            
            # Process trade history
            for trade in trade_history:
                all_trades.append({
                    "id": f"history_{trade.ticket}",
                    "ticket": str(trade.ticket),
                    "symbol": trade.symbol,
                    "trade_type": trade.trade_type,
                    "volume": trade.volume,
                    "open_price": trade.open_price,
                    "close_price": trade.close_price,
                    "open_time": trade.open_time.isoformat(),
                    "close_time": trade.close_time.isoformat() if trade.close_time else None,
                    "profit": trade.profit,
                    "is_open": False,
                    "duration": str(trade.close_time - trade.open_time) if trade.close_time else None,
                    "source": "mt5_live"
                })
            
            # Sort by open time (newest first)
            all_trades.sort(key=lambda x: x["open_time"], reverse=True)
            
            logger.info(f"Fetched {len(all_trades)} trades directly from MT5 ({len(open_positions)} open, {len(trade_history)} closed)")
            return all_trades
        
        else:
            logger.warning("MT5 not connected, falling back to database")
    
    except ImportError:
        logger.warning("MT5 bridge not available, using database")
    except Exception as e:
        logger.error(f"Error fetching live trades from MT5: {e}")
    
    # Fallback to database
    user = db.query(User).first()
    if not user:
        return []
    
    # Get recent trades (last 24 hours)
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    trades = db.query(Trade).filter(
        Trade.user_id == user.id,
        Trade.open_time >= cutoff_time
    ).order_by(Trade.open_time.desc()).all()
    
    result = []
    for trade in trades:
        result.append({
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
            "duration": str(datetime.utcnow() - trade.open_time) if trade.open_time and trade.is_open else None,
            "source": "database"
        })
    
    logger.info(f"Fetched {len(result)} trades from database")
    return result

@app.get("/api/analytics/performance")
async def get_performance_analytics(db: Session = Depends(get_db)):
    """Get detailed performance analytics"""
    # Use current user
    user = db.query(User).first()
    if not user:
        return {}
    
    trades = db.query(Trade).filter(Trade.user_id == user.id).all()
    
    if not trades:
        return {"message": "No trades found"}
    
    # Calculate analytics
    total_trades = len(trades)
    profitable_trades = len([t for t in trades if t.profit > 0])
    losing_trades = len([t for t in trades if t.profit < 0])
    total_profit = sum(t.profit for t in trades)
    
    # Calculate win rate
    win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate average profit/loss
    avg_profit = total_profit / total_trades if total_trades > 0 else 0
    avg_win = sum(t.profit for t in trades if t.profit > 0) / profitable_trades if profitable_trades > 0 else 0
    avg_loss = sum(t.profit for t in trades if t.profit < 0) / losing_trades if losing_trades > 0 else 0
    
    # Calculate risk metrics
    profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    
    # Daily profit data for chart
    daily_profits = {}
    for trade in trades:
        if trade.close_time:
            date_key = trade.close_time.date().isoformat()
            daily_profits[date_key] = daily_profits.get(date_key, 0) + trade.profit
    
    return {
        "total_trades": total_trades,
        "profitable_trades": profitable_trades,
        "losing_trades": losing_trades,
        "win_rate": round(win_rate, 2),
        "total_profit": round(total_profit, 2),
        "average_profit": round(avg_profit, 2),
        "average_win": round(avg_win, 2),
        "average_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "daily_profits": daily_profits
    }

@app.get("/api/account/stats")
async def get_account_stats(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get comprehensive account statistics including MT5 account info and trade metrics"""
    # User is already provided by dependency injection
    
    try:
        from mt5_bridge import get_user_mt5_bridge
        
        # Get user-specific MT5 bridge
        user_bridge = get_user_mt5_bridge(user.id)
        
        # Ensure MT5 is connected
        if not user_bridge.connected:
            success = await user_bridge.connect()
            if not success:
                raise HTTPException(status_code=500, detail="Failed to connect to MT5")

        # Get current account info from MT5
        account_info = await user_bridge._get_account_info()
        logger.info(f"Account info retrieved: {account_info.__dict__ if account_info else 'None'}")

        # Get all trades for calculations
        trades = db.query(Trade).filter(Trade.user_id == user.id).all()

        # Calculate trade statistics
        open_trades = [t for t in trades if t.is_open]
        closed_trades = [t for t in trades if not t.is_open]

        # Historical profit (closed trades only)
        historical_profit = sum(t.profit for t in closed_trades)

        # Floating profit (open trades only)
        floating_profit = sum(t.profit for t in open_trades)

        # Total realized + unrealized
        total_profit = historical_profit + floating_profit

        # Win rate calculation (closed trades only)
        profitable_closed = len([t for t in closed_trades if t.profit > 0])
        win_rate = (profitable_closed / len(closed_trades)) * 100 if closed_trades else 0

        # Calculate margin level percentage
        margin_level_percent = account_info.margin_level if account_info and account_info.margin_level else 0

        return {
            # Account Info from MT5
            "account": {
                "login": account_info.login if account_info else None,
                "server": account_info.server if account_info else None,
                "company": account_info.company if account_info else None,
                "currency": account_info.currency if account_info else "USD",
                "balance": round(account_info.balance, 2) if account_info else 0,
                "equity": round(account_info.equity, 2) if account_info else 0,
                "margin": round(account_info.margin, 2) if account_info else 0,
                "free_margin": round(account_info.free_margin, 2) if account_info else 0,
                "margin_level": round(margin_level_percent, 2) if margin_level_percent else 0,
            },

            # Trade Statistics
            "trading": {
                "total_trades": len(trades),
                "open_trades": len(open_trades),
                "closed_trades": len(closed_trades),
                "historical_profit": round(historical_profit, 2),
                "floating_profit": round(floating_profit, 2),
                "total_profit": round(total_profit, 2),
                "win_rate": round(win_rate, 2),
            },

            # Real-time status
            "status": {
                "mt5_connected": user_bridge.connected,
                "last_update": datetime.now().isoformat(),
            }
        }

    except Exception as e:
        logger.error(f"Error getting account stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get account stats: {e}")

async def auto_sync_mt5_trades():
    """Background task to automatically sync MT5 trades"""
    while True:
        try:
            from models import SessionLocal, User, MT5Connection
            from mt5_bridge import get_user_mt5_bridge
            
            # Wait a bit before starting
            await asyncio.sleep(10)
            
            db = SessionLocal()
            try:
                # Get all users with MT5 connections
                connections = db.query(MT5Connection).filter(MT5Connection.is_connected == True).all()
                
                for connection in connections:
                    try:
                        # Get user-specific MT5 bridge
                        user_bridge = get_user_mt5_bridge(connection.user_id)
                        
                        # Ensure MT5 is connected for this user (only if they have credentials)
                        if not user_bridge.connected:
                            logger.info(f"Auto-sync: Attempting to connect to MT5 for user {connection.user_id}...")
                            # Pass the stored credentials from the connection
                            success = await user_bridge.connect(
                                connection.login, 
                                connection.password, 
                                connection.server
                            )
                            if not success:
                                logger.warning(f"Auto-sync: Failed to connect to MT5 for user {connection.user_id}")
                                continue
                        
                        # Sync trades for this user
                        logger.info(f"Auto-sync: Syncing trades for user {connection.user_id}")
                        await user_bridge.sync_trades_to_database(connection.user_id, db)
                        
                    except Exception as e:
                        logger.error(f"Auto-sync error for user {connection.user_id}: {e}")
                
            finally:
                db.close()
            
            # Wait 5 seconds before next sync  
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Auto-sync background task error: {e}")
            await asyncio.sleep(60)  # Wait longer on error

@app.on_event("startup")
async def startup_event():
    # Start background tasks (MT5 monitoring now starts per user session)
    asyncio.create_task(start_ping_task())
    asyncio.create_task(auto_sync_mt5_trades())
    logger.info("CopyArena API started - Multi-user session system active")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 