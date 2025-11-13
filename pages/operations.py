import streamlit as st
from app_settings import set_page_configuration

set_page_configuration()

from data_manager import DataManager
from barcode_handler import BarcodeHandler
from user_management import login_required, init_session_state, check_and_restore_session
from datetime import datetime
import navbar
import time
import pandas as pd


current_page = "Operations"
st.header(current_page)

# Initialize session state and check for existing session
init_session_state()
if not st.session_state.authenticated:
    check_and_restore_session()

navbar.nav(current_page)


@login_required
def render_operations_page():
    # Initialize session state if needed
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()
    if 'barcode_handler' not in st.session_state:
        st.session_state.barcode_handler = BarcodeHandler()
    if 'last_scans' not in st.session_state:
        st.session_state.last_scans = []

    # Initialize department selection in session state
    if 'operations_parent_dept' not in st.session_state:
        st.session_state.operations_parent_dept = None
    if 'operations_child_dept' not in st.session_state:
        st.session_state.operations_child_dept = None

    # Show any active alerts
    lpl_stock = st.session_state.data_manager.get_last_piece_stock_items()
    if not lpl_stock.empty:
        with st.expander("🚨 Last Piece Stock Alerts", expanded=False):
            st.warning(f"{len(lpl_stock)} items need attention!")
            for _, item in lpl_stock.iterrows():
                st.error(f"""
                    **{item['name']}** (Part #{item['part_number']})
                    - Current Stock: {float(item['quantity']):.3f}
                    - Minimum Level: {float(item['min_order_level']):.3f}
                    - Suggested Order: {float(item['min_order_quantity']):.3f}
                """)

    low_stock = st.session_state.data_manager.get_low_stock_items()
    if not low_stock.empty:
        with st.expander("🚨 Low Stock Alerts", expanded=False):
            st.warning(f"{len(low_stock)} items need attention!")
            for _, item in low_stock.iterrows():
                st.error(f"""
                    **{item['name']}** (Part #{item['part_number']})
                    - Current Stock: {float(item['quantity']):.3f}
                    - Minimum Level: {float(item['min_order_level']):.3f}
                    - Suggested Order: {float(item['min_order_quantity']):.3f}
                """)

    tab1, tab2 = st.tabs(
        ["Barcode Scanner Interface", "Check-In / Check-Out"])

    with tab1:
        st.info("""
        📱 Use this interface with a physical barcode scanner or enter the barcode manually.
        The scanner should work automatically when you scan a barcode.
        """)

        col1, col2 = st.columns([2, 1])
        with col1:
            barcode_input = st.text_input("Scan or Enter Barcode",
                                          key="barcode_scanner",
                                          placeholder="ABC-D-1234")

            if barcode_input:
                is_valid, cleaned_barcode = st.session_state.barcode_handler.validate_barcode(
                    barcode_input)
                if is_valid:
                    success, part = st.session_state.barcode_handler.get_part_by_barcode(
                        st.session_state.data_manager, barcode_input)
                    if success:
                        # Show alert if item is low on stock
                        if float(part['quantity']) <= float(part['min_order_level']):
                            st.warning(
                                f"⚠️ Low stock alert: Only {float(part['quantity']):.3f} units remaining!"
                            )

                        st.json({
                            "Name": part['name'],
                            "Part Number": part['part_number'],
                            "Box No": part['box_no'],
                            "Compartment Name": part['compartment_no'],
                            "ILMS Code": part['ilms_code'],
                            "Current Quantity": float(part['quantity']),
                            "Min Order Level": float(part['min_order_level'])
                        })

                        cols = st.columns(2)
                        with cols[0]:
                            # Quick actions for scanned part
                            action = st.selectbox("Select Action",
                                                ["Check In", "Check Out"],
                                                key="barcode_action")

                            # Convert all values to float to avoid mixed types
                            available_quantity = float(part['quantity'])
                            
                            quantity = st.number_input(
                                "Quantity",
                                min_value=0.1,
                                max_value=float(available_quantity) if action == "Check Out" else None,
                                value=1.0,
                                step=0.1,
                                format="%.3f",
                                key="barcode_quantity"
                            )
                        with cols[1]:
                            if action == "Check Out":
                                reason = st.selectbox("Reason", ["Operational", "Maintenance", "Damaged"], key="barcode_reason_out")
                                remarks = st.text_area("Remarks", key="barcode_remarks_out")
                            else:
                                reason = st.selectbox("Reason", ["New", "After Maintenance"], key="barcode_reason_in")
                                remarks = st.text_area("Remarks", key="barcode_remarks_in")

                        if st.button(f"Confirm {action}"):
                            transaction_type = 'check_in' if action == "Check In" else 'check_out'

                            success, error_msg = st.session_state.data_manager.record_transaction(
                                part['id'], transaction_type, quantity, reason, remarks)

                            if success:
                                st.success(
                                    f"Successfully {action.lower()}ed {quantity:.3f} units"
                                )

                                # Check if action triggered low stock alert
                                updated_df = st.session_state.data_manager.get_part_by_id(
                                    part['id'])
                                if updated_df is not None and not updated_df.empty:
                                    updated_part = updated_df.iloc[0]
                                    if float(updated_part['quantity']) <= float(updated_part['min_order_level']):
                                        st.warning(
                                            f"⚠️ Stock Alert: {updated_part['name']} is now below minimum stock level!"
                                        )

                                st.session_state.last_scans.append(
                                    f"{datetime.now().strftime('%H:%M:%S')} - {part['name']}"
                                )
                                st.rerun()
                            else:
                                st.error(f"Transaction failed: {error_msg}")
                    else:
                        st.error("Barcode not found in system")
                else:
                    st.error(
                        "Invalid barcode format. Expected format: 3 chars - 1 char - 4 digits (ABC-D-1234)"
                    )

        with col2:
            if len(barcode_input) > 0:
                barcode_image = st.session_state.barcode_handler.generate_barcode(barcode_input)
                st.image(f"data:image/png;base64,{barcode_image}")
            st.markdown("### Last Scanned")
            for scan in st.session_state.last_scans[-5:]:
                st.text(scan)

    with tab2:
        # Department Selection for Check-In/Check-Out
        #st.subheader("Department Selection")
        
        # Get current user's role and department
        current_user_role = st.session_state.get('user_role')
        current_user_dept_id = st.session_state.get('user_department_id')
        
        selected_parent = None
        selected_child = None
        
        if current_user_role == 'User':
            # Regular users can only see their own department
            selected_child = current_user_dept_id
            if selected_child:
                dept_info = st.session_state.data_manager.get_department_info(selected_child)
                if dept_info is not None and not dept_info.empty:
                    st.info(f"📋 Your Department: {dept_info['child_department']} - {dept_info['parent_department']}")
        else:
            # Admin/Super User can select departments
            cols = st.columns(2)
            
            with cols[0]:
                # Parent department selection - use on_change to update session state
                parent_depts = st.session_state.data_manager.get_parent_departments()
                if not parent_depts.empty:
                    # Define callback function to update session state
                    def update_parent_dept():
                        st.session_state.operations_parent_dept = st.session_state.operations_parent_dept_widget
                        # Reset child department when parent changes
                        st.session_state.operations_child_dept = None
                    
                    selected_parent = st.selectbox(
                        "Select Parent Department",
                        parent_depts['id'].tolist(),
                        index=None,
                        placeholder="Select Parent Department",
                        format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0],
                        key="operations_parent_dept_widget",
                        on_change=update_parent_dept
                    )
                    
                    # Initialize or sync session state
                    if selected_parent is not None:
                        st.session_state.operations_parent_dept = selected_parent
                    else:
                        selected_parent = st.session_state.operations_parent_dept
            
            with cols[1]:
                if selected_parent:
                    child_depts = st.session_state.data_manager.get_child_departments(selected_parent)
                    if not child_depts.empty:
                        # Define callback function to update session state
                        def update_child_dept():
                            st.session_state.operations_child_dept = st.session_state.operations_child_dept_widget
                        
                        selected_child = st.selectbox(
                            "Select Child Department",
                            child_depts['id'].tolist(),
                            index=None,
                            placeholder="Select Child Department",
                            format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                            key="operations_child_dept_widget",
                            on_change=update_child_dept
                        )
                        
                        # Initialize or sync session state
                        if selected_child is not None:
                            st.session_state.operations_child_dept = selected_child
                        else:
                            selected_child = st.session_state.operations_child_dept
                else:
                    st.info("Please select a parent department first")
        
        # Use session state values for consistency
        if current_user_role != 'User':
            selected_parent = st.session_state.operations_parent_dept
            selected_child = st.session_state.operations_child_dept
        
        # Get parts based on department selection
        df = pd.DataFrame()
        if selected_child:
            if current_user_role == 'User':
                # For regular users, get parts from their department
                df = st.session_state.data_manager.get_parts_by_department(selected_child)
            else:
                # For admin users, get parts from selected department
                df = st.session_state.data_manager.get_parts_by_department(selected_child)
            
            # Show department info
            dept_info = st.session_state.data_manager.get_department_info(selected_child)
            if dept_info is not None and not dept_info.empty:
                st.success(f"📊 Showing parts for: {dept_info['child_department']} - {dept_info['parent_department']}")

        # Only show part selection if we have parts
        if not df.empty:
            #st.subheader("Part Selection")
            
            # Create a user-friendly display for the dropdown
            part_options = []
            for _, part in df.iterrows():
                display_text = f"{part['name']} (Part#: {part['part_number']}, Qty: {float(part['quantity']):.3f})"
                part_options.append((display_text, part))
            
            # Part selection dropdown
            if part_options:
                selected_display = st.selectbox(
                    "Select Part for Check-In/Check-Out",
                    options=[opt[0] for opt in part_options],
                    key="operations_part_select"
                )
                
                # Get the selected part data
                selected_part_data = None
                for display_text, part_data in part_options:
                    if display_text == selected_display:
                        selected_part_data = part_data
                        break
                
                if selected_part_data is not None:
                    part_data = selected_part_data
                    
                    # Show stock level warning if applicable
                    if float(part_data['quantity']) <= float(part_data['min_order_level']):
                        st.warning(
                            f"⚠️ Low stock alert: Only {float(part_data['quantity']):.3f} units remaining!"
                        )
                    else:
                        st.info(f"Current quantity: {float(part_data['quantity']):.3f}")

                    col1, col2 = st.columns(2)

                    with col1:
                        with st.form("check_in_form"):
                            check_in_quantity = st.number_input(
                                "Check-In Quantity",
                                min_value=0.1,
                                value=1.0,
                                step=0.1,
                                format="%.3f",
                                key="checkin_quantity"
                            )
                            reason = st.selectbox("Reason", ["New", "After Maintenance"], key="checkin_reason")
                            remarks = st.text_area("Remarks", key="checkin_remarks")
                            
                            if st.form_submit_button("Check-In"):
                                success, error_msg = st.session_state.data_manager.record_transaction(
                                    part_data['id'], 'check_in', check_in_quantity, reason, remarks)
                                if success:
                                    st.success(f"Checked in {check_in_quantity:.3f} units")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error(f"Transaction failed: {error_msg}")

                    with col2:
                        with st.form(f"check_out_form_{part_data['id']}"):
                            # Get the available quantity as float
                            available_quantity = float(part_data['quantity'])
                            
                            if available_quantity > 0:
                                check_out_quantity = st.number_input(
                                    "Check-Out Quantity",
                                    min_value=0.1,
                                    max_value=float(available_quantity),
                                    value=min(1.0, available_quantity),
                                    step=0.1,
                                    format="%.3f",
                                    key=f"checkout_quantity_{part_data['id']}"
                                )
                                reason = st.selectbox("Reason", ["Operational", "Maintenance", "Damaged"], key="checkout_reason")
                                remarks = st.text_area("Remarks", key="checkout_remarks")
                            else:
                                st.warning("This item is currently out of stock")
                                check_out_quantity = 0.0
                            
                            submitted = st.form_submit_button("Check-Out", disabled=(available_quantity <= 0))
                            
                            if submitted and available_quantity > 0:
                                success, error_msg = st.session_state.data_manager.record_transaction(
                                    part_data['id'], 'check_out', check_out_quantity, reason, remarks)

                                if success:
                                    # Check for low stock alert
                                    updated_df = st.session_state.data_manager.get_part_by_id(part_data['id'])
                                    if updated_df is not None and not updated_df.empty:
                                        updated_part = updated_df.iloc[0]
                                        if float(updated_part['quantity']) <= float(updated_part['min_order_level']):
                                            st.warning(
                                                f"⚠️ Stock Alert: {updated_part['name']} is now below minimum stock level!"
                                            )
                                    
                                    st.success(f"Successfully checked out {check_out_quantity:.3f} units of {part_data['name']}")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error(f"Transaction failed: {error_msg}")
            else:
                st.info("No parts available in the selected department")
        else:
            if selected_child:
                st.info("No parts found in the selected department")
            else:
                st.info("Please select a department to view available parts")


if __name__ == "__main__":
    render_operations_page()