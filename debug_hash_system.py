#!/usr/bin/env python3
"""
Debug script to check hash generation and copy trade system
"""

import sys
import os

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from models import SessionLocal, CopyTrade, Follow, User, Trade
from sqlalchemy import desc

def debug_hash_system():
    """Debug the hash generation system"""
    db = SessionLocal()
    try:
        print("🔍 DEBUGGING HASH SYSTEM\n")
        
        # 1. Check copy trades with and without hashes
        print("1️⃣ COPY TRADES ANALYSIS:")
        all_copy_trades = db.query(CopyTrade).order_by(desc(CopyTrade.created_at)).limit(10).all()
        
        print(f"📊 Total recent copy trades: {len(all_copy_trades)}")
        
        for ct in all_copy_trades:
            hash_status = "✅ HAS HASH" if ct.copy_hash else "❌ NO HASH"
            print(f"  - ID: {ct.id} | Status: {ct.status} | Master Ticket: {ct.master_ticket} | {hash_status}")
            if ct.copy_hash:
                print(f"    Hash: {ct.copy_hash[:16]}...")
            print(f"    Created: {ct.created_at}")
        
        # 2. Check follow relationships
        print(f"\n2️⃣ FOLLOW RELATIONSHIPS:")
        follows = db.query(Follow).filter(Follow.is_active == True).all()
        
        for follow in follows:
            follower = db.query(User).filter(User.id == follow.follower_id).first()
            master = db.query(User).filter(User.id == follow.following_id).first()
            
            print(f"  - {follower.username if follower else 'Unknown'} follows {master.username if master else 'Unknown'}")
            print(f"    Follow ID: {follow.id} | Active: {follow.is_active}")
        
        # 3. Check recent master trades
        print(f"\n3️⃣ RECENT MASTER TRADES:")
        master_users = db.query(User).filter(User.is_master_trader == True).all()
        
        for master in master_users:
            recent_trades = db.query(Trade).filter(
                Trade.user_id == master.id,
                Trade.status == "open"
            ).order_by(desc(Trade.open_time)).limit(3).all()
            
            print(f"  - Master: {master.username} | Open trades: {len(recent_trades)}")
            for trade in recent_trades:
                print(f"    Ticket: {trade.ticket} | Symbol: {trade.symbol} | Type: {trade.trade_type}")
        
        # 4. Test hash generation function
        print(f"\n4️⃣ HASH GENERATION TEST:")
        # Import hash function
        sys.path.append('backend')
        from app import generate_copy_hash
        
        test_hash = generate_copy_hash("mariosat2", "11046500", "2025-01-09T11:11:48")
        print(f"Test hash: {test_hash[:16]}...")
        print(f"Full hash: {test_hash}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_hash_system()
