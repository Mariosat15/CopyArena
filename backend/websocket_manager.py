import asyncio
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}  # user_id -> set of websockets
        self.client_connections: Dict[int, WebSocket] = {}       # user_id -> client websocket
        self.connection_metadata: Dict[WebSocket, Dict] = {}     # websocket -> metadata
    
    async def connect(self, websocket: WebSocket, user_id: int, connection_type: str = "general"):
        """Connect a new WebSocket"""
        await websocket.accept()
        
        # Initialize user connections if not exists
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        # Add connection
        self.active_connections[user_id].add(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connection_type": connection_type,
            "connected_at": datetime.now(),
            "last_ping": datetime.now()
        }
        
        logger.info(f"User {user_id} connected via WebSocket ({connection_type})")
    
    async def connect_client(self, websocket: WebSocket, user_id: int):
        """Connect a Windows Client WebSocket for trade commands"""
        await websocket.accept()
        
        # Check if this is a new connection (not a reconnection)
        was_offline = user_id not in self.client_connections
        
        # Store client connection (only one per user)
        if user_id in self.client_connections:
            # Disconnect existing client connection
            old_websocket = self.client_connections[user_id]
            if old_websocket in self.connection_metadata:
                del self.connection_metadata[old_websocket]
        
        self.client_connections[user_id] = websocket
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connection_type": "client",
            "connected_at": datetime.now(),
            "last_ping": datetime.now()
        }
        
        logger.info(f"Windows Client for user {user_id} connected and ready for trade commands")
        
        # Check if this is a master trader coming online
        if was_offline:
            await self._notify_master_online_if_needed(user_id)
    
    async def _notify_master_online_if_needed(self, user_id: int):
        """Check if user is a master and notify followers if they came online"""
        try:
            # We need to import here to avoid circular imports
            from sqlalchemy.orm import sessionmaker
            from .database import engine
            from .models import User, Follow
            
            Session = sessionmaker(bind=engine)
            db = Session()
            
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_master_trader:
                    # Master came online - notify all followers
                    followers = db.query(Follow).filter(
                        Follow.following_id == user.id,
                        Follow.is_active == True
                    ).all()
                    
                    # Send online notification to all connected followers
                    online_message = {
                        "type": "master_status_change",
                        "data": {
                            "master_id": user.id,
                            "master_username": user.username,
                            "status": "online",
                            "timestamp": datetime.utcnow().isoformat(),
                            "message": f"Master trader {user.username} is now online"
                        }
                    }
                    
                    for follow in followers:
                        await self.send_user_message(online_message, follow.follower_id)
                    
                    logger.info(f"🟢 Master {user.username} online notification sent to {len(followers)} followers")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error notifying master online: {e}")
    
    def disconnect_client(self, websocket: WebSocket, user_id: int):
        """Disconnect a Windows Client WebSocket and notify followers if master goes offline"""
        if user_id in self.client_connections and self.client_connections[user_id] == websocket:
            del self.client_connections[user_id]
            
            # Check if this was a master trader going offline
            asyncio.create_task(self._notify_master_offline_if_needed(user_id))
        
        if websocket in self.connection_metadata:
            del self.connection_metadata[websocket]
        
        logger.info(f"Windows Client for user {user_id} disconnected")
    
    async def _notify_master_offline_if_needed(self, user_id: int):
        """Check if user is a master and notify followers if they went offline"""
        try:
            # We need to import here to avoid circular imports
            from sqlalchemy.orm import sessionmaker
            from .database import engine
            from .models import User, Follow
            
            Session = sessionmaker(bind=engine)
            db = Session()
            
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user and user.is_master_trader:
                    # Master went offline - notify all followers
                    followers = db.query(Follow).filter(
                        Follow.following_id == user.id,
                        Follow.is_active == True
                    ).all()
                    
                    # Send offline notification to all connected followers
                    offline_message = {
                        "type": "master_status_change",
                        "data": {
                            "master_id": user.id,
                            "master_username": user.username,
                            "status": "offline",
                            "timestamp": datetime.utcnow().isoformat(),
                            "message": f"Master trader {user.username} went offline"
                        }
                    }
                    
                    for follow in followers:
                        await self.send_user_message(offline_message, follow.follower_id)
                    
                    logger.info(f"📴 Master {user.username} offline notification sent to {len(followers)} followers")
                    
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error notifying master offline: {e}")
    
    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket"""
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata[websocket]
            user_id = metadata["user_id"]
            
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                
                # Clean up empty user connections
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            
            # Remove metadata
            del self.connection_metadata[websocket]
            
            logger.info(f"User {user_id} disconnected from WebSocket")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def send_user_message(self, message: Dict, user_id: int):
        """Send message to all connections for a specific user"""
        if user_id not in self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = set()
        
        for websocket in self.active_connections[user_id]:
            try:
                await websocket.send_text(message_str)
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                disconnected.add(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_message(self, message: Dict, exclude_user: int = None):
        """Broadcast message to all connected users"""
        message_str = json.dumps(message)
        disconnected = set()
        
        for user_id, websockets in self.active_connections.items():
            if exclude_user and user_id == exclude_user:
                continue
                
            for websocket in websockets:
                try:
                    await websocket.send_text(message_str)
                except Exception as e:
                    logger.error(f"Error broadcasting to user {user_id}: {e}")
                    disconnected.add(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def send_trade_update(self, trade_data: Dict, user_id: int):
        """Send trade update to user and their followers"""
        # Send to the trader
        await self.send_user_message({
            "type": "trade_update",
            "data": trade_data,
            "timestamp": datetime.now().isoformat()
        }, user_id)
        
        # Broadcast to all users for leaderboard updates if it's a significant trade
        if trade_data.get("profit", 0) != 0:  # Only closed trades
            await self.broadcast_message({
                "type": "leaderboard_update",
                "trader_id": user_id,
                "profit": trade_data.get("profit", 0),
                "timestamp": datetime.now().isoformat()
            }, exclude_user=user_id)
    
    async def send_account_update(self, account_data: Dict, user_id: int):
        """Send account status update"""
        await self.send_user_message({
            "type": "account_update",
            "data": account_data,
            "timestamp": datetime.now().isoformat()
        }, user_id)
    
    async def send_xp_update(self, user_id: int, xp_gained: int, new_total: int, level_up: bool = False):
        """Send XP update notification"""
        message = {
            "type": "xp_update",
            "data": {
                "xp_gained": xp_gained,
                "new_total": new_total,
                "level_up": level_up
            },
            "timestamp": datetime.now().isoformat()
        }
        
        await self.send_user_message(message, user_id)
    
    async def send_badge_earned(self, user_id: int, badge_data: Dict):
        """Send badge earned notification"""
        await self.send_user_message({
            "type": "badge_earned",
            "data": badge_data,
            "timestamp": datetime.now().isoformat()
        }, user_id)
    
    async def send_copy_trade_notification(self, follower_id: int, trader_id: int, trade_data: Dict):
        """Send copy trade notification"""
        await self.send_user_message({
            "type": "copy_trade",
            "data": {
                "trader_id": trader_id,
                "trade": trade_data,
                "message": f"Copied trade from trader {trader_id}"
            },
            "timestamp": datetime.now().isoformat()
        }, follower_id)
    
    async def send_trade_command(self, user_id: int, command_type: str, command_data: Dict):
        """Send trade command to Windows Client"""
        if user_id not in self.client_connections:
            logger.warning(f"Cannot send trade command to user {user_id}: No client connection")
            return False
        
        websocket = self.client_connections[user_id]
        message = {
            "type": command_type,
            "data": command_data,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            await websocket.send_text(json.dumps(message))
            logger.info(f"Trade command '{command_type}' sent to user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send trade command to user {user_id}: {e}")
            self.disconnect_client(websocket, user_id)
            return False
    
    def is_client_connected(self, user_id: int) -> bool:
        """Check if user has Windows Client connected"""
        return user_id in self.client_connections
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of connections for a specific user"""
        return len(self.active_connections.get(user_id, set()))
    
    def is_user_online(self, user_id: int) -> bool:
        """Check if user has any active connections"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    async def ping_all_connections(self):
        """Send ping to all connections to keep them alive"""
        ping_message = json.dumps({
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        })
        
        disconnected = set()
        
        for user_id, websockets in self.active_connections.items():
            for websocket in websockets:
                try:
                    await websocket.send_text(ping_message)
                    # Update last ping time
                    if websocket in self.connection_metadata:
                        self.connection_metadata[websocket]["last_ping"] = datetime.now()
                except Exception as e:
                    logger.error(f"Error pinging user {user_id}: {e}")
                    disconnected.add(websocket)
        
        # Clean up disconnected sockets
        for websocket in disconnected:
            self.disconnect(websocket)

# Global connection manager instance
manager = ConnectionManager()

async def start_ping_task():
    """Start background task to ping all connections"""
    while True:
        await asyncio.sleep(30)  # Ping every 30 seconds
        await manager.ping_all_connections() 