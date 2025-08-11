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
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import logging
from dataclasses import dataclass
from typing import Optional, Dict, List
import hashlib

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
            
    def sync_positions_data(self):
        """Sync open positions"""
        try:
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
                
            # Check if data changed
            data_hash = hashlib.md5(str(sorted(positions_data, key=lambda x: x['ticket'])).encode()).hexdigest()
            if data_hash != self.last_positions_hash:
                self.send_data_to_server("positions_update", positions_data)
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
