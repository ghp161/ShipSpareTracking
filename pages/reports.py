import streamlit as st
from data_manager import DataManager
from utils import create_stock_level_chart, create_transaction_trend, format_transaction_table
import pandas as pd
from user_management import login_required

@login_required
def render_reports_page():
    st.title("Reports and Analytics")

    tab1, tab2, tab3 = st.tabs(["Stock Levels", "Transaction History", "Export Data"])

    with tab1:
        df = st.session_state.data_manager.get_all_parts()
        if not df.empty:
            fig = create_stock_level_chart(df)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No inventory data available")

    with tab2:
        days = st.slider("Select time period (days)", 1, 90, 30)
        transactions = st.session_state.data_manager.get_transaction_history(days)

        if not transactions.empty:
            fig = create_transaction_trend(transactions)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Transaction Details")
            formatted_transactions = format_transaction_table(transactions)
            st.dataframe(formatted_transactions, hide_index=True)
        else:
            st.info("No transaction data available")

    with tab3:
        st.subheader("Export Data")

        export_type = st.radio("Select data to export", 
                              ["Inventory", "Transactions", "Low Stock Items"])

        if st.button("Generate Export"):
            if export_type == "Inventory":
                data = st.session_state.data_manager.get_all_parts()
            elif export_type == "Transactions":
                data = st.session_state.data_manager.get_transaction_history()
            else:
                data = st.session_state.data_manager.get_low_stock_items()

            if not data.empty:
                csv = data.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{export_type.lower()}_export.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No data available for export")

if __name__ == "__main__":
    render_reports_page()