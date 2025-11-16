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
                    "quantity": st.column_config.NumberColumn("Qty", format="%.2f"),  # NEW - float with 2 decimal places
                    "min_order_level": st.column_config.NumberColumn("Min Order Level", format="%.2f")  # Also update min_order_level if needed
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

                    # Format quantity and min_order_level for display
                    display_df['quantity'] = display_df['quantity'].apply(lambda x: f"{float(x):.2f}")
                    display_df['min_order_level'] = display_df['min_order_level'].apply(lambda x: f"{float(x):.2f}")
                    
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
    """Show edit form for selected part with decimal quantity support"""
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
            # Update to handle decimal quantities
            new_quantity = st.number_input(
                "Quantity", 
                value=float(part_data['quantity']), 
                min_value=0.0, 
                step=0.1,
                format="%.3f"
            )
            new_min_level = st.number_input(
                "Minimum Order Level", 
                value=float(part_data['min_order_level']), 
                min_value=0.0,
                step=0.1,
                format="%.3f"
            )
            new_min_quantity = st.number_input(
                "Minimum Order Quantity", 
                value=float(part_data['min_order_quantity']), 
                min_value=0.1,
                step=0.1,
                format="%.3f"
            )
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
            # Display readonly fields for information with formatted decimal quantities
            st.text_input("Part Number", value=part_data['part_number'], disabled=True)
            st.text_input("Name", value=part_data['name'], disabled=True)
            st.text_input("Barcode", value=part_data['barcode'], disabled=True)
            st.text_input("Current Quantity", value=f"{float(part_data['quantity']):.3f}", disabled=True)
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
    """Update part using part_number AND department_id in WHERE condition with decimal quantity support"""
    try:
        conn = st.session_state.data_manager.conn
        cursor = conn.cursor()
        
        # Build the update query dynamically based on provided fields
        set_clauses = []
        params = []
        
        if 'quantity' in update_data:
            set_clauses.append("quantity = ?")
            params.append(float(update_data['quantity']))  # Convert to float for decimal quantities
        
        if 'min_order_level' in update_data:
            set_clauses.append("min_order_level = ?")
            params.append(float(update_data['min_order_level']))  # Convert to float
        
        if 'min_order_quantity' in update_data:
            set_clauses.append("min_order_quantity = ?")
            params.append(float(update_data['min_order_quantity']))  # Convert to float
        
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
    """Generate and provide a downloadable CSV template with unique barcodes"""
    # Create sample DataFrame with required columns and example rows
    template_data = {
        'part_number': ['ABC-123', 'XYZ-456', 'DEF-789'],
        'name': ['Bearing 10mm', 'Hydraulic Seal', 'Oil Filter'],
        'quantity': [5.5, 10.0, 2.25],
        'line_no': [1, 2, 3],
        'description': ['High precision bearing', 'Hydraulic system seal', 'Engine oil filter'],
        'barcode': ['POP-P-001', 'POP-P-002', 'POP-P-003'],  # Ensure these are unique
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
        help="Download template with all required columns and UNIQUE barcodes",
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
                    'part_number', 'name', 'quantity',  'box_no', 'compartment_name'
                ]
                
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    st.error(f"Missing required columns: {', '.join(missing_columns)}")
                    st.info("Please download the template above and ensure all required columns are present.")
                    return
                
                # Show data validation
                st.subheader("Data Validation")
                
                # Check for empty values in required columns
                validation_issues = []
                for col in required_columns:
                    empty_count = df[col].isna().sum() + (df[col] == '').sum()
                    if empty_count > 0:
                        validation_issues.append(f"{col}: {empty_count} empty values")
                
                if validation_issues:
                    st.warning("⚠️ Validation issues found:")
                    for issue in validation_issues:
                        st.write(f"- {issue}")
                else:
                    st.success("✅ All required fields have values")
                
                # Data cleaning and type conversion
                df_clean = df.copy()
                
                # Handle numeric columns
                numeric_cols = ['quantity', 'min_order_level', 'min_order_quantity', 'line_no']
                for col in numeric_cols:
                    if col in df_clean.columns:
                        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0.0)
                
                # Handle text columns - properly handle NaN values
                text_cols = [
                    'page_no', 'order_no', 'material_code', 'compartment_name', 'description', 'name',
                    'ilms_code', 'item_denomination', 'box_no', 'Remark', 'part_number', 'barcode'
                ]
                for col in text_cols:
                    if col in df_clean.columns:
                        # Replace NaN with empty string and convert to string
                        df_clean[col] = df_clean[col].fillna('')
                        df_clean[col] = df_clean[col].astype(str)
                        # Clean 'nan' strings
                        df_clean[col] = df_clean[col].apply(lambda x: '' if x.strip().lower() == 'nan' else x.strip())
                
                # Handle boolean column
                if 'mustered' in df_clean.columns:
                    df_clean['mustered'] = df_clean['mustered'].fillna(False)
                    df_clean['mustered'] = df_clean['mustered'].apply(lambda x: 
                        str(x).lower() in ['true', '1', 'yes', 'y'] if isinstance(x, str) else bool(x))
                
                # Show preview
                st.subheader("Import Preview")
                st.info(f"All items will be assigned to: {child_depts[child_depts['id'] == selected_child]['name'].iloc[0]}")
                
                preview_df = df_clean.head().copy()
                st.dataframe(preview_df, hide_index=True)
                
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
                if 'compartment_no' not in df_import.columns:
                    df_import['compartment_no'] = ''
                if 'remark' not in df_import.columns:
                    df_import['remark'] = 'Imported via bulk upload'
                
                # Step 3: Import Confirmation
                st.markdown("### Step 3: Confirm Import")
                if st.button(f"Import {len(df_clean)} Records", key="bulk_import_confirm", type="primary"):
                    with st.spinner(f"Importing {len(df_clean)} records..."):
                        results, success, message = st.session_state.data_manager.bulk_import_spare_parts(
                            df_import, selected_child, selected_parent
                        )
                        
                        # Display detailed results
                        st.subheader("📊 Import Results")
                        st.write(message)
                        
                        # Create detailed results dataframe
                        results_df = pd.DataFrame(results)
                        
                        # Calculate statistics
                        total_records = len(results)
                        success_count = len(results_df[results_df['status'] == 'success'])
                        failed_count = len(results_df[results_df['status'] == 'failed'])
                        
                        # Display summary
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Total Records", total_records)
                        with col2:
                            st.metric("Successfully Imported", success_count)
                        with col3:
                            st.metric("Failed", failed_count, delta=f"-{failed_count}", delta_color="inverse")
                        
                        # Display detailed results in tabs
                        tab1, tab2, tab3 = st.tabs(["📋 All Results", "✅ Successful", "❌ Failed"])
                        
                        with tab1:
                            st.dataframe(results_df, use_container_width=True, hide_index=True)
                        
                        with tab2:
                            success_df = results_df[results_df['status'] == 'success']
                            if not success_df.empty:
                                st.dataframe(success_df, use_container_width=True, hide_index=True)
                            else:
                                st.info("No successful imports")
                        
                        with tab3:
                            failed_df = results_df[results_df['status'] == 'failed']
                            if not failed_df.empty:
                                st.dataframe(failed_df, use_container_width=True, hide_index=True)
                                
                                # Show common failure reasons
                                st.subheader("Common Failure Reasons")
                                failure_reasons = failed_df['message'].value_counts()
                                for reason, count in failure_reasons.items():
                                    st.write(f"**{count} records**: {reason}")
                            else:
                                st.success("No failed imports!")
                        
                        # Download options
                        st.markdown("---")
                        st.subheader("📥 Download Reports")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.download_button(
                                "Download All Results",
                                data=convert_df_to_csv(results_df),
                                file_name="import_all_results.csv",
                                mime="text/csv"
                            )
                        with col2:
                            if not success_df.empty:
                                st.download_button(
                                    "Download Successful",
                                    data=convert_df_to_csv(success_df),
                                    file_name="import_successful.csv",
                                    mime="text/csv"
                                )
                        with col3:
                            if not failed_df.empty:
                                st.download_button(
                                    "Download Failed",
                                    data=convert_df_to_csv(failed_df),
                                    file_name="import_failed.csv",
                                    mime="text/csv"
                                )
                            
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")

def convert_df_to_csv(df):
    """Convert dataframe to CSV for download"""
    return df.to_csv(index=False).encode('utf-8')

if __name__ == "__main__":
    render_inventory_page()
