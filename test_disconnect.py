#!/usr/bin/env python3
"""Test WebSocket disconnect functionality"""

import requests
import base64
import time

def test_disconnect():
    print("🧪 Testing WebSocket disconnect functionality...")
    
    auth_string = base64.b64encode(b'admin:admin123').decode('ascii')
    headers = {'Authorization': f'Basic {auth_string}'}
    
    def get_online_count():
        try:
            response = requests.get('http://localhost:5000/api/stats', headers=headers, timeout=5)
            if response.status_code == 200:
                stats = response.json()
                return stats.get('users', {}).get('online', 0)
        except:
            pass
        return -1
    
    print("\n1. Checking initial online count...")
    initial_count = get_online_count()
    print(f"   📊 Initial online users: {initial_count}")
    
    print("\n2. Instructions:")
    print("   - Open your web app (http://localhost:3000)")
    print("   - Login with mariosat account")
    print("   - Watch the admin panel online count increase")
    print("   - Close the browser tab")
    print("   - Watch the admin panel online count decrease")
    
    print("\n3. Monitoring online count every 5 seconds...")
    print("   Press Ctrl+C to stop monitoring")
    
    try:
        previous_count = initial_count
        while True:
            time.sleep(5)
            current_count = get_online_count()
            
            if current_count != previous_count:
                if current_count > previous_count:
                    print(f"   🟢 CONNECTED: {current_count} users online (+{current_count - previous_count})")
                else:
                    print(f"   🔴 DISCONNECTED: {current_count} users online (-{previous_count - current_count})")
                previous_count = current_count
            else:
                print(f"   📊 Stable: {current_count} users online")
                
    except KeyboardInterrupt:
        print(f"\n✅ Monitoring stopped. Final count: {get_online_count()}")

if __name__ == "__main__":
    test_disconnect() 