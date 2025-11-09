# cookie_session_manager.py
import streamlit as st
from streamlit_cookies_controller import CookieController
import sqlite3
import hashlib
from datetime import datetime

class CookieSessionManager:
    def __init__(self):
        self.controller = CookieController()
        self.cookie_name = "inventory_user_session"
        self.session_timeout_days = 7  # 7 days session
    
    def authenticate_user(self, username, password):
        """Authenticate user against database"""
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            
            # Get stored password hash and salt
            cursor.execute(
                "SELECT password_hash, salt, role, id, department_id, isactive FROM users WHERE username = ?", 
                (username,)
            )
            result = cursor.fetchone()
            conn.close()
            
            if result:
                stored_hash, salt, role, user_id, department_id, isactive = result
                
                # Verify password
                password_hash = hashlib.pbkdf2_hmac(
                    'sha256', 
                    password.encode('utf-8'), 
                    salt.encode('utf-8'), 
                    100000
                ).hex()
                
                if password_hash == stored_hash and isactive == 1:
                    return {
                        'user_id': user_id,
                        'username': username,
                        'role': role,
                        'department_id': department_id
                    }
            
            return None
        except Exception as e:
            print(f"Authentication error: {e}")
            return None
    
    def login(self, username, password):
        """Handle user login"""
        user_data = self.authenticate_user(username, password)
        if user_data:
            # Create session data
            session_data = {
                'user_id': user_data['user_id'],
                'username': user_data['username'],
                'role': user_data['role'],
                'department_id': user_data['department_id'],
                'login_time': datetime.now().isoformat()
            }
            
            # Set cookie
            self.controller.set(
                self.cookie_name, 
                str(user_data['user_id']),  # Store user_id as string
                max_age=self.session_timeout_days * 24 * 60 * 60
            )
            
            # Set session state
            st.session_state.authenticated = True
            st.session_state.user_id = user_data['user_id']
            st.session_state.username = user_data['username']
            st.session_state.user_role = user_data['role']
            st.session_state.user_department_id = user_data['department_id']
            st.session_state.login_time = datetime.now()
            
            # Update last login in database
            self.update_last_login(user_data['user_id'])
            
            return True
        return False
    
    def logout(self):
        """Handle user logout"""
        # Clear cookie
        self.controller.set(self.cookie_name, "", max_age=0)
        
        # Clear session state
        keys_to_clear = [
            'authenticated', 'user_id', 'username', 
            'user_role', 'user_department_id', 'login_time'
        ]
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def check_session(self):
        """Check and restore session from cookie"""
        try:
            user_id_cookie = self.controller.get(self.cookie_name)
            
            if user_id_cookie and not st.session_state.get('authenticated', False):
                user_id = int(user_id_cookie)
                
                # Verify user still exists and is active
                conn = sqlite3.connect('inventory.db')
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT username, role, department_id, isactive FROM users WHERE id = ?", 
                    (user_id,)
                )
                result = cursor.fetchone()
                conn.close()
                
                if result and result[3] == 1:  # isactive check
                    username, role, department_id, _ = result
                    
                    # Restore session state
                    st.session_state.authenticated = True
                    st.session_state.user_id = user_id
                    st.session_state.username = username
                    st.session_state.user_role = role
                    st.session_state.user_department_id = department_id
                    st.session_state.login_time = datetime.now()
                    
                    return True
            
            return False
            
        except Exception as e:
            print(f"Session check error: {e}")
            return False
    
    def update_last_login(self, user_id):
        """Update last login time in database"""
        try:
            conn = sqlite3.connect('inventory.db')
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (datetime.now(), user_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error updating last login: {e}")

# Global session manager instance
cookie_session = CookieSessionManager()