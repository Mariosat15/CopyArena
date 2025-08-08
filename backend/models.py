from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./copyarena.db")

# SQLite specific configuration
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    api_key = Column(String, unique=True, index=True)  # For EA authentication
    subscription_plan = Column(String, default="free")  # free, pro, elite
    credits = Column(Integer, default=0)
    xp_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    is_online = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    trades = relationship("Trade", back_populates="user")
    mt5_connection = relationship("MT5Connection", back_populates="user", uselist=False)

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticket = Column(Integer, index=True)  # MT5 position/order ticket
    symbol = Column(String, nullable=False)
    trade_type = Column(String, nullable=False)  # buy, sell
    volume = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    current_price = Column(Float, default=0)
    close_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    unrealized_profit = Column(Float, default=0)  # For open positions
    realized_profit = Column(Float)  # For closed positions
    swap = Column(Float, default=0)
    commission = Column(Float, default=0)
    open_time = Column(DateTime, nullable=False)
    close_time = Column(DateTime)
    comment = Column(String)
    status = Column(String, default="open")  # open, closed, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
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

# Create tables
Base.metadata.create_all(bind=engine)

# Helper functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 