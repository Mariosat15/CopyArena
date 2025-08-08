"""
CopyArena Backend API - Expert Advisor Version

Simplified backend that works with MQL5 Expert Advisors.
No complex MT5 bridge setup - just pure web API for EA connections.
Can be deployed anywhere (Render, Vercel, DigitalOcean, etc.)
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
import json
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
import uuid
import secrets

# Import models and database
from models import User, Trade, Follow, MT5Connection, SessionLocal, get_db

# Import EA API
from ea_api import router as ea_router

# Initialize FastAPI app
app = FastAPI(
    title="CopyArena API", 
    version="2.0.0",
    description="Expert Advisor based copy trading platform"
)

# Include EA API routes
app.include_router(ea_router)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for your domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Session management (simplified)
user_sessions: Dict[str, int] = {}

def hash_password(password: str) -> str:
    """Simple password hashing (use proper hashing in production)"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def generate_api_key() -> str:
    """Generate secure API key for EA"""
    return secrets.token_urlsafe(32)

# Pydantic models
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    subscription_plan: str
    credits: int
    xp_points: int
    level: int
    is_online: bool

# Session management functions
def get_session_id_from_request(request: Request) -> str:
    """Get or create session ID"""
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

def get_or_create_session_user(session_id: str, db: Session) -> User:
    """Get or create user for session"""
    if session_id in user_sessions:
        user_id = user_sessions[session_id]
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    
    # Create new user
    import time
    timestamp = str(int(time.time()))[-6:]
    new_user = User(
        email=f"user_{session_id[:8]}_{timestamp}@copyarena.com",
        username=f"Trader_{session_id[:8]}_{timestamp}",
        hashed_password=hash_password("temp_password"),
        subscription_plan="free",
        credits=0,
        xp_points=0,
        level=1,
        is_online=True,
        api_key=generate_api_key()  # Generate API key for EA
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    user_sessions[session_id] = new_user.id
    logger.info(f"Created user {new_user.id} with API key")
    
    return new_user

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get current user from session"""
    session_id = get_session_id_from_request(request)
    return get_or_create_session_user(session_id, db)

# Basic API endpoints
@app.get("/")
async def root():
    return {
        "message": "CopyArena API - Expert Advisor Version",
        "version": "2.0.0",
        "documentation": "/docs",
        "ea_endpoints": "/api/mt5/"
    }

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/auth/session")
async def get_session(request: Request, response: Response, db: Session = Depends(get_db)):
    """Get or create user session"""
    session_id = get_session_id_from_request(request)
    user = get_or_create_session_user(session_id, db)
    
    # Set session cookie
    response.set_cookie(
        key="session_id", 
        value=session_id, 
        max_age=30*24*60*60,  # 30 days
        httponly=True
    )
    
    return {
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "subscription_plan": user.subscription_plan,
            "credits": user.credits,
            "xp_points": user.xp_points,
            "level": user.level,
            "is_online": user.is_online,
            "api_key": user.api_key  # Return API key for EA setup
        }
    }

@app.get("/api/user/profile")
async def get_profile(user: User = Depends(get_current_user)):
    """Get user profile with API key"""
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "subscription_plan": user.subscription_plan,
        "credits": user.credits,
        "xp_points": user.xp_points,
        "level": user.level,
        "api_key": user.api_key,
        "mt5_connected": False  # Will be updated by EA
    }

@app.post("/api/user/regenerate-api-key")
async def regenerate_api_key(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Regenerate API key for EA"""
    user.api_key = generate_api_key()
    db.commit()
    
    return {
        "message": "API key regenerated successfully",
        "api_key": user.api_key
    }

@app.get("/api/trades")
async def get_trades(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get user's trades"""
    trades = db.query(Trade).filter(Trade.user_id == user.id).order_by(Trade.created_at.desc()).limit(100).all()
    
    return {
        "trades": [
            {
                "id": trade.id,
                "mt5_ticket": trade.mt5_ticket,
                "symbol": trade.symbol,
                "trade_type": trade.trade_type,
                "volume": trade.volume,
                "open_price": trade.open_price,
                "current_price": trade.current_price,
                "profit": trade.profit,
                "status": trade.status,
                "open_time": trade.open_time.isoformat() if trade.open_time else None,
                "close_time": trade.close_time.isoformat() if trade.close_time else None
            }
            for trade in trades
        ]
    }

@app.get("/api/account/stats")
async def get_account_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get account statistics from MT5 connection"""
    mt5_connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    
    if not mt5_connection or not mt5_connection.account_info:
        return {
            "balance": 0.0,
            "equity": 0.0,
            "margin": 0.0,
            "free_margin": 0.0,
            "margin_level": 0.0,
            "profit": 0.0,
            "currency": "USD",
            "connected": False
        }
    
    try:
        account_data = json.loads(mt5_connection.account_info)
        return {
            "balance": account_data.get("balance", 0.0),
            "equity": account_data.get("equity", 0.0),
            "margin": account_data.get("margin", 0.0),
            "free_margin": account_data.get("free_margin", 0.0),
            "margin_level": account_data.get("margin_level", 0.0),
            "profit": account_data.get("profit", 0.0),
            "currency": account_data.get("currency", "USD"),
            "connected": mt5_connection.is_connected
        }
    except Exception as e:
        logger.error(f"Failed to parse account info: {e}")
        return {
            "balance": 0.0,
            "equity": 0.0,
            "margin": 0.0,
            "free_margin": 0.0,
            "margin_level": 0.0,
            "profit": 0.0,
            "currency": "USD",
            "connected": False
        }

@app.get("/api/mt5/status")
async def get_mt5_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get MT5 connection status"""
    mt5_connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    
    if not mt5_connection:
        return {
            "connected": False,
            "message": "No MT5 connection found. Please install and run the Expert Advisor."
        }
    
    return {
        "connected": mt5_connection.is_connected,
        "login": mt5_connection.login,
        "server": mt5_connection.server,
        "last_sync": mt5_connection.last_sync.isoformat() if mt5_connection.last_sync else None,
        "last_connection": mt5_connection.last_connection.isoformat() if mt5_connection.last_connection else None
    }

# WebSocket endpoint for real-time updates (simplified)
@app.websocket("/ws/user/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    try:
        while True:
            # Keep connection alive and send updates
            await websocket.send_json({
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            })
            await asyncio.sleep(30)  # Ping every 30 seconds
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user_id}")

# Simplified startup
if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting CopyArena EA Backend...")
    logger.info("📡 Expert Advisor endpoints: /api/mt5/")
    logger.info("📖 Documentation: /docs")
    
    uvicorn.run(app, host="0.0.0.0", port=8000) 