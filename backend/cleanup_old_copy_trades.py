#!/usr/bin/env python3
"""
Clean up old copy trade records causing wrong close commands
"""

from models import SessionLocal, CopyTrade
from datetime import datetime, timedelta

def cleanup_old_copy_trades():
    """Remove old copy trade records without hashes"""
    db = SessionLocal()
    try:
        print("🧹 CLEANING UP OLD COPY TRADES\n")
        
        # Find all old copy trades (especially those without hashes)
        all_copy_trades = db.query(CopyTrade).all()
        print(f"📊 Total copy trades before cleanup: {len(all_copy_trades)}")
        
        # Remove copy trades without hashes or very old ones
        cleanup_count = 0
        for ct in all_copy_trades:
            should_remove = False
            reason = ""
            
            # Remove if no hash (old system)
            if not ct.copy_hash:
                should_remove = True
                reason = "No hash (old system)"
            
            # Remove if very old and stuck in executed state
            elif ct.status == "executed" and ct.executed_at:
                age = datetime.utcnow() - ct.executed_at
                if age > timedelta(hours=1):
                    should_remove = True
                    reason = f"Old executed trade ({age})"
            
            if should_remove:
                print(f"  🗑️ Removing: ID {ct.id} | Status: {ct.status} | Ticket: {ct.master_ticket} | Reason: {reason}")
                db.delete(ct)
                cleanup_count += 1
        
        if cleanup_count > 0:
            db.commit()
            print(f"\n✅ Cleaned up {cleanup_count} old copy trades")
        else:
            print(f"\n✅ No cleanup needed")
        
        # Show remaining copy trades
        remaining = db.query(CopyTrade).all()
        print(f"📊 Total copy trades after cleanup: {len(remaining)}")
        
        for ct in remaining:
            hash_status = "✅ HAS HASH" if ct.copy_hash else "❌ NO HASH"
            print(f"  - ID: {ct.id} | Status: {ct.status} | Ticket: {ct.master_ticket} | {hash_status}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_old_copy_trades()
