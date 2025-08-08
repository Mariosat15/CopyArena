from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, WebSocketDisconnect, Header
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
from models import Base, User, Trade, MT5Connection, SessionLocal, engine, hash_password, verify_password
from websocket_manager import ConnectionManager

# Import for password validation
from pydantic import BaseModel

# Request models for authentication
class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str

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

# ===== SESSION MANAGEMENT (FOR EA ONLY) =====

def get_session_id_from_request(request: Request) -> str:
    """Extract session ID from request headers or create new one"""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

def get_or_create_session_user_for_ea(session_id: str, db: Session) -> User:
    """Create session user ONLY for EA connections - not for web auth"""
    if session_id in user_sessions:
        user_id = user_sessions[session_id]
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    
    # Check if user exists in database with this session pattern
    existing_user = db.query(User).filter(
        User.email.like(f"user_{session_id[:8]}_%@copyarena.com")
    ).first()
    
    if existing_user:
        # Found existing user, cache the session
        user_sessions[session_id] = existing_user.id
        user_api_keys[existing_user.api_key] = existing_user.id
        logger.info(f"Retrieved existing EA user {existing_user.id} for session {session_id[:8]}")
        return existing_user
    
    # Create a new user for EA session with timestamp to ensure uniqueness
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
    
    logger.info(f"Created new EA user {new_user.id} (session: {session_id[:8]}) with API key: {final_api_key[:20]}...")
    
    return new_user

def get_current_user_from_token(authorization: str, db: Session) -> User:
    """Get user from JWT token or session token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No valid token provided")
    
    token = authorization.replace("Bearer ", "")
    
    # Check if it's a session token format
    if token.startswith("session_"):
        user_id = token.replace("session_", "")
        try:
            user = db.query(User).filter(User.id == int(user_id)).first()
            if user:
                return user
        except:
            pass
    
    # If no valid token found
    raise HTTPException(status_code=401, detail="Invalid token")

def get_user_by_api_key(api_key: str, db: Session) -> User:
    """Get user by API key for EA authentication"""
    if not api_key:
        return None
    
    # First check the in-memory cache
    if api_key in user_api_keys:
        user_id = user_api_keys[api_key]
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    
    # If not in cache, query database
    user = db.query(User).filter(User.api_key == api_key).first()
    if user:
        # Cache the mapping
        user_api_keys[api_key] = user.id
        return user
    
    return None

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)) -> User:
    """Get current user - requires proper authentication"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    return get_current_user_from_token(authorization, db)

# ===== AUTHENTICATION ENDPOINTS =====

@app.post("/api/auth/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new user with email and password"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check if username is taken
        existing_username = db.query(User).filter(User.username == request.username).first()
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Validate password length
        if len(request.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Create new user
        hashed_password = hash_password(request.password)
        api_key = f"ca_user_{uuid.uuid4().hex[:16]}"
        
        new_user = User(
            email=request.email,
            username=request.username,
            hashed_password=hashed_password,
            api_key=api_key,
            subscription_plan="free",
            credits=100,  # Welcome credits
            xp_points=0,
            level=1,
            is_online=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Update API key with user ID
        final_api_key = f"ca_{new_user.id}_{uuid.uuid4().hex[:12]}"
        new_user.api_key = final_api_key
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"New user registered: {new_user.email} (ID: {new_user.id})")
        
        return {
            "user": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email,
                "api_key": new_user.api_key,
                "subscription_plan": new_user.subscription_plan,
                "credits": new_user.credits,
                "xp_points": new_user.xp_points,
                "level": new_user.level,
                "is_online": new_user.is_online
            },
            "token": f"session_{new_user.id}",
            "message": "Registration successful"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/api/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login with email and password"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Verify password
        if not verify_password(request.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Update user status
        user.is_online = True
        user.last_seen = datetime.utcnow()
        db.commit()
        
        logger.info(f"User logged in: {user.email} (ID: {user.id})")
        
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
            "token": f"session_{user.id}",
            "message": "Login successful"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.post("/api/auth/logout")
async def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Logout current user"""
    user.is_online = False
    db.commit()
    return {"message": "Logged out successfully"}

# ===== SESSION ENDPOINTS (FOR EA ONLY) =====

@app.get("/api/auth/session")
async def get_session(request: Request, db: Session = Depends(get_db)):
    """Get session info - ONLY for EA connections"""
    session_id = get_session_id_from_request(request)
    user = get_or_create_session_user_for_ea(session_id, db)
    return {
        "session_id": session_id,
        "user_id": user.id,
        "username": user.username,
        "api_key": user.api_key,
        "message": "Session valid"
    }

@app.post("/api/auth/session")
async def create_session(request: Request, db: Session = Depends(get_db)):
    """Create/get session user info - ONLY for EA connections"""
    session_id = get_session_id_from_request(request)
    user = get_or_create_session_user_for_ea(session_id, db)
    return {
        "session_id": session_id,
        "user_id": user.id,
        "username": user.username,
        "api_key": user.api_key,
        "message": "Session active"
    }

# === EA DATA ENDPOINTS ===

@app.post("/api/ea/data")
async def receive_ea_data(request: Request, db: Session = Depends(get_db)):
    """Receive data from Expert Advisor"""
    try:
        # Log incoming request
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        content_type = request.headers.get("content-type", "unknown")
        
        logger.info(f"EA request from {client_host}, User-Agent: {user_agent}, Content-Type: {content_type}")
        
        data = await request.json()
        api_key = data.get("api_key")
        data_type = data.get("type")
        timestamp = data.get("timestamp")
        payload = data.get("data")
        
        logger.info(f"EA data received - Type: {data_type}, API Key: {api_key[:8] if api_key else 'None'}...")
        
        if not api_key:
            logger.warning("EA request missing API key")
            raise HTTPException(status_code=400, detail="API key required")
        
        # Get user by API key
        user = get_user_by_api_key(api_key, db)
        if not user:
            logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        logger.info(f"EA data from user {user.username} - Type: {data_type}")
        
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
        
        logger.info(f"EA data processed successfully for user {user.username}")
        return {"status": "success", "message": "Data received"}
        
    except HTTPException as e:
        logger.error(f"HTTP Error processing EA data: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error processing EA data: {e}")
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
        # Store raw values from EA
        connection.account_balance = data.get("balance", 0)
        connection.account_equity = data.get("equity", 0)
        connection.account_margin = data.get("margin", 0)
        connection.account_free_margin = data.get("free_margin", 0)
        
        # Fix margin level calculation - MT5 sends percentage already
        margin_level = data.get("margin_level", 0)
        # If margin is 0 or very small, margin level should be very high (or infinite)
        account_margin = data.get("margin", 0)
        if account_margin > 0:
            # MT5 already calculates this correctly as percentage
            connection.account_margin_level = margin_level
        else:
            # No margin used = infinite margin level, but cap at reasonable value
            connection.account_margin_level = 999999.0
        
        connection.account_profit = data.get("profit", 0)
        connection.account_currency = data.get("account_currency", "USD")
        connection.last_sync = datetime.utcnow()
        db.commit()
        
        # Log account update for debugging
        logger.info(f"Account updated for user {user.id}: Balance={data.get('balance')}, "
                   f"Equity={data.get('equity')}, Margin={data.get('margin')}, "
                   f"Free Margin={data.get('free_margin')}, Margin Level={margin_level}%")

async def handle_positions_update(user: User, positions: list, db: Session):
    """Handle positions update from EA - LIVE DATA PROCESSING"""
    logger.info(f"🔄 Processing {len(positions)} positions for {user.username}")
    
    if not positions:
        logger.info("📭 No positions received - CLOSING ALL OPEN TRADES")
        # When EA sends empty positions, close all open trades
        open_trades = db.query(Trade).filter(
            Trade.user_id == user.id,
            Trade.status == "open"
        ).all()
        
        closed_count = 0
        for trade in open_trades:
            trade.status = "closed"
            trade.close_time = datetime.utcnow()
            trade.close_price = trade.current_price or trade.open_price
            if trade.unrealized_profit:
                trade.realized_profit = trade.unrealized_profit
                trade.unrealized_profit = 0
            closed_count += 1
            
        db.commit()
        logger.info(f"🔒 CLOSED {closed_count} trades due to empty positions")
        
        # Send WebSocket update
        await manager.send_user_message({
            "type": "all_trades_closed",
            "data": {"closed": closed_count},
            "message": f"All {closed_count} trades closed"
        }, user.id)
        return
    
    # Process each position from EA
    new_count = 0
    updated_count = 0
    
    for pos in positions:
        try:
            ticket = str(pos.get("ticket", ""))
            if not ticket:
                continue
                
            # Extract position data
            symbol = pos.get("symbol", "")
            trade_type = "buy" if pos.get("type") == 0 else "sell"
            volume = float(pos.get("volume", 0))
            open_price = float(pos.get("open_price", 0))
            current_price = float(pos.get("current_price", 0))
            profit = float(pos.get("profit", 0))
            swap = float(pos.get("swap", 0))
            open_time = datetime.fromtimestamp(pos.get("open_time", 0)) if pos.get("open_time") else datetime.utcnow()
            
            # Find existing trade
            existing_trade = db.query(Trade).filter(
                Trade.user_id == user.id,
                Trade.ticket == ticket
            ).first()
            
            if existing_trade:
                # Update existing trade - ENSURE IT'S OPEN
                existing_trade.status = "open"  # 🔥 CRITICAL: Force open status
                existing_trade.current_price = current_price
                existing_trade.unrealized_profit = profit
                existing_trade.realized_profit = 0 if existing_trade.status != "closed" else existing_trade.realized_profit
                existing_trade.swap = swap
                existing_trade.close_time = None  # Clear close time for open trades
                existing_trade.close_price = None  # Clear close price for open trades
                updated_count += 1
                logger.info(f"✅ Updated {ticket}: {symbol} {profit:.2f}")
            else:
                # Create NEW trade - ALWAYS OPEN
                new_trade = Trade(
                    user_id=user.id,
                    ticket=ticket,
                    symbol=symbol,
                    trade_type=trade_type,
                    volume=volume,
                    open_price=open_price,
                    current_price=current_price,
                    stop_loss=float(pos.get("sl", 0)),
                    take_profit=float(pos.get("tp", 0)),
                    unrealized_profit=profit,
                    realized_profit=0,
                    swap=swap,
                    commission=0,
                    open_time=open_time,
                    close_time=None,
                    close_price=None,
                    comment=pos.get("comment", ""),
                    status="open"  # 🔥 CRITICAL: ALWAYS open for new positions
                )
                db.add(new_trade)
                new_count += 1
                logger.info(f"🆕 Created {ticket}: {symbol} {trade_type} {volume} lots P&L={profit:.2f}")
                
        except Exception as e:
            logger.error(f"❌ Error processing position {pos}: {e}")
            continue
    
    # Commit all changes
    db.commit()
    logger.info(f"🎯 LIVE UPDATE: {new_count} new, {updated_count} updated trades")
    
    # 🔥 CRITICAL: Check for trades that were closed (exist in DB but not in EA positions)
    current_ea_tickets = {str(pos.get("ticket", "")) for pos in positions if pos.get("ticket")}
    db_open_trades = db.query(Trade).filter(
        Trade.user_id == user.id,
        Trade.status == "open"
    ).all()
    
    closed_missing_count = 0
    for db_trade in db_open_trades:
        if db_trade.ticket not in current_ea_tickets:
            # This trade is open in DB but missing from EA positions = CLOSED!
            db_trade.status = "closed"
            db_trade.close_time = datetime.utcnow()
            db_trade.close_price = db_trade.current_price or db_trade.open_price
            if db_trade.unrealized_profit:
                db_trade.realized_profit = db_trade.unrealized_profit
                db_trade.unrealized_profit = 0
            closed_missing_count += 1
            logger.info(f"🔒 CLOSED missing trade {db_trade.ticket} (not in EA positions)")
    
    if closed_missing_count > 0:
        db.commit()
        logger.info(f"🎯 CLOSED {closed_missing_count} trades that were missing from EA positions")
    
    # Send immediate WebSocket update for instant UI refresh
    await manager.send_user_message({
        "type": "positions_updated",
        "data": {"new": new_count, "updated": updated_count, "closed": closed_missing_count},
        "message": "Live trades updated"
    }, user.id)

async def handle_orders_update(user: User, orders: list, db: Session):
    """Handle pending orders update"""
    # Similar logic to positions but for pending orders
    # Can be implemented based on requirements
    pass

async def handle_history_update(user: User, history: list, db: Session):
    """Handle trade history update - Only process NEW history entries"""
    logger.info(f"📊 Processing {len(history)} history deals for {user.username}")
    
    if not history:
        logger.info("📭 No history received")
        return
    
    # Track which tickets we've already processed to avoid duplicates
    existing_tickets = set(
        db.query(Trade.ticket).filter(Trade.user_id == user.id).all()
    )
    existing_tickets = {ticket[0] for ticket in existing_tickets}
    
    closed_count = 0
    new_count = 0
    skipped_count = 0
    
    for deal in history:
        try:
            ticket = str(deal.get("ticket", ""))
            if not ticket:
                continue
                
            # SKIP if we already have this ticket - DON'T re-process
            if ticket in existing_tickets:
                skipped_count += 1
                continue
                
            # Only process truly NEW history entries
            new_trade = Trade(
                user_id=user.id,
                ticket=ticket,
                symbol=deal.get("symbol", ""),
                trade_type="buy" if deal.get("type") == 0 else "sell",
                volume=float(deal.get("volume", 0)),
                open_price=float(deal.get("price", 0)),
                current_price=float(deal.get("price", 0)),
                close_price=float(deal.get("price", 0)),
                realized_profit=float(deal.get("profit", 0)),
                swap=float(deal.get("swap", 0)),
                commission=float(deal.get("commission", 0)),
                open_time=datetime.fromtimestamp(deal.get("time", 0)) if deal.get("time") else datetime.utcnow(),
                close_time=datetime.fromtimestamp(deal.get("time", 0)) if deal.get("time") else datetime.utcnow(),
                comment=deal.get("comment", ""),
                status="closed"
            )
            db.add(new_trade)
            new_count += 1
            logger.info(f"📋 NEW historical trade {ticket}: P&L={new_trade.realized_profit:.2f}")
                    
        except Exception as e:
            logger.error(f"❌ Error processing history deal {deal}: {e}")
            continue
    
    db.commit()
    logger.info(f"🎯 HISTORY UPDATE: {new_count} NEW, {skipped_count} skipped (already exist)")
    
    # Only send WebSocket update if we processed new trades
    if new_count > 0:
        await manager.send_user_message({
            "type": "history_update", 
            "data": {"new_trades": new_count},
            "message": f"{new_count} new trades added to history"
        }, user.id)

# === WEB APP ENDPOINTS ===

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
    
    # Get account values - use real-time data from MT5 connection
    balance = float(connection.account_balance) if connection and connection.account_balance else 0
    equity = float(connection.account_equity) if connection and connection.account_equity else 0
    margin = float(connection.account_margin) if connection and connection.account_margin else 0
    free_margin = float(connection.account_free_margin) if connection and connection.account_free_margin else 0
    margin_level = float(connection.account_margin_level) if connection and connection.account_margin_level else 0
    
    # Validate margin level - should be reasonable percentage
    if margin > 0:
        # Calculate margin level as (Equity / Margin) * 100
        calculated_margin_level = (equity / margin) * 100
        # Use calculated value if stored value seems wrong
        if margin_level > 100000 or margin_level < 0:
            margin_level = calculated_margin_level
            logger.warning(f"Fixed invalid margin level from {connection.account_margin_level}% to {calculated_margin_level}%")
    else:
        # No margin used = infinite margin level
        margin_level = 999999.0
    
    return {
        "account": {
            "balance": balance,
            "equity": equity,
            "margin": margin,
            "free_margin": free_margin,
            "margin_level": round(margin_level, 2),  # Round to 2 decimal places
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

@app.get("/api/user/profile")
async def get_user_profile(user: User = Depends(get_current_user)):
    """Get user profile information - requires authentication"""
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
            "is_online": user.is_online,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_seen": user.last_seen.isoformat() if user.last_seen else None
        }
    }

@app.get("/api/mt5/status")
async def get_mt5_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get MT5 connection status"""
    connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    return {
        "is_connected": connection.is_connected if connection else False,
        "account_number": connection.login if connection else None,
        "last_sync": connection.last_sync.isoformat() if connection and connection.last_sync else None
    }

@app.get("/api/ea/download")
async def download_ea(user: User = Depends(get_current_user)):
    """Download Expert Advisor file"""
    ea_path = Path(__file__).parent / "ea" / "CopyArenaConnector.mq5"
    if not ea_path.exists():
        # Try relative path from backend directory
        ea_path = Path("../ea/CopyArenaConnector.mq5")
    if not ea_path.exists():
        # Try absolute path from project root
        ea_path = Path(__file__).parent.parent / "ea" / "CopyArenaConnector.mq5"
    
    if ea_path.exists():
        return FileResponse(
            ea_path,
            media_type="text/plain",
            filename="CopyArenaConnector.mq5",
            headers={"Content-Disposition": "attachment; filename=CopyArenaConnector.mq5"}
        )
    else:
        raise HTTPException(status_code=404, detail=f"EA file not found. Checked: {ea_path}")

@app.get("/api/leaderboard")
async def get_leaderboard(sort_by: str = "xp_points", db: Session = Depends(get_db)):
    """Get leaderboard data from real users"""
    try:
        # Get real users from database, sorted by requested field
        query = db.query(User).filter(User.is_online == True)
        
        if sort_by == "total_profit":
            # Calculate total profit for each user and sort
            from sqlalchemy import func, case
            users_with_profit = db.query(
                User,
                func.coalesce(
                    func.sum(case(
                        (Trade.status == "open", Trade.unrealized_profit),
                        else_=Trade.realized_profit
                    )), 0
                ).label("total_profit")
            ).outerjoin(Trade, User.id == Trade.user_id)\
             .group_by(User.id)\
             .order_by(func.coalesce(
                 func.sum(case(
                     (Trade.status == "open", Trade.unrealized_profit),
                     else_=Trade.realized_profit
                 )), 0
             ).desc())\
             .limit(50).all()
            
            leaderboard_data = []
            for user, total_profit in users_with_profit:
                # Calculate additional stats
                win_rate = 0
                closed_trades = db.query(Trade).filter(
                    Trade.user_id == user.id, 
                    Trade.status == "closed"
                ).count()
                
                if closed_trades > 0:
                    winning_trades = db.query(Trade).filter(
                        Trade.user_id == user.id,
                        Trade.status == "closed",
                        Trade.realized_profit > 0
                    ).count()
                    win_rate = (winning_trades / closed_trades * 100)
                
                leaderboard_data.append({
                    "id": user.id,
                    "username": user.username,
                    "total_profit": float(total_profit) if total_profit else 0,
                    "win_rate": round(win_rate, 1),
                    "followers": 0,  # TODO: Implement follower system
                    "xp_points": user.xp_points,
                    "level": user.level,
                    "subscription_plan": user.subscription_plan,
                    "is_online": user.is_online
                })
        else:
            # Sort by XP points, level, or other user fields
            if sort_by == "xp_points":
                query = query.order_by(User.xp_points.desc())
            elif sort_by == "level":
                query = query.order_by(User.level.desc())
            else:
                query = query.order_by(User.xp_points.desc())  # Default fallback
            
            users = query.limit(50).all()
            
            leaderboard_data = []
            for user in users:
                # Calculate total profit for each user
                total_profit = db.query(Trade).filter(Trade.user_id == user.id).with_entities(
                    func.sum(case(
                        (Trade.status == "open", Trade.unrealized_profit),
                        else_=Trade.realized_profit
                    )).label("total_profit")
                ).scalar() or 0
                
                # Calculate win rate
                closed_trades = db.query(Trade).filter(
                    Trade.user_id == user.id, 
                    Trade.status == "closed"
                ).count()
                
                win_rate = 0
                if closed_trades > 0:
                    winning_trades = db.query(Trade).filter(
                        Trade.user_id == user.id,
                        Trade.status == "closed",
                        Trade.realized_profit > 0
                    ).count()
                    win_rate = (winning_trades / closed_trades * 100)
                
                leaderboard_data.append({
                    "id": user.id,
                    "username": user.username,
                    "total_profit": float(total_profit),
                    "win_rate": round(win_rate, 1),
                    "followers": 0,  # TODO: Implement follower system
                    "xp_points": user.xp_points,
                    "level": user.level,
                    "subscription_plan": user.subscription_plan,
                    "is_online": user.is_online
                })
        
        return {"leaderboard": leaderboard_data}
        
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        # Fallback to basic user list if complex queries fail
        users = db.query(User).order_by(User.xp_points.desc()).limit(10).all()
        return {
            "leaderboard": [
                {
                    "id": user.id,
                    "username": user.username,
                    "total_profit": 0,
                    "win_rate": 0,
                    "followers": 0,
                    "xp_points": user.xp_points,
                    "level": user.level,
                    "subscription_plan": user.subscription_plan,
                    "is_online": user.is_online
                }
                for user in users
            ]
        }

@app.get("/api/marketplace")
async def get_marketplace(db: Session = Depends(get_db)):
    """Get marketplace traders from real users with trading activity"""
    try:
        # Get users who have active trading and good performance
        from sqlalchemy import func, case
        
        # Find users with trades and calculate their stats
        users_with_trades = db.query(
            User,
            func.count(Trade.id).label("total_trades"),
            func.coalesce(
                func.sum(case(
                    (Trade.status == "open", Trade.unrealized_profit),
                    else_=Trade.realized_profit
                )), 0
            ).label("total_profit")
        ).join(Trade, User.id == Trade.user_id)\
         .group_by(User.id)\
         .having(func.count(Trade.id) > 0)\
         .order_by(func.coalesce(
             func.sum(case(
                 (Trade.status == "open", Trade.unrealized_profit),
                 else_=Trade.realized_profit
             )), 0
         ).desc())\
         .limit(20).all()
        
        marketplace_data = []
        for user, total_trades, total_profit in users_with_trades:
            # Calculate win rate
            closed_trades = db.query(Trade).filter(
                Trade.user_id == user.id, 
                Trade.status == "closed"
            ).count()
            
            win_rate = 0
            if closed_trades > 0:
                winning_trades = db.query(Trade).filter(
                    Trade.user_id == user.id,
                    Trade.status == "closed",
                    Trade.realized_profit > 0
                ).count()
                win_rate = (winning_trades / closed_trades * 100)
            
            # Determine risk level based on trade volume and performance
            risk_level = "Low"
            if win_rate > 70:
                risk_level = "Low"
            elif win_rate > 50:
                risk_level = "Medium"
            else:
                risk_level = "High"
            
            marketplace_data.append({
                "id": user.id,
                "username": user.username,
                "description": f"Active trader with {total_trades} trades",
                "total_profit": float(total_profit) if total_profit else 0,
                "win_rate": round(win_rate, 1),
                "followers": 0,  # TODO: Implement follower system
                "risk_level": risk_level,
                "subscription_fee": 0,  # Free for now
                "level": user.level,
                "xp_points": user.xp_points,
                "is_online": user.is_online,
                "subscription_plan": user.subscription_plan
            })
        
        return {"traders": marketplace_data}
        
    except Exception as e:
        logger.error(f"Error fetching marketplace: {e}")
        # Fallback to simple user list
        users = db.query(User).filter(User.is_online == True).limit(5).all()
        return {
            "traders": [
                {
                    "id": user.id,
                    "username": user.username,
                    "description": f"Level {user.level} trader",
                    "total_profit": 0,
                    "win_rate": 0,
                    "followers": 0,
                    "risk_level": "Medium",
                    "subscription_fee": 0,
                    "level": user.level,
                    "xp_points": user.xp_points,
                    "is_online": user.is_online,
                    "subscription_plan": user.subscription_plan
                }
                for user in users
            ]
        }

@app.get("/api/debug/live-data")
async def debug_live_data(user: User = Depends(get_current_user)):
    """Debug endpoint to see current live data"""
    return {
        "user": user.username,
        "positions_count": "Check WebSocket data",
        "history_count": "Check WebSocket data", 
        "note": "Live data is in WebSocket messages, not stored in backend"
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