#!/usr/bin/env python3
"""Check trade statuses in database"""

import sys
sys.path.append('../backend')

from models import SessionLocal, Trade

def check_trades():
    db = SessionLocal()
    try:
        # Get status breakdown
        total_trades = db.query(Trade).count()
        open_trades = db.query(Trade).filter(Trade.status == 'open').count()
        closed_trades = db.query(Trade).filter(Trade.status == 'closed').count()
        
        print(f"=== TRADE STATUS BREAKDOWN ===")
        print(f"Total Trades: {total_trades}")
        print(f"Open Trades: {open_trades}")
        print(f"Closed Trades: {closed_trades}")
        print()
        
        # Show recent trades
        recent_trades = db.query(Trade).order_by(Trade.created_at.desc()).limit(10).all()
        
        print(f"=== RECENT 10 TRADES ===")
        for trade in recent_trades:
            status_icon = "🟢" if trade.status == 'open' else "🔴"
            print(f"{status_icon} ID: {trade.id} | Status: {trade.status} | Symbol: {trade.symbol} | Open: {trade.open_time} | Close: {trade.close_time}")
        
        # Check for any issues
        print(f"\n=== POTENTIAL ISSUES ===")
        
        # Trades with no close_time but status = closed
        bad_closed = db.query(Trade).filter(Trade.status == 'closed', Trade.close_time == None).count()
        print(f"Closed trades with no close_time: {bad_closed}")
        
        # Trades with close_time but status = open  
        bad_open = db.query(Trade).filter(Trade.status == 'open', Trade.close_time != None).count()
        print(f"Open trades with close_time: {bad_open}")
        
        # Check open trades
        if open_trades > 0:
            print(f"\n=== OPEN TRADES DETAILS ===")
            open_trade_list = db.query(Trade).filter(Trade.status == 'open').limit(5).all()
            for trade in open_trade_list:
                print(f"   Open Trade: {trade.symbol} | Ticket: {trade.ticket} | Open: {trade.open_time} | P&L: {trade.unrealized_profit}")
        
    finally:
        db.close()

if __name__ == "__main__":
    check_trades() 