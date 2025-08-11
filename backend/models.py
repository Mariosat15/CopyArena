from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import bcrypt
import os

# Configuration with security and performance optimizations
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./copyarena.db")

# Professional SQLite configuration with security enhancements
if DATABASE_URL.startswith("sqlite"):
    # Extract the database path for logging
    db_path = DATABASE_URL.replace("sqlite:///", "")
    
    # Production-grade SQLite engine with security features
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,  # 30 second timeout for busy database
        },
        # Connection pooling for better performance
        pool_size=10,           # Maintain 10 connections
        max_overflow=20,        # Allow 20 additional connections under load
        pool_pre_ping=True,     # Verify connections before use
        pool_recycle=3600,      # Refresh connections every hour
        # Security and debugging
        echo=False,             # Disable SQL logging in production
        echo_pool=False,        # Disable connection pool logging
    )
    
    # Configure SQLite security and performance pragmas
    from sqlalchemy import event
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        
        # === SECURITY PRAGMAS ===
        # Enable foreign key constraints (data integrity)
        cursor.execute("PRAGMA foreign_keys=ON")
        
        # Secure delete - overwrite deleted data (prevents data recovery)
        cursor.execute("PRAGMA secure_delete=ON")
        
        # === PERFORMANCE PRAGMAS ===
        # Enable WAL mode for better concurrency and crash recovery
        cursor.execute("PRAGMA journal_mode=WAL")
        
        # Set cache size to 64MB for better performance
        cursor.execute("PRAGMA cache_size=-64000")
        
        # Optimize synchronization (faster but still safe)
        cursor.execute("PRAGMA synchronous=NORMAL")
        
        # Use memory for temporary data (faster operations)
        cursor.execute("PRAGMA temp_store=MEMORY")
        
        # Enable memory mapping for large databases (1GB)
        cursor.execute("PRAGMA mmap_size=1073741824")
        
        # Optimize page size for better I/O
        cursor.execute("PRAGMA page_size=4096")
        
        # Enable automatic VACUUM for space management
        cursor.execute("PRAGMA auto_vacuum=INCREMENTAL")
        
        cursor.close()
    
    print(f"Professional SQLite: {db_path}")
    print("Security features enabled (secure_delete, foreign_keys)")
    print("Performance optimized (WAL mode, 64MB cache, connection pooling)")
    
elif DATABASE_URL.startswith("postgresql"):
    # PostgreSQL configuration for future scaling
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False
    )
    print("PostgreSQL database connected with professional configuration")
    
else:
    # Fallback for other database types
    engine = create_engine(DATABASE_URL)
    print(f"🔧 Database: {DATABASE_URL.split('://')[0]}")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def hash_password(password: str) -> str:
    """Hash a password using bcrypt with professional-grade security"""
    # Use high cost factor for better security (12 rounds = ~250ms)
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def generate_secure_api_key() -> str:
    """Generate a cryptographically secure API key"""
    import secrets
    import string
    # Generate 32 character secure random string
    alphabet = string.ascii_letters + string.digits
    api_key = ''.join(secrets.choice(alphabet) for _ in range(32))
    return f"ca_{api_key}"

def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets security requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    return True, "Password meets security requirements"

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    api_key = Column(String(100), unique=True, index=True)  # For EA authentication
    
    # Account security and status
    is_active = Column(Boolean, default=True)           # Account active/suspended
    is_verified = Column(Boolean, default=False)        # Email verified
    failed_login_attempts = Column(Integer, default=0)  # Security tracking
    last_login_ip = Column(String(45))                  # IPv4/IPv6 support
    
    # Subscription and gamification
    subscription_plan = Column(String(20), default="free")  # free, pro, elite
    credits = Column(Integer, default=0)
    xp_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    is_online = Column(Boolean, default=False)
    is_master_trader = Column(Boolean, default=False)  # Allow others to copy trades
    
    # Audit fields - professional tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    mt5_connection = relationship("MT5Connection", back_populates="user", uselist=False, cascade="all, delete-orphan")
    followers = relationship("Follow", foreign_keys="Follow.following_id", back_populates="following", cascade="all, delete-orphan")
    following = relationship("Follow", foreign_keys="Follow.follower_id", back_populates="follower", cascade="all, delete-orphan")

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ticket = Column(String(50), nullable=False, index=True)  # MT5 position/order ticket (string for large numbers)
    
    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    trade_type = Column(String(10), nullable=False)  # buy, sell
    volume = Column(Float, nullable=False)
    
    # Price information with better precision
    open_price = Column(Float, nullable=False)
    current_price = Column(Float, default=0)
    close_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    
    # Profit and loss tracking
    unrealized_profit = Column(Float, default=0)  # For open positions
    realized_profit = Column(Float)               # For closed positions
    swap = Column(Float, default=0)
    commission = Column(Float, default=0)
    
    # Timing information
    open_time = Column(DateTime, nullable=False, index=True)
    close_time = Column(DateTime, index=True)
    
    # Metadata
    comment = Column(String(255))
    status = Column(String(20), default="open", nullable=False, index=True)  # open, closed, cancelled
    magic_number = Column(Integer)  # EA magic number for trade identification
    
    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="trades")

class MT5Connection(Base):
    __tablename__ = "mt5_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    login = Column(Integer)  # MT5 account number
    server = Column(String)
    is_connected = Column(Boolean, default=False)
    
    # Account information from EA
    account_balance = Column(Float, default=0)
    account_equity = Column(Float, default=0)
    account_margin = Column(Float, default=0)
    account_free_margin = Column(Float, default=0)
    account_margin_level = Column(Float, default=0)
    account_currency = Column(String, default="USD")
    account_leverage = Column(Integer, default=1)
    
    last_sync = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="mt5_connection")

class Leaderboard(Base):
    __tablename__ = "leaderboard"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_profit = Column(Float, default=0)
    win_rate = Column(Float, default=0)
    total_trades = Column(Integer, default=0)
    followers = Column(Integer, default=0)
    rank = Column(Integer)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Badge(Base):
    __tablename__ = "badges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    icon = Column(String)
    criteria = Column(Text)  # JSON string describing earning criteria
    created_at = Column(DateTime, default=datetime.utcnow)

class UserBadge(Base):
    __tablename__ = "user_badges"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=False)
    earned_at = Column(DateTime, default=datetime.utcnow)

class Achievement(Base):
    __tablename__ = "achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    category = Column(String)  # trading, social, milestone
    xp_reward = Column(Integer, default=0)
    credit_reward = Column(Integer, default=0)
    criteria = Column(Text)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow)

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    achievement_id = Column(Integer, ForeignKey("achievements.id"), nullable=False)
    progress = Column(Float, default=0)  # 0-100 percentage
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Follow(Base):
    __tablename__ = "follows"
    
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    following_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Follow settings
    copy_percentage = Column(Float, default=100.0)  # What % of trades to copy
    max_risk_per_trade = Column(Float, default=2.0)  # Max % of account per trade
    is_active = Column(Boolean, default=True)
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_copied_trade = Column(DateTime)
    total_copied_trades = Column(Integer, default=0)
    total_profit_from_copying = Column(Float, default=0.0)
    
    # Relationships
    follower = relationship("User", foreign_keys=[follower_id], back_populates="following")
    following = relationship("User", foreign_keys=[following_id], back_populates="followers")
    
    # Unique constraint - can't follow same person twice
    __table_args__ = (UniqueConstraint('follower_id', 'following_id', name='unique_follow'),)


# Database is ready for use 