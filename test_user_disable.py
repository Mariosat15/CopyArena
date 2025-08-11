#!/usr/bin/env python3
"""
Test script to temporarily disable a user to verify security works
"""

import sys
import os

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Set the correct database path
os.environ['DATABASE_URL'] = 'sqlite:///./backend/copyarena.db'

from models import SessionLocal, User

def disable_user_test():
    """Temporarily disable user 4 to test if EA stops working"""
    db = SessionLocal()
    
    print("🔧 User Account Disable Test")
    print("=" * 60)
    
    try:
        # Get user 4 (mariosat)
        user = db.query(User).filter(User.id == 4).first()
        
        if not user:
            print("❌ User 4 not found")
            return
            
        print(f"📊 User: {user.username} (ID: {user.id})")
        print(f"📊 Current status: {'Active' if user.is_active else 'Inactive'}")
        print(f"📊 API Key: {user.api_key[:20]}...")
        
        # Check current status and toggle
        if user.is_active:
            print(f"\n🔒 DISABLING user {user.username} to test security...")
            user.is_active = False
            action = "disabled"
        else:
            print(f"\n🔓 ENABLING user {user.username}...")
            user.is_active = True
            action = "enabled"
            
        db.commit()
        
        print(f"✅ User {user.username} has been {action}")
        print(f"\n📋 Expected behavior:")
        if not user.is_active:
            print("   - EA should be rejected with 401 error")
            print("   - No new MT5 data should appear in dashboard")
            print("   - User should appear offline")
        else:
            print("   - EA should work normally")
            print("   - MT5 data should flow to dashboard")
            print("   - User should appear online when EA connects")
            
        print(f"\n⚠️  Run this script again to toggle back!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()

if __name__ == "__main__":
    disable_user_test()
