import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import random
from user_management import login_required
import navbar
from app_settings import set_page_configuration

set_page_configuration()

current_page = "Data Management"
st.header(current_page)

navbar.nav(current_page)

@login_required
def render_data_management_page():
    # Restrict access to Super User only
    if st.session_state.user_role != 'Super User':
        st.error("🔒 Access Denied: This page is only available for Super Users")
        return

    #st.title("Data Management - Super User Only")
    st.warning("🚨 **Warning**: These operations will permanently delete and reset all data!")

    tab1, tab2, tab3 = st.tabs(["Reset Database", "Sample Data Setup", "Database Status"])

    with tab1:
        st.subheader("Reset Database Tables")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🗑️ Reset Departments", type="secondary"):
                if reset_table("departments"):
                    st.success("Departments table reset successfully!")
        
        with col2:
            if st.button("🗑️ Reset Spare Parts", type="secondary"):
                if reset_table("spare_parts"):
                    st.success("Spare parts table reset successfully!")
        
        with col3:
            if st.button("🗑️ Reset Transactions", type="secondary"):
                if reset_table("transactions"):
                    st.success("Transactions table reset successfully!")

        st.markdown("---")
        
        if st.button("💥 Reset ALL Tables", type="primary"):
            if st.checkbox("I understand this will delete ALL data permanently"):
                if reset_all_tables():
                    st.success("All tables reset successfully!")
                    st.rerun()

    with tab2:
        st.subheader("Generate Sample Data")
        
        if st.button("🏗️ Create Sample Departments", type="primary"):
            if create_sample_departments():
                st.success("Sample departments created successfully!")
                st.rerun()
        
        if st.button("📦 Create Sample Spare Parts", type="primary"):
            if create_sample_spare_parts():
                st.success("Sample spare parts created successfully!")
                st.rerun()
        
        if st.button("📊 Create Sample Transactions", type="primary"):
            if create_sample_transactions():
                st.success("Sample transactions created successfully!")
                st.rerun()

        st.markdown("---")
        
        if st.button("🚀 Generate Complete Sample Dataset", type="secondary"):
            if generate_complete_sample_data():
                st.success("Complete sample dataset created successfully!")
                st.rerun()

    with tab3:
        st.subheader("Database Status")
        display_database_status()

def reset_table(table_name):
    """Reset a specific table and its primary key sequence"""
    try:
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        
        # Delete all data from table
        cursor.execute(f"DELETE FROM {table_name}")
        
        # Reset SQLite sequence for primary key only if the table uses AUTOINCREMENT
        # Check if the table exists in sqlite_sequence
        #cursor.execute("SELECT name FROM sqlite_sequence WHERE name=?", (table_name,))
        #table_in_sequence = cursor.fetchone()
        
        #if table_in_sequence:
        #    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}'")
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error resetting {table_name}: {str(e)}")
        return False

def reset_all_tables():
    """Reset all three main tables"""
    try:
        tables = ["transactions", "spare_parts", "departments"]
        for table in tables:
            if not reset_table(table):
                return False
        return True
    except Exception as e:
        st.error(f"Error resetting all tables: {str(e)}")
        return False

def create_sample_departments():
    """Create hierarchical department structure"""
    try:
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()

        # First, check if departments already exist to avoid duplicates
        cursor.execute("SELECT COUNT(*) FROM departments")
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            st.warning(f"Departments table already contains {existing_count} records. Skipping creation.")
            conn.close()
            return True

        # Parent departments (Main areas of the ship)
        parent_departments = [
            ("ENG", "Engineering"),
            ("DECK", "Deck Operations"),
            ("NAV", "Navigation"),
            ("CAB", "Cabins & Accommodation"),
            ("GAL", "Galley & Provisions")
        ]

        # Child departments for each parent
        child_departments = {
            "ENG": [
                ("MEP", "Main Engine Parts"),
                ("AEP", "Auxiliary Engine Parts"),
                ("ELC", "Electrical Systems"),
                ("HUL", "Hull Maintenance")
            ],
            "DECK": [
                ("CAR", "Cargo Operations"),
                ("ANC", "Anchoring Systems"),
                ("MOR", "Mooring Equipment"),
                ("LIF", "Life Saving Appliances")
            ],
            "NAV": [
                ("COM", "Communication Systems"),
                ("RAD", "Radar & Navigation"),
                ("AIS", "AIS & GPS Systems")
            ],
            "CAB": [
                ("PLU", "Plumbing Systems"),
                ("HVAC", "HVAC Systems"),
                ("FIR", "Fire Fighting Equipment")
            ],
            "GAL": [
                ("KIT", "Kitchen Equipment"),
                ("REF", "Refrigeration"),
                ("PRO", "Provisions Storage")
            ]
        }

        # Insert parent departments
        parent_ids = {}
        for code, name in parent_departments:
            cursor.execute(
                "INSERT INTO departments (code, name, parent_id) VALUES (?, ?, ?)",
                (code, name, None)
            )
            parent_ids[code] = cursor.lastrowid

        # Insert child departments
        for parent_code, children in child_departments.items():
            parent_id = parent_ids[parent_code]
            for child_code, child_name in children:
                cursor.execute(
                    "INSERT INTO departments (code, name, parent_id) VALUES (?, ?, ?)",
                    (child_code, child_name, parent_id)
                )

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error creating sample departments: {str(e)}")
        return False

def create_sample_spare_parts():
    """Create sample spare parts data"""
    try:
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()

        # Check if spare parts already exist
        cursor.execute("SELECT COUNT(*) FROM spare_parts")
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            st.warning(f"Spare parts table already contains {existing_count} records. Skipping creation.")
            conn.close()
            return True

        # Get all child departments
        cursor.execute("SELECT id, code, name FROM departments WHERE parent_id IS NOT NULL")
        child_depts = cursor.fetchall()

        if not child_depts:
            st.error("No child departments found. Please create departments first.")
            return False

        # Sample spare parts data
        spare_part_categories = {
            "MEP": [
                ("Piston Ring Set", "High-pressure piston rings for main engine", "MEP-PRS-001"),
                ("Cylinder Liner", "Main engine cylinder liner assembly", "MEP-CL-002"),
                ("Fuel Injector", "Electronic fuel injector unit", "MEP-FI-003"),
                ("Turbocharger Blade", "Turbine blades for turbocharger", "MEP-TCB-004"),
                ("Bearing Set", "Main bearing set for crankshaft", "MEP-BS-005")
            ],
            "AEP": [
                ("Generator Brush", "Carbon brushes for auxiliary generator", "AEP-GB-001"),
                ("Cooling Pump Impeller", "Impeller for cooling water pump", "AEP-CPI-002"),
                ("Air Compressor Valve", "Reed valves for air compressor", "AEP-ACV-003"),
                ("Heat Exchanger Tube", "Copper tubes for heat exchanger", "AEP-HET-004")
            ],
            "ELC": [
                ("Circuit Breaker", "Main circuit breaker 400A", "ELC-CB-001"),
                ("Motor Starter", "Electric motor starter unit", "ELC-MS-002"),
                ("Control Relay", "24V DC control relay", "ELC-CR-003"),
                ("Cable Terminal", "High voltage cable terminals", "ELC-CT-004")
            ],
            "CAR": [
                ("Crane Wire Rope", "20mm wire rope for deck crane", "CAR-CWR-001"),
                ("Container Lock", "Twist locks for containers", "CAR-CL-002"),
                ("Hatch Cover Seal", "Rubber seals for hatch covers", "CAR-HCS-003")
            ],
            "COM": [
                ("VHF Radio Unit", "Marine VHF communication radio", "COM-VHF-001"),
                ("Satellite Phone", "Satellite communication phone", "COM-SAT-002"),
                ("Antenna Cable", "Coaxial cable for antennas", "COM-AC-003")
            ]
        }

        part_id = 1
        for dept_id, dept_code, dept_name in child_depts:
            # Get parts for this department category or use default
            parts = spare_part_categories.get(dept_code, [
                (f"General Part {i}", f"General spare part for {dept_name}", f"{dept_code}-GP-{i:03d}")
                for i in range(1, 6)
            ])

            for i, (name, description, part_number) in enumerate(parts):
                # Create variations for each base part
                for variant in range(4):  # 4 variants per base part
                    variant_part_number = f"{part_number}-V{variant+1:02d}"
                    variant_name = f"{name} - Variant {variant+1}"
                    
                    # Create stock levels: some normal, some low stock, some last piece
                    if variant == 0:  # Last piece level
                        quantity = 1
                        min_order_level = 5
                    elif variant == 1:  # Low stock
                        quantity = random.randint(2, 4)
                        min_order_level = 10
                    else:  # Normal stock
                        quantity = random.randint(15, 50)
                        min_order_level = 10
                    
                    min_order_quantity = random.randint(5, 20)
                    
                    cursor.execute('''
                        INSERT INTO spare_parts (
                            part_number, name, description, quantity, line_no, page_no,
                            order_no, material_code, ilms_code, item_denomination,
                            mustered, department_id, compartment_no, box_no, remark,
                            min_order_level, min_order_quantity, barcode, last_updated, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        variant_part_number,
                        variant_name,
                        f"{description} - Specific variant for specialized use",
                        quantity,
                        random.randint(1, 10),
                        f"P{random.randint(1, 5)}",
                        f"ORD-{random.randint(1000, 9999)}",
                        f"MAT-{random.randint(100, 999)}",
                        f"ILMS-{random.randint(1000, 9999)}",
                        "Pieces",
                        random.choice([True, False]),
                        dept_id,
                        f"C{random.randint(1, 10)}",
                        f"B{random.randint(1, 20)}",
                        "Sample data for testing",
                        min_order_level,
                        min_order_quantity,
                        f"{dept_code}-{variant_part_number}",
                        datetime.now(),
                        random.choice(["In Store", "Operational", "Under Maintenance"])
                    ))
                    
                    part_id += 1

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error creating sample spare parts: {str(e)}")
        return False

def create_sample_transactions():
    """Create sample transaction data for the last 3 months"""
    try:
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()

        # Check if transactions already exist
        cursor.execute("SELECT COUNT(*) FROM transactions")
        existing_count = cursor.fetchone()[0]
        
        if existing_count > 0:
            st.warning(f"Transactions table already contains {existing_count} records. Skipping creation.")
            conn.close()
            return True

        # Get all spare parts
        cursor.execute("SELECT id, quantity, min_order_level FROM spare_parts")
        spare_parts = cursor.fetchall()

        if not spare_parts:
            st.error("No spare parts found. Please create spare parts first.")
            return False

        # Generate transactions for the last 90 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        transaction_reasons = {
            'check_out': ['Operational Use', 'Maintenance', 'Replacement', 'Emergency'],
            'check_in': ['Restock', 'Return from Maintenance', 'New Supply']
        }

        for part_id, current_quantity, min_order_level in spare_parts:
            # Generate transaction pattern for this part
            transactions_count = random.randint(5, 20)
            
            for _ in range(transactions_count):
                # Random date within the last 90 days
                days_ago = random.randint(0, 90)
                transaction_date = end_date - timedelta(days=days_ago)
                
                # Decide transaction type with bias towards check_out for realism
                transaction_type = random.choices(
                    ['check_out', 'check_in'], 
                    weights=[70, 30]
                )[0]
                
                if transaction_type == 'check_out':
                    quantity = random.randint(1, min(5, current_quantity))
                    reason = random.choice(transaction_reasons['check_out'])
                    remarks = f"Used for {reason.lower()}"
                else:
                    quantity = random.randint(1, 10)
                    reason = random.choice(transaction_reasons['check_in'])
                    remarks = f"Received from {reason.lower()}"
                
                cursor.execute('''
                    INSERT INTO transactions (part_id, transaction_type, quantity, timestamp, reason, remarks)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (part_id, transaction_type, quantity, transaction_date, reason, remarks))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error creating sample transactions: {str(e)}")
        return False

def generate_complete_sample_data():
    """Generate complete sample dataset in correct order"""
    try:
        st.info("Starting sample data generation...")
        
        if not create_sample_departments():
            return False
        st.success("✓ Departments created")
        
        if not create_sample_spare_parts():
            return False
        st.success("✓ Spare parts created")
        
        if not create_sample_transactions():
            return False
        st.success("✓ Transactions created")
        
        return True
    except Exception as e:
        st.error(f"Error generating complete sample data: {str(e)}")
        return False

def display_database_status():
    """Display current database statistics"""
    try:
        conn = sqlite3.connect('inventory.db')
        
        # Get table counts
        tables = ['departments', 'spare_parts', 'transactions', 'users']
        stats = {}
        
        for table in tables:
            try:
                count = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {table}", conn).iloc[0]['count']
                stats[table] = count
            except:
                stats[table] = 0  # Table might not exist
        
        # Display statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Departments", stats['departments'])
        with col2:
            st.metric("Spare Parts", stats['spare_parts'])
        with col3:
            st.metric("Transactions", stats['transactions'])
        with col4:
            st.metric("Users", stats['users'])
        
        # Show low stock alerts
        st.subheader("Current Stock Alerts")
        
        try:
            low_stock = pd.read_sql_query('''
                SELECT name, quantity, min_order_level, min_order_quantity 
                FROM spare_parts 
                WHERE quantity <= min_order_level AND quantity > 1
                ORDER BY quantity ASC
            ''', conn)
            
            last_piece = pd.read_sql_query('''
                SELECT name, quantity, min_order_level, min_order_quantity 
                FROM spare_parts 
                WHERE quantity = 1
                ORDER BY name
            ''', conn)
            
            if not low_stock.empty:
                st.warning(f"🚨 {len(low_stock)} Low Stock Items")
                st.dataframe(low_stock, hide_index=True)
            
            if not last_piece.empty:
                st.error(f"🔥 {len(last_piece)} Last Piece Level Items")
                st.dataframe(last_piece, hide_index=True)
                
        except Exception as e:
            st.info("No stock alert data available yet")
        
        conn.close()
        
    except Exception as e:
        st.error(f"Error displaying database status: {str(e)}")

if __name__ == "__main__":
    render_data_management_page()