#!/usr/bin/env python3
"""
CopyArena Windows Client
Secure MT5 to Web Integration Client

This replaces the MT5 EA with a secure Windows application that:
1. Connects to MT5 using MetaTrader5 Python library
2. Authenticates with CopyArena web platform using user credentials
3. Sends trading data securely with user verification
4. Provides real-time status and logging
"""

import sys
import os
import json
import time
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import MetaTrader5 as mt5
from datetime import datetime
import websocket
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
import hashlib
from dataclasses import dataclass
from typing import Optional, Dict, List

def generate_copy_hash(master_name: str, master_ticket: str, open_time: str) -> str:
    """Generate unique hash for copy trade tracking"""
    hash_input = f"{master_name}_{master_ticket}_{open_time}"
    return hashlib.sha256(hash_input.encode()).hexdigest()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('copyarena_client.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ClientConfig:
    """Client configuration"""
    server_url: str = "https://your-domain.com"  # Change to your production URL
    username: str = ""
    password: str = ""
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""
    update_interval: int = 1
    auto_connect: bool = False

class CopyArenaClient:
    """Main CopyArena Windows Client"""
    
    def __init__(self):
        self.config = ClientConfig()
        self.api_token = None  # JWT token for web API
        self.api_key = None    # User's API key for MT5 data
        self.user_id = None
        self.username = None
        self.is_running = False
        self.mt5_connected = False
        self.web_connected = False
        
        # Threading
        self.update_thread = None
        self.stop_event = threading.Event()
        
        # Data caches for change detection
        self.last_account_hash = ""
        self.last_positions_hash = ""
        self.last_orders_hash = ""
        
        # HTTP session for connection reuse
        self.session = requests.Session()
        # Add retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=5,  # Number of connection pools to cache
            pool_maxsize=10,     # Maximum number of connections in the pool
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # WebSocket for receiving trade commands
        self.ws_thread = None
        self.websocket = None
        
        # Initialize GUI
        self.setup_gui()
        self.load_config()
        
    def setup_gui(self):
        """Setup the GUI interface"""
        self.root = tk.Tk()
        self.root.title("CopyArena Client v1.0")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Configure styles
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_connection_tab()
        self.create_status_tab()
        self.create_logs_tab()
        self.create_settings_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Disconnected")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken')
        self.status_bar.pack(side='bottom', fill='x')
        
    def create_connection_tab(self):
        """Create connection/authentication tab"""
        conn_frame = ttk.Frame(self.notebook)
        self.notebook.add(conn_frame, text="Connection")
        
        # Web credentials section
        web_frame = ttk.LabelFrame(conn_frame, text="CopyArena Web Credentials", padding="10")
        web_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(web_frame, text="Server URL:").grid(row=0, column=0, sticky='w', pady=2)
        self.server_entry = ttk.Entry(web_frame, width=40)
        self.server_entry.grid(row=0, column=1, sticky='ew', pady=2)
        self.server_entry.insert(0, self.config.server_url)
        
        ttk.Label(web_frame, text="Username:").grid(row=1, column=0, sticky='w', pady=2)
        self.username_entry = ttk.Entry(web_frame, width=40)
        self.username_entry.grid(row=1, column=1, sticky='ew', pady=2)
        
        ttk.Label(web_frame, text="Password:").grid(row=2, column=0, sticky='w', pady=2)
        self.password_entry = ttk.Entry(web_frame, width=40, show="*")
        self.password_entry.grid(row=2, column=1, sticky='ew', pady=2)
        
        web_frame.columnconfigure(1, weight=1)
        
        # MT5 credentials section
        mt5_frame = ttk.LabelFrame(conn_frame, text="MetaTrader 5 Credentials", padding="10")
        mt5_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(mt5_frame, text="Login:").grid(row=0, column=0, sticky='w', pady=2)
        self.mt5_login_entry = ttk.Entry(mt5_frame, width=40)
        self.mt5_login_entry.grid(row=0, column=1, sticky='ew', pady=2)
        
        ttk.Label(mt5_frame, text="Password:").grid(row=1, column=0, sticky='w', pady=2)
        self.mt5_password_entry = ttk.Entry(mt5_frame, width=40, show="*")
        self.mt5_password_entry.grid(row=1, column=1, sticky='ew', pady=2)
        
        ttk.Label(mt5_frame, text="Server:").grid(row=2, column=0, sticky='w', pady=2)
        self.mt5_server_entry = ttk.Entry(mt5_frame, width=40)
        self.mt5_server_entry.grid(row=2, column=1, sticky='ew', pady=2)
        
        mt5_frame.columnconfigure(1, weight=1)
        
        # Control buttons
        button_frame = ttk.Frame(conn_frame)
        button_frame.pack(fill='x', padx=10, pady=10)
        
        self.connect_btn = ttk.Button(button_frame, text="Connect All", command=self.connect_all)
        self.connect_btn.pack(side='left', padx=5)
        
        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect All", command=self.disconnect_all, state='disabled')
        self.disconnect_btn.pack(side='left', padx=5)
        
        self.save_config_btn = ttk.Button(button_frame, text="Save Config", command=self.save_config)
        self.save_config_btn.pack(side='right', padx=5)
        
    def create_status_tab(self):
        """Create status monitoring tab"""
        status_frame = ttk.Frame(self.notebook)
        self.notebook.add(status_frame, text="Status")
        
        # Connection status
        conn_status_frame = ttk.LabelFrame(status_frame, text="Connection Status", padding="10")
        conn_status_frame.pack(fill='x', padx=10, pady=5)
        
        self.web_status_var = tk.StringVar(value="❌ Not Connected")
        self.mt5_status_var = tk.StringVar(value="❌ Not Connected")
        self.sync_status_var = tk.StringVar(value="⏸️ Stopped")
        
        ttk.Label(conn_status_frame, text="Web Platform:").grid(row=0, column=0, sticky='w')
        ttk.Label(conn_status_frame, textvariable=self.web_status_var).grid(row=0, column=1, sticky='w')
        
        ttk.Label(conn_status_frame, text="MetaTrader 5:").grid(row=1, column=0, sticky='w')
        ttk.Label(conn_status_frame, textvariable=self.mt5_status_var).grid(row=1, column=1, sticky='w')
        
        ttk.Label(conn_status_frame, text="Data Sync:").grid(row=2, column=0, sticky='w')
        ttk.Label(conn_status_frame, textvariable=self.sync_status_var).grid(row=2, column=1, sticky='w')
        
        # Account info
        account_frame = ttk.LabelFrame(status_frame, text="Account Information", padding="10")
        account_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Create treeview for account info
        self.account_tree = ttk.Treeview(account_frame, columns=('Value',), show='tree headings', height=10)
        self.account_tree.heading('#0', text='Property')
        self.account_tree.heading('Value', text='Value')
        self.account_tree.column('#0', width=200)
        self.account_tree.column('Value', width=200)
        
        account_scroll = ttk.Scrollbar(account_frame, orient='vertical', command=self.account_tree.yview)
        self.account_tree.configure(yscrollcommand=account_scroll.set)
        
        self.account_tree.pack(side='left', fill='both', expand=True)
        account_scroll.pack(side='right', fill='y')
        
    def create_logs_tab(self):
        """Create logs tab"""
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Logs")
        
        # Log display
        self.log_text = scrolledtext.ScrolledText(logs_frame, height=30, width=100)
        self.log_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Log controls
        log_controls = ttk.Frame(logs_frame)
        log_controls.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(log_controls, text="Clear Logs", command=self.clear_logs).pack(side='left')
        ttk.Button(log_controls, text="Save Logs", command=self.save_logs).pack(side='left', padx=5)
        
    def create_settings_tab(self):
        """Create settings tab"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
        
        # Update interval
        interval_frame = ttk.LabelFrame(settings_frame, text="Update Settings", padding="10")
        interval_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(interval_frame, text="Update Interval (seconds):").grid(row=0, column=0, sticky='w')
        self.interval_var = tk.IntVar(value=self.config.update_interval)
        self.interval_spin = ttk.Spinbox(interval_frame, from_=1, to=60, textvariable=self.interval_var, width=10)
        self.interval_spin.grid(row=0, column=1, sticky='w', padx=5)
        
        # Auto-connect
        self.auto_connect_var = tk.BooleanVar(value=self.config.auto_connect)
        ttk.Checkbutton(interval_frame, text="Auto-connect on startup", variable=self.auto_connect_var).grid(row=1, column=0, columnspan=2, sticky='w', pady=5)
        
    def log_message(self, message: str, level: str = "INFO"):
        """Add message to log display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        # Also log to file
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
            
    def clear_logs(self):
        """Clear log display"""
        self.log_text.delete(1.0, tk.END)
        
    def save_logs(self):
        """Save logs to file"""
        try:
            with open(f"copyarena_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 'w') as f:
                f.write(self.log_text.get(1.0, tk.END))
            messagebox.showinfo("Success", "Logs saved successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save logs: {e}")
            
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists('copyarena_config.json'):
                with open('copyarena_config.json', 'r') as f:
                    config_data = json.load(f)
                    
                self.config.server_url = config_data.get('server_url', self.config.server_url)
                self.config.username = config_data.get('username', '')
                self.config.mt5_login = config_data.get('mt5_login', 0)
                self.config.mt5_server = config_data.get('mt5_server', '')
                self.config.update_interval = config_data.get('update_interval', 3)
                self.config.auto_connect = config_data.get('auto_connect', False)
                
                # Update GUI
                self.server_entry.delete(0, tk.END)
                self.server_entry.insert(0, self.config.server_url)
                self.username_entry.insert(0, self.config.username)
                self.mt5_login_entry.insert(0, str(self.config.mt5_login) if self.config.mt5_login else '')
                self.mt5_server_entry.insert(0, self.config.mt5_server)
                
        except Exception as e:
            self.log_message(f"Failed to load config: {e}", "WARNING")
            
    def save_config(self):
        """Save configuration to file"""
        try:
            config_data = {
                'server_url': self.server_entry.get(),
                'username': self.username_entry.get(),
                'mt5_login': int(self.mt5_login_entry.get()) if self.mt5_login_entry.get() else 0,
                'mt5_server': self.mt5_server_entry.get(),
                'update_interval': self.interval_var.get(),
                'auto_connect': self.auto_connect_var.get()
            }
            
            with open('copyarena_config.json', 'w') as f:
                json.dump(config_data, f, indent=2)
                
            self.log_message("Configuration saved successfully!")
            messagebox.showinfo("Success", "Configuration saved!")
            
        except Exception as e:
            self.log_message(f"Failed to save config: {e}", "ERROR")
            messagebox.showerror("Error", f"Failed to save config: {e}")
            
    def authenticate_web(self) -> bool:
        """Authenticate with CopyArena web platform"""
        try:
            server_url = self.server_entry.get().rstrip('/')
            username = self.username_entry.get()
            password = self.password_entry.get()
            
            if not all([server_url, username, password]):
                self.log_message("Missing web credentials", "ERROR")
                return False
                
            self.log_message(f"Attempting to connect to: {server_url}")
            self.log_message(f"Using email: {username}")
            
            # Login request
            login_data = {
                "email": username,
                "password": password
            }
            
            response = self.session.post(f"{server_url}/api/auth/login", json=login_data, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.api_token = data.get('token')
                self.user_id = data['user']['id']
                self.username = data['user']['username']
                self.api_key = data['user']['api_key']  # Get the actual API key for MT5 data
                
                self.web_connected = True
                self.web_status_var.set("✅ Connected")
                self.log_message(f"Web authentication successful for user: {self.username}")
                self.log_message(f"API Key retrieved: {self.api_key[:20]}... (Length: {len(self.api_key)})")
                
                # Start WebSocket for receiving trade commands
                self.start_websocket_connection()
                return True
            elif response.status_code == 401:
                self.log_message("Authentication failed: Invalid email or password", "ERROR")
                return False
            else:
                self.log_message(f"Web authentication failed (HTTP {response.status_code}): {response.text}", "ERROR")
                return False
                
        except requests.exceptions.ConnectionError:
            self.log_message(f"Connection error: Cannot reach server at {server_url}", "ERROR")
            self.log_message("Make sure the CopyArena backend is running and accessible", "ERROR")
            return False
        except requests.exceptions.Timeout:
            self.log_message(f"Timeout error: Server at {server_url} is not responding", "ERROR")
            return False
        except Exception as e:
            self.log_message(f"Web authentication error: {e}", "ERROR")
            return False
            
    def connect_mt5(self) -> bool:
        """Connect to MetaTrader 5"""
        try:
            if not mt5.initialize():
                self.log_message("Failed to initialize MT5", "ERROR")
                return False
                
            login = int(self.mt5_login_entry.get()) if self.mt5_login_entry.get() else None
            password = self.mt5_password_entry.get()
            server = self.mt5_server_entry.get()
            
            if login and password and server:
                if not mt5.login(login, password=password, server=server):
                    self.log_message(f"Failed to login to MT5: {mt5.last_error()}", "ERROR")
                    return False
                    
            account_info = mt5.account_info()
            if account_info is None:
                self.log_message("Failed to get MT5 account info", "ERROR")
                return False
                
            self.mt5_connected = True
            self.mt5_status_var.set("✅ Connected")
            self.log_message(f"MT5 connected successfully - Account: {account_info.login}")
            self.update_account_display(account_info)
            return True
            
        except Exception as e:
            self.log_message(f"MT5 connection error: {e}", "ERROR")
            return False
            
    def update_account_display(self, account_info):
        """Update account information display"""
        # Clear existing items
        for item in self.account_tree.get_children():
            self.account_tree.delete(item)
            
        # Add account information
        if account_info:
            self.account_tree.insert('', 'end', text='Login', values=(account_info.login,))
            self.account_tree.insert('', 'end', text='Server', values=(account_info.server,))
            self.account_tree.insert('', 'end', text='Name', values=(account_info.name,))
            self.account_tree.insert('', 'end', text='Company', values=(account_info.company,))
            self.account_tree.insert('', 'end', text='Currency', values=(account_info.currency,))
            self.account_tree.insert('', 'end', text='Balance', values=(f"{account_info.balance:.2f}",))
            self.account_tree.insert('', 'end', text='Equity', values=(f"{account_info.equity:.2f}",))
            self.account_tree.insert('', 'end', text='Margin', values=(f"{account_info.margin:.2f}",))
            self.account_tree.insert('', 'end', text='Free Margin', values=(f"{account_info.margin_free:.2f}",))
            self.account_tree.insert('', 'end', text='Margin Level', values=(f"{account_info.margin_level:.2f}%" if account_info.margin_level else "N/A",))
            
    def connect_all(self):
        """Connect to both web platform and MT5"""
        self.log_message("Starting connection process...")
        
        # Authenticate with web platform
        if not self.authenticate_web():
            messagebox.showerror("Error", "Failed to authenticate with CopyArena web platform")
            return
            
        # Connect to MT5
        if not self.connect_mt5():
            messagebox.showerror("Error", "Failed to connect to MetaTrader 5")
            return
            
        # Start data sync
        self.start_data_sync()
        
        # Update UI
        self.connect_btn.config(state='disabled')
        self.disconnect_btn.config(state='normal')
        self.status_var.set("Connected - Syncing Data")
        
    def disconnect_all(self):
        """Disconnect from all services"""
        self.stop_data_sync()
        
        if self.mt5_connected:
            mt5.shutdown()
            self.mt5_connected = False
            self.mt5_status_var.set("❌ Disconnected")
            
        self.web_connected = False
        self.web_status_var.set("❌ Disconnected")
        self.sync_status_var.set("⏸️ Stopped")
        
        self.connect_btn.config(state='normal')
        self.disconnect_btn.config(state='disabled')
        self.status_var.set("Disconnected")
        
        self.log_message("All connections closed")
        
        # Close HTTP session
        if hasattr(self, 'session'):
            self.session.close()
            self.log_message("HTTP session closed")
        
    def start_data_sync(self):
        """Start the data synchronization thread"""
        if not self.is_running:
            self.is_running = True
            self.stop_event.clear()
            self.update_thread = threading.Thread(target=self.data_sync_loop, daemon=True)
            self.update_thread.start()
            self.sync_status_var.set("🔄 Running")
            self.log_message("Data synchronization started")
            
    def stop_data_sync(self):
        """Stop the data synchronization thread"""
        if self.is_running:
            self.is_running = False
            self.stop_event.set()
            if self.update_thread:
                self.update_thread.join(timeout=5)
            self.sync_status_var.set("⏸️ Stopped")
            self.log_message("Data synchronization stopped")
            
    def data_sync_loop(self):
        """Main data synchronization loop"""
        while self.is_running and not self.stop_event.is_set():
            try:
                if self.web_connected and self.mt5_connected:
                    self.sync_account_data()
                    self.sync_positions_data()
                    self.sync_orders_data()
                    
                # Wait for next iteration
                self.stop_event.wait(self.interval_var.get())
                
            except Exception as e:
                self.log_message(f"Data sync error: {e}", "ERROR")
                self.stop_event.wait(5)  # Wait 5 seconds on error
                
    def sync_account_data(self):
        """Sync account information"""
        try:
            account_info = mt5.account_info()
            if account_info is None:
                return
                
            # Create account data
            account_data = {
                "balance": account_info.balance,
                "equity": account_info.equity,
                "margin": account_info.margin,
                "free_margin": account_info.margin_free,
                "margin_level": account_info.margin_level,
                "profit": account_info.profit,
                "credit": account_info.credit,
                "leverage": account_info.leverage,
                "company": account_info.company,
                "name": account_info.name,
                "server": account_info.server,
                "currency": account_info.currency,
                "trade_allowed": True,
                "trade_expert": True
            }
            
            # Check if data changed
            data_hash = hashlib.md5(str(sorted(account_data.items())).encode()).hexdigest()
            if data_hash != self.last_account_hash:
                self.send_data_to_server("account_update", account_data)
                self.last_account_hash = data_hash
                
                # Update display
                self.root.after(0, lambda: self.update_account_display(account_info))
                
        except Exception as e:
            self.log_message(f"Account sync error: {e}", "ERROR")
            
    def get_market_status(self):
        """Check if the market is open for major symbols"""
        try:
            if not self.mt5_connected:
                return False
                
            # Check multiple major symbols to determine market status
            test_symbols = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD"]
            
            for symbol in test_symbols:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is not None:
                    # Check if symbol is tradeable (market is open)
                    if symbol_info.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                        # Double-check with tick data - ensure it's recent (within last hour)
                        tick = mt5.symbol_info_tick(symbol)
                        if tick is not None and tick.time > 0:
                            current_time = time.time()
                            # If tick is recent (within last hour), market is likely open
                            if (current_time - tick.time) < 3600:
                                return True
                            
            return False
            
        except Exception as e:
            self.log_message(f"Failed to check market status: {e}", "ERROR")
            return False
    
    def sync_positions_data(self):
        """Sync open positions with market status"""
        try:
            # Get market status first
            market_open = self.get_market_status()
            
            positions = mt5.positions_get()
            if positions is None:
                positions = []
                
            positions_data = []
            for pos in positions:
                position_data = {
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "buy" if pos.type == 0 else "sell",
                    "volume": pos.volume,
                    "open_price": pos.price_open,
                    "current_price": pos.price_current,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                    "swap": pos.swap,
                    "commission": getattr(pos, 'commission', 0.0),  # Safe access with default
                    "magic": pos.magic,
                    "identifier": pos.identifier,
                    "comment": pos.comment,
                    "time": int(pos.time),
                    "time_update": int(pos.time_update) if pos.time_update else None
                }
                positions_data.append(position_data)
            
            # Create payload with market status and metadata
            payload = {
                "positions": positions_data,
                "market_open": market_open,
                "total_positions": len(positions_data),
                "timestamp": time.time()
            }
            
            # Log market status for debugging
            market_status = "🟢 OPEN" if market_open else "🔴 CLOSED"
            self.log_message(f"📊 Market: {market_status} | Positions: {len(positions_data)}")
            
            # Check if data changed
            data_hash = hashlib.md5(str(sorted(positions_data, key=lambda x: x['ticket'])).encode()).hexdigest()
            if data_hash != self.last_positions_hash:
                self.send_data_to_server("positions_update", payload)
                self.last_positions_hash = data_hash
                
        except Exception as e:
            self.log_message(f"Positions sync error: {e}", "ERROR")
            
    def sync_orders_data(self):
        """Sync pending orders"""
        try:
            orders = mt5.orders_get()
            if orders is None:
                orders = []
                
            orders_data = []
            for order in orders:
                order_data = {
                    "ticket": order.ticket,
                    "symbol": order.symbol,
                    "type": "buy_limit" if order.type == 2 else "sell_limit" if order.type == 3 else 
                           "buy_stop" if order.type == 4 else "sell_stop" if order.type == 5 else "unknown",
                    "volume": order.volume_initial,
                    "price_open": order.price_open,
                    "sl": order.sl,
                    "tp": order.tp,
                    "magic": order.magic,
                    "comment": order.comment,
                    "time_setup": int(order.time_setup),
                    "time_expiration": int(order.time_expiration) if order.time_expiration else None
                }
                orders_data.append(order_data)
                
            # Check if data changed
            data_hash = hashlib.md5(str(sorted(orders_data, key=lambda x: x['ticket'])).encode()).hexdigest()
            if data_hash != self.last_orders_hash:
                self.send_data_to_server("orders_update", orders_data)
                self.last_orders_hash = data_hash
                
        except Exception as e:
            self.log_message(f"Orders sync error: {e}", "ERROR")
    
    # === TRADE EXECUTION FUNCTIONS ===
    
    def ensure_symbol_ready(self, symbol: str) -> bool:
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                self.log_message(f"❌ Unknown symbol: {symbol}", "ERROR")
                return False
            if not info.visible:
                if not mt5.symbol_select(symbol, True):
                    self.log_message(f"❌ Failed to select symbol: {symbol}", "ERROR")
                    return False
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                self.log_message(f"❌ No tick data for symbol: {symbol}", "ERROR")
                return False
            return True
        except Exception as e:
            self.log_message(f"❌ ensure_symbol_ready error: {e}", "ERROR")
            return False

    def execute_buy_order(self, symbol: str, volume: float, price: float = None, sl: float = None, tp: float = None, comment: str = "CopyTrade"):
        """Execute a BUY order on MT5"""
        try:
            if not self.mt5_connected:
                self.log_message("❌ Cannot execute buy order: MT5 not connected", "ERROR")
                return False
            if not self.ensure_symbol_ready(symbol):
                return False
                
            # Prepare order request
            tick = mt5.symbol_info_tick(symbol)
            exec_price = tick.ask if price is None and tick else price
            if exec_price is None:
                self.log_message(f"❌ No exec price for BUY {symbol}", "ERROR")
                return False
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY,
                "price": exec_price,
                "sl": sl,
                "tp": tp,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send the order
            result = mt5.order_send(request)
            
            if result is None:
                self.log_message(f"❌ Buy order failed: {mt5.last_error()}", "ERROR")
                return False
            if getattr(result, 'retcode', None) != mt5.TRADE_RETCODE_DONE:
                self.log_message(f"❌ Buy order failed: {result.comment} (Code: {result.retcode})", "ERROR")
                return False
            
            self.log_message(f"✅ BUY order executed: {symbol} {volume} lots, Ticket: {result.order}")
            return result.order
            
        except Exception as e:
            self.log_message(f"❌ Buy order error: {e}", "ERROR")
            return False
    
    def execute_sell_order(self, symbol: str, volume: float, price: float = None, sl: float = None, tp: float = None, comment: str = "CopyTrade"):
        """Execute a SELL order on MT5"""
        try:
            if not self.mt5_connected:
                self.log_message("❌ Cannot execute sell order: MT5 not connected", "ERROR")
                return False
            if not self.ensure_symbol_ready(symbol):
                return False
                
            # Prepare order request
            tick = mt5.symbol_info_tick(symbol)
            exec_price = tick.bid if price is None and tick else price
            if exec_price is None:
                self.log_message(f"❌ No exec price for SELL {symbol}", "ERROR")
                return False
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_SELL,
                "price": exec_price,
                "sl": sl,
                "tp": tp,
                "comment": comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send the order
            result = mt5.order_send(request)
            
            if result is None:
                self.log_message(f"❌ Sell order failed: {mt5.last_error()}", "ERROR")
                return False
            if getattr(result, 'retcode', None) != mt5.TRADE_RETCODE_DONE:
                self.log_message(f"❌ Sell order failed: {result.comment} (Code: {result.retcode})", "ERROR")
                return False
            
            self.log_message(f"✅ SELL order executed: {symbol} {volume} lots, Ticket: {result.order}")
            return result.order
            
        except Exception as e:
            self.log_message(f"❌ Sell order error: {e}", "ERROR")
            return False
    
    def close_position(self, ticket: int, volume: float = None):
        """Close a position by ticket"""
        try:
            if not self.mt5_connected:
                self.log_message("❌ Cannot close position: MT5 not connected", "ERROR")
                return False
            
            self.log_message(f"🔍 DEBUG: Looking for position with ticket: {ticket}")
            
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if not position:
                self.log_message(f"❌ Position {ticket} not found", "ERROR")
                
                # 🔍 DEBUG: Show all current positions to help debug
                all_positions = mt5.positions_get()
                if all_positions:
                    self.log_message(f"🔍 DEBUG: Current positions: {[p.ticket for p in all_positions]}")
                else:
                    self.log_message(f"🔍 DEBUG: No positions currently open")
                return False
                
            position = position[0]
            close_volume = volume if volume else position.volume
            
            self.log_message(f"🔍 DEBUG: Found position - Symbol: {position.symbol}, Volume: {position.volume}, Type: {position.type}")
            
            # Determine close order type (opposite of position type)
            close_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
            close_price = mt5.symbol_info_tick(position.symbol).bid if position.type == 0 else mt5.symbol_info_tick(position.symbol).ask
            
            # Prepare close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": close_volume,
                "type": close_type,
                "position": ticket,
                "price": close_price,
                "comment": "CopyTrade Close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send close order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                self.log_message(f"❌ Close position failed: {result.comment} (Code: {result.retcode})", "ERROR")
                return False
            
            self.log_message(f"✅ Position CLOSED: {ticket} ({close_volume} lots)")
            return True
            
        except Exception as e:
            self.log_message(f"❌ Close position error: {e}", "ERROR")
            return False
    
    # === WEBSOCKET COMMAND HANDLING ===
    
    def start_websocket_connection(self):
        """Start WebSocket connection for receiving trade commands"""
        if not self.user_id or not self.api_token:
            self.log_message("❌ Cannot start WebSocket: Missing authentication", "ERROR")
            return
            
        try:
            server_url = self.server_entry.get().replace("http://", "").replace("https://", "")
            ws_url = f"ws://{server_url}/ws/client/{self.user_id}"
            
            self.log_message(f"🔌 Connecting to WebSocket: {ws_url}")
            
            # Create WebSocket connection
            self.websocket = websocket.WebSocketApp(
                ws_url,
                header={"Authorization": f"Bearer {self.api_token}"},
                on_message=self.on_websocket_message,
                on_error=self.on_websocket_error,
                on_close=self.on_websocket_close,
                on_open=self.on_websocket_open
            )
            
            # Start WebSocket in separate thread
            self.ws_thread = threading.Thread(target=self.websocket.run_forever, daemon=True)
            self.ws_thread.start()
            
        except Exception as e:
            self.log_message(f"❌ WebSocket connection error: {e}", "ERROR")
    
    def on_websocket_open(self, ws):
        """WebSocket connection opened"""
        self.log_message("✅ WebSocket connected - Ready to receive trade commands")
    
    def on_websocket_message(self, ws, message):
        """Handle incoming WebSocket messages (trade commands)"""
        try:
            data = json.loads(message)
            command_type = data.get("type")
            payload = data.get("data", {})
            
            self.log_message(f"📨 Received command: {command_type}")
            
            if command_type == "execute_trade":
                self.handle_trade_command(payload)
            elif command_type == "close_trade":
                self.handle_close_command(payload)
            elif command_type == "modify_trade":
                self.handle_modify_command(payload)
            else:
                self.log_message(f"❓ Unknown command type: {command_type}", "WARNING")
                
        except json.JSONDecodeError:
            self.log_message(f"❌ Invalid WebSocket message format: {message}", "ERROR")
        except Exception as e:
            self.log_message(f"❌ WebSocket message error: {e}", "ERROR")
    
    def handle_trade_command(self, payload):
        """Execute a trade order from copy trading"""
        try:
            symbol = payload.get("symbol")
            trade_type = payload.get("type")  # "buy" or "sell"
            volume = payload.get("volume")
            sl = payload.get("sl")
            tp = payload.get("tp")
            master_trader = payload.get("master_trader", "Unknown")
            
            # 🔍 DEBUG: Log the exact trade type received
            self.log_message(f"🔍 DEBUG: Raw trade_type received: '{trade_type}' (type: {type(trade_type)})")
            self.log_message(f"🔍 DEBUG: Full payload: {payload}")
            
            self.log_message(f"🎯 Executing copy trade: {trade_type.upper()} {symbol} {volume} lots (from {master_trader})")
            
            # Use provided copy_hash for robust cloning/identification via MT5 comment
            copy_hash = payload.get("copy_hash")
            short_hash = copy_hash[:16] if copy_hash else None  # MT5 comment length limit
            comment = f"CA:{short_hash}" if short_hash else f"Copy:{master_trader}"

            if trade_type.lower() == "buy":
                self.log_message(f"✅ Executing BUY order for {symbol}")
                result = self.execute_buy_order(symbol, volume, sl=sl, tp=tp, comment=comment)
            elif trade_type.lower() == "sell":
                self.log_message(f"✅ Executing SELL order for {symbol}")
                result = self.execute_sell_order(symbol, volume, sl=sl, tp=tp, comment=comment)
            else:
                self.log_message(f"❌ Invalid trade type: '{trade_type}' (should be 'buy' or 'sell')", "ERROR")
                return
            
            # Send execution result back to server
            self.send_execution_result("trade_executed", {
                "success": bool(result),
                "ticket": result if result else None,
                "copy_hash": copy_hash,
                "master_trader": master_trader,
                "master_ticket": payload.get("master_ticket", ""),
                "open_time": datetime.now().isoformat(),
                "original_command": payload
            })
            
        except Exception as e:
            self.log_message(f"❌ Trade command execution error: {e}", "ERROR")
    
    def handle_close_command(self, payload):
        """Close a position from copy trading"""
        try:
            ticket = payload.get("ticket")
            volume = payload.get("volume")
            master_trader = payload.get("master_trader", "Unknown")
            reason = payload.get("reason", "master_closed")
            
            # 🔍 DEBUG: Log the close command details
            self.log_message(f"🔍 DEBUG: Close command received - Ticket: {ticket} (type: {type(ticket)})")
            self.log_message(f"🔍 DEBUG: Full close payload: {payload}")
            
            self.log_message(f"🔒 Closing copy trade: Ticket {ticket} (from {master_trader}, reason: {reason})")
            
            result = False
            actual_ticket_closed = None
            
            # Try closing by ticket if provided and valid
            if ticket is not None:
                # Convert ticket to int if it's a string
                if isinstance(ticket, str):
                    try:
                        ticket = int(ticket)
                        self.log_message(f"🔍 DEBUG: Converted ticket to int: {ticket}")
                    except ValueError:
                        self.log_message(f"❌ Invalid ticket format: {ticket}", "ERROR")
                        ticket = None
                
                if ticket is not None:
                    result = self.close_position(ticket, volume)
                    if result:
                        actual_ticket_closed = ticket
            
            # If ticket is None or closing by ticket failed, try fallback by copy_hash in comment
            if not result:
                copy_hash = payload.get("copy_hash")
                if copy_hash:
                    short_hash = copy_hash[:16]
                    self.log_message(f"🔍 Fallback: searching for position with hash '{short_hash}' in comment...")
                    try:
                        all_positions = mt5.positions_get()
                        if all_positions:
                            self.log_message(f"🔍 DEBUG: Found {len(all_positions)} open positions")
                            for p in all_positions:
                                position_comment = str(p.comment) if p.comment else ""
                                self.log_message(f"🔍 DEBUG: Position {p.ticket} - Symbol: {p.symbol}, Comment: '{position_comment}'")
                                # Check both CA:hash format and just the hash
                                if position_comment and (short_hash in position_comment or f"CA:{short_hash}" in position_comment):
                                    self.log_message(f"🔍 Fallback: found matching position ticket {p.ticket} with comment '{position_comment}'")
                                    result = self.close_position(p.ticket, volume)
                                    if result:
                                        actual_ticket_closed = p.ticket
                                    break
                            if not result:
                                self.log_message(f"🔍 Fallback: no position found with hash '{short_hash}' in comment")
                                # Additional debug: show what hashes we're looking for vs what we have
                                self.log_message(f"🔍 DEBUG: Looking for hash '{short_hash}' or 'CA:{short_hash}' in comments")
                        else:
                            self.log_message(f"🔍 Fallback: no positions currently open")
                    except Exception as e:
                        self.log_message(f"Fallback close by hash error: {e}", "ERROR")
                else:
                    self.log_message(f"❌ No copy_hash provided for fallback close", "ERROR")
            
            if result:
                self.log_message(f"✅ Copy trade closed successfully: Ticket {actual_ticket_closed}")
            else:
                self.log_message(f"❌ Failed to close copy trade: No matching position found", "ERROR")
            
            # Send close result back to server with copy hash
            copy_hash = payload.get("copy_hash", "")
            self.send_execution_result("trade_closed", {
                "success": result,
                "ticket": actual_ticket_closed,
                "copy_hash": copy_hash,
                "master_trader": master_trader,
                "original_command": payload
            })
            
        except Exception as e:
            self.log_message(f"❌ Close command execution error: {e}", "ERROR")
    
    def handle_modify_command(self, payload):
        """Modify a position (SL/TP) from copy trading"""
        try:
            # Implementation for modifying positions
            ticket = payload.get("ticket")
            new_sl = payload.get("sl")
            new_tp = payload.get("tp")
            
            self.log_message(f"🔧 Modifying trade: Ticket {ticket}")
            
            # TODO: Implement MT5 position modification
            # This would use mt5.order_send with TRADE_ACTION_SLTP
            
        except Exception as e:
            self.log_message(f"❌ Modify command execution error: {e}", "ERROR")
    
    def send_execution_result(self, result_type: str, data: dict):
        """Send trade execution results back to server via WebSocket"""
        try:
            if self.websocket and hasattr(self.websocket, 'sock') and self.websocket.sock:
                # Send via WebSocket for copy trading processing
                message = {
                    "type": result_type,
                    "data": data  # Wrap data in "data" field as backend expects
                }
                self.websocket.send(json.dumps(message))
                self.log_message(f"✅ {result_type} sent via WebSocket successfully")
            else:
                # Fallback to HTTP if WebSocket not available
                self.send_data_to_server(result_type, data)
                self.log_message(f"✅ {result_type} sent via HTTP fallback")
        except Exception as e:
            self.log_message(f"❌ Failed to send execution result: {e}", "ERROR")
            # Try HTTP fallback
            try:
                self.send_data_to_server(result_type, data)
                self.log_message(f"✅ {result_type} sent via HTTP fallback after WebSocket error")
            except Exception as e2:
                self.log_message(f"❌ Both WebSocket and HTTP failed: {e2}", "ERROR")
    
    def on_websocket_error(self, ws, error):
        """WebSocket error handler"""
        self.log_message(f"❌ WebSocket error: {error}", "ERROR")
    
    def on_websocket_close(self, ws, close_status_code, close_msg):
        """WebSocket connection closed"""
        self.log_message(f"🔌 WebSocket disconnected: {close_msg}", "WARNING")
            
    def send_data_to_server(self, data_type: str, data: any):
        """Send data to CopyArena server with proper authentication"""
        try:
            if not self.web_connected or not self.api_token:
                return
                
            server_url = self.server_entry.get().rstrip('/')
            
            # Prepare secure data payload with proper API key
            payload = {
                "api_key": self.api_key,     # Use the user's actual API key (not JWT token)
                "user_id": self.user_id,     # Include user ID for verification  
                "username": self.username,    # Include username for logging
                "type": data_type,
                "timestamp": datetime.now().isoformat(),
                "data": data,
                "client_info": {
                    "version": "1.0",
                    "type": "windows_client",
                    "platform": "Windows"
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_token}"
            }
            
            response = self.session.post(
                f"{server_url}/api/ea/data",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self.log_message(f"✅ {data_type} sent successfully")
            else:
                self.log_message(f"❌ Failed to send {data_type}: {response.status_code} - {response.text}", "ERROR")
                
        except Exception as e:
            self.log_message(f"Failed to send {data_type}: {e}", "ERROR")
            
    def run(self):
        """Run the application"""
        try:
            # Auto-connect if enabled
            if self.config.auto_connect:
                self.root.after(1000, self.connect_all)  # Connect after 1 second
                
            self.root.mainloop()
        except KeyboardInterrupt:
            self.disconnect_all()
        finally:
            if self.mt5_connected:
                mt5.shutdown()

def main():
    """Main entry point"""
    try:
        app = CopyArenaClient()
        app.run()
    except Exception as e:
        logger.error(f"Application error: {e}")
        messagebox.showerror("Fatal Error", f"Application failed to start: {e}")

if __name__ == "__main__":
    main()
