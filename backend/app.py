from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, desc
from datetime import datetime, timedelta
import asyncio
import logging
import json
import uuid
import os
from pathlib import Path

# Import models and database
from models import Base, User, Trade, MT5Connection, SessionLocal, engine, hash_password
from websocket_manager import ConnectionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="CopyArena API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# WebSocket manager
manager = ConnectionManager()

# Session management
user_sessions = {}
user_api_keys = {}  # Maps API keys to user IDs

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session_id_from_request(request: Request) -> str:
    """Extract session ID from request headers or create new one"""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

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
    
    # Generate unique API key
    temp_api_key = f"ca_temp_{uuid.uuid4().hex[:16]}"
    
    new_user = User(
        email=f"user_{session_id[:8]}_{timestamp}@copyarena.com",
        username=f"Trader_{session_id[:8]}_{timestamp}",
        hashed_password=hash_password("temp_password"),
        api_key=temp_api_key,
        subscription_plan="free",
        credits=0,
        xp_points=0,
        level=1,
        is_online=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Update with proper API key using the actual user ID
    final_api_key = f"ca_{new_user.id}_{uuid.uuid4().hex[:16]}"
    new_user.api_key = final_api_key
    db.commit()
    db.refresh(new_user)
    
    # Store the session mapping
    user_sessions[session_id] = new_user.id
    user_api_keys[final_api_key] = new_user.id
    
    logger.info(f"Created new user {new_user.id} (session: {session_id[:8]}) with API key: {final_api_key[:20]}...")
    
    return new_user

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user from session"""
    session_id = get_session_id_from_request(request)
    return get_or_create_session_user(session_id, db)

def get_user_by_api_key(api_key: str, db: Session) -> User:
    """Get user by API key"""
    if api_key in user_api_keys:
        user_id = user_api_keys[api_key]
        return db.query(User).filter(User.id == user_id).first()
    
    # Fallback: search in database
    user = db.query(User).filter(User.api_key == api_key).first()
    if user:
        user_api_keys[api_key] = user.id
    return user

# === EA DATA ENDPOINTS ===

@app.post("/api/ea/data")
async def receive_ea_data(request: Request, db: Session = Depends(get_db)):
    """Receive data from Expert Advisor"""
    try:
        data = await request.json()
        api_key = data.get("api_key")
        data_type = data.get("type")
        timestamp = data.get("timestamp")
        payload = data.get("data")
        
        if not api_key:
            raise HTTPException(status_code=400, detail="API key required")
        
        # Get user by API key
        user = get_user_by_api_key(api_key, db)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Update user's last seen time
        user.last_seen = datetime.utcnow()
        user.is_online = True
        db.commit()
        
        # Process data based on type
        if data_type == "connection_status":
            await handle_connection_status(user, payload, db)
        elif data_type == "account_update":
            await handle_account_update(user, payload, db)
        elif data_type == "positions_update":
            await handle_positions_update(user, payload, db)
        elif data_type == "orders_update":
            await handle_orders_update(user, payload, db)
        elif data_type == "history_update":
            await handle_history_update(user, payload, db)
        
        # Send real-time update to connected clients
        await manager.send_user_message({
            "type": data_type,
            "data": payload,
            "timestamp": timestamp
        }, user.id)
        
        return {"status": "success", "message": "Data received"}
        
    except Exception as e:
        logger.error(f"Error processing EA data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_connection_status(user: User, data: dict, db: Session):
    """Handle EA connection status"""
    connected = data.get("connected", False)
    account_number = data.get("account_number")
    
    # Update or create MT5Connection record
    connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    if not connection:
        connection = MT5Connection(
            user_id=user.id,
            login=account_number,
            is_connected=connected,
            last_sync=datetime.utcnow()
        )
        db.add(connection)
    else:
        connection.is_connected = connected
        connection.last_sync = datetime.utcnow()
    
    db.commit()
    logger.info(f"User {user.id} EA connection: {'CONNECTED' if connected else 'DISCONNECTED'}")

async def handle_account_update(user: User, data: dict, db: Session):
    """Handle account information update"""
    # Update user's account info (can be stored in User model or separate table)
    # For now, we'll store in MT5Connection
    connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    if connection:
        connection.account_balance = data.get("balance", 0)
        connection.account_equity = data.get("equity", 0)
        connection.account_margin = data.get("margin", 0)
        connection.account_free_margin = data.get("free_margin", 0)
        connection.account_margin_level = data.get("margin_level", 0)
        connection.last_sync = datetime.utcnow()
        db.commit()

async def handle_positions_update(user: User, positions: list, db: Session):
    """Handle positions update from EA"""
    # Get existing open trades for this user
    existing_trades = db.query(Trade).filter(
        Trade.user_id == user.id,
        Trade.status == "open"
    ).all()
    
    existing_tickets = {trade.ticket for trade in existing_trades}
    incoming_tickets = {pos["ticket"] for pos in positions}
    
    # Close trades that are no longer in positions
    for trade in existing_trades:
        if trade.ticket not in incoming_tickets:
            trade.status = "closed"
            trade.close_time = datetime.utcnow()
    
    # Update or create trades
    for pos in positions:
        ticket = pos["ticket"]
        existing_trade = db.query(Trade).filter(
            Trade.user_id == user.id,
            Trade.ticket == ticket
        ).first()
        
        if existing_trade:
            # Update existing trade
            existing_trade.current_price = pos.get("current_price", 0)
            existing_trade.unrealized_profit = pos.get("profit", 0)
            existing_trade.swap = pos.get("swap", 0)
            existing_trade.commission = pos.get("commission", 0)
        else:
            # Create new trade
            new_trade = Trade(
                user_id=user.id,
                ticket=ticket,
                symbol=pos.get("symbol", ""),
                trade_type="buy" if pos.get("type") == 0 else "sell",
                volume=pos.get("volume", 0),
                open_price=pos.get("open_price", 0),
                current_price=pos.get("current_price", 0),
                stop_loss=pos.get("sl", 0),
                take_profit=pos.get("tp", 0),
                unrealized_profit=pos.get("profit", 0),
                swap=pos.get("swap", 0),
                commission=pos.get("commission", 0),
                open_time=datetime.fromtimestamp(pos.get("open_time", 0)),
                comment=pos.get("comment", ""),
                status="open"
            )
            db.add(new_trade)
    
    db.commit()

async def handle_orders_update(user: User, orders: list, db: Session):
    """Handle pending orders update"""
    # Similar logic to positions but for pending orders
    # Can be implemented based on requirements
    pass

async def handle_history_update(user: User, history: list, db: Session):
    """Handle trade history update"""
    for deal in history:
        ticket = deal["ticket"]
        
        # Check if we already have this deal
        existing_trade = db.query(Trade).filter(
            Trade.user_id == user.id,
            Trade.ticket == ticket
        ).first()
        
        if not existing_trade:
            # Create closed trade from history
            new_trade = Trade(
                user_id=user.id,
                ticket=ticket,
                symbol=deal.get("symbol", ""),
                trade_type="buy" if deal.get("type") == 0 else "sell",
                volume=deal.get("volume", 0),
                open_price=deal.get("price", 0),
                current_price=deal.get("price", 0),
                realized_profit=deal.get("profit", 0),
                swap=deal.get("swap", 0),
                commission=deal.get("commission", 0),
                open_time=datetime.fromtimestamp(deal.get("time", 0)),
                close_time=datetime.fromtimestamp(deal.get("time", 0)),
                comment=deal.get("comment", ""),
                status="closed"
            )
            db.add(new_trade)
    
    db.commit()

# === WEB APP ENDPOINTS ===

@app.get("/api/auth/session")
async def get_session(user: User = Depends(get_current_user)):
    """Get current session user info"""
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "api_key": user.api_key,
            "subscription_plan": user.subscription_plan,
            "credits": user.credits,
            "xp_points": user.xp_points,
            "level": user.level,
            "is_online": user.is_online
        }
    }

@app.post("/api/auth/session")
async def create_session(request: Request, db: Session = Depends(get_db)):
    """Create/get session user info"""
    user = get_current_user(request, db)
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "api_key": user.api_key,
            "subscription_plan": user.subscription_plan,
            "credits": user.credits,
            "xp_points": user.xp_points,
            "level": user.level,
            "is_online": user.is_online
        }
    }

@app.post("/api/auth/login")
async def login(request: Request, db: Session = Depends(get_db)):
    """Login endpoint - for session-based system, just return session user"""
    user = get_current_user(request, db)
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "api_key": user.api_key,
            "subscription_plan": user.subscription_plan,
            "credits": user.credits,
            "xp_points": user.xp_points,
            "level": user.level,
            "is_online": user.is_online
        },
        "token": f"session_{user.id}"  # Simple session token
    }

@app.post("/api/auth/register")
async def register(request: Request, db: Session = Depends(get_db)):
    """Register endpoint - for session-based system, just return session user"""
    user = get_current_user(request, db)
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "api_key": user.api_key,
            "subscription_plan": user.subscription_plan,
            "credits": user.credits,
            "xp_points": user.xp_points,
            "level": user.level,
            "is_online": user.is_online
        },
        "token": f"session_{user.id}"  # Simple session token
    }

@app.get("/api/trades")
async def get_trades(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's trades"""
    trades = db.query(Trade).filter(Trade.user_id == user.id).order_by(desc(Trade.open_time)).all()
    return [
        {
            "id": trade.id,
            "ticket": trade.ticket,
            "symbol": trade.symbol,
            "type": trade.trade_type,
            "volume": float(trade.volume),
            "open_price": float(trade.open_price),
            "current_price": float(trade.current_price),
            "stop_loss": float(trade.stop_loss) if trade.stop_loss else None,
            "take_profit": float(trade.take_profit) if trade.take_profit else None,
            "profit": float(trade.unrealized_profit or trade.realized_profit or 0),
            "swap": float(trade.swap) if trade.swap else 0,
            "commission": float(trade.commission) if trade.commission else 0,
            "open_time": trade.open_time.isoformat() if trade.open_time else None,
            "close_time": trade.close_time.isoformat() if trade.close_time else None,
            "comment": trade.comment,
            "status": trade.status
        }
        for trade in trades
    ]

@app.get("/api/account/stats")
async def get_account_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's account statistics"""
    connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    
    # Calculate total profit from trades
    from sqlalchemy import func, case
    total_profit = db.query(Trade).filter(Trade.user_id == user.id).with_entities(
        func.sum(case(
            (Trade.status == "open", Trade.unrealized_profit),
            else_=Trade.realized_profit
        )).label("total_profit")
    ).scalar() or 0
    
    # Calculate trading stats
    open_trades = db.query(Trade).filter(Trade.user_id == user.id, Trade.status == "open").count()
    closed_trades = db.query(Trade).filter(Trade.user_id == user.id, Trade.status == "closed").count()
    
    # Calculate floating profit (unrealized)
    floating_profit = db.query(Trade).filter(
        Trade.user_id == user.id, 
        Trade.status == "open"
    ).with_entities(func.sum(Trade.unrealized_profit)).scalar() or 0
    
    # Calculate historical profit (realized)
    historical_profit = db.query(Trade).filter(
        Trade.user_id == user.id, 
        Trade.status == "closed"
    ).with_entities(func.sum(Trade.realized_profit)).scalar() or 0
    
    # Calculate win rate
    winning_trades = db.query(Trade).filter(
        Trade.user_id == user.id,
        Trade.status == "closed",
        Trade.realized_profit > 0
    ).count()
    win_rate = (winning_trades / closed_trades * 100) if closed_trades > 0 else 0
    
    return {
        "account": {
            "balance": float(connection.account_balance) if connection and connection.account_balance else 0,
            "equity": float(connection.account_equity) if connection and connection.account_equity else 0,
            "margin": float(connection.account_margin) if connection and connection.account_margin else 0,
            "free_margin": float(connection.account_free_margin) if connection and connection.account_free_margin else 0,
            "margin_level": float(connection.account_margin_level) if connection and connection.account_margin_level else 0,
            "currency": connection.account_currency if connection else "USD"
        },
        "trading": {
            "total_profit": float(total_profit),
            "floating_profit": float(floating_profit),
            "historical_profit": float(historical_profit),
            "open_trades": open_trades,
            "closed_trades": closed_trades,
            "win_rate": win_rate
        },
        "is_connected": connection.is_connected if connection else False
    }

@app.get("/api/ea/download")
async def download_ea(user: User = Depends(get_current_user)):
    """Download Expert Advisor file"""
    ea_path = Path("ea/CopyArenaConnector.mq5")
    if ea_path.exists():
        return FileResponse(
            ea_path,
            media_type="text/plain",
            filename="CopyArenaConnector.mq5",
            headers={"Content-Disposition": "attachment; filename=CopyArenaConnector.mq5"}
        )
    else:
        raise HTTPException(status_code=404, detail="EA file not found")

@app.get("/api/leaderboard")
async def get_leaderboard(db: Session = Depends(get_db)):
    """Get leaderboard data"""
    # Mock leaderboard data for now
    return {
        "leaderboard": [
            {
                "id": 1,
                "username": "ProTrader",
                "total_profit": 15420.50,
                "win_rate": 78.5,
                "followers": 245,
                "xp_points": 12500,
                "level": 15
            },
            {
                "id": 2,
                "username": "FXMaster",
                "total_profit": 12380.25,
                "win_rate": 72.1,
                "followers": 189,
                "xp_points": 9800,
                "level": 12
            }
        ]
    }

@app.get("/api/marketplace")
async def get_marketplace(db: Session = Depends(get_db)):
    """Get marketplace traders"""
    # Mock marketplace data for now
    return {
        "traders": [
            {
                "id": 1,
                "username": "SignalKing",
                "description": "Expert in EUR/USD scalping",
                "total_profit": 8500.75,
                "win_rate": 82.3,
                "followers": 156,
                "risk_level": "Medium",
                "subscription_fee": 29.99
            }
        ]
    }

# === WEBSOCKET ===

@app.websocket("/ws/user/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle any client messages if needed
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# === STATIC FILES AND SPA ===

# Only mount static files if they exist (for production builds)
if Path("dist/assets").exists():
    app.mount("/assets", StaticFiles(directory="dist/assets"), name="static")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Serve the React SPA for all routes"""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    
    index_file = Path("dist/index.html")
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return HTMLResponse("<h1>CopyArena Backend API</h1><p>Backend is running successfully!</p>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 