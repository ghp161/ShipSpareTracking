import streamlit as st
from data_manager import DataManager

def render_operations_page():
    st.title("Operations")
    
    tab1, tab2 = st.tabs(["Check-In/Check-Out", "Issue Parts"])
    
    with tab1:
        df = st.session_state.data_manager.get_all_parts()
        
        if not df.empty:
            selected_part = st.selectbox(
                "Select Part",
                df['name'].tolist(),
                key="checkin_part"
            )
            
            part_data = df[df['name'] == selected_part].iloc[0]
            
            st.info(f"Current quantity: {part_data['quantity']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                with st.form("check_in_form"):
                    check_in_quantity = st.number_input(
                        "Check-In Quantity",
                        min_value=1,
                        value=1,
                        key="checkin_quantity"
                    )
                    
                    if st.form_submit_button("Check-In"):
                        st.session_state.data_manager.record_transaction(
                            part_data['id'],
                            'check_in',
                            check_in_quantity
                        )
                        st.success(f"Checked in {check_in_quantity} units")
                        st.rerun()
            
            with col2:
                with st.form("check_out_form"):
                    check_out_quantity = st.number_input(
                        "Check-Out Quantity",
                        min_value=1,
                        max_value=part_data['quantity'],
                        value=1,
                        key="checkout_quantity"
                    )
                    
                    if st.form_submit_button("Check-Out"):
                        st.session_state.data_manager.record_transaction(
                            part_data['id'],
                            'check_out',
                            check_out_quantity
                        )
                        st.success(f"Checked out {check_out_quantity} units")
                        st.rerun()
    
    with tab2:
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
