from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./copyarena.db")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    subscription_plan = Column(String, default="free")
    credits = Column(Integer, default=5)
    xp_points = Column(Integer, default=0)
    level = Column(Integer, default=1)
    avatar_url = Column(String, default="")
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, default=datetime.utcnow)

class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    ticket = Column(String, index=True)
    symbol = Column(String)
    trade_type = Column(String)  # BUY or SELL
    volume = Column(Float)
    open_price = Column(Float)
    close_price = Column(Float, nullable=True)
    open_time = Column(DateTime)
    close_time = Column(DateTime, nullable=True)
    profit = Column(Float, default=0.0)
    is_open = Column(Boolean, default=True)

class Follow(Base):
    __tablename__ = "follows"
    
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"))
    trader_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    auto_copy = Column(Boolean, default=False)
    max_trade_size = Column(Float, default=0.01)
    risk_level = Column(Float, default=1.0)

class MT5Connection(Base):
    __tablename__ = "mt5_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    login = Column(Integer)
    server = Column(String)
    password_hash = Column(String)  # Encrypted MT5 password
    is_connected = Column(Boolean, default=False)
    last_sync = Column(DateTime, default=datetime.utcnow)
    connection_token = Column(String, unique=True)  # Unique token for this connection
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Badge(Base):
    __tablename__ = "badges"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    description = Column(Text)
    icon = Column(String)
    criteria = Column(Text)  # JSON string describing the criteria
    created_at = Column(DateTime, default=datetime.utcnow)

class UserBadge(Base):
    __tablename__ = "user_badges"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    badge_id = Column(Integer, ForeignKey("badges.id"))
    earned_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    badge = relationship("Badge")

# Create tables
Base.metadata.create_all(bind=engine)

# Helper functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 