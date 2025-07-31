import streamlit as st
import pandas as pd  # Add this import at the top
from data_manager import DataManager
from barcode_handler import BarcodeHandler
from user_management import login_required
import navbar
from datetime import datetime
from app_settings import set_page_configuration
import time

set_page_configuration()

current_page = "Inventory"
st.header(current_page)

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

                if st.session_state.user_role in ['Admin', 'Super User']:
                    # Edit part
                    if not df.empty:
                        part_to_edit = st.selectbox("Select part to edit",
                                                    df['description'].tolist())
                        
                        # Define available status options
                        status_options = ["In Store", "Operational", "Under Maintenance"]
                        
                        if part_to_edit:
                            part_data = df[df['description'] == part_to_edit].iloc[0]
                            # Get current status (handle empty/NaN values)
                            current_status = str(part_data['status']).strip() if pd.notna(part_data['status']) else None
                            try:
                                # Handle empty/None values first
                                if pd.isna(part_data['last_maintenance_date']) or not part_data['last_maintenance_date']:
                                    last_default_date = None
                                else:
                                    # Convert to string and parse date
                                    date_str = str(part_data['last_maintenance_date']).strip()
                                    last_default_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                            except (ValueError, TypeError) as e:
                                #st.warning(f"Could not parse date: {part_data['last_maintenance_date']}. Error: {str(e)}")
                                last_default_date = None

                            try:
                                # Handle empty/None values first
                                if pd.isna(part_data['next_maintenance_date']) or not part_data['next_maintenance_date']:
                                    next_default_date = None
                                else:
                                    # Convert to string and parse date
                                    date_str = str(part_data['next_maintenance_date']).strip()
                                    next_default_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                            except (ValueError, TypeError) as e:
                                #st.warning(f"Could not parse date: {part_data['last_maintenance_date']}. Error: {str(e)}")
                                next_default_date = None

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
                                    "Status*",
                                    options=status_options,
                                    index=None if current_status not in status_options else status_options.index(current_status),
                                    placeholder="Select a status...",
                                    key=f"status_select_{part_data['id']}"
                                )
                                new_last_maintenance_date = st.date_input(
                                    "Last Maintenance Date (optional)",
                                    value=last_default_date,
                                    key=f"last_maint_{part_data['id']}"
                                )
                                new_next_maintenance_date = st.date_input(
                                    "Next Maintenance Date (optional)",
                                    value=next_default_date,
                                    key=f"next_maint_{part_data['id']}"
                                )

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
                                                nlast_maint_date_str,
                                                'next_maintenance_date':
                                                nnext_maint_date_str
                                            })
                                        st.success("Part updated successfully!")
                                        st.rerun()
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
                    quantity = st.number_input("Initial Quantity*", min_value=0)
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
                                    'quantity': quantity,
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
    """Generate and provide a downloadable CSV template"""
    # Create sample DataFrame with required columns and example rows
    template_data = {
        'part_number': ['ABC-123', 'XYZ-456', ''],
        'name': ['Bearing 10mm', 'Hydraulic Seal', ''],
        'quantity': [5, 10, ''],
        'line_no': [1, 2, ''],
        'description': [1, 1, ''],
        'barcode': ['POP-P-001', 'POP-P-002', ''],
        'page_no': ['A12', 'B34', ''],
        'order_no': ['PO-2023-001', 'PO-2023-002', ''],
        'material_code': ['MAT-001', 'MAT-002', ''],
        'ilms_code': ['ILMS-001', 'ILMS-002', ''],
        'item_denomination': ['Pieces', 'Pieces', ''],
        'mustered': [True, False, ''],
        'compartment_name': ['C-12', 'D-34', ''],
        'box_no': ['B1', 'B2', ''],
        'remark': ['Urgent', 'Normal', '']
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
        help="Download template with all required columns"
    )

def bulk_import_section():
    """Bulk import from CSV with department selection"""
    #st.subheader("Bulk Import from CSV")
    # Add the download button at the top
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
            format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0]
        )
    
    with cols[1]:
        child_depts = st.session_state.data_manager.get_child_departments(selected_parent)
        if not child_depts.empty:
            selected_child = st.selectbox(
                "Select Child Department*",
                child_depts['id'].tolist(),
                index=None,
                placeholder="Select Child Department",
                format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0]
            )
    
    # Step 2: File Upload
    if selected_parent and selected_child:
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
                    'part_number', 'name', 'quantity', 'ilms_code', #'Remark', 'compartment_name',
                    'description', 'box_no'
                ]
                
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    st.error(f"Missing required columns: {', '.join(missing_columns)}")
                    return
                
                # Data cleaning and type conversion
                df_clean = df.copy()
                
                # Handle numeric columns - fill NaN with 0 and convert to int
                numeric_cols = ['quantity', 'line_no']
                for col in numeric_cols:
                    if col in df_clean.columns:
                        df_clean[col] = df_clean[col].fillna(0).astype(int)
                
                # Handle text columns - fill NaN with empty string
                text_cols = [
                    'page_no', 'order_no', 'material_code', 'compartment_name',  'description', 'name',
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
                    'page_no': 'page_no',
                    'order_no': 'order_no',
                    'material_code': 'material_code',
                    'ilms_code': 'ilms_code',
                    'item_denomination': 'item_denomination',
                    'mustered': 'mustered',
                    'box_no': 'box_no',
                    'compartment_no' : 'compartment_name',
                    'Remark': 'remark',
                    'barcode': 'barcode'
                }
                
                df_import = df_clean.rename(columns=column_mapping)
                
                # Step 3: Import Confirmation
                st.markdown("### Step 3: Confirm Import")
                if st.button(f"Import {len(df_clean)} Records"):
                    with st.spinner(f"Importing {len(df_clean)} records..."):
                        results, success, message = st.session_state.data_manager.bulk_import_spare_parts(
                            df_import, selected_child, selected_parent
                        )
                        if success:
                            st.toast(message, icon="✅")
                            time.sleep(3)  # This will block the UI
                            # Process results
                            success_count = len([r for r in results if r['status'] == 'success'])
                            failed_count = len([r for r in results if r['status'] == 'failed'])
                            
                            # Create results dataframe
                            results_df = pd.DataFrame(results)
                            
                            # Show summary
                            st.success(f"Successfully imported {success_count} records")
                            if failed_count > 0:
                                st.error(f"Failed to import {failed_count} records")
                            
                            # Display results table with tabs
                            tab1, tab2 = st.tabs(["All Results", "Failed Only"])
                            
                            with tab1:
                                st.dataframe(results_df, hide_index=True)
                            
                            with tab2:
                                failed_df = results_df[results_df['status'] == 'failed']
                                st.dataframe(failed_df, hide_index=True)
                            
                            # Download buttons
                            st.markdown("### Download Import Results")
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.download_button(
                                    label="Download Full Results (CSV)",
                                    data=convert_df_to_csv(results_df),
                                    file_name="import_results_all.csv",
                                    mime="text/csv"
                                )
                            
                            with col2:
                                st.download_button(
                                    label="Download Failed Only (CSV)",
                                    data=convert_df_to_csv(failed_df),
                                    file_name="import_results_failed.csv",
                                    mime="text/csv"
                                )
                            #st.rerun()
                        else:
                            st.error(message)
                            
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")

def convert_df_to_csv(df):
    """Convert dataframe to CSV for download"""
    return df.to_csv(index=False).encode('utf-8')

if __name__ == "__main__":
    render_inventory_page()
