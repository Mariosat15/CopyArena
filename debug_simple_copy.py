#!/usr/bin/env python3
"""
Simple debugging script to check the current state of copy trading
"""
import sqlite3
from datetime import datetime

# Connect to database
db_path = "backend/copyarena.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("=== CURRENT COPY TRADING STATE ===\n")

# Check users
cursor.execute("SELECT id, username, is_master_trader FROM users WHERE username IN ('mariosat', 'mariosat2')")
users = cursor.fetchall()
print("Users:")
for user in users:
    print(f"  {user[1]} (ID: {user[0]}) - Master: {bool(user[2])}")

# Check follow relationships
cursor.execute("""
    SELECT f.id, u1.username as follower, u2.username as master 
    FROM follows f
    JOIN users u1 ON f.follower_id = u1.id
    JOIN users u2 ON f.following_id = u2.id
    WHERE u1.username = 'mariosat' AND u2.username = 'mariosat2'
""")
follows = cursor.fetchall()
print(f"\nFollow relationships: {len(follows)}")
for follow in follows:
    print(f"  {follow[1]} follows {follow[2]} (Follow ID: {follow[0]})")

# Check open trades for each user
for user in users:
    user_id, username = user[0], user[1]
    cursor.execute("SELECT id, ticket, symbol, status FROM trades WHERE user_id = ? AND status = 'open'", (user_id,))
    trades = cursor.fetchall()
    print(f"\n{username} open trades: {len(trades)}")
    for trade in trades:
        print(f"  Trade {trade[0]}: Ticket {trade[1]}, {trade[2]}, Status: {trade[3]}")

# Check copy trades
cursor.execute("""
    SELECT ct.id, ct.master_ticket, ct.follower_ticket, ct.status, ct.copy_hash,
           u1.username as master, u2.username as follower,
           t1.status as master_trade_status, t2.status as follower_trade_status
    FROM copy_trades ct
    JOIN follows f ON ct.follow_id = f.id
    JOIN users u1 ON f.following_id = u1.id
    JOIN users u2 ON f.follower_id = u2.id
    LEFT JOIN trades t1 ON ct.master_trade_id = t1.id
    LEFT JOIN trades t2 ON ct.follower_trade_id = t2.id
    WHERE u1.username = 'mariosat2' AND u2.username = 'mariosat'
    ORDER BY ct.id DESC
    LIMIT 10
""")
copy_trades = cursor.fetchall()
print(f"\nCopy trades (last 10): {len(copy_trades)}")
for ct in copy_trades:
    print(f"  ID {ct[0]}: Master {ct[1]} -> Follower {ct[2]} | Status: {ct[3]} | Hash: {ct[4][:16] if ct[4] else None}")
    print(f"    Master trade: {ct[7] or 'None'} | Follower trade: {ct[8] or 'None'}")

# Check what SHOULD be closed when master closes all
print(f"\n=== WHAT SHOULD BE CLOSED ===")
cursor.execute("""
    SELECT ct.id, ct.master_ticket, ct.follower_ticket, ct.copy_hash,
           t2.ticket as actual_follower_ticket, t2.status as follower_status
    FROM copy_trades ct
    JOIN follows f ON ct.follow_id = f.id
    JOIN users u1 ON f.following_id = u1.id
    JOIN users u2 ON f.follower_id = u2.id
    LEFT JOIN trades t2 ON ct.follower_trade_id = t2.id
    WHERE u1.username = 'mariosat2' AND u2.username = 'mariosat'
      AND ct.status = 'executed'
      AND t2.status = 'open'
""")
should_close = cursor.fetchall()
print(f"Copy trades that SHOULD get close commands: {len(should_close)}")
for ct in should_close:
    print(f"  CopyTrade {ct[0]}: Master {ct[1]} -> Follower {ct[2]} | Actual: {ct[4]} | Status: {ct[5]}")
    print(f"    Hash: {ct[3][:16] if ct[3] else 'MISSING'}")

conn.close()
