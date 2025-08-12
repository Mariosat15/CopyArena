#!/usr/bin/env python3
"""
Check what users exist in the database
"""

import sys
import os

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from models import SessionLocal, User, Follow

def check_users():
    """Check all users in the database"""
    db = SessionLocal()
    try:
        print("👥 CHECKING USERS IN DATABASE\n")
        
        all_users = db.query(User).all()
        print(f"📊 Total users: {len(all_users)}")
        
        for user in all_users:
            master_status = "🎯 MASTER" if user.is_master_trader else "👤 REGULAR"
            print(f"  - ID: {user.id} | Username: {user.username} | Email: {user.email} | {master_status}")
        
        if len(all_users) == 0:
            print("❌ No users found in database!")
        
        # Check follows
        all_follows = db.query(Follow).all()
        print(f"\n📈 Total follow relationships: {len(all_follows)}")
        
        for follow in all_follows:
            status = "✅ ACTIVE" if follow.is_active else "❌ INACTIVE"
            print(f"  - Follower ID: {follow.follower_id} -> Following ID: {follow.following_id} | {status}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_users()
