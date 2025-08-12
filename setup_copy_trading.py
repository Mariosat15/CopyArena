#!/usr/bin/env python3
"""
Setup script to ensure copy trading is properly configured
"""

import sys
import os

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from models import SessionLocal, User, Follow

def setup_copy_trading():
    """Ensure copy trading relationships are properly set up"""
    db = SessionLocal()
    try:
        print("🔧 SETTING UP COPY TRADING SYSTEM\n")
        
        # 1. Ensure mariosat2 is a master trader
        master = db.query(User).filter(User.username == "mariosat2").first()
        if master:
            if not master.is_master_trader:
                master.is_master_trader = True
                db.commit()
                print(f"✅ Set {master.username} as master trader")
            else:
                print(f"✅ {master.username} is already a master trader")
        else:
            print("❌ Master trader 'mariosat2' not found")
            return
        
        # 2. Ensure mariosat follows mariosat2
        follower = db.query(User).filter(User.username == "mariosat").first()
        if follower:
            print(f"✅ Found follower: {follower.username}")
        else:
            print("❌ Follower 'mariosat' not found")
            return
        
        # 3. Check/Create follow relationship
        follow = db.query(Follow).filter(
            Follow.follower_id == follower.id,
            Follow.following_id == master.id
        ).first()
        
        if follow:
            if not follow.is_active:
                follow.is_active = True
                db.commit()
                print(f"✅ Activated follow relationship: {follower.username} -> {master.username}")
            else:
                print(f"✅ Follow relationship already active: {follower.username} -> {master.username}")
        else:
            # Create new follow relationship
            new_follow = Follow(
                follower_id=follower.id,
                following_id=master.id,
                is_active=True,
                copy_percentage=100.0,
                max_risk_per_trade=10.0
            )
            db.add(new_follow)
            db.commit()
            print(f"✅ Created follow relationship: {follower.username} -> {master.username}")
        
        # 4. Display final status
        print(f"\n📊 COPY TRADING STATUS:")
        print(f"Master: {master.username} (ID: {master.id}) - Master Trader: {master.is_master_trader}")
        print(f"Follower: {follower.username} (ID: {follower.id})")
        
        active_follows = db.query(Follow).filter(
            Follow.following_id == master.id,
            Follow.is_active == True
        ).count()
        print(f"Active followers of {master.username}: {active_follows}")
        
        print(f"\n🎯 Copy trading is ready!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_copy_trading()
