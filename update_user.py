import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from models import SessionLocal, User

def update_ea_user_to_mariosat():
    db = SessionLocal()
    try:
        # Find the user with API key ca_6_41a78f423ec54bc6
        user = db.query(User).filter(User.api_key == 'ca_6_41a78f423ec54bc6').first()
        if user:
            print(f'Found user: {user.username} (ID: {user.id})')
            print(f'Email: {user.email}')
            print(f'API Key: {user.api_key}')
            
            # Update to mariosat
            user.username = 'mariosat'
            user.email = 'mariosat@copyarena.com'
            db.commit()
            print('✅ Updated user to mariosat')
            print(f'New username: {user.username}')
        else:
            print('❌ User not found with that API key')
            
        # List all users
        print('\n📋 All users in database:')
        all_users = db.query(User).all()
        for u in all_users:
            print(f'  - ID: {u.id}, Username: {u.username}, Email: {u.email}, API: {u.api_key[:10]}...')
            
    except Exception as e:
        print(f'Error: {e}')
    finally:
        db.close()

if __name__ == '__main__':
    update_ea_user_to_mariosat() 