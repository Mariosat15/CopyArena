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
from models import Base, User, Trade, MT5Connection, SessionLocal, engine, hash_password, verify_password, Follow
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
    """DEPRECATED: Session-based user creation disabled for security"""
    logger.error("🚨 SECURITY: Attempted to use deprecated session-based user creation")
    raise HTTPException(
        status_code=410,
        detail="Session-based authentication deprecated for security. Use proper API key authentication."
    )

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
    """Get user by API key for EA authentication - SECURE VERSION"""
    if not api_key:
        logger.warning("🚨 EA authentication attempted with no API key")
        return None
    
    # SECURITY: Always validate API key format first
    if not api_key.startswith('ca_'):
        logger.warning(f"🚨 Invalid API key format attempted: {api_key[:10]}...")
        return None
    
    # First check the in-memory cache
    if api_key in user_api_keys:
        user_id = user_api_keys[api_key]
        user = db.query(User).filter(User.id == user_id, User.api_key == api_key).first()
        if user:
            # SECURITY: Double-check that the cached user still owns this API key
            if user.api_key == api_key:
                logger.info(f"✅ Valid cached API key for user {user.id} ({user.username})")
                return user
            else:
                # Cache is stale - remove it
                logger.warning(f"🚨 Stale cache detected for API key {api_key[:10]}... - removing")
                del user_api_keys[api_key]
    
    # If not in cache, query database with strict validation
    user = db.query(User).filter(User.api_key == api_key).first()
    if user:
        # SECURITY: Verify the API key exactly matches and user is active
        if user.api_key == api_key and user.is_active:
            # Cache the mapping
            user_api_keys[api_key] = user.id
            logger.info(f"✅ Valid API key authentication for user {user.id} ({user.username})")
            return user
        else:
            logger.warning(f"🚨 API key mismatch or inactive user: {api_key[:10]}... for user {user.id if user else 'None'}")
    
    logger.warning(f"🚨 Invalid API key attempted: {api_key[:10]}...")
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
        # Check if user already exists (case-insensitive)
        existing_user = db.query(User).filter(User.email.ilike(request.email)).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Check if username is taken
        existing_username = db.query(User).filter(User.username == request.username).first()
        if existing_username:
            raise HTTPException(status_code=400, detail="Username already taken")
        
        # Validate password length
        if len(request.password) < 6:
            raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
        
        # Create new user with temporary API key
        hashed_password = hash_password(request.password)
        
        new_user = User(
            email=request.email.lower(),
            username=request.username,
            hashed_password=hashed_password,
            api_key="temp_placeholder",  # Temporary placeholder
            subscription_plan="free",
            credits=100,  # Welcome credits
            xp_points=0,
            level=1,
            is_online=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Generate secure unique API key using the actual user ID
        final_api_key = generate_unique_api_key(new_user.id, db)
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
        # Find user by email (case-insensitive)
        user = db.query(User).filter(User.email.ilike(request.email)).first()
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

# ===== SESSION ENDPOINTS (DEPRECATED - SECURITY RISK) =====
# These endpoints are disabled to prevent API key bypass attacks

@app.get("/api/auth/session")
async def get_session(request: Request, db: Session = Depends(get_db)):
    """DEPRECATED: Session endpoint disabled for security - use proper API key authentication"""
    logger.error("🚨 SECURITY: Attempted access to deprecated session endpoint")
    raise HTTPException(
        status_code=410, 
        detail="Session endpoint deprecated. Please use proper API key authentication via /api/ea/data"
    )

@app.post("/api/auth/session")
async def create_session(request: Request, db: Session = Depends(get_db)):
    """DEPRECATED: Session endpoint disabled for security - use proper API key authentication"""
    logger.error("🚨 SECURITY: Attempted access to deprecated session creation endpoint")
    raise HTTPException(
        status_code=410, 
        detail="Session creation deprecated. Please use proper API key authentication via /api/ea/data"
    )

# === EA DATA ENDPOINTS ===

@app.post("/api/ea/data")  # Keep endpoint for backwards compatibility
async def receive_client_data(request: Request, db: Session = Depends(get_db)):
    """Receive data from Windows Client (formerly Expert Advisor)"""
    try:
        # Log incoming request
        client_host = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        content_type = request.headers.get("content-type", "unknown")
        
        logger.info(f"Client request from {client_host}, User-Agent: {user_agent}, Content-Type: {content_type}")
        
        data = await request.json()
        api_key = data.get("api_key")
        data_type = data.get("type")
        timestamp = data.get("timestamp")
        payload = data.get("data")
        
        # NEW: Additional security fields
        expected_user_id = data.get("user_id")  # Windows Client should know which user it belongs to
        account_info = data.get("account_info", {})  # MT5 account details for verification
        
        logger.info(f"Client data received - Type: {data_type}, API Key: {api_key[:8] if api_key else 'None'}...")
        
        if not api_key:
            logger.warning("Client request missing API key")
            raise HTTPException(status_code=400, detail="API key required")
        
        # Get user by API key - SECURE AUTHENTICATION
        user = get_user_by_api_key(api_key, db)
        if not user:
            logger.error(f"🚨 SECURITY ALERT: Invalid API key attempted from {client_host} - Key: {api_key[:8]}...")
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # 🔐 CRITICAL SECURITY CHECK: Verify user identity
        client_info = data.get("client_info", {})
        client_type = client_info.get("type", "unknown")
        
        # For new Windows client: verify user ID matches API key owner
        if expected_user_id and expected_user_id != user.id:
            logger.error(f"🚨 SECURITY VIOLATION: User ID mismatch - API belongs to user {user.id} but client claims {expected_user_id}")
            logger.error(f"🚨 Host: {client_host}, Client: {client_type}, API Key: {api_key[:12]}...")
            raise HTTPException(
                status_code=403, 
                detail=f"Security violation: User ID does not match API key owner"
            )
            
        # For Windows client: also verify username matches
        expected_username = data.get("username")
        if expected_username and expected_username != user.username:
            logger.error(f"🚨 SECURITY VIOLATION: Username mismatch - Expected {user.username} but got {expected_username}")
            raise HTTPException(
                status_code=403,
                detail=f"Security violation: Username does not match account"
            )
            
        # Log client type for monitoring
        logger.info(f"🔐 Client type: {client_type} from {client_host}")
        
        # 🔐 ADDITIONAL SECURITY: IP-based API key binding (prevent key sharing)
        stored_ip = getattr(user, 'last_login_ip', None) if hasattr(user, 'last_login_ip') else None
        current_ip = client_host
        
        # Store the IP when user first uses their API key
        if not user.last_login_ip:
            user.last_login_ip = current_ip
            db.commit()
            logger.info(f"🔐 BINDING: API key {api_key[:12]}... bound to IP {current_ip} for user {user.id}")
        elif user.last_login_ip != current_ip:
            # Same API key being used from different IP - SECURITY ALERT
            logger.error(f"🚨 SECURITY ALERT: API key {api_key[:12]}... used from new IP!")
            logger.error(f"🚨 Registered IP: {user.last_login_ip} | Current IP: {current_ip}")
            logger.error(f"🚨 User: {user.id} ({user.username}) | Host: {client_host}")
            
            # For now, allow but log heavily (you can make this stricter later)
            logger.warning(f"⚠️  ALLOWING IP change for user {user.id} - consider implementing stricter controls")
            
            # Update to new IP (you might want to require manual verification instead)
            user.last_login_ip = current_ip
            db.commit()
        
        logger.info(f"✅ AUTHENTICATED Client data from user {user.username} (ID: {user.id}) - Type: {data_type}")
        
        # SECURITY: Log the API key usage for audit trail
        logger.info(f"🔐 API Key usage: User {user.id} ({user.username}) from {client_host} using key {api_key[:12]}...")
        
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
        
        logger.info(f"Client data processed successfully for user {user.username}")
        return {"status": "success", "message": "Data received"}
        
    except HTTPException as e:
        logger.error(f"HTTP Error processing Client data: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error processing Client data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def handle_connection_status(user: User, data: dict, db: Session):
    """Handle Windows Client connection status"""
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
    logger.info(f"User {user.id} Windows Client connection: {'CONNECTED' if connected else 'DISCONNECTED'}")

async def handle_account_update(user: User, data: dict, db: Session):
    """Handle account information update"""
    # Update user's account info (can be stored in User model or separate table)
    # For now, we'll store in MT5Connection
    connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    if connection:
        # Store raw values from Windows Client
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
    """Handle positions update from Windows Client - LIVE DATA PROCESSING"""
    logger.info(f"🔄 Processing {len(positions)} positions for {user.username}")
    
    if not positions:
        logger.info("📭 No positions received - MARKET MAY BE CLOSED (not closing trades)")
        # ⚠️ IMPORTANT: Don't automatically close trades on empty positions!
        # Empty positions could mean:
        # 1. Market is closed
        # 2. EA temporarily disconnected
        # 3. Actual trades were closed
        # We should only close trades when we get explicit close signals
        
        # Send WebSocket update that no live positions are available
        await manager.send_user_message({
            "type": "positions_update",
            "data": [],
            "message": "No live positions (market may be closed)"
        }, user.id)
        return
    
    # Process each position from Windows Client
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
                    unrealized_profit=profit,
                    swap=swap,
                    open_time=open_time,
                    status="open",  # 🔥 CRITICAL: Always open for new positions
                    comment=""
                )
                db.add(new_trade)
                new_count += 1
                logger.info(f"🆕 NEW trade {ticket}: {symbol} {profit:.2f}")
                
        except Exception as e:
            logger.error(f"❌ Error processing position {pos}: {e}")
            continue
    
    # 🔥 CRITICAL: Now check for trades that were actually closed
    # Only close trades that exist in DB but are NOT in the current Windows Client positions
    if positions:  # Only do this check if we have positions data
        current_client_tickets = {str(pos.get("ticket", "")) for pos in positions if pos.get("ticket")}
        db_open_trades = db.query(Trade).filter(
            Trade.user_id == user.id,
            Trade.status == "open"
        ).all()
        
        closed_missing_count = 0
        for db_trade in db_open_trades:
            if db_trade.ticket not in current_client_tickets:
                # This trade is open in DB but missing from Windows Client positions = ACTUALLY CLOSED!
                db_trade.status = "closed"
                db_trade.close_time = datetime.utcnow()
                db_trade.close_price = db_trade.current_price or db_trade.open_price
                if db_trade.unrealized_profit:
                    db_trade.realized_profit = db_trade.unrealized_profit
                    db_trade.unrealized_profit = 0
                closed_missing_count += 1
                logger.info(f"🔒 CLOSED missing trade {db_trade.ticket} (not in Windows Client positions)")
        
        if closed_missing_count > 0:
            logger.info(f"🎯 CLOSED {closed_missing_count} trades that were actually closed")
    
    db.commit()
    logger.info(f"🚀 Position update complete: {new_count} new, {updated_count} updated")
    
    # Send immediate WebSocket update for instant UI refresh
    await manager.send_user_message({
        "type": "positions_updated",
        "data": {"new": new_count, "updated": updated_count},
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

# ===== USER PROFILE ENDPOINTS =====

@app.get("/api/user/profile")
async def get_user_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's profile information"""
    try:
        return {
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "username": current_user.username,
                "api_key": current_user.api_key,
                "subscription_plan": current_user.subscription_plan,
                "credits": current_user.credits,
                "xp_points": current_user.xp_points,
                "level": current_user.level,
                "is_master_trader": current_user.is_master_trader,
                "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
                "last_seen": current_user.last_seen.isoformat() if current_user.last_seen else None
            }
        }
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user profile")

@app.post("/api/user/master-trader")
async def toggle_master_trader(
    request: dict,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Toggle user's master trader status"""
    try:
        is_master_trader = request.get("is_master_trader", False)
        
        # Update user's master trader status
        current_user.is_master_trader = is_master_trader
        db.commit()
        
        logger.info(f"User {current_user.username} (ID: {current_user.id}) master trader status: {is_master_trader}")
        
        return {
            "success": True,
            "is_master_trader": is_master_trader,
            "message": f"Master trader status {'enabled' if is_master_trader else 'disabled'}"
        }
    except Exception as e:
        logger.error(f"Error updating master trader status: {e}")
        raise HTTPException(status_code=500, detail="Failed to update master trader status")

@app.get("/api/user/stats")
async def get_user_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's trading statistics"""
    try:
        # Get trading statistics from database
        total_trades = db.query(Trade).filter(Trade.user_id == current_user.id).count()
        
        closed_trades = db.query(Trade).filter(
            Trade.user_id == current_user.id,
            Trade.status == 'closed'
        ).all()
        
        # Calculate win rate
        winning_trades = sum(1 for trade in closed_trades if (trade.profit or 0) > 0)
        win_rate = round((winning_trades / len(closed_trades)) * 100, 1) if closed_trades else 0.0
        
        # Calculate total profit
        total_profit = sum(trade.profit or 0 for trade in closed_trades)
        
        # Get follower counts
        followers_count = db.query(Follow).filter(Follow.following_id == current_user.id).count()
        following_count = db.query(Follow).filter(Follow.follower_id == current_user.id).count()
        
        # Calculate rank based on total profit and performance
        rank = "Bronze"  # Default
        if total_profit > 10000 and win_rate > 80:
            rank = "Diamond"
        elif total_profit > 5000 and win_rate > 70:
            rank = "Platinum"
        elif total_profit > 2000 and win_rate > 60:
            rank = "Gold"
        elif total_profit > 500 and win_rate > 50:
            rank = "Silver"
        
        return {
            "totalTrades": total_trades,
            "winRate": win_rate,
            "totalProfit": round(total_profit, 2),
            "followers": followers_count,
            "following": following_count,
            "rank": rank,
            "level": current_user.level,
            "xp": current_user.xp_points,
            "nextLevelXp": current_user.level * 1000
        }
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user statistics")

def clear_all_api_key_cache():
    """Clear all cached API keys to force re-validation"""
    global user_api_keys, user_sessions
    
    old_api_count = len(user_api_keys)
    old_session_count = len(user_sessions)
    
    user_api_keys.clear()
    user_sessions.clear()
    
    logger.info(f"🔐 SECURITY: Cleared {old_api_count} cached API keys and {old_session_count} sessions - forcing re-validation")

def generate_unique_api_key(user_id: int, db: Session, max_attempts: int = 100) -> str:
    """Generate a unique, complex API key with collision detection"""
    import secrets
    import hashlib
    import time
    
    for attempt in range(max_attempts):
        # Create highly complex API key components
        timestamp = str(int(time.time() * 1000000))  # Microsecond precision
        user_salt = str(user_id).zfill(8)  # Pad user ID to 8 digits
        random_bytes = secrets.token_bytes(32)  # 32 bytes of cryptographic randomness
        
        # Create multiple hash components for complexity
        hash1 = hashlib.sha256(f"{user_id}:{timestamp}:{secrets.token_hex(16)}".encode()).hexdigest()[:12]
        hash2 = hashlib.blake2b(random_bytes, digest_size=16).hexdigest()[:16]
        hash3 = secrets.token_urlsafe(12).replace('-', '').replace('_', '')[:12]
        
        # Combine into complex API key format
        api_key = f"ca_{user_salt}_{hash1}_{hash2}_{hash3}_{timestamp[-8:]}"
        
        # Check for uniqueness in database
        existing_key = db.query(User).filter(User.api_key == api_key).first()
        if not existing_key:
            logger.info(f"🔐 Generated unique API key on attempt {attempt + 1} for user {user_id}")
            return api_key
        else:
            logger.warning(f"🚨 API key collision detected on attempt {attempt + 1} for user {user_id} - regenerating...")
    
    # If we get here, we couldn't generate a unique key after max attempts
    raise Exception(f"Failed to generate unique API key after {max_attempts} attempts")

@app.post("/api/user/regenerate-api-key")
async def regenerate_api_key(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Regenerate API key for security purposes with collision detection"""
    try:
        # Generate new secure API key with uniqueness guarantee
        new_api_key = generate_unique_api_key(current_user.id, db)
        
        # Remove old API key from cache if it exists
        if current_user.api_key and current_user.api_key in user_api_keys:
            del user_api_keys[current_user.api_key]
        
        # Update user's API key in database
        old_api_key = current_user.api_key
        current_user.api_key = new_api_key
        db.commit()
        db.refresh(current_user)  # Ensure database is updated
        
        # Cache the new API key
        user_api_keys[new_api_key] = current_user.id
        
        # Verify the key was saved correctly
        verification = db.query(User).filter(User.id == current_user.id).first()
        if verification.api_key != new_api_key:
            raise Exception("API key was not saved correctly to database")
        
        logger.info(f"🔐 SECURITY: User {current_user.username} (ID: {current_user.id}) regenerated API key")
        logger.info(f"🔐 Old key: {old_api_key[:20] if old_api_key else 'None'}...")
        logger.info(f"🔐 New key: {new_api_key[:20]}... (Length: {len(new_api_key)})")
        
        # Clear all caches to force re-validation everywhere
        clear_all_api_key_cache()
        
        return {
            "success": True,
            "message": "Secure API key regenerated successfully. Please update your EA with the new key.",
            "api_key": new_api_key,
            "key_info": {
                "length": len(new_api_key),
                "format": "ca_[user_id]_[hash1]_[hash2]_[hash3]_[timestamp]",
                "security_level": "Maximum"
            }
        }
        
    except Exception as e:
        logger.error(f"Error regenerating API key: {e}")
        raise HTTPException(status_code=500, detail="Failed to regenerate API key")

@app.post("/api/admin/clear-api-cache")
async def clear_api_cache():
    """Admin endpoint to clear all API key cache and force re-validation"""
    try:
        clear_all_api_key_cache()
        return {
            "success": True,
            "message": "All API key caches cleared - all connections will be re-validated"
        }
    except Exception as e:
        logger.error(f"Error clearing API cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear API cache")

@app.get("/api/marketplace/traders")
async def get_marketplace_traders(db: Session = Depends(get_db)):
    """Get all master traders for the marketplace with enhanced metrics"""
    try:
        # Get users who are master traders with their trading stats
        traders_query = db.query(User).filter(
            User.is_master_trader == True,
            User.is_active == True
        ).all()
        
        traders_data = []
        
        for trader in traders_query:
            # Get trader's trading statistics
            total_trades = db.query(Trade).filter(Trade.user_id == trader.id).count()
            closed_trades = db.query(Trade).filter(
                Trade.user_id == trader.id,
                Trade.status == 'closed'
            ).all()
            
            open_trades = db.query(Trade).filter(
                Trade.user_id == trader.id,
                Trade.status == 'open'
            ).all()
            
            # Calculate performance metrics
            total_profit = sum(trade.realized_profit or 0 for trade in closed_trades)
            winning_trades = [trade for trade in closed_trades if (trade.realized_profit or 0) > 0]
            losing_trades = [trade for trade in closed_trades if (trade.realized_profit or 0) < 0]
            win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0
            
            # Calculate additional performance metrics
            avg_win = sum(trade.realized_profit for trade in winning_trades) / len(winning_trades) if winning_trades else 0
            avg_loss = sum(abs(trade.realized_profit) for trade in losing_trades) / len(losing_trades) if losing_trades else 0
            profit_factor = (avg_win * len(winning_trades)) / (avg_loss * len(losing_trades)) if losing_trades else 10
            
            # Calculate drawdown (simplified)
            max_drawdown = 0
            if closed_trades:
                running_profit = 0
                peak_profit = 0
                for trade in sorted(closed_trades, key=lambda x: x.created_at):
                    running_profit += trade.realized_profit or 0
                    if running_profit > peak_profit:
                        peak_profit = running_profit
                    current_drawdown = (peak_profit - running_profit) / peak_profit * 100 if peak_profit > 0 else 0
                    max_drawdown = max(max_drawdown, current_drawdown)
            
            # Calculate recent performance (last 30 days)
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_trades = [trade for trade in closed_trades if trade.created_at >= thirty_days_ago]
            recent_profit = sum(trade.realized_profit or 0 for trade in recent_trades)
            
            # Get current open trades count
            open_trades_count = len(open_trades)
            
            # Calculate unrealized profit from open trades
            unrealized_profit = sum(trade.unrealized_profit or 0 for trade in open_trades)
            
            # Get account info if available
            mt5_connection = db.query(MT5Connection).filter(MT5Connection.user_id == trader.id).first()
            account_balance = mt5_connection.account_balance if mt5_connection else 1000
            
            # Calculate daily return based on recent performance
            daily_return = (recent_profit / account_balance) / 30 * 100 if account_balance > 0 else 0
            
            # Estimate follower count based on performance and trades
            base_followers = max(1, int(total_trades / 10))  # At least 1 follower per 10 trades
            performance_bonus = int(win_rate / 5) if win_rate > 50 else 0  # Bonus for good performance
            estimated_followers = min(base_followers + performance_bonus, 999)
            
            # Get real follower count from database
            follower_count = db.query(Follow).filter(
                Follow.following_id == trader.id,
                Follow.is_active == True
            ).count()
            
            # Calculate risk score (0-100, lower is safer)
            base_risk = max(10, min(90, 100 - win_rate))  # Base risk from win rate
            drawdown_risk = min(max_drawdown, 50)  # Cap drawdown impact
            risk_score = min(100, max(5, base_risk + (drawdown_risk / 2)))
            
            # Calculate Sharpe ratio (simplified)
            if closed_trades and avg_loss > 0:
                sharpe_ratio = (total_profit / len(closed_trades)) / avg_loss
            else:
                sharpe_ratio = 0
            
            # Check if trader is currently online (from WebSocket connections)
            is_online = trader.id in manager.active_connections
            
            traders_data.append({
                "id": trader.id,
                "username": trader.username,
                "level": trader.level,
                "xp_points": trader.xp_points,
                "subscription_plan": trader.subscription_plan,
                "is_online": is_online,
                "created_at": trader.created_at.isoformat() if trader.created_at else None,
                "stats": {
                    "total_trades": total_trades,
                    "closed_trades": len(closed_trades),
                    "open_trades": open_trades_count,
                    "total_profit": round(total_profit, 2),
                    "unrealized_profit": round(unrealized_profit, 2),
                    "win_rate": round(win_rate, 1),
                    "account_balance": round(account_balance, 2),
                    "recent_profit": round(recent_profit, 2),
                    "daily_return": round(daily_return, 3),
                    "avg_win": round(avg_win, 2),
                    "avg_loss": round(avg_loss, 2),
                },
                "performance": {
                    "profit_factor": round(profit_factor, 2),
                    "max_drawdown": round(max_drawdown, 2),
                    "sharpe_ratio": round(sharpe_ratio, 2),
                    "followers_count": follower_count,
                    "risk_score": round(risk_score, 1),
                    "win_streak": 0,  # TODO: Calculate actual win streak
                    "loss_streak": 0,  # TODO: Calculate actual loss streak
                    "monthly_return": round((recent_profit / account_balance) * 100, 2) if account_balance > 0 else 0,
                    "consistency_score": round(min(100, win_rate + (100 - max_drawdown)), 1)
                }
            })
        
        # Sort by total profit descending
        traders_data.sort(key=lambda x: x["stats"]["total_profit"], reverse=True)
        
        return {
            "traders": traders_data,
            "total_count": len(traders_data),
            "total_online": sum(1 for t in traders_data if t["is_online"]),
            "total_profit": sum(t["stats"]["total_profit"] for t in traders_data),
            "avg_win_rate": sum(t["stats"]["win_rate"] for t in traders_data) / len(traders_data) if traders_data else 0,
            "message": f"Found {len(traders_data)} master traders"
        }
        
    except Exception as e:
        logger.error(f"Error fetching marketplace traders: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch marketplace traders")


@app.post("/api/marketplace/follow/{trader_id}")
async def follow_trader(trader_id: int, request: Request, db: Session = Depends(get_db)):
    """Follow a master trader for copy trading"""
    try:
        # Get current user from session
        session_token = request.cookies.get("session_token")
        if not session_token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user = db.query(User).filter(User.session_token == session_token).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Check if trader exists and is a master trader
        trader = db.query(User).filter(
            User.id == trader_id,
            User.is_master_trader == True,
            User.is_active == True
        ).first()
        
        if not trader:
            raise HTTPException(status_code=404, detail="Master trader not found")
        
        # Can't follow yourself
        if user.id == trader_id:
            raise HTTPException(status_code=400, detail="Cannot follow yourself")
        
        # Check if already following
        existing_follow = db.query(Follow).filter(
            Follow.follower_id == user.id,
            Follow.following_id == trader_id
        ).first()
        
        if existing_follow:
            if existing_follow.is_active:
                raise HTTPException(status_code=400, detail="Already following this trader")
            else:
                # Reactivate existing follow
                existing_follow.is_active = True
                existing_follow.created_at = datetime.utcnow()
        else:
            # Create new follow
            new_follow = Follow(
                follower_id=user.id,
                following_id=trader_id,
                copy_percentage=100.0,
                max_risk_per_trade=2.0,
                is_active=True
            )
            db.add(new_follow)
        
        db.commit()
        
        # Get updated follower count
        follower_count = db.query(Follow).filter(
            Follow.following_id == trader_id,
            Follow.is_active == True
        ).count()
        
        return {
            "message": f"Successfully following {trader.username}",
            "following": True,
            "follower_count": follower_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error following trader {trader_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to follow trader")


@app.post("/api/marketplace/unfollow/{trader_id}")
async def unfollow_trader(trader_id: int, request: Request, db: Session = Depends(get_db)):
    """Unfollow a master trader"""
    try:
        # Get current user from session
        session_token = request.cookies.get("session_token")
        if not session_token:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        user = db.query(User).filter(User.session_token == session_token).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Check if following this trader
        follow = db.query(Follow).filter(
            Follow.follower_id == user.id,
            Follow.following_id == trader_id,
            Follow.is_active == True
        ).first()
        
        if not follow:
            raise HTTPException(status_code=400, detail="Not following this trader")
        
        # Deactivate follow instead of deleting (for history)
        follow.is_active = False
        db.commit()
        
        # Get updated follower count
        follower_count = db.query(Follow).filter(
            Follow.following_id == trader_id,
            Follow.is_active == True
        ).count()
        
        return {
            "message": "Successfully unfollowed trader",
            "following": False,
            "follower_count": follower_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unfollowing trader {trader_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to unfollow trader")


@app.get("/api/marketplace/following-status/{trader_id}")
async def get_following_status(trader_id: int, request: Request, db: Session = Depends(get_db)):
    """Check if current user is following a trader"""
    try:
        # Get current user from session
        session_token = request.cookies.get("session_token")
        if not session_token:
            return {"following": False, "authenticated": False}
        
        user = db.query(User).filter(User.session_token == session_token).first()
        if not user:
            return {"following": False, "authenticated": False}
        
        # Check if following
        follow = db.query(Follow).filter(
            Follow.follower_id == user.id,
            Follow.following_id == trader_id,
            Follow.is_active == True
        ).first()
        
        return {
            "following": bool(follow),
            "authenticated": True,
            "copy_percentage": follow.copy_percentage if follow else None,
            "max_risk_per_trade": follow.max_risk_per_trade if follow else None
        }
        
    except Exception as e:
        logger.error(f"Error checking following status for trader {trader_id}: {e}")
        return {"following": False, "authenticated": True}

@app.get("/api/mt5/status")
async def get_mt5_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get MT5 connection status"""
    connection = db.query(MT5Connection).filter(MT5Connection.user_id == user.id).first()
    return {
        "connected": connection.is_connected if connection else False,
        "is_connected": connection.is_connected if connection else False,  # Legacy support
        "account_number": connection.login if connection else None,
        "last_sync": connection.last_sync.isoformat() if connection and connection.last_sync else None,
        "message": "MT5 Connected" if (connection and connection.is_connected) else "MT5 Not Connected"
    }

@app.get("/api/client/download")
async def download_client(user: User = Depends(get_current_user)):
    """Download CopyArena Windows Client"""
    logger.info(f"User {user.username} ({user.email}) downloading Windows Client")
    # Look for the compiled executable
    client_paths = [
        Path(__file__).parent / "CopyArenaClient.exe",  # In backend directory (production)
        Path(__file__).parent / "windows_client" / "dist" / "CopyArenaClient.exe",
        Path(__file__).parent.parent / "windows_client" / "dist" / "CopyArenaClient.exe",
        Path("windows_client") / "dist" / "CopyArenaClient.exe"
    ]
    
    for client_path in client_paths:
        if client_path.exists():
            logger.info(f"Serving Windows Client from: {client_path}")
            return FileResponse(
                client_path,
                media_type="application/octet-stream",
                filename="CopyArenaClient.exe",
                headers={
                    "Content-Disposition": "attachment; filename=CopyArenaClient.exe",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
    
    # If executable not found, offer the Python script
    script_paths = [
        Path(__file__).parent / "windows_client" / "copyarena_client.py",
        Path(__file__).parent.parent / "windows_client" / "copyarena_client.py"
    ]
    
    for script_path in script_paths:
        if script_path.exists():
            return FileResponse(
                script_path,
                media_type="text/plain",
                filename="copyarena_client.py",
                headers={"Content-Disposition": "attachment; filename=copyarena_client.py"}
            )
    
    # Log the error for debugging
    logger.error(f"Windows Client executable not found. Searched paths: {[str(p) for p in client_paths]}")
    
    raise HTTPException(
        status_code=404, 
        detail="CopyArena Windows Client not found. Please contact support to get the latest client version."
    )

@app.get("/api/ea/download")
async def download_ea_deprecated(user: User = Depends(get_current_user)):
    """DEPRECATED: EA download - Use Windows Client instead"""
    logger.warning(f"🚨 User {user.username} attempted to download deprecated EA")
    raise HTTPException(
        status_code=410,
        detail="Expert Advisor is deprecated. Please download the new Windows Client from your profile."
    )

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

@app.get("/api/websocket/status")
async def get_websocket_status():
    """Get WebSocket connection status for admin panel"""
    try:
        # Get all active WebSocket connections from the manager
        # manager.active_connections is a Dict[int, Set[WebSocket]]
        online_users = list(manager.active_connections.keys())
        connection_count = sum(len(connections) for connections in manager.active_connections.values())
        
        return {
            "online_users": online_users,
            "connection_count": connection_count,
            "total_unique_users": len(online_users),
            "status": "ok"
        }
    except Exception as e:
        logger.error(f"Error getting WebSocket status: {e}")
        return {
            "online_users": [],
            "connection_count": 0,
            "total_unique_users": 0,
            "status": "error",
            "error": str(e)
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
        manager.disconnect(websocket)  # Pass websocket object, not user_id

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