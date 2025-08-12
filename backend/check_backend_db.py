#!/usr/bin/env python3
"""
Check users in the backend database and setup copy trading
"""

from models import SessionLocal, User, Follow

def check_and_setup():
    """Check backend database and setup copy trading"""
    db = SessionLocal()
    try:
        print("👥 CHECKING BACKEND DATABASE\n")
        
        all_users = db.query(User).all()
        print(f"📊 Total users: {len(all_users)}")
        
        master = None
        follower = None
        
        for user in all_users:
            master_status = "🎯 MASTER" if user.is_master_trader else "👤 REGULAR"
            print(f"  - ID: {user.id} | Username: {user.username} | Email: {user.email} | {master_status}")
            
            # Identify users based on backend logs
            if user.id == 9:  # mariosat2 from logs
                master = user
            elif user.id == 4:  # mariosat from logs
                follower = user
        
        if master and follower:
            print(f"\n🎯 SETTING UP COPY TRADING:")
            print(f"Master: {master.username} (ID: {master.id})")
            print(f"Follower: {follower.username} (ID: {follower.id})")
            
            # Ensure master is set as master trader
            if not master.is_master_trader:
                master.is_master_trader = True
                db.commit()
                print(f"✅ Set {master.username} as master trader")
            
            # Check/create follow relationship
            follow = db.query(Follow).filter(
                Follow.follower_id == follower.id,
                Follow.following_id == master.id
            ).first()
            
            if follow:
                if not follow.is_active:
                    follow.is_active = True
                    db.commit()
                    print(f"✅ Activated follow: {follower.username} -> {master.username}")
                else:
                    print(f"✅ Follow already active: {follower.username} -> {master.username}")
            else:
                # Create follow relationship
                new_follow = Follow(
                    follower_id=follower.id,
                    following_id=master.id,
                    is_active=True,
                    copy_percentage=100.0,
                    max_risk_per_trade=10.0
                )
                db.add(new_follow)
                db.commit()
                print(f"✅ Created follow: {follower.username} -> {master.username}")
                
            print(f"\n🚀 Copy trading is now ready!")
        else:
            print(f"❌ Cannot setup - Master: {master}, Follower: {follower}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    check_and_setup()
