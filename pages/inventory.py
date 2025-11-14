import streamlit as st
from app_settings import set_page_configuration

set_page_configuration()

import pandas as pd  # Add this import at the top
from data_manager import DataManager
from barcode_handler import BarcodeHandler
from user_management import login_required, init_session_state, check_and_restore_session
import navbar
from datetime import datetime
import time



current_page = "Inventory"
st.header(current_page)

# Initialize session state and check for existing session
init_session_state()
if not st.session_state.authenticated:
    check_and_restore_session()

navbar.nav(current_page)

@login_required
def render_inventory_page():

    # Initialize session state if needed
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()
    if 'barcode_handler' not in st.session_state:
        st.session_state.barcode_handler = BarcodeHandler()
             
    # Initialize session state for department selection
    if 'selected_parent_dept' not in st.session_state:
        st.session_state.selected_parent_dept = None
    if 'selected_child_dept' not in st.session_state:
        st.session_state.selected_child_dept = None
    if 'selected_part' not in st.session_state:
        st.session_state.selected_part = None
    if 'selected_department_id' not in st.session_state:
        st.session_state.selected_department_id = None

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
            #print("dept_id:", current_user_dept_id)  # Add this temporarily
            # Show department info
            dept_info = st.session_state.data_manager.get_department_info(current_user_dept_id)
            #print("dept_info:", dept_info)  # Add this temporarily
            if dept_info is not None and not dept_info.empty:
                st.subheader(f"Inventory for {dept_info['child_department']} Department")
            
            # Get items only for user's department
            df = st.session_state.data_manager.get_parts_by_department(current_user_dept_id)

            # Search and filter 
            search_term = st.text_input("Search parts by name, description, part_number, box_no, compartment_no, ilms_code or barcode")
            if search_term:
                df = df[df['name'].str.contains(search_term, case=False) |
                        df['description'].str.contains(search_term, case=False) |
                        df['part_number'].str.contains(search_term, case=False) |
                        df['barcode'].str.contains(search_term, case=False) |
                        df['ilms_code'].str.contains(search_term, case=False) |
                        df['compartment_no'].str.contains(search_term, case=False) |
                        df['box_no'].str.contains(search_term, case=False)]

            if not df.empty:
                st.dataframe(df[[
                    'part_number', 'name', 'quantity', 'parent_department', 'child_department', 
                    'line_no', 'description', 'page_no', 'order_no',
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
            else:
                st.info("""
                📱 Stock information not available for selected department.
                """)
        else:
            # Admin/Super User view with department selection
            selected_child = ""
            cols = st.columns(2)

            with cols[0]:
                # Department selection
                parent_depts = st.session_state.data_manager.get_parent_departments()
                if parent_depts.empty:
                    st.error("No departments found. Please create departments first.")
                    return
                
                selected_parent = st.selectbox(
                    "Select Parent Department*",
                    parent_depts['id'].tolist(),
                    index=None,
                    placeholder="Select Parent Department",
                    format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0],
                    key = "ListParentDept"
                )
            
            with cols[1]:
                if selected_parent:
                    child_depts = st.session_state.data_manager.get_child_departments(selected_parent)
                    if not child_depts.empty:                                
                        selected_child = st.selectbox(
                            "Select Child Department*",
                            child_depts['id'].tolist(),
                            index=None,
                            placeholder="Select Child Department",
                            format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                            key = "ListChildDept"
                        )

            if selected_child is not None:
                df = st.session_state.data_manager.get_parts_by_department(selected_child)
                st.session_state.inventory_data = df

                # Search and filter 
                search_term = st.text_input("Search parts by name, description, part_number, box_no, compartment_no, ilms_code or barcode")
                if search_term:
                    df = df[df['name'].str.contains(search_term, case=False) |
                            df['description'].str.contains(search_term, case=False) |
                            df['part_number'].str.contains(search_term, case=False) |
                            df['barcode'].str.contains(search_term, case=False) |
                            df['ilms_code'].str.contains(search_term, case=False) |
                            df['compartment_no'].str.contains(search_term, case=False) |
                            df['box_no'].str.contains(search_term, case=False)]

                if not df.empty:
                    #st.subheader("Inventory Items - Select a row to edit")
                    
                    # Create a copy for display
                    display_df = df[[
                        'part_number', 'name', 'quantity', 'parent_department', 'child_department', 
                        'description', 'item_denomination', 'compartment_no', 'box_no', 'ilms_code', 'min_order_level', 'barcode', 'status', 'department_id'
                    ]].copy()
                    
                    # Add row numbers for selection
                    display_df['row_id'] = range(len(display_df))
                    
                    # Create selection form
                    with st.form("row_selection_form"):
                        # Display the dataframe
                        st.dataframe(
                            display_df.drop(columns=['row_id']),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Selection dropdown
                        row_options = {f"Row {i+1}: {row['part_number']} (Name: {row['name']}) (Dept: {row['department_id']})": row['row_id'] 
                                    for i, row in display_df.iterrows()}
                        selected_label = st.selectbox(
                            "Select a row to edit:",
                            options=[""] + list(row_options.keys()),
                            key="row_selector"
                        )
                        
                        submitted = st.form_submit_button("Select Row")
                        
                        if submitted and selected_label:
                            selected_row_id = row_options[selected_label]
                            selected_row = display_df[display_df['row_id'] == selected_row_id].iloc[0]
                            
                            # Store selection in session state
                            st.session_state.selected_part = selected_row['part_number']
                            st.session_state.selected_department_id = selected_row['department_id']
                            
                            # Rerun to show the form immediately
                            st.rerun()
                    
                    # Show edit form if a row is selected
                    if st.session_state.selected_part and st.session_state.selected_department_id:
                        selected_part_data = df[
                            (df['part_number'] == st.session_state.selected_part) & 
                            (df['department_id'] == st.session_state.selected_department_id)
                        ].iloc[0]
                        
                        show_edit_form(selected_part_data)
                else:
                    st.info("""
                    📱 Stock information not available for selected department.
                    """)                
            else:
                st.info("""
                📱 Please select Department to view stock information.
                """)

    if st.session_state.user_role in ['Admin', 'Super User']:
        with add_tab:
            cols = st.columns(2)

            with cols[0]:
                # Department selection
                parent_depts = st.session_state.data_manager.get_parent_departments()
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
            
            with cols[1]:
                child_depts = st.session_state.data_manager.get_child_departments(selected_parent)
                if not child_depts.empty:            
                    selected_child = st.selectbox(
                        "Select Child Department*",
                        child_depts['id'].tolist(),
                        index=None,
                        placeholder="Select Child Department",
                        format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                        key = "AddChildDept"
                    )

            with st.form("add_part_form"):
                barcode_lbl = ''
                if selected_parent and selected_child:
                    # Get department names
                    parent_dept_name = parent_depts[parent_depts['id'] == selected_parent]['name'].iloc[0]
                    child_dept_name = child_depts[child_depts['id'] == selected_child]['name'].iloc[0]
                    
                    # Get last serial number from database
                    last_serial = st.session_state.data_manager.get_last_serial_number(selected_child)
                    
                    # Generate barcode
                    barcode_lbl = generate_custom_barcode(
                        parent_dept_name, 
                        child_dept_name, 
                        last_serial
                    )
                    
                cols = st.columns(3)

                with cols[0]:
                    part_number = st.text_input("Part Number*", max_chars=20)
                    name = st.text_input("Part Name*", max_chars=100)
                    compartment_no = st.text_input("Compartment Name*", max_chars=20)
                    box_no = st.text_input("Box No*", max_chars=20)                
                    quantity = st.text_input("Initial Quantity*", value="0.0")
                    line_no = st.number_input("Line No*", min_value=1)
                    page_no = st.text_input("Page No", max_chars=20)
                    #yard_no = st.number_input("Yard No*", min_value=1)
                    
                with cols[1]:      
                    barcode = st.text_input("Barcode", value=barcode_lbl, disabled=True)              
                    order_no = st.text_input("Order No", max_chars=20)
                    material_code = st.text_input("Material Code", max_chars=50)
                    ilms_code = st.text_input("ILMS Code*", max_chars=50)
                    item_denomination = st.text_input("Item Denomination", max_chars=100)
                    min_order_level = st.number_input("Minimum Order Level", min_value=0)
                    min_order_quantity = st.number_input("Minimum Order Quantity", min_value=1) 
                    
                with cols[2]:                    
                    last_maintenance_date = st.date_input("Last Maintenance Date")     
                    next_maintenance_date = st.date_input("Next Maintenance Date")
                    status = st.selectbox("Status", ["In Store", "Operational", "Under Maintenance"])                
                    description = st.text_area("Description*")
                    remark = st.text_area("Remarks*")
                    mustered = st.checkbox("Mustered")
                    

                if st.form_submit_button("Add Part"):
                    if part_number and name and ilms_code and description and remark and compartment_no and box_no and barcode:
                        # Convert quantity to float
                        quantity_float = float(quantity)
                        if last_maintenance_date > datetime.now().date():
                            st.error(
                                "Last Maintenance Date should not be greater than the current date."
                            )
                        elif next_maintenance_date <= datetime.now().date():
                            st.error(
                                "Next Maintenance Date should be greater than the current date."
                            )
                        else:
                            #barcode = st.session_state.barcode_handler.generate_unique_barcode()
                            success = st.session_state.data_manager.add_spare_part(
                                {
                                    'part_number': part_number,
                                    'name': name,
                                    'description': description,
                                    'quantity': quantity_float,
                                    'line_no': line_no,
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
                        st.error("Part number, Box No, Remarks, Name, Desc, Compartment Name, ILMS Code and Barcode are required!")

        with bulk_tab:
            bulk_import_section()


def show_edit_form(part_data):
    """Show edit form for selected part"""
    st.subheader(f"Edit Part: {part_data['name']} ({part_data['part_number']})")

    # Clear selection button
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("✖️ Clear Selection", use_container_width=True):
            st.session_state.selected_part = None
            st.session_state.selected_department_id = None
            st.rerun()
    
    with col2:
        if st.button("🗑️ Delete Part", type="secondary", use_container_width=True):
            handle_delete_part(part_data)
    
    # Define available status options
    status_options = ["In Store", "Operational", "Under Maintenance"]
    
    # Get current status (handle empty/NaN values)
    current_status = str(part_data['status']).strip() if pd.notna(part_data['status']) else None
    
    # Handle date conversions safely
    try:
        if pd.isna(part_data['last_maintenance_date']) or not part_data['last_maintenance_date']:
            last_default_date = None
        else:
            date_str = str(part_data['last_maintenance_date']).strip()
            last_default_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        last_default_date = None

    try:
        if pd.isna(part_data['next_maintenance_date']) or not part_data['next_maintenance_date']:
            next_default_date = None
        else:
            date_str = str(part_data['next_maintenance_date']).strip()
            next_default_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        next_default_date = None

    with st.form("edit_part_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            new_quantity = st.number_input(
                "Quantity", 
                value=float(part_data['quantity']), 
                min_value=0.0, 
                step=0.1,
                format="%.3f"
            )
            new_min_level = st.number_input("Minimum Order Level", value=int(part_data['min_order_level']), min_value=0)
            new_min_quantity = st.number_input("Minimum Order Quantity", value=int(part_data['min_order_quantity']), min_value=1)
            new_status = st.selectbox(
                "Status*",
                options=status_options,
                index=None if current_status not in status_options else status_options.index(current_status),
                placeholder="Select a status...",
                key=f"status_select_{part_data['part_number']}_{part_data['department_id']}"
            )
        
        with col2:
            new_last_maintenance_date = st.date_input(
                "Last Maintenance Date (optional)",
                value=last_default_date,
                key=f"last_maint_{part_data['part_number']}_{part_data['department_id']}"
            )
            new_next_maintenance_date = st.date_input(
                "Next Maintenance Date (optional)",
                value=next_default_date,
                key=f"next_maint_{part_data['part_number']}_{part_data['department_id']}"
            )
            # Display readonly fields for information
            st.text_input("Part Number", value=part_data['part_number'], disabled=True)
            st.text_input("Name", value=part_data['name'], disabled=True)
            st.text_input("Barcode", value=part_data['barcode'], disabled=True)
            st.text_input("Department", value=f"{part_data['parent_department']} - {part_data['child_department']}", disabled=True)

        # Convert back to string for database
        if new_last_maintenance_date:
            nlast_maint_date_str = new_last_maintenance_date.strftime('%Y-%m-%d')
        else:
            nlast_maint_date_str = None
        
        if new_next_maintenance_date:
            nnext_maint_date_str = new_next_maintenance_date.strftime('%Y-%m-%d')
        else:
            nnext_maint_date_str = None

        if st.form_submit_button("Update Part"):
            if new_last_maintenance_date and new_last_maintenance_date > datetime.now().date():
                st.error("Last Maintenance Date should not be greater than the current date.")
            elif new_next_maintenance_date and new_next_maintenance_date <= datetime.now().date():
                st.error("Next Maintenance Date should be greater than the current date.")
            else:
                # Use part_number AND department_id in WHERE condition
                success = update_part_by_part_number_and_department(
                    part_data['part_number'],
                    part_data['department_id'],
                    {
                        'quantity': new_quantity,
                        'min_order_level': new_min_level,
                        'min_order_quantity': new_min_quantity,
                        'status': new_status,
                        'last_maintenance_date': nlast_maint_date_str,
                        'next_maintenance_date': nnext_maint_date_str
                    }
                )
                if success:
                    st.success("Part updated successfully!")
                    time.sleep(2)
                    st.session_state.selected_part = None
                    st.session_state.selected_department_id = None
                    st.rerun()
                else:
                    st.error("Failed to update part. Please try again.")

def update_part_by_part_number_and_department(part_number, department_id, update_data):
    """Update part using part_number AND department_id in WHERE condition"""
    try:
        conn = st.session_state.data_manager.conn
        cursor = conn.cursor()
        
        # Build the update query dynamically based on provided fields
        set_clauses = []
        params = []
        
        if 'quantity' in update_data:
            set_clauses.append("quantity = ?")
            params.append(int(update_data['quantity']))  # Convert to native int
        
        if 'min_order_level' in update_data:
            set_clauses.append("min_order_level = ?")
            params.append(int(update_data['min_order_level']))  # Convert to native int
            
        if 'min_order_quantity' in update_data:
            set_clauses.append("min_order_quantity = ?")
            params.append(int(update_data['min_order_quantity']))  # Convert to native int
            
        if 'status' in update_data:
            set_clauses.append("status = ?")
            params.append(update_data['status'])
            
        if 'last_maintenance_date' in update_data:
            set_clauses.append("last_maintenance_date = ?")
            params.append(update_data['last_maintenance_date'])
            
        if 'next_maintenance_date' in update_data:
            set_clauses.append("next_maintenance_date = ?")
            params.append(update_data['next_maintenance_date'])
        
        # Always update last_updated
        set_clauses.append("last_updated = ?")
        params.append(datetime.now())
        
        # Convert part_number and department_id to native types
        native_part_number = str(part_number)  # Ensure string
        native_department_id = int(department_id)  # Convert to native int
        
        # Add part_number and department_id to params for WHERE clause
        params.append(native_part_number)
        params.append(native_department_id)
        
        query = f"UPDATE spare_parts SET {', '.join(set_clauses)} WHERE part_number = ? AND department_id = ?"
        print(f"update inventory query: {query}")
        print(f"update inventory params: {params}")
        
        cursor.execute(query, params)
        conn.commit()
        
        # Check if any rows were affected
        if cursor.rowcount > 0:
            print(f"Successfully updated {cursor.rowcount} row(s)")
            return True
        else:
            print("No rows were updated - check if part_number and department_id match")
            return False
        
    except Exception as e:
        st.error(f"Error updating part: {e}")
        print(f"Detailed error: {str(e)}")
        return False

def handle_delete_part(part_data):
    """Handle part deletion with transaction check"""
    try:
        conn = st.session_state.data_manager.conn
        cursor = conn.cursor()
        
        # Check for transactions first
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE part_id IN (SELECT id FROM spare_parts WHERE part_number = ? AND department_id = ?)",
            (part_data['part_number'], part_data['department_id'])
        )
        transaction_count = cursor.fetchone()[0]
        
        if transaction_count > 0:
            # If transactions exist, ask for confirmation
            st.warning(f"⚠️ This part has {transaction_count} transaction(s) in the system. Are you sure you want to delete it? This will also remove all associated transaction history.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"✅ Yes, Delete Part with {transaction_count} Transactions", type="primary", use_container_width=True):
                    delete_part(part_data)
            with col2:
                if st.button("❌ Cancel Delete", use_container_width=True):
                    st.info("Delete operation cancelled")
                    # Optional: add a small delay and rerun to clear the confirmation
                    time.sleep(1)
                    st.rerun()
        else:
            # No transactions exist, proceed with deletion directly
            st.warning("Are you sure you want to delete this part?")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Delete Part", type="primary", use_container_width=True):
                    delete_part(part_data)
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.info("Delete operation cancelled")
            
    except Exception as e:
        st.error(f"Error checking transactions: {e}")

def delete_part(part_data):
    """Delete the selected part"""
    try:
        conn = st.session_state.data_manager.conn
        cursor = conn.cursor()
        
        # Convert to native types
        native_part_number = str(part_data['part_number'])
        native_department_id = int(part_data['department_id'])
        
        print(f"Deleting part: {native_part_number}, department: {native_department_id}")
        
        # First get the part_id for debugging
        cursor.execute(
            "SELECT id FROM spare_parts WHERE part_number = ? AND department_id = ?",
            (native_part_number, native_department_id)
        )
        part_result = cursor.fetchone()
        
        if part_result:
            part_id = part_result[0]
            print(f"Found part ID: {part_id}")
            
            # First delete transactions for this part
            cursor.execute(
                "DELETE FROM transactions WHERE part_id = ?",
                (part_id,)
            )
            print(f"Deleted transactions for part ID: {part_id}")
            
            # Then delete the part
            cursor.execute(
                "DELETE FROM spare_parts WHERE part_number = ? AND department_id = ?",
                (native_part_number, native_department_id)
            )
            
            conn.commit()
            st.success(f"Part '{part_data['name']}' deleted successfully!")
            
            # Clear selection
            st.session_state.selected_part = None
            st.session_state.selected_department_id = None
            
            time.sleep(2)
            st.rerun()
        else:
            st.error("Part not found in database")
            
    except Exception as e:
        st.error(f"Error deleting part: {e}")
        print(f"Detailed delete error: {str(e)}")


    
def generate_custom_barcode(parent_dept_name, child_dept_name, last_serial_no):
    """
    Generate barcode in format: PAR-CH-SERIAL
    Where:
    - PAR: First 3 chars of parent department (uppercase)
    - CH: First char of child department (uppercase)
    - SERIAL: Last serial no + 1 (padded with zeros)
    """
    # Get department codes
    parent_code = parent_dept_name[:3].upper().strip()
    child_code = child_dept_name[:1].upper().strip()
    
    # Calculate next serial number
    next_serial = int(last_serial_no) + 1 if last_serial_no else 1
    
    # Format with leading zeros (e.g., 000123)
    serial_str = f"{next_serial:04d}"  # 4-digit padding
    
    # Combine components
    return f"{parent_code}-{child_code}-{serial_str}"

def download_csv_template():
    """Generate and provide a downloadable CSV template with decimal quantities"""
    # Create sample DataFrame with required columns and example rows
    template_data = {
        'part_number': ['ABC-123', 'XYZ-456', 'DEF-789'],
        'name': ['Bearing 10mm', 'Hydraulic Seal', 'Oil Filter'],
        'quantity': [5.5, 10.0, 2.25],
        'line_no': [1, 2, 3],
        'description': ['High precision bearing', 'Hydraulic system seal', 'Engine oil filter'],
        'barcode': ['POP-P-001', 'POP-P-002', 'POP-P-003'],
        'page_no': ['A12', 'B34', 'C56'],
        'order_no': ['PO-2023-001', 'PO-2023-002', 'PO-2023-003'],
        'material_code': ['MAT-001', 'MAT-002', 'MAT-003'],
        'ilms_code': ['ILMS-001', 'ILMS-002', 'ILMS-003'],
        'item_denomination': ['Pieces', 'Pieces', 'Pieces'],
        'mustered': [True, False, True],
        'compartment_name': ['C-12', 'D-34', 'E-56'],
        'box_no': ['B1', 'B2', 'B3'],
        'remark': ['Urgent', 'Normal', 'Critical'],
        'min_order_level': [2.0, 5.0, 1.5],
        'min_order_quantity': [10.0, 20.0, 5.0]
    }
    
    df = pd.DataFrame(template_data)
    
    # Convert to CSV
    csv = df.to_csv(index=False)
    
    # Create download button
    st.download_button(
        label="📥 Download CSV Template",
        data=csv,
        file_name="inventory_import_template.csv",
        mime="text/csv",
        help="Download template with all required columns and decimal quantity examples",
        key="download_template"
    )

def bulk_import_section():
    """Bulk import from CSV with department selection"""
    download_csv_template()

    # Step 1: Department Selection
    st.markdown("### Step 1: Select Department")
    
    cols = st.columns(2)

    with cols[0]:
        parent_depts = st.session_state.data_manager.get_parent_departments()
        if parent_depts.empty:
            st.error("No departments found. Please create departments first.")
            return
        
        selected_parent = st.selectbox(
            "Select Parent Department*",
            parent_depts['id'].tolist(),
            index=None,
            placeholder="Select Parent Department",
            format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0],
            key="bulk_import_parent"
        )
    
    with cols[1]:
        if selected_parent:
            child_depts = st.session_state.data_manager.get_child_departments(selected_parent)
            if not child_depts.empty:
                selected_child = st.selectbox(
                    "Select Child Department*",
                    child_depts['id'].tolist(),
                    index=None,
                    placeholder="Select Child Department",
                    format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                    key="bulk_import_child"
                )
            else:
                st.error("No child departments found for selected parent department")
                selected_child = None
        else:
            selected_child = None
    
    # Step 2: File Upload
    if selected_parent and selected_child:
        st.markdown("### Step 2: Upload CSV File")
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            help="Upload a CSV file with spare parts data",
            key="bulk_import_file"
        )
    
        if uploaded_file is not None and selected_child:
            try:
                # Read the uploaded file
                df = pd.read_csv(uploaded_file)
                
                # Validate required columns
                required_columns = [
                    'part_number', 'name', 'quantity',  'box_no'
                ]
                
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    st.error(f"Missing required columns: {', '.join(missing_columns)}")
                    return
                
                # Data cleaning and type conversion for decimal quantities
                df_clean = df.copy()
                
                # Handle numeric columns - fill NaN with 0.0 and convert to float for decimal quantities
                numeric_cols = ['quantity', 'min_order_level', 'min_order_quantity', 'line_no']
                for col in numeric_cols:
                    if col in df_clean.columns:
                        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0.0)
                
                # Handle text columns - fill NaN with empty string
                text_cols = [
                    'page_no', 'order_no', 'material_code', 'compartment_name', 'description', 'name',
                    'ilms_code', 'item_denomination', 'box_no', 'Remark', 'part_number', 'barcode'
                ]
                for col in text_cols:
                    if col in df_clean.columns:
                        df_clean[col] = df_clean[col].fillna('').astype(str)
                
                # Handle boolean column
                if 'mustered' in df_clean.columns:
                    df_clean['mustered'] = df_clean['mustered'].fillna(False)
                    # Convert to boolean, handling string representations
                    df_clean['mustered'] = df_clean['mustered'].apply(lambda x: 
                        str(x).lower() in ['true', '1', 'yes', 'y'] if isinstance(x, str) else bool(x))
                
                # Validate critical fields
                critical_errors = []
                for idx, row in df_clean.iterrows():
                    if not row['part_number'] or str(row['part_number']).strip() == '':
                        critical_errors.append(f"Row {idx+1}: Part Number is required")
                    if not row['name'] or str(row['name']).strip() == '':
                        critical_errors.append(f"Row {idx+1}: Name is required")
                    if not row['box_no'] or str(row['box_no']).strip() == '':
                        critical_errors.append(f"Row {idx+1}: Box No is required")
                
                if critical_errors:
                    st.error("Critical validation errors found:")
                    for error in critical_errors:
                        st.error(error)
                    return
                
                # Show preview with department info
                st.subheader("Import Preview")
                st.info(f"All items will be assigned to: {child_depts[child_depts['id'] == selected_child]['name'].iloc[0]}")
                
                preview_df = df_clean.head().copy()
                preview_df['assigned_department'] = child_depts[child_depts['id'] == selected_child]['name'].iloc[0]
                
                # Format numeric columns for display
                display_df = preview_df.copy()
                numeric_display_cols = ['quantity', 'min_order_level', 'min_order_quantity', 'line_no']
                for col in numeric_display_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{float(x):.3f}" if pd.notna(x) else "0.000")
                
                st.dataframe(display_df, hide_index=True)
                
                # Map CSV columns to database columns
                column_mapping = {
                    'part_number': 'part_number',
                    'name': 'name',
                    'description': 'description',
                    'quantity': 'quantity',
                    'line_no': 'line_no',
                    'page_no': 'page_no',
                    'order_no': 'order_no',
                    'material_code': 'material_code',
                    'ilms_code': 'ilms_code',
                    'item_denomination': 'item_denomination',
                    'mustered': 'mustered',
                    'box_no': 'box_no',
                    'compartment_name': 'compartment_no',
                    'Remark': 'remark',
                    'barcode': 'barcode'
                }
                
                # Only include columns that exist in the CSV
                available_mapping = {csv_col: db_col for csv_col, db_col in column_mapping.items() if csv_col in df_clean.columns}
                df_import = df_clean.rename(columns=available_mapping)
                
                # Add missing columns with default values
                required_db_columns = ['compartment_no', 'remark']
                for col in required_db_columns:
                    if col not in df_import.columns:
                        if col == 'compartment_no':
                            df_import['compartment_no'] = ''  # Default empty compartment
                        elif col == 'remark':
                            df_import['remark'] = 'Imported via bulk upload'  # Default remark
                
                # Step 3: Import Confirmation
                st.markdown("### Step 3: Confirm Import")
                if st.button(f"Import {len(df_clean)} Records", key="bulk_import_confirm"):
                    with st.spinner(f"Importing {len(df_clean)} records..."):
                        results, success, message = st.session_state.data_manager.bulk_import_spare_parts(
                            df_import, selected_child, selected_parent
                        )
                        
                        # Display detailed results
                        st.subheader("📊 Import Results")
                        
                        # Calculate statistics
                        total_records = len(results)
                        success_count = len([r for r in results if r['status'] == 'success'])
                        failed_count = len([r for r in results if r['status'] == 'failed'])
                        
                        # Display summary metrics
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Records Processed", total_records)
                        with col2:
                            st.metric("Successfully Imported", success_count)
                        with col3:
                            st.metric("Failed", failed_count, delta=f"-{failed_count}", delta_color="inverse")
                        
                        if success_count > 0:
                            st.success(f"✅ Successfully imported {success_count} records")
                        if failed_count > 0:
                            st.error(f"❌ Failed to import {failed_count} records")
                        
                        # Create detailed results dataframe
                        results_df = pd.DataFrame(results)
                        
                        # Display results in tabs
                        tab1, tab2, tab3 = st.tabs(["📋 All Results", "✅ Successful", "❌ Failed"])
                        
                        with tab1:
                            st.write("### All Import Results")
                            if not results_df.empty:
                                # Format the display
                                display_df = results_df.copy()
                                # Add row numbers
                                display_df['#'] = range(1, len(display_df) + 1)
                                # Reorder columns to show row number first
                                cols = ['#'] + [col for col in display_df.columns if col != '#']
                                display_df = display_df[cols]
                                
                                st.dataframe(display_df, hide_index=True, use_container_width=True)
                            else:
                                st.info("No results to display")
                        
                        with tab2:
                            st.write("### Successfully Imported Records")
                            success_df = results_df[results_df['status'] == 'success']
                            if not success_df.empty:
                                success_display = success_df.copy()
                                success_display['#'] = range(1, len(success_display) + 1)
                                cols = ['#'] + [col for col in success_display.columns if col != '#']
                                success_display = success_display[cols]
                                
                                st.dataframe(success_display, hide_index=True, use_container_width=True)
                                
                                # Show success summary
                                st.info(f"**Success Summary:** {len(success_df)} records imported successfully")
                            else:
                                st.warning("No records were successfully imported")
                        
                        with tab3:
                            st.write("### Failed Records with Reasons")
                            failed_df = results_df[results_df['status'] == 'failed']
                            if not failed_df.empty:
                                failed_display = failed_df.copy()
                                failed_display['#'] = range(1, len(failed_display) + 1)
                                cols = ['#'] + [col for col in failed_display.columns if col != '#']
                                failed_display = failed_display[cols]
                                
                                st.dataframe(failed_display, hide_index=True, use_container_width=True)
                                
                                # Show failure analysis
                                st.error("### Failure Analysis")
                                failure_reasons = failed_display['message'].value_counts()
                                for reason, count in failure_reasons.items():
                                    st.write(f"- **{count} records**: {reason}")
                            else:
                                st.success("No failed records - all imports were successful!")
                        
                        # Download buttons
                        st.markdown("---")
                        st.subheader("📥 Download Detailed Reports")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.download_button(
                                label="Download All Results (CSV)",
                                data=convert_df_to_csv(results_df),
                                file_name="import_results_all.csv",
                                mime="text/csv",
                                key="download_all_results",
                                help="Download complete import results with all records"
                            )
                        
                        with col2:
                            if not success_df.empty:
                                st.download_button(
                                    label="Download Successful Only (CSV)",
                                    data=convert_df_to_csv(success_df),
                                    file_name="import_results_successful.csv",
                                    mime="text/csv",
                                    key="download_success_results",
                                    help="Download only successfully imported records"
                                )
                            else:
                                st.button(
                                    "Download Successful Only (CSV)",
                                    disabled=True,
                                    help="No successful records to download"
                                )
                        
                        with col3:
                            if not failed_df.empty:
                                st.download_button(
                                    label="Download Failed Only (CSV)",
                                    data=convert_df_to_csv(failed_df),
                                    file_name="import_results_failed.csv",
                                    mime="text/csv",
                                    key="download_failed_results",
                                    help="Download only failed records with error reasons"
                                )
                            else:
                                st.button(
                                    "Download Failed Only (CSV)",
                                    disabled=True,
                                    help="No failed records to download"
                                )
                            
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                st.info("Please check the CSV format and try again. Make sure all required columns are present and data is properly formatted.")

def convert_df_to_csv(df):
    """Convert dataframe to CSV for download"""
    return df.to_csv(index=False).encode('utf-8')

if __name__ == "__main__":
    render_inventory_page()
