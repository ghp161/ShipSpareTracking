import sqlite3
import pandas as pd
from datetime import datetime

class DataManager:
    def __init__(self):
        self.conn = sqlite3.connect('inventory.db', check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Create spare parts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS spare_parts (
                id INTEGER PRIMARY KEY,
                part_number TEXT UNIQUE,
                name TEXT,
                description TEXT,
                quantity INTEGER,
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

    def add_spare_part(self, part_data):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO spare_parts (part_number, name, description, quantity, 
                min_order_level, min_order_quantity, barcode, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                part_data['part_number'], part_data['name'], part_data['description'],
                part_data['quantity'], part_data['min_order_level'],
                part_data['min_order_quantity'], part_data['barcode'],
                datetime.now()
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_spare_part(self, part_id, part_data):
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE spare_parts 
            SET name=?, description=?, quantity=?, min_order_level=?,
                min_order_quantity=?, last_updated=?
            WHERE id=?
        ''', (
            part_data['name'], part_data['description'], part_data['quantity'],
            part_data['min_order_level'], part_data['min_order_quantity'],
            datetime.now(), part_id
        ))
        self.conn.commit()

    def get_all_parts(self):
        return pd.read_sql_query("SELECT * FROM spare_parts", self.conn)

    def get_part_by_id(self, part_id):
        return pd.read_sql_query("SELECT * FROM spare_parts WHERE id=?", 
                                self.conn, params=[part_id])

    def get_low_stock_items(self):
        return pd.read_sql_query(
            "SELECT * FROM spare_parts WHERE quantity <= min_order_level", 
            self.conn
        )

    def record_transaction(self, part_id, transaction_type, quantity):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO transactions (part_id, transaction_type, quantity, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (part_id, transaction_type, quantity, datetime.now()))
        
        if transaction_type == 'check_out':
            quantity = -quantity
        
        cursor.execute('''
            UPDATE spare_parts 
            SET quantity = quantity + ?, last_updated = ?
            WHERE id = ?
        ''', (quantity, datetime.now(), part_id))
        
        self.conn.commit()

    def get_transaction_history(self, days=30):
        query = '''
            SELECT t.*, sp.name, sp.part_number
            FROM transactions t
            JOIN spare_parts sp ON t.part_id = sp.id
            WHERE t.timestamp >= date('now', ?)
        '''
        return pd.read_sql_query(query, self.conn, params=[f'-{days} days'])
