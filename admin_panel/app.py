#!/usr/bin/env python3
"""
CopyArena Admin Panel
Professional database management, security monitoring, and user administration
"""

import os
import sys
import sqlite3
import json
import threading
import schedule
import time
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session, send_file
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

# Add backend to path for imports
sys.path.append('../backend')

# Set correct database path
backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
db_path = os.path.join(backend_dir, 'copyarena.db')
os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'

from models import SessionLocal, User, Trade, MT5Connection, engine
from database_security import DatabaseSecurity
from sqlalchemy import func
from models import Follow

app = Flask(__name__)
app.secret_key = 'admin_panel_secret_key_change_in_production'
auth = HTTPBasicAuth()

# Admin credentials (change these!)
ADMIN_USERS = {
    'admin': generate_password_hash('admin123'),  # Change this password!
    'copyarena': generate_password_hash('copyarena2025')  # And this one!
}

# Initialize security manager
security_manager = DatabaseSecurity(db_path)

def get_live_online_users():
    """Get actually online users by checking backend WebSocket connections"""
    try:
        # Check backend for active WebSocket connections
        response = requests.get('http://localhost:8002/api/websocket/status', timeout=2)
        if response.status_code == 200:
            data = response.json()
            return data.get('online_users', [])
    except:
        pass
    return []

@auth.verify_password
def verify_password(username, password):
    if username in ADMIN_USERS and check_password_hash(ADMIN_USERS.get(username), password):
        session['admin_user'] = username
        return username

@app.route('/')
@app.route('/dashboard')
@auth.login_required
def dashboard():
    """Main admin dashboard"""
    db = SessionLocal()
    try:
        # Basic stats
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.is_active == True).count()
        master_traders = db.query(User).filter(User.is_master_trader == True).count()
        total_trades = db.query(Trade).count()
        open_trades = db.query(Trade).filter(Trade.status == 'open').count()
        total_profit = db.query(func.sum(Trade.realized_profit)).scalar() or 0
        
        print(f"DEBUG: Found {total_users} users, {total_trades} trades")
        
        # Get actually online users from WebSocket connections
        online_user_ids = get_live_online_users()
        print(f"DEBUG: Online users from WebSocket: {online_user_ids}")
        
        # Get follower statistics (SQLite compatible)
        total_follows = db.query(Follow).filter(Follow.is_active == True).count()
        
        # Count unique followers (SQLite compatible way)
        active_followers = db.query(Follow.follower_id).filter(Follow.is_active == True).distinct().count()
        active_leaders = db.query(Follow.following_id).filter(Follow.is_active == True).distinct().count()
        
        # Get master traders count
        master_traders = db.query(User).filter(User.is_master_trader == True).count()
        
        # Get top traders for display
        top_traders_query = db.query(User).filter(User.is_master_trader == True).limit(5).all()
        top_traders_query = db.query(User).filter(User.is_master_trader == True).limit(5).all()
        top_traders = []
        for user in top_traders_query:
            try:
                total_profit = db.query(func.sum(Trade.realized_profit)).filter(Trade.user_id == user.id).scalar() or 0
                follower_count = db.query(Follow).filter(Follow.following_id == user.id, Follow.is_active == True).count()
                trade_count = db.query(Trade).filter(Trade.user_id == user.id).count()
                open_trades = db.query(Trade).filter(Trade.user_id == user.id, Trade.status == 'open').count()
                user.is_online = user.id in online_user_ids  # Update with real status
                top_traders.append({
                    'user': user,
                    'total_profit': total_profit,
                    'follower_count': follower_count,
                    'trade_count': trade_count,
                    'open_trades': open_trades
                })
            except Exception as e:
                print(f"DEBUG: Error processing top trader {user.id}: {e}")
        
        stats = {
            'users': {
                'total': total_users,
                'online': len(online_user_ids),
                'offline': total_users - len(online_user_ids),
                'master_traders': master_traders,
                'active_followers': active_followers,
                'active_leaders': active_leaders
            },
            'trades': {
                'total': total_trades,
                'open': open_trades,
                'closed': total_trades - open_trades
            },
            'follows': {
                'total': total_follows,
                'active_followers': active_followers,
                'active_leaders': active_leaders
            },
            'security': security_manager.check_security_status()
        }
        
        # System information
        system_info = {
            'database_path': db_path,
            'last_backup': None  # Will be updated with actual backup info
        }
        
        return render_template('dashboard.html', 
                             stats=stats, 
                             top_traders=top_traders,
                             system_info=system_info)
    except Exception as e:
        print(f"ERROR in dashboard: {e}")
        import traceback
        traceback.print_exc()
        return f"Error loading dashboard: {e}", 500
    finally:
        db.close()

@app.route('/users')
@auth.login_required
def users():
    """User management page"""
    db = SessionLocal()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        users_query = db.query(User).order_by(User.created_at.desc())
        total = users_query.count()
        users_list = users_query.offset((page - 1) * per_page).limit(per_page).all()
        
        print(f"DEBUG: Found {total} total users, showing {len(users_list)} on this page")
        
        # Get actually online users from WebSocket connections
        online_user_ids = get_live_online_users()
        print(f"DEBUG: Online users from WebSocket: {online_user_ids}")
        
        # Get follower statistics
        total_follows = db.query(Follow).filter(Follow.is_active == True).count()
        active_followers = len(set(follow.follower_id for follow in db.query(Follow).filter(Follow.is_active == True).all()))
        active_leaders = len(set(follow.following_id for follow in db.query(Follow).filter(Follow.is_active == True).all()))
        
        # Get master traders count
        master_traders = db.query(User).filter(User.is_master_trader == True).count()
        
        # Add trade statistics for each user
        users_data = []
        for user in users_list:
            try:
                trade_count = db.query(Trade).filter(Trade.user_id == user.id).count()
                open_trades = db.query(Trade).filter(Trade.user_id == user.id, Trade.status == 'open').count()
                total_profit = db.query(func.sum(Trade.realized_profit)).filter(Trade.user_id == user.id).scalar() or 0
                
                # Get follower count (investors following this user)
                follower_count = db.query(Follow).filter(
                    Follow.following_id == user.id,
                    Follow.is_active == True
                ).count()
                
                # Get following count (users this user is following)
                following_count = db.query(Follow).filter(
                    Follow.follower_id == user.id,
                    Follow.is_active == True
                ).count()
                
                # Override is_online with real WebSocket status
                user.is_online = user.id in online_user_ids
                
                users_data.append({
                    'user': user,
                    'trade_count': trade_count,
                    'open_trades': open_trades,
                    'total_profit': total_profit,
                    'follower_count': follower_count,
                    'following_count': following_count
                })
            except Exception as e:
                print(f"DEBUG: Error processing user {user.id}: {e}")
                # Override is_online with real WebSocket status
                user.is_online = user.id in online_user_ids
                users_data.append({
                    'user': user,
                    'trade_count': 0,
                    'open_trades': 0,
                    'total_profit': 0,
                    'follower_count': 0,
                    'following_count': 0
                })
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
        
        return render_template('users.html', users=users_data, pagination=pagination)
    except Exception as e:
        print(f"ERROR in users: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}", 500
    finally:
        db.close()

@app.route('/trades')
@auth.login_required
def trades():
    """Trade monitoring page"""
    db = SessionLocal()
    try:
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', 'all')
        per_page = 50
        
        trades_query = db.query(Trade).join(User)
        
        if status_filter != 'all':
            trades_query = trades_query.filter(Trade.status == status_filter)
        
        trades_query = trades_query.order_by(Trade.created_at.desc())
        total = trades_query.count()
        trades_list = trades_query.offset((page - 1) * per_page).limit(per_page).all()
        
        print(f"DEBUG: Found {total} trades with filter '{status_filter}', showing {len(trades_list)} on this page")
        
        # Debug: Show status breakdown
        open_count = db.query(Trade).filter(Trade.status == 'open').count()
        closed_count = db.query(Trade).filter(Trade.status == 'closed').count()
        print(f"DEBUG: Status breakdown - Open: {open_count}, Closed: {closed_count}")
        
        # Debug: Show first few trades
        for i, trade in enumerate(trades_list[:3]):
            print(f"DEBUG: Trade {i+1}: ID={trade.id}, Status='{trade.status}', Symbol={trade.symbol}, Open={trade.open_time}, Close={trade.close_time}")
        
        pagination = {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
        
        return render_template('trades.html', trades=trades_list, pagination=pagination, status_filter=status_filter)
    except Exception as e:
        print(f"ERROR in trades: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}", 500
    finally:
        db.close()

@app.route('/security')
@auth.login_required
def security():
    """Security monitoring and management"""
    security_report = security_manager.generate_security_report()
    security_status = security_manager.check_security_status()
    
    # Get recent security logs
    security_logs = []
    if os.path.exists('../backend/security.log'):
        with open('../backend/security.log', 'r') as f:
            lines = f.readlines()
            security_logs = lines[-50:]  # Last 50 log entries
    
    return render_template('security.html', 
                         report=security_report, 
                         status=security_status, 
                         logs=security_logs)

@app.route('/backups')
@auth.login_required
def backups():
    """Backup management page"""
    backup_dir = '../backend/backups'
    backups_list = []
    
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if file.endswith('.db') or file.endswith('.zip'):
                file_path = os.path.join(backup_dir, file)
                file_stat = os.stat(file_path)
                backups_list.append({
                    'name': file,
                    'size': file_stat.st_size,
                    'created': datetime.fromtimestamp(file_stat.st_ctime),
                    'modified': datetime.fromtimestamp(file_stat.st_mtime)
                })
    
    backups_list.sort(key=lambda x: x['created'], reverse=True)
    
    return render_template('backups.html', backups=backups_list)

@app.route('/api/create_backup', methods=['POST'])
@auth.login_required
def create_backup():
    """API endpoint to create a backup"""
    try:
        backup_info = security_manager.create_secure_backup()
        if backup_info:
            return jsonify({'success': True, 'backup': backup_info})
        else:
            return jsonify({'success': False, 'error': 'Backup creation failed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download_backup/<filename>')
@auth.login_required
def download_backup(filename):
    """Download a backup file"""
    try:
        backup_path = os.path.join('../backend/backups', filename)
        if os.path.exists(backup_path):
            return send_file(backup_path, as_attachment=True, download_name=filename)
        else:
            return jsonify({'success': False, 'error': 'Backup file not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/delete_backup/<filename>', methods=['DELETE'])
@auth.login_required
def delete_backup(filename):
    """Delete a backup file"""
    try:
        backup_path = os.path.join('../backend/backups', filename)
        if os.path.exists(backup_path):
            os.remove(backup_path)
            # Also remove metadata file if it exists
            meta_path = backup_path + '.meta'
            if os.path.exists(meta_path):
                os.remove(meta_path)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Backup file not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/user/<int:user_id>/toggle_active', methods=['POST'])
@auth.login_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.is_active = not user.is_active
            db.commit()
            return jsonify({'success': True, 'is_active': user.is_active})
        return jsonify({'success': False, 'error': 'User not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        db.close()

@app.route('/api/integrity_check', methods=['POST'])
@auth.login_required
def integrity_check():
    """Run database integrity check"""
    try:
        result = security_manager.verify_database_integrity()
        return jsonify({'success': True, 'integrity_ok': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stats')
@auth.login_required
def api_stats():
    """API endpoint for real-time statistics"""
    db = SessionLocal()
    try:
        # Get real online users from WebSocket connections
        online_user_ids = get_live_online_users()
        
        stats = {
            'users': {
                'total': db.query(User).count(),
                'active': db.query(User).filter(User.is_active == True).count(),
                'online': len(online_user_ids),  # Use real WebSocket connections
            },
            'trades': {
                'total': db.query(Trade).count(),
                'open': db.query(Trade).filter(Trade.status == 'open').count(),
                'closed': db.query(Trade).filter(Trade.status == 'closed').count(),
            },
            'security': security_manager.check_security_status()
        }
        return jsonify(stats)
    finally:
        db.close()

@app.route('/api/online-status')
@auth.login_required
def api_online_status():
    """API endpoint for real-time online status"""
    try:
        online_user_ids = get_live_online_users()
        return jsonify({
            'online_users': online_user_ids,
            'count': len(online_user_ids),
            'status': 'ok'
        })
    except Exception as e:
        print(f"ERROR getting online status: {e}")
        return jsonify({
            'online_users': [],
            'count': 0,
            'status': 'error'
        })

@app.route('/api/toggle-user/<int:user_id>', methods=['POST'])
@auth.login_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    db = SessionLocal()
    try:
        data = request.get_json() or {}
        new_status = data.get('active', True)
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        user.is_active = new_status
        db.commit()
        
        action = 'activated' if new_status else 'suspended'
        return jsonify({
            'success': True,
            'message': f'User {user.username} {action} successfully',
            'user_id': user_id,
            'active': new_status
        })
    except Exception as e:
        db.rollback()
        print(f"ERROR toggling user status: {e}")
        return jsonify({'error': 'Failed to update user status'}), 500
    finally:
        db.close()

@app.route('/debug')
@auth.login_required
def debug():
    """Debug endpoint to check database connectivity"""
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        trade_count = db.query(Trade).count()
        
        # Get some sample data
        sample_users = db.query(User).limit(3).all()
        sample_trades = db.query(Trade).limit(3).all()
        
        debug_info = {
            'users': user_count,
            'trades': trade_count,
            'sample_users': [{'id': u.id, 'username': u.username, 'email': u.email} for u in sample_users],
            'sample_trades': [{'id': t.id, 'symbol': t.symbol, 'user_id': t.user_id} for t in sample_trades],
            'database_path': '../backend/copyarena.db'
        }
        
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.close()

# Automated backup scheduler
def automated_backup():
    """Automated backup function"""
    try:
        backup_info = security_manager.create_secure_backup()
        print(f"[ADMIN] Automated backup created: {backup_info.get('filename', 'Unknown')}")
    except Exception as e:
        print(f"[ADMIN] Automated backup failed: {e}")

def start_backup_scheduler():
    """Start the backup scheduler in a separate thread"""
    # Schedule backups every 6 hours
    schedule.every(6).hours.do(automated_backup)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Start backup scheduler in background
backup_thread = threading.Thread(target=start_backup_scheduler, daemon=True)
backup_thread.start()
print("[ADMIN] Automated backup scheduler started (every 6 hours)")

@app.context_processor
def inject_now():
    """Inject current time into all templates"""
    return {'now': datetime.now()}

if __name__ == '__main__':
    print("=" * 60)
    print("CopyArena Admin Panel Starting...")
    print("=" * 60)
    print("URL: http://localhost:5000")
    print("Default Admin: admin / admin123")
    print("Change passwords in admin_panel/app.py!")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True) 