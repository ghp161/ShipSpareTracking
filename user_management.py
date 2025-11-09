import sqlite3
import hashlib
import pandas as pd
import secrets
from datetime import datetime
import streamlit as st
from data_manager import DataManager
from barcode_handler import BarcodeHandler
from session_manager import cookie_session

class UserManager:

    def __init__(self, db_path='inventory.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_users_table()

    def get_all_users_with_departments(self):
        query = '''
            SELECT u.id, u.username, u.role, 
                   u.created_at, u.last_login, u.isactive,
                   d1.name as parent_department,
                   d2.name as child_department
            FROM users u
            LEFT JOIN departments d2 ON u.department_id = d2.id
            LEFT JOIN departments d1 ON d2.parent_id = d1.id
            ORDER BY u.role, u.username
        '''
        return pd.read_sql_query(query, self.conn)
    
    def get_parent_departments(self):
        query = "SELECT id, name FROM departments WHERE parent_id IS NULL"
        return pd.read_sql_query(query, self.conn)
    
    def get_child_departments(self, parent_id):
        if not parent_id:
            return pd.DataFrame(columns=['id', 'name'])
        query = "SELECT id, name FROM departments WHERE parent_id = ?"
        return pd.read_sql_query(query, self.conn, params=(parent_id,))
    
    def update_user(self, user_id, username, role, department_id=None, new_password=None):
        cursor = self.conn.cursor()
        try:
            if new_password:
                # Update password if provided
                password_hash, salt = self.hash_password(new_password)
                cursor.execute(
                    '''
                    UPDATE users 
                    SET username=?, role=?, department_id=?, 
                        password_hash=?, salt=?
                    WHERE id=?
                ''', (username, role, department_id, password_hash, salt, user_id))
            else:
                # Update without changing password
                #print("dept_id:", department_id)  # Add this temporarily
                cursor.execute('''
                    UPDATE users 
                    SET username=?, role=?, department_id=?
                    WHERE id=?
                ''', (username, role, department_id, user_id))
                
            self.conn.commit()
            return True, None
        except sqlite3.Error as e:
            return False, str(e)
    
    def deactivate_user(self, user_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute("UPDATE users SET isactive=0 WHERE id=?", (user_id,))
            self.conn.commit()
            return True, None
        except sqlite3.Error as e:
            return False, str(e)
    
    def activate_user(self, user_id):
        cursor = self.conn.cursor()
        try:
            cursor.execute("UPDATE users SET isactive=1 WHERE id=?", (user_id,))
            self.conn.commit()
            return True, None
        except sqlite3.Error as e:
            return False, str(e)

    def create_users_table(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL,
                    created_at TIMESTAMP,
                    last_login TIMESTAMP,
                    isactive boolean NOT NULL default 0
                )
            ''')
            self.conn.commit()
            # Create default admin user if not exists
            self.create_default_admin()
        except sqlite3.Error as e:
            print(f"Error creating users table: {e}")
            raise

    def create_default_admin(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            self.register_user('admin', 'admin123', 'admin')

    def hash_password(self, password, salt=None):
        if salt is None:
            salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'),
                                            salt.encode('utf-8'),
                                            100000).hex()
        return password_hash, salt

    def register_user(self, username, password, role='staff', department_id=None, isactive=True):
        cursor = self.conn.cursor()
        try:
            password_hash, salt = self.hash_password(password)
            cursor.execute(
                '''
                INSERT INTO users (username, password_hash, salt, role, created_at, department_id, isactive)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (username, password_hash, salt, role, datetime.now(), department_id, isactive))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def verify_user(self, username, password):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT password_hash, salt, role, isactive, id, department_id FROM users WHERE username = ?
        ''', (username, ))
        result = cursor.fetchone()

        if result:
            stored_hash, salt, role, isactive, user_id, department_id = result
            password_hash, _ = self.hash_password(password, salt)
            if password_hash == stored_hash:
                if not isactive:
                    return False, None, None, None, "Account is inactive. Please contact administrator."
                # Update last login time
                cursor.execute(
                    '''
                    UPDATE users SET last_login = ? WHERE username = ?
                ''', (datetime.now(), username))
                self.conn.commit()
                return True, role, user_id, department_id, None
        return False, None, None, None, "Invalid username or password"

    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id, username, role, created_at, last_login 
            FROM users
        ''')
        return cursor.fetchall()

    def update_user_role(self, username, new_role):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                '''
                UPDATE users SET role = ? WHERE username = ?
            ''', (new_role, username))
            self.conn.commit()
            return True
        except sqlite3.Error:
            return False


def init_session_state():
    """Initialize session state with required variables"""
    required_vars = {
        'authenticated': False,
        'username': None,
        'user_role': None,
        'user_id': None,
        'user_department_id': None,
        'login_time': None
    }
    
    for var, default in required_vars.items():
        if var not in st.session_state:
            st.session_state[var] = default
    
    # Initialize managers
    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager()
        
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()
    
    if 'barcode_handler' not in st.session_state:
        st.session_state.barcode_handler = BarcodeHandler()

def check_and_restore_session():
    """Check for existing session and restore it"""
    return cookie_session.check_session()

def login_required(func):
    """Decorator to require login for accessing pages"""
    def wrapper(*args, **kwargs):
        init_session_state()
        
        # Check if user is authenticated
        if not st.session_state.authenticated:
            # Try to restore session from cookie
            if not check_and_restore_session():
                st.warning("Please log in to access this page")
                render_login_page()
                st.stop()
        
        return func(*args, **kwargs)
    return wrapper

def render_login_page():
    """Render login page"""
    # Clear any existing invalid session
    if st.session_state.get('authenticated', False):
        cookie_session.logout()
    
    st.image("logo.png", width=100)
    st.write("")
    st.title("Ship Inventory Management System")

    with st.form("login_form", clear_on_submit=True):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")

        if st.form_submit_button("Login", use_container_width=True):
            if username and password:
                if cookie_session.login(username, password):
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.error("Please enter both username and password")

def logout():
    """Handle user logout"""
    cookie_session.logout()
    st.success("Logged out successfully!")
    st.rerun()