import sqlite3
from contextlib import contextmanager
import pandas as pd
from datetime import datetime
import os
from barcode_handler import BarcodeHandler

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
        cursor = self.conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def close(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()
            print("Database connection closed")
            
    def create_tables(self):
        with self.get_cursor() as cursor:
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
                        reason TEXT,
                        remarks TEXT,
                        FOREIGN KEY (part_id) REFERENCES spare_parts (id)
                    )
                ''')

                self.conn.commit()
                print("Database tables created successfully")
            except sqlite3.Error as e:
                print(f"Error creating tables: {e}")
                raise

    def update_department(self, dept_id, code, name, parent_id=None):
        with self.get_cursor() as cursor:
            try:
                # Prevent circular references
                if parent_id == dept_id:
                    return False, "Department cannot be its own parent"
                    
                cursor.execute('''
                    UPDATE departments 
                    SET code=?, name=?, parent_id=?
                    WHERE id=?
                ''', (code, name, parent_id, dept_id))
                self.conn.commit()
                return True, None
            except sqlite3.Error as e:
                return False, str(e)

    def delete_department(self, dept_id):
        with self.get_cursor() as cursor:
            try:
                # Check if department has children
                cursor.execute("SELECT COUNT(*) FROM departments WHERE parent_id=?", (dept_id,))
                child_count = cursor.fetchone()[0]
                if child_count > 0:
                    return False, "Cannot delete department with child departments"

                # Check if department is used in spare_parts
                cursor.execute("SELECT COUNT(*) FROM spare_parts WHERE department_id=?", (dept_id,))
                part_count = cursor.fetchone()[0]
                if part_count > 0:
                    return False, f"Cannot delete department - {part_count} inventory items reference it"

                cursor.execute("DELETE FROM departments WHERE id=?", (dept_id,))
                self.conn.commit()
                return True, None
            except sqlite3.Error as e:
                return False, str(e)

    def add_department(self, code, name, parent_id=None):
        with self.get_cursor() as cursor:
            try:
                cursor.execute('''
                    INSERT INTO departments (code, name, parent_id)
                    VALUES (?, ?, ?)
                ''', (code, name, parent_id))
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_all_departments_as_df(self):
        with self.get_cursor() as cursor:
            try:
                """Returns department data as a pandas DataFrame"""
                query = '''
                    SELECT d1.id, d1.code, d1.name, 
                        COALESCE(d2.name, 'Top Level') as parent_name
                    FROM departments d1
                    LEFT JOIN departments d2 ON d1.parent_id = d2.id
                    ORDER BY COALESCE(d1.parent_id, d1.id), d1.id
                '''
                return pd.read_sql_query(query, self.conn)
            except pd.io.sql.DatabaseError as e:
                print(f"Error retrieving parts: {e}")
                return pd.DataFrame()

    def get_parent_options(self):
        with self.get_cursor() as cursor:
            """Returns options for parent department dropdown"""
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id, name FROM departments WHERE parent_id IS NULL
            ''')
            return cursor.fetchall()
    
    def get_department_info(self, department_id):
        with self.get_cursor() as cursor:
            """Get department hierarchy info for a department ID"""
            query = '''
                SELECT d1.name as parent_department,
                    d2.name as child_department
                FROM departments d2
                LEFT JOIN departments d1 ON d2.parent_id = d1.id
                WHERE d2.id = ?
            '''
            result = pd.read_sql_query(query, self.conn, params=(department_id,))
            return result.iloc[0] if not result.empty else None
    
    def get_parent_departments(self):
        with self.get_cursor() as cursor:
            """Get all parent departments"""
            query = "SELECT id, name FROM departments WHERE parent_id IS NULL"
            return pd.read_sql_query(query, self.conn)

    def get_child_departments(self, parent_id):
        """Get child departments for a given parent"""
        if not parent_id:
            return pd.DataFrame(columns=['id', 'name'])
        query = "SELECT id, name FROM departments WHERE parent_id = ?"
        return pd.read_sql_query(query, self.conn, params=(parent_id,))
    
    def bulk_import_spare_parts(self, df, child_department_id, parent_department_id):
        """Bulk import spare parts with detailed error reporting"""
        results = []
        success_count = 0
        
        for index, row in df.iterrows():
            try:
                # Validate required fields
                part_number = str(row.get('part_number', '')).strip()
                name = str(row.get('name', '')).strip()
                description = str(row.get('description', '')).strip()
                box_no = str(row.get('box_no', '')).strip()
                ilms_code = str(row.get('ilms_code', '')).strip()
                compartment_no = str(row.get('compartment_no', '')).strip()
                
                # Check for required fields
                if not part_number:
                    results.append({
                        'part_number': 'MISSING',
                        'name': name if name else 'MISSING',
                        'status': 'failed',
                        'message': 'Part Number is required'
                    })
                    continue
                    
                if not name:
                    results.append({
                        'part_number': part_number,
                        'name': 'MISSING',
                        'status': 'failed',
                        'message': 'Part Name is required'
                    })
                    continue
                    
                # if not description:
                #     results.append({
                #         'part_number': part_number,
                #         'name': name,
                #         'status': 'failed',
                #         'message': 'Description is required'
                #     })
                #     continue
                    
                if not box_no:
                    results.append({
                        'part_number': part_number,
                        'name': name,
                        'status': 'failed',
                        'message': 'Box No is required'
                    })
                    continue
                    
                # if not ilms_code:
                #     results.append({
                #         'part_number': part_number,
                #         'name': name,
                #         'status': 'failed',
                #         'message': 'ILMS Code is required'
                #     })
                #     continue

                # Check if part number already exists in this department
                cursor = self.conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM spare_parts WHERE part_number = ? AND department_id = ?",
                    (part_number, child_department_id)
                )
                existing_count = cursor.fetchone()[0]
                
                if existing_count > 0:
                    results.append({
                        'part_number': part_number,
                        'name': name,
                        'status': 'failed',
                        'message': f'Part number already exists in this department'
                    })
                    continue

                # Prepare part data with proper type conversion
                part_data = {
                    'part_number': part_number,
                    'name': name,
                    'description': description,
                    'quantity': float(row.get('quantity', 0.0)),
                    'line_no': int(float(row.get('line_no', 1))),
                    'page_no': str(row.get('page_no', '')),
                    'order_no': str(row.get('order_no', '')),
                    'material_code': str(row.get('material_code', '')),
                    'ilms_code': ilms_code,
                    'item_denomination': str(row.get('item_denomination', '')),
                    'mustered': bool(row.get('mustered', False)),
                    'department_id': child_department_id,
                    'compartment_no': compartment_no,
                    'box_no': box_no,
                    'remark': str(row.get('remark', 'Imported via bulk upload')),
                    'min_order_level': float(row.get('min_order_level', 0.0)),
                    'min_order_quantity': float(row.get('min_order_quantity', 1.0)),
                    'barcode': str(row.get('barcode', '')),
                    'status': str(row.get('status', 'In Store')),
                    'last_maintenance_date': row.get('last_maintenance_date'),
                    'next_maintenance_date': row.get('next_maintenance_date')
                }

                # Handle date fields
                if part_data['last_maintenance_date']:
                    try:
                        part_data['last_maintenance_date'] = pd.to_datetime(part_data['last_maintenance_date']).strftime('%Y-%m-%d')
                    except:
                        part_data['last_maintenance_date'] = None
                        
                if part_data['next_maintenance_date']:
                    try:
                        part_data['next_maintenance_date'] = pd.to_datetime(part_data['next_maintenance_date']).strftime('%Y-%m-%d')
                    except:
                        part_data['next_maintenance_date'] = None

                # Add the part
                success = self.add_spare_part(part_data)
                
                if success:
                    success_count += 1
                    results.append({
                        'part_number': part_data['part_number'],
                        'name': part_data['name'],
                        'status': 'success',
                        'message': 'Successfully imported'
                    })
                else:
                    results.append({
                        'part_number': part_data['part_number'],
                        'name': part_data['name'],
                        'status': 'failed',
                        'message': 'Database insertion failed'
                    })
                
            except Exception as e:
                error_msg = str(e)
                # Make error message more user-friendly
                if "UNIQUE constraint failed" in error_msg:
                    error_msg = "Part number already exists in this department"
                elif "NOT NULL constraint failed" in error_msg:
                    error_msg = "Missing required field"
                    
                results.append({
                    'part_number': str(row.get('part_number', 'Unknown')),
                    'name': str(row.get('name', 'Unknown')),
                    'status': 'failed',
                    'message': f'{error_msg}'
                })
        
        # Determine overall success
        overall_success = success_count > 0
        overall_message = f"Processed {len(results)} records: {success_count} successful, {len(results) - success_count} failed"
        
        return results, overall_success, overall_message
    
    def add_spare_part(self, part_data):
        with self.get_cursor() as cursor:
            try:
                # Ensure quantity is converted to float
                part_data['quantity'] = float(part_data.get('quantity', 0))

                cursor.execute(
                    '''
                    INSERT INTO spare_parts (part_number, name, description, quantity,
                    line_no, page_no, order_no, material_code, ilms_code, item_denomination,
                    mustered, department_id, compartment_no,  box_no, remark, 
                    min_order_level, min_order_quantity, barcode, last_updated, status,
                    last_maintenance_date, next_maintenance_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                    (part_data['part_number'], part_data['name'],
                    part_data['description'], part_data['quantity'],
                    part_data['line_no'], part_data['page_no'], part_data['order_no'],
                    part_data['material_code'], part_data['ilms_code'],
                    part_data['item_denomination'], part_data['mustered'],
                    part_data['department_id'], part_data['compartment_no'],
                    part_data['box_no'], part_data['remark'],
                    part_data['min_order_level'], part_data['min_order_quantity'],
                    part_data['barcode'], datetime.now(), 
                    part_data['status'], part_data['last_maintenance_date'],
                    part_data['next_maintenance_date']))
                self.conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False
            except sqlite3.Error as e:
                print(f"Error adding spare part: {e}")
                return False

    def update_spare_part(self, part_id, part_data):
        with self.get_cursor() as cursor:
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

    def get_parts_by_department(self, department_id):
        """Get all parts for a specific department"""
        with self.get_cursor() as cursor:
            try:
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
                return df
            except pd.io.sql.DatabaseError as e:
                print(f"Error retrieving parts: {e}")
                return pd.DataFrame()
    
    def get_all_parts(self):
        with self.get_cursor() as cursor:
            try:
                query = '''
                    SELECT s.*, 
                        dp.name as parent_department,
                        dc.name as child_department
                    FROM spare_parts s
                    LEFT JOIN departments dc ON s.department_id = dc.id
                    LEFT JOIN departments dp ON dc.parent_id = dp.id
                '''
                df = pd.read_sql_query(query, self.conn)
                return df
            except pd.io.sql.DatabaseError as e:
                print(f"Error retrieving parts: {e}")
                return pd.DataFrame()

    def get_part_by_id(self, part_id):
        with self.get_cursor() as cursor:
            try:
                df = pd.read_sql_query(
                    f"SELECT * FROM spare_parts WHERE id= {part_id}", self.conn)
                if df.empty:
                    print(f"No part found with ID {part_id}")
                    return None
                return df
            except pd.io.sql.DatabaseError as e:
                print(f"Error retrieving part {part_id}: {e}")
                return None
        
    def is_barcode_unique(self, barcode):
        with self.get_cursor() as cursor:
            """Check if barcode already exists"""
            query = "SELECT 1 FROM spare_parts WHERE barcode = ?"
            result = pd.read_sql_query(query, self.conn, params=(barcode,))
            return result.empty

    def get_last_serial_number(self, dept_id):
        with self.get_cursor() as cursor:
            """Get the highest serial number from existing barcodes"""
            query = f"""
            SELECT barcode FROM spare_parts 
            WHERE barcode LIKE '%-%-%' and department_id= {dept_id}
            ORDER BY barcode DESC 
            LIMIT 1
            """
            result = pd.read_sql_query(query, self.conn)
            
            if not result.empty:
                last_barcode = result.iloc[0]['barcode']
                try:
                    return int(last_barcode.split('-')[-1])
                except (IndexError, ValueError):
                    return 0
            return 0

    def get_last_piece_stock_items(self):
        with self.get_cursor() as cursor:
            try:
                return pd.read_sql_query(
                    "SELECT * FROM spare_parts WHERE quantity = 1",
                    self.conn)
            except pd.io.sql.DatabaseError as e:
                print(f"Error retrieving low stock items: {e}")
                return pd.DataFrame()
        
    def get_last_piece_stock_items_by_dept(self, department_id):
        with self.get_cursor() as cursor:
            try:
                return pd.read_sql_query(
                    "SELECT * FROM spare_parts WHERE department_id = ?  AND quantity = 1",
                    self.conn, params=(department_id,))
            except pd.io.sql.DatabaseError as e:
                print(f"Error retrieving low stock items: {e}")
                return pd.DataFrame()
        
    def get_low_stock_items(self):
        with self.get_cursor() as cursor:
            try:
                return pd.read_sql_query(
                    "SELECT * FROM spare_parts WHERE quantity <= min_order_level AND quantity > 1",
                    self.conn)
            except pd.io.sql.DatabaseError as e:
                print(f"Error retrieving low stock items: {e}")
                return pd.DataFrame()
        
    def get_low_stock_items_by_dept(self, department_id):
        with self.get_cursor() as cursor:
            try:
                return pd.read_sql_query(
                    "SELECT * FROM spare_parts WHERE department_id = ? AND quantity <= min_order_level AND quantity > 1",
                    self.conn, params=(department_id,))
            except pd.io.sql.DatabaseError as e:
                print(f"Error retrieving low stock items: {e}")
                return pd.DataFrame()

    def record_transaction(self, part_id, transaction_type, quantity, reason, remarks):
        with self.get_cursor() as cursor:
            try:
                # First verify the part exists and has enough stock
                # print(f"recording transaction: {part_id}")  # hari
                quantity = float(quantity)
                part_df = self.get_part_by_id(part_id)
                if part_df is None or part_df.empty:
                    raise ValueError(f"Part with ID {part_id} not found")

                part = part_df.iloc[0]
                current_quantity = float(part['quantity'])
                selected_part = int(part_id)

                if transaction_type == 'check_out' and current_quantity < quantity:
                    raise ValueError(
                        f"Insufficient stock. Available: {current_quantity}, Requested: {quantity}"
                    )

                # Record the transaction
                cursor.execute(
                    '''
                    INSERT INTO transactions (part_id, transaction_type, quantity, timestamp, reason, remarks)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (selected_part, transaction_type, quantity, datetime.now(), reason, remarks))

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
        with self.get_cursor() as cursor:
            query = '''
                SELECT t.*, sp.name, sp.part_number, 
                    d1.name as parent_department,
                    d2.name as child_department
                FROM transactions t
                JOIN spare_parts sp ON t.part_id = sp.id
                LEFT JOIN departments d2 ON sp.department_id = d2.id
                LEFT JOIN departments d1 ON d2.parent_id = d1.id
                WHERE t.timestamp >= date('now', ?)
            '''
            try:
                return pd.read_sql_query(query,
                                        self.conn,
                                        params=[f'-{days} days'])
            except pd.io.sql.DatabaseError as e:
                print(f"Error retrieving transaction history: {e}")
                return pd.DataFrame()
        
    def get_transaction_history_by_department(self, department_id, days=30):
        with self.get_cursor() as cursor:
            """Get all parts for a specific department"""
            try:
                cursor = self.conn.cursor()
                query = '''
                    SELECT t.*, sp.name, sp.part_number, 
                        d1.name as parent_department,
                        d2.name as child_department
                    FROM transactions t
                    JOIN spare_parts sp ON t.part_id = sp.id
                    LEFT JOIN departments d2 ON sp.department_id = d2.id
                    LEFT JOIN departments d1 ON d2.parent_id = d1.id
                    WHERE t.timestamp >= date('now', ?) and sp.department_id = ?
                    ORDER BY sp.name
                '''
                df =  pd.read_sql_query(query, self.conn, params=(f'-{days} days', department_id,))
                return df
            except pd.io.sql.DatabaseError as e:
                print(f"Error retrieving parts: {e}")
                return pd.DataFrame()
