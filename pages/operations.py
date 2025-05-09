import streamlit as st
from data_manager import DataManager
from barcode_handler import BarcodeHandler
from user_management import login_required
from datetime import datetime
import navbar
from app_settings import set_page_configuration

set_page_configuration()

current_page = "Operations"
st.header(current_page)

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

    #st.title("Operations")

    # Show any active alerts
    low_stock = st.session_state.data_manager.get_low_stock_items()
    if not low_stock.empty:
        with st.expander("🚨 Low Stock Alerts", expanded=True):
            st.warning(f"{len(low_stock)} items need attention!")
            for _, item in low_stock.iterrows():
                st.error(f"""
                    **{item['name']}** (Part #{item['part_number']})
                    - Current Stock: {item['quantity']}
                    - Minimum Level: {item['min_order_level']}
                    - Suggested Order: {item['min_order_quantity']}
                """)

    tab1, tab2, tab3 = st.tabs(
        ["Barcode Scanner", "Check-In/Check-Out", "Issue Parts"])

    with tab1:
        st.subheader("Barcode Scanner Interface")
        st.info("""
        📱 Use this interface with a physical barcode scanner or enter the barcode manually.
        The scanner should work automatically when you scan a barcode.
        """)

        col1, col2 = st.columns([2, 1])
        with col1:
            barcode_input = st.text_input("Scan or Enter Barcode",
                                          key="barcode_scanner",
                                          placeholder="SP00509457")

            if barcode_input:
                is_valid, cleaned_barcode = st.session_state.barcode_handler.validate_barcode(
                    barcode_input)
                if is_valid:
                    success, part = st.session_state.barcode_handler.get_part_by_barcode(
                        st.session_state.data_manager, cleaned_barcode)
                    if success:
                        st.success("Part found!")

                        # Show alert if item is low on stock
                        if part['quantity'] <= part['min_order_level']:
                            st.warning(
                                f"⚠️ Low stock alert: Only {part['quantity']} units remaining!"
                            )

                        st.json({
                            "Name": part['name'],
                            "Part Number": part['part_number'],
                            "Current Quantity": int(part['quantity']),
                            "Min Order Level": int(part['min_order_level'])
                        })

                        # Quick actions for scanned part
                        action = st.selectbox("Select Action",
                                              ["Check In", "Check Out"],
                                              key="barcode_action")

                        quantity = st.number_input(
                            "Quantity",
                            min_value=1,
                            max_value=int(part['quantity'])
                            if action == "Check Out" else None,
                            value=1,
                            key="barcode_quantity")

                        if st.button(f"Confirm {action}"):
                            transaction_type = 'check_in' if action == "Check In" else 'check_out'

                            success, error_msg = st.session_state.data_manager.record_transaction(
                                part['id'], transaction_type, quantity)

                            if success:
                                st.success(
                                    f"Successfully {action.lower()}ed {quantity} units"
                                )

                                # Check if action triggered low stock alert
                                updated_df = st.session_state.data_manager.get_part_by_id(
                                    part['id'])
                                if updated_df is not None and not updated_df.empty:
                                    updated_part = updated_df.iloc[0]
                                    if updated_part[
                                            'quantity'] <= updated_part[
                                                'min_order_level']:
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
                        "Invalid barcode format. Expected format: SP followed by 8 digits"
                    )

        with col2:
            st.markdown("### Last Scanned")
            for scan in st.session_state.last_scans[-5:]:
                st.text(scan)

    with tab2:
        df = st.session_state.data_manager.get_all_parts()

        if not df.empty:
            selected_part = st.selectbox("Select Part",
                                         df['name'].tolist(),
                                         key="checkin_part")

            part_data = df[df['name'] == selected_part].iloc[0]

            # Show stock level warning if applicable
            if part_data['quantity'] <= part_data['min_order_level']:
                st.warning(
                    f"⚠️ Low stock alert: Only {part_data['quantity']} units remaining!"
                )
            else:
                st.info(f"Current quantity: {part_data['quantity']}")

            col1, col2 = st.columns(2)

            with col1:
                with st.form("check_in_form"):
                    check_in_quantity = st.number_input("Check-In Quantity",
                                                        min_value=1,
                                                        value=1,
                                                        key="checkin_quantity")

                    if st.form_submit_button("Check-In"):
                        success, error_msg = st.session_state.data_manager.record_transaction(
                            part_data['id'], 'check_in', check_in_quantity)
                        if success:
                            st.success(f"Checked in {check_in_quantity} units")
                            st.rerun()
                        else:
                            st.error(f"Transaction failed: {error_msg}")

            with col2:
                with st.form("check_out_form"):
                    check_out_quantity = st.number_input(
                        "Check-Out Quantity",
                        min_value=1,
                        max_value=int(part_data['quantity']),
                        value=1,
                        key="checkout_quantity")

                    if st.form_submit_button("Check-Out"):
                        success, error_msg = st.session_state.data_manager.record_transaction(
                            part_data['id'], 'check_out', check_out_quantity)

                        if success:
                            # Check if this transaction triggered a low stock alert
                            updated_df = st.session_state.data_manager.get_part_by_id(
                                part_data['id'])
                            if updated_df is not None and not updated_df.empty:
                                updated_part = updated_df.iloc[0]
                                if updated_part['quantity'] <= updated_part[
                                        'min_order_level']:
                                    st.warning(
                                        f"⚠️ Stock Alert: {updated_part['name']} is now below minimum stock level!"
                                    )

                            #st.rerun()
                            st.success(f"Checked out {check_out_quantity} units")
                             # Debugging: Check if success message is reached
                            st.write("Check-Out successful")
                            #st.rerun()
                        else:
                            st.error(f"Transaction failed: {error_msg}")

                            

    with tab3:
        low_stock = st.session_state.data_manager.get_low_stock_items()

        if not low_stock.empty:
            st.warning("The following items are below minimum order level:")

            for _, part in low_stock.iterrows():
                st.markdown(f"""
                    **{part['name']}** (Part #: {part['part_number']})
                    - Current Quantity: {part['quantity']}
                    - Minimum Order Level: {part['min_order_level']}
                    - Suggested Order Quantity: {part['min_order_quantity']}
                """)
        else:
            st.success("All items are above minimum order level")


if __name__ == "__main__":
    render_operations_page()
