import streamlit as st
from data_manager import DataManager
from barcode_handler import BarcodeHandler
from user_management import login_required, init_session_state, render_login_page

st.set_page_config(
    page_title="Ship Inventory Management",
    page_icon="🚢",
    layout="wide"
)

# Initialize session state
init_session_state()

# Initialize data manager and barcode handler if needed
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()
if 'barcode_handler' not in st.session_state:
    st.session_state.barcode_handler = BarcodeHandler()

@login_required
def main():
    st.title("Ship Inventory Management System")

    # Show user info in sidebar
    with st.sidebar:
        st.write(f"Logged in as: {st.session_state.username}")
        st.write(f"Role: {st.session_state.user_role}")
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.user_role = None
            st.rerun()

    # Dashboard layout
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Inventory Overview")
        df = st.session_state.data_manager.get_all_parts()
        st.metric("Total Parts", len(df))
        st.metric("Low Stock Items", len(st.session_state.data_manager.get_low_stock_items()))

    with col2:
        st.subheader("Quick Actions")
        if st.button("View Low Stock Items"):
            low_stock = st.session_state.data_manager.get_low_stock_items()
            st.dataframe(low_stock[['name', 'part_number', 'quantity', 'min_order_level']])

    # Recent Transactions
    st.subheader("Recent Transactions")
    recent_transactions = st.session_state.data_manager.get_transaction_history(days=7)
    if not recent_transactions.empty:
        st.dataframe(
            recent_transactions[['timestamp', 'name', 'transaction_type', 'quantity']],
            hide_index=True
        )
    else:
        st.info("No recent transactions found")

if __name__ == "__main__":
    if not st.session_state.authenticated:
        render_login_page()
    else:
        main()