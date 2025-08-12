#!/usr/bin/env python3
"""
Check the actual database state - users, follows, master status
"""

import sys
import os

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from models import SessionLocal, User, Follow

def check_database_state():
    """Check users and their relationships"""
    db = SessionLocal()
    try:
        print("🔍 DATABASE STATE CHECK\n")
        
        # 1. Check all users
        print("1️⃣ ALL USERS:")
        users = db.query(User).all()
        
        for user in users:
            master_status = "🎯 MASTER" if user.is_master_trader else "👤 Regular"
            print(f"  - ID: {user.id} | Username: {user.username} | Email: {user.email} | {master_status}")
        
        # 2. Check all follow relationships (active and inactive)
        print(f"\n2️⃣ ALL FOLLOW RELATIONSHIPS:")
        follows = db.query(Follow).all()
        
        print(f"📊 Total follows: {len(follows)}")
        
        for follow in follows:
            follower = db.query(User).filter(User.id == follow.follower_id).first()
            master = db.query(User).filter(User.id == follow.following_id).first()
            
            status = "✅ ACTIVE" if follow.is_active else "❌ INACTIVE"
            follower_name = follower.username if follower else f"Unknown({follow.follower_id})"
            master_name = master.username if master else f"Unknown({follow.following_id})"
            
            print(f"  - {follower_name} → {master_name} | {status}")
            print(f"    Follow ID: {follow.id} | Created: {follow.created_at}")
        
        # 3. Check specific users mentioned in logs
        print(f"\n3️⃣ SPECIFIC USERS CHECK:")
        target_users = ["mariosat", "mariosat2"]
        
        for username in target_users:
            user = db.query(User).filter(User.username == username).first()
            if user:
                master_status = "🎯 MASTER" if user.is_master_trader else "👤 Regular"
                print(f"  - {username}: EXISTS | ID: {user.id} | {master_status}")
            else:
                print(f"  - {username}: ❌ NOT FOUND")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_database_state()
