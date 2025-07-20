import streamlit as st
import pandas as pd  # Add this import at the top
from data_manager import DataManager
from barcode_handler import BarcodeHandler
from user_management import login_required
import navbar
from datetime import datetime
from app_settings import set_page_configuration

set_page_configuration()

current_page = "Inventory"
st.header(current_page)

navbar.nav(current_page)

class EnhancedDataManager(DataManager):

    def get_department_info(self, department_id):
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
        """Get all parent departments"""
        query = "SELECT id, name FROM departments WHERE parent_id IS NULL"
        return pd.read_sql_query(query, self.conn)

    def get_child_departments(self, parent_id):
        """Get child departments for a given parent"""
        if not parent_id:
            return pd.DataFrame(columns=['id', 'name'])
        query = "SELECT id, name FROM departments WHERE parent_id = ?"
        return pd.read_sql_query(query, self.conn, params=(parent_id,))
    
    def bulk_import_spare_parts(self, df, department_id):
        """Bulk import spare parts from DataFrame with department assignment"""
        cursor = self.conn.cursor()
        try:
            records = df.to_dict('records')
            cursor.execute("BEGIN TRANSACTION")
            
            for record in records:
                # Generate barcode if not provided
                if 'barcode' not in record or pd.isna(record.get('barcode')) or not record.get('barcode'):
                    record['barcode'] = BarcodeHandler.generate_unique_barcode()
                
                # Set default values
                record['department_id'] = department_id
                record['min_order_level'] = record.get('min_order_level', 0)
                record['min_order_quantity'] = record.get('min_order_quantity', 1)
                record['compartment_no'] = record.get('compartment_no', '')
                record['last_updated'] = datetime.now()
                
                # Ensure all required fields have values
                record['part_number'] = str(record['part_number'])
                record['name'] = str(record['name'])
                record['quantity'] = int(record['quantity'])
                record['line_no'] = int(record.get('line_no', 0))
                record['yard_no'] = int(record.get('yard_no', 0))
                
                cursor.execute('''
                    INSERT OR REPLACE INTO spare_parts (
                        part_number, name, description, quantity,
                        line_no, yard_no, page_no, order_no,
                        material_code, ilms_code, item_denomination,
                        mustered, department_id, compartment_no,
                        box_no, remark, min_order_level,
                        min_order_quantity, barcode, last_updated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    record['part_number'],
                    record['name'],
                    record.get('description', ''),
                    record['quantity'],
                    record['line_no'],
                    record['yard_no'],
                    str(record.get('page_no', '')),
                    str(record.get('order_no', '')),
                    str(record.get('material_code', '')),
                    str(record.get('ilms_code', '')),
                    str(record.get('item_denomination', '')),
                    bool(record.get('mustered', False)),
                    record['department_id'],
                    str(record.get('compartment_no', '')),
                    str(record.get('box_no', '')),
                    str(record.get('remark', '')),
                    int(record.get('min_order_level', 0)),
                    int(record.get('min_order_quantity', 1)),
                    record['barcode'],
                    record['last_updated']
                ))
            
            self.conn.commit()
            return True, f"Successfully imported {len(records)} records to selected department"
        except Exception as e:
            self.conn.rollback()
            return False, f"Error during import: {str(e)}"
        finally:
            cursor.close()

@login_required
def render_inventory_page():
     
    # Initialize enhanced data manager
    if 'enhanced_data_manager' not in st.session_state:
        st.session_state.enhanced_data_manager = EnhancedDataManager()
        
    # Initialize session state for department selection
    if 'selected_parent_dept' not in st.session_state:
        st.session_state.selected_parent_dept = None
    if 'selected_child_dept' not in st.session_state:
        st.session_state.selected_child_dept = None

    # Get current user's department from session state
    current_user_dept_id = st.session_state.get('user_department_id')
    
    # Create tabs - CORRECTED VERSION
    if st.session_state.user_role == 'User':
        tabs = st.tabs(["View Inventory"])
        view_tab = tabs[0]  # Get the first (and only) tab
    else:
        tabs = st.tabs(["View Inventory", "Add New Part", "Bulk Import"])
        view_tab, add_tab, bulk_tab = tabs  # Properly unpack the tabs

    with view_tab:
        if st.session_state.user_role == 'User':
            # For regular users, only show items from their department
            if not current_user_dept_id:
                st.error("You are not assigned to any department. Please contact administrator.")
                return
            print("dept_id:", current_user_dept_id)  # Add this temporarily
            # Show department info
            dept_info = st.session_state.enhanced_data_manager.get_department_info(current_user_dept_id)
            print("dept_info:", dept_info)  # Add this temporarily
            if dept_info is not None and not dept_info.empty:
                st.subheader(f"Inventory for {dept_info['child_department']} Department")
            
            # Get items only for user's department
            df = st.session_state.data_manager.get_parts_by_department(current_user_dept_id)
        else:
            df = st.session_state.data_manager.get_all_parts()

        # Search and filter
        search_term = st.text_input("Search parts by name, part_number, box_no or barcode")
        if search_term:
            df = df[df['name'].str.contains(search_term, case=False) |
                    df['part_number'].str.contains(search_term, case=False) |
                    df['barcode'].str.contains(search_term, case=False) |
                    df['box_no'].str.contains(search_term, case=False)]

        st.dataframe(df[[
            'part_number', 'name', 'quantity', 'parent_department', 'child_department', 
            'line_no', 'yard_no', 'page_no', 'order_no',
            'material_code', 'ilms_code', 'item_denomination',
            'mustered', 'compartment_no', 'box_no', 'remark',
            'min_order_level', 'barcode',
            'status', 'last_maintenance_date',
            'next_maintenance_date'
        ]],
        column_config={
            "mustered": st.column_config.CheckboxColumn("Mustered"),
            "quantity": st.column_config.NumberColumn("Qty", format="%d")
        },
        use_container_width=True,
        hide_index=True)

        if st.session_state.user_role in ['Admin', 'Super User']:
            # Edit part
            if not df.empty:
                part_to_edit = st.selectbox("Select part to edit",
                                            df['name'].tolist())

                if part_to_edit:
                    part_data = df[df['name'] == part_to_edit].iloc[0]
                    with st.form("edit_part_form"):
                        new_quantity = st.number_input("Quantity",
                                                    value=int(
                                                        part_data['quantity']),
                                                    min_value=0)
                        new_min_level = st.number_input(
                            "Minimum Order Level",
                            value=int(part_data['min_order_level']),
                            min_value=0)
                        new_min_quantity = st.number_input(
                            "Minimum Order Quantity",
                            value=int(part_data['min_order_quantity']),
                            min_value=1)                    
                        new_status = st.selectbox(
                            "Status",
                            ["Operational", "Under Maintenance", "In Store"],
                            index=["Operational", "Under Maintenance",
                                "In Store"].index(part_data['status']))
                        new_last_maintenance_date = st.date_input(
                            "Last Maintenance Date",
                            value=datetime.strptime(
                                part_data['last_maintenance_date'],
                                '%Y-%m-%d').date())
                        new_next_maintenance_date = st.date_input(
                            "Next Maintenance Date",
                            value=datetime.strptime(
                                part_data['next_maintenance_date'],
                                '%Y-%m-%d').date())

                        if st.form_submit_button("Update Part"):
                            if new_last_maintenance_date > datetime.now().date():
                                st.error(
                                    "Last Maintenance Date should not be greater than the current date."
                                )
                            elif new_next_maintenance_date <= datetime.now().date(
                            ):
                                st.error(
                                    "Next Maintenance Date should be greater than the current date."
                                )
                            else:
                                st.session_state.data_manager.update_spare_part(
                                    part_data['id'], {
                                        'name':
                                        part_data['name'],
                                        'description':
                                        part_data['description'],
                                        'quantity':
                                        new_quantity,
                                        'min_order_level':
                                        new_min_level,
                                        'min_order_quantity':
                                        new_min_quantity,                                   
                                        'status':
                                        new_status,
                                        'last_maintenance_date':
                                        new_last_maintenance_date.strftime(
                                            '%Y-%m-%d'),
                                        'next_maintenance_date':
                                        new_next_maintenance_date.strftime(
                                            '%Y-%m-%d')
                                    })
                                st.success("Part updated successfully!")
                                st.rerun()

    if st.session_state.user_role in ['Admin', 'Super User']:
        with add_tab:
            # Department selection
            parent_depts = st.session_state.enhanced_data_manager.get_parent_departments()
            if parent_depts.empty:
                st.error("No departments found. Please create departments first.")
                return
            
            selected_parent = st.selectbox(
                "Select Parent Department*",
                parent_depts['id'].tolist(),
                index=None,
                placeholder="Select Parent Department",
                format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0],
                key = "AddParentDept"
            )
            
            child_depts = st.session_state.enhanced_data_manager.get_child_departments(selected_parent)
            if child_depts.empty:
                st.error("No child departments found for selected parent.")
            else:            
                selected_child = st.selectbox(
                    "Select Child Department*",
                    child_depts['id'].tolist(),
                    index=None,
                    placeholder="Select Child Department",
                    format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                    key = "AddChildDept"
                )

            with st.form("add_part_form"):
                
                cols = st.columns(3)

                with cols[0]:
                    part_number = st.text_input("Part Number*", max_chars=20)
                    name = st.text_input("Part Name*", max_chars=100)
                    compartment_no = st.text_input("Compartment No", max_chars=20)
                    box_no = st.text_input("Box No", max_chars=20)                
                    quantity = st.number_input("Initial Quantity*", min_value=0)
                    line_no = st.number_input("Line No*", min_value=1)
                    yard_no = st.number_input("Yard No*", min_value=1)
                    
                with cols[1]:
                    page_no = st.text_input("Page No", max_chars=20)
                    order_no = st.text_input("Order No", max_chars=20)
                    material_code = st.text_input("Material Code", max_chars=50)
                    ilms_code = st.text_input("ILMS Code", max_chars=50)
                    item_denomination = st.text_input("Item Denomination", max_chars=100)
                    min_order_level = st.number_input("Minimum Order Level", min_value=0)
                    min_order_quantity = st.number_input("Minimum Order Quantity", min_value=1) 
                    
                with cols[2]:
                    last_maintenance_date = st.date_input("Last Maintenance Date")     
                    next_maintenance_date = st.date_input("Next Maintenance Date")
                    status = st.selectbox("Status", ["Operational", "Under Maintenance", "In Store"])                
                    description = st.text_area("Description")
                    remark = st.text_area("Remarks")
                    mustered = st.checkbox("Mustered")
                    

                if st.form_submit_button("Add Part"):
                    if part_number and name:
                        if last_maintenance_date > datetime.now().date():
                            st.error(
                                "Last Maintenance Date should not be greater than the current date."
                            )
                        elif next_maintenance_date <= datetime.now().date():
                            st.error(
                                "Next Maintenance Date should be greater than the current date."
                            )
                        else:
                            barcode = st.session_state.barcode_handler.generate_unique_barcode(
                            )
                            success = st.session_state.data_manager.add_spare_part(
                                {
                                    'part_number': part_number,
                                    'name': name,
                                    'description': description,
                                    'quantity': quantity,
                                    'line_no': line_no,
                                    'yard_no': yard_no,
                                    'page_no': page_no,
                                    'order_no': order_no,
                                    'material_code': material_code,
                                    'ilms_code': ilms_code,
                                    'item_denomination': item_denomination,
                                    'mustered': mustered,
                                    'department_id': selected_child,
                                    'compartment_no': compartment_no,
                                    'box_no': box_no,
                                    'remark': remark,
                                    'min_order_level': min_order_level,
                                    'min_order_quantity': min_order_quantity,
                                    'barcode': barcode,                                
                                    'status': status,
                                    'last_maintenance_date': last_maintenance_date.strftime('%Y-%m-%d'),
                                    'next_maintenance_date': next_maintenance_date.strftime('%Y-%m-%d')
                                })

                            if success:
                                st.success("Part added successfully!")
                                st.markdown(f"Generated barcode: `{barcode}`")
                                barcode_image = st.session_state.barcode_handler.generate_barcode(
                                    barcode)
                                st.image(f"data:image/png;base64,{barcode_image}")
                            else:
                                st.error("Part number already exists!")
                    else:
                        st.error("Part number and name are required!")

        with bulk_tab:
            bulk_import_section()

def bulk_import_section():
    """Bulk import from CSV with department selection"""
    st.subheader("Bulk Import from CSV")
    
    # Step 1: Department Selection
    st.markdown("### Step 1: Select Department")
    
    parent_depts = st.session_state.enhanced_data_manager.get_parent_departments()
    if parent_depts.empty:
        st.error("No departments found. Please create departments first.")
        return
    
    selected_parent = st.selectbox(
        "Select Parent Department*",
        parent_depts['id'].tolist(),
        index=None,
        placeholder="Select Parent Department",
        format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0]
    )
    
    child_depts = st.session_state.enhanced_data_manager.get_child_departments(selected_parent)
    if child_depts.empty:
        st.error("No child departments found for selected parent.")
        return
    
    selected_child = st.selectbox(
        "Select Child Department*",
        child_depts['id'].tolist(),
        index=None,
        placeholder="Select Child Department",
        format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0]
    )
    
    # Step 2: File Upload
    st.markdown("### Step 2: Upload CSV File")
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Upload a CSV file with spare parts data"
    )
    
    if uploaded_file is not None and selected_child:
        try:
            # Read the uploaded file
            df = pd.read_csv(uploaded_file)
            
            # Validate required columns
            required_columns = [
                'part_number', 'name', 'quantity',
                'line_no', 'yard_no'
            ]
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.error(f"Missing required columns: {', '.join(missing_columns)}")
                return
            
            # Data cleaning and type conversion
            df_clean = df.copy()
            
            # Handle numeric columns - fill NaN with 0 and convert to int
            numeric_cols = ['quantity', 'line_no', 'yard_no']
            for col in numeric_cols:
                if col in df_clean.columns:
                    df_clean[col] = df_clean[col].fillna(0).astype(int)
            
            # Handle text columns - fill NaN with empty string
            text_cols = [
                'page_no', 'order_no', 'material_code', 
                'ilms_code', 'item_denomination', 'box_no', 'Remark'
            ]
            for col in text_cols:
                if col in df_clean.columns:
                    df_clean[col] = df_clean[col].fillna('').astype(str)
            
            # Handle boolean column
            if 'mustered' in df_clean.columns:
                df_clean['mustered'] = df_clean['mustered'].fillna(False).astype(bool)
            
            # Show preview with department info
            st.subheader("Import Preview")
            st.info(f"All items will be assigned to: {child_depts[child_depts['id'] == selected_child]['name'].iloc[0]}")
            
            preview_df = df_clean.head().copy()
            preview_df['assigned_department'] = child_depts[child_depts['id'] == selected_child]['name'].iloc[0]
            st.dataframe(preview_df, hide_index=True)
            
            # Map CSV columns to database columns
            column_mapping = {
                'part_number': 'part_number',
                'name': 'name',
                'description': 'description',
                'quantity': 'quantity',
                'line_no': 'line_no',
                'yard_no': 'yard_no',
                'page_no': 'page_no',
                'order_no': 'order_no',
                'material_code': 'material_code',
                'ilms_code': 'ilms_code',
                'item_denomination': 'item_denomination',
                'mustered': 'mustered',
                'box_no': 'box_no',
                'Remark': 'remark',
                'barcode': 'barcode'
            }
            
            df_import = df_clean.rename(columns=column_mapping)
            
            # Step 3: Import Confirmation
            st.markdown("### Step 3: Confirm Import")
            if st.button(f"Import {len(df_clean)} Records"):
                with st.spinner(f"Importing {len(df_clean)} records..."):
                    success, message = st.session_state.enhanced_data_manager.bulk_import_spare_parts(
                        df_import, selected_child
                    )
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")

if __name__ == "__main__":
    render_inventory_page()
