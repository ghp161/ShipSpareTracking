import sqlite3
from contextlib import contextmanager
import pandas as pd
from datetime import datetime
import os


class DataManager:

    def __init__(self):
        # Ensure database directory exists
        self.db_path = 'inventory.db'
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False,
                               timeout=10)
        self.create_tables()
        print(f"Connected to database at {self.db_path}")

    @contextmanager
    def get_cursor(self):
        cursor = self.conn_pool.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def create_tables(self):
        cursor = self.conn.cursor()
        try:
            # Create departments table (add this)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS departments (
                    id INTEGER PRIMARY KEY,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    parent_id INTEGER,
                    FOREIGN KEY (parent_id) REFERENCES departments (id)
                )
            ''')

            # Create spare parts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS spare_parts (
                    id INTEGER PRIMARY KEY,
                    part_number TEXT UNIQUE,
                    name TEXT,
                    description TEXT,
                    quantity INTEGER,
                    line_no INTEGER,
                    yard_no INTEGER,
                    page_no TEXT,
                    order_no TEXT,
                    material_code TEXT,
                    ilms_code TEXT,
                    item_denomination TEXT,
                    mustered BOOLEAN,
                    department_id INTEGER,
                    compartment_no TEXT,
                    box_no TEXT,
                    remark TEXT,
                    min_order_level INTEGER,
                    min_order_quantity INTEGER,
                    barcode TEXT UNIQUE,
                    last_updated TIMESTAMP
                )
            ''')

            # Create transactions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    part_id INTEGER,
                    transaction_type TEXT,
                    quantity INTEGER,
                    timestamp TIMESTAMP,
                    FOREIGN KEY (part_id) REFERENCES spare_parts (id)
                )
            ''')

            self.conn.commit()
            print("Database tables created successfully")
        except sqlite3.Error as e:
            print(f"Error creating tables: {e}")
            raise

    def add_spare_part(self, part_data):
        cursor = self.conn.cursor()
        try:
            cursor.execute(
                '''
                INSERT INTO spare_parts (part_number, name, description, quantity,
                line_no, yard_no, page_no, order_no, material_code, ilms_code, item_denomination,
                mustered, department_id, compartment_no,  box_no, remark, 
                min_order_level, min_order_quantity, barcode, last_updated, status,
                last_maintenance_date, next_maintenance_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
                (part_data['part_number'], part_data['name'],
                part_data['description'], part_data['quantity'],
                part_data['line_no'], part_data['yard_no'],
                part_data['page_no'], part_data['order_no'],
                part_data['material_code'], part_data['ilms_code'],
                part_data['item_denomination'], part_data['mustered'],
                part_data['department_id'], part_data['compartment_no'],
                part_data['box_no'], part_data['remark'],
                part_data['min_order_level'], part_data['min_order_quantity'],
                part_data['barcode'], datetime.now(), 
                part_data['status'], part_data['last_maintenance_date'],
                part_data['next_maintenance_date']))
            self.conn.commit()
            cursor.close()  # Explicitly close cursor
            return True
        except sqlite3.IntegrityError:
            return False
        except sqlite3.Error as e:
            print(f"Error adding spare part: {e}")
            return False

    def update_spare_part(self, part_id, part_data):
        cursor = self.conn.cursor()
        cursor.execute(
            '''
            UPDATE spare_parts 
            SET name=?, description=?, quantity=?, min_order_level=?,
                min_order_quantity=?, last_updated=?, location=?, status=?,
                last_maintenance_date=?, next_maintenance_date=?
            WHERE id=?
        ''', (part_data['name'], part_data['description'],
            part_data['quantity'], part_data['min_order_level'],
            part_data['min_order_quantity'], datetime.now(), part_data['location'],
            part_data['status'], part_data['last_maintenance_date'],
            part_data['next_maintenance_date'], part_id))
        self.conn.commit()
        cursor.close()  # Explicitly close cursor

    def get_parts_by_department(self, department_id):
        """Get all parts for a specific department"""
        try:
            cursor = self.conn.cursor()
            query = '''
                SELECT sp.*, 
                    d1.name as parent_department,
                    d2.name as child_department
                FROM spare_parts sp
                LEFT JOIN departments d2 ON sp.department_id = d2.id
                LEFT JOIN departments d1 ON d2.parent_id = d1.id
                WHERE sp.department_id = ?
                ORDER BY sp.name
            '''
            df =  pd.read_sql_query(query, self.conn, params=(department_id,))
            cursor.close()  # Explicitly close cursor
            return df
        except pd.io.sql.DatabaseError as e:
            print(f"Error retrieving parts: {e}")
            return pd.DataFrame()
    
    def get_all_parts(self):
        try:
            cursor = self.conn.cursor()
            query = '''
                SELECT s.*, 
                    dp.name as parent_department,
                    dc.name as child_department
                FROM spare_parts s
                LEFT JOIN departments dc ON s.department_id = dc.id
                LEFT JOIN departments dp ON dc.parent_id = dp.id
            '''
            df = pd.read_sql_query(query, self.conn)
            cursor.close()  # Explicitly close cursor
            return df
        except pd.io.sql.DatabaseError as e:
            print(f"Error retrieving parts: {e}")
            return pd.DataFrame()

    def get_part_by_id(self, part_id):
        try:
            cursor = self.conn.cursor()
            df = pd.read_sql_query(
                f"SELECT * FROM spare_parts WHERE id= {part_id}", self.conn)
            cursor.close()  # Explicitly close cursor
            if df.empty:
                print(f"No part found with ID {part_id}")
                return None
            return df
        except pd.io.sql.DatabaseError as e:
            print(f"Error retrieving part {part_id}: {e}")
            return None

    def get_low_stock_items(self):
        try:
            return pd.read_sql_query(
                "SELECT * FROM spare_parts WHERE quantity <= min_order_level",
                self.conn)
        except pd.io.sql.DatabaseError as e:
            print(f"Error retrieving low stock items: {e}")
            return pd.DataFrame()
        
    def get_low_stock_items_by_dept(self, department_id):
        try:
            return pd.read_sql_query(
                "SELECT * FROM spare_parts WHERE department_id = ? AND quantity <= min_order_level",
                self.conn, params=(department_id,))
        except pd.io.sql.DatabaseError as e:
            print(f"Error retrieving low stock items: {e}")
            return pd.DataFrame()

    def record_transaction(self, part_id, transaction_type, quantity):
        cursor = self.conn.cursor()
        try:
            # First verify the part exists and has enough stock
            # print(f"recording transaction: {part_id}")  # hari
            part_df = self.get_part_by_id(part_id)
            if part_df is None or part_df.empty:
                raise ValueError(f"Part with ID {part_id} not found")

            part = part_df.iloc[0]
            current_quantity = int(part['quantity'])
            selected_part = int(part_id)

            if transaction_type == 'check_out' and current_quantity < quantity:
                raise ValueError(
                    f"Insufficient stock. Available: {current_quantity}, Requested: {quantity}"
                )

            # Record the transaction
            cursor.execute(
                '''
                INSERT INTO transactions (part_id, transaction_type, quantity, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (selected_part, transaction_type, quantity, datetime.now()))

            print(f"Recorded transaction: {transaction_type}")

            # Update stock quantity
            update_quantity = -quantity if transaction_type == 'check_out' else quantity
            cursor.execute(
                '''
                UPDATE spare_parts 
                SET quantity = quantity + ?, last_updated = ?
                WHERE id = ?
            ''', (update_quantity, datetime.now(), selected_part))

            self.conn.commit()
            return True, None  # Success, no error message
        except (sqlite3.Error, ValueError) as e:
            print(f"Error recording transaction: {e}")
            self.conn.rollback()
            return False, str(e)  # Return error status and message

    def get_transaction_history(self, days=30):
        query = '''
            SELECT t.*, sp.name, sp.part_number
            FROM transactions t
            JOIN spare_parts sp ON t.part_id = sp.id
            WHERE t.timestamp >= date('now', ?)
        '''
        try:
            return pd.read_sql_query(query,
                                     self.conn,
                                     params=[f'-{days} days'])
        except pd.io.sql.DatabaseError as e:
            print(f"Error retrieving transaction history: {e}")
            return pd.DataFrame()
