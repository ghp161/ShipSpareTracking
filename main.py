import streamlit as st
from data_manager import DataManager
from barcode_handler import BarcodeHandler
from user_management import login_required, init_session_state, render_login_page
from navbar import make_sidebar
from app_settings import set_page_configuration #, add_logo_background
from io import BytesIO
set_page_configuration()



# Initialize alerts in session state
if 'alerts' not in st.session_state:
    st.session_state.alerts = []


@login_required
def main():

    # Initialize session state
    init_session_state()

    # Add the background logo (40% opacity = 0.4)
    #add_logo_background("logo.png", opacity=0.4)

    # Set page config (will be overridden by navbar if needed)
    #st.set_page_config(layout="centered")

    #if not st.session_state.get('authenticated', False):
    #    render_login_page()

    # Initialize data manager and barcode handler if needed
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()
    if 'barcode_handler' not in st.session_state:
        st.session_state.barcode_handler = BarcodeHandler()

    st.title("Ship Inventory Management System")

    # Show user info in sidebar
    with st.sidebar:
        #st.write(f"Logged in as: {st.session_state.username}")
        #st.write(f"Role: {st.session_state.user_role}")

        # Alert Section in Sidebar
        #low_stock = st.session_state.data_manager.get_low_stock_items()
        #if not low_stock.empty:
        #    st.error(f"🚨 {len(low_stock)} items below minimum stock level!")
        #    with st.expander("View Low Stock Alerts"):
        #        for _, item in low_stock.iterrows():
        #            st.warning(f"""
        #                **{item['name']}**
        #                - Current: {item['quantity']}
        #                - Minimum: {item['min_order_level']}
        #                - Order Quantity: {item['min_order_quantity']}
        #            """)

        make_sidebar()

        #if st.button("Logout"):
        #    st.session_state.authenticated = False
        #    st.session_state.username = None
        #    st.session_state.user_role = None
        #    st.rerun()

    # Dashboard layout
    col1, col2 = st.columns(2)

    with col1:
        lpl_stock = st.session_state.data_manager.get_last_piece_stock_items()
        low_stock = st.session_state.data_manager.get_low_stock_items()
        st.subheader("Inventory Overview")
        df = st.session_state.data_manager.get_all_parts()
        total_parts = len(df)
        low_stock_count = len(low_stock)
        lpl_stock_count = len(lpl_stock)

        st.metric("Total Parts",
                  total_parts,
                  help="Total number of unique parts in inventory")
        st.metric("LPL Stock Items",
                  lpl_stock_count,
                  delta=lpl_stock_count,
                  delta_color="inverse",
                  help="Number of items below last piece level")
        st.metric("Low Stock Items",
                  low_stock_count,
                  delta=low_stock_count,
                  delta_color="inverse",
                  help="Number of items below minimum order level")

    with col2:
        st.subheader("Quick Actions")
        if st.button("View Last Piece Level Stock Alerts"):
            lpl_stock = st.session_state.data_manager.get_last_piece_stock_items()
            if not lpl_stock.empty:
                st.dataframe(lpl_stock[[
                    'name', 'part_number', 'quantity', 'min_order_level'
                ]],
                             hide_index=True)

                # Download low stock report
                csv = lpl_stock.to_csv(index=False)
                st.download_button(
                    "Download Last Piece Level Stock Report",
                    csv,
                    "last_piece_stock_report.csv",
                    "text/csv",
                    help="Download a CSV report of all last piece level stock items")
            else:
                st.success("All items are above last piece levels")

        if st.button("View Low Stock Items"):
            low_stock = st.session_state.data_manager.get_low_stock_items()
            if not low_stock.empty:
                st.dataframe(low_stock[[
                    'name', 'part_number', 'quantity', 'min_order_level'
                ]],
                             hide_index=True)

                # Download low stock report
                csv = low_stock.to_csv(index=False)
                st.download_button(
                    "Download Low Stock Report",
                    csv,
                    "low_stock_report.csv",
                    "text/csv",
                    help="Download a CSV report of all low stock items")
            else:
                st.success("All items are above minimum stock levels")

    # Recent Transactions
    st.subheader("Recent Transactions")
    recent_transactions = st.session_state.data_manager.get_transaction_history(
        days=7)
    if not recent_transactions.empty:
        st.dataframe(recent_transactions[[
            'timestamp', 'name', 'transaction_type', 'quantity'
        ]],
                     hide_index=True)
    else:
        st.info("No recent transactions found")

    # Close the main div at the end
    #st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    if 'authenticated' not in st.session_state:
        render_login_page()
    else:
        main()
