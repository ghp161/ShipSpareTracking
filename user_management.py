import sqlite3
import hashlib
import secrets
from datetime import datetime
import streamlit as st


class UserManager:

    def __init__(self, db_path='inventory.db'):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_users_table()

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
                    last_login TIMESTAMP
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

    def register_user(self, username, password, role='staff'):
        cursor = self.conn.cursor()
        try:
            password_hash, salt = self.hash_password(password)
            cursor.execute(
                '''
                INSERT INTO users (username, password_hash, salt, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, password_hash, salt, role, datetime.now()))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def verify_user(self, username, password):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            SELECT password_hash, salt, role FROM users WHERE username = ?
        ''', (username, ))
        result = cursor.fetchone()

        if result:
            stored_hash, salt, role = result
            password_hash, _ = self.hash_password(password, salt)
            if password_hash == stored_hash:
                # Update last login time
                cursor.execute(
                    '''
                    UPDATE users SET last_login = ? WHERE username = ?
                ''', (datetime.now(), username))
                self.conn.commit()
                return True, role
        return False, None

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
    """Initialize session state variables for authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager()


def login_required(func):
    """Decorator to require login for accessing pages"""

    def wrapper(*args, **kwargs):
        init_session_state()
        if not st.session_state.authenticated:
            st.warning("Please log in to access this page")
            render_login_page()
            return
        return func(*args, **kwargs)

    return wrapper


def render_login_page():
    st.image("logo.png", width=100)
    st.write("")
    st.title("Ship Inventory Management System")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.form_submit_button("Login"):
            if username and password:
                success, role = st.session_state.user_manager.verify_user(
                    username, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.user_role = role
                    st.success(f"Welcome back, {username}!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            else:
                st.error("Please enter both username and password")
