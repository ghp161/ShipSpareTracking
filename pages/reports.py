import streamlit as st
from data_manager import DataManager
from utils import create_stock_level_chart, create_transaction_trend, format_transaction_table
import pandas as pd
from user_management import login_required
import navbar
from app_settings import set_page_configuration

set_page_configuration()

current_page = "Reports"
st.header(current_page)

navbar.nav(current_page)


@login_required
def render_reports_page():
    #st.title("Reports and Analytics")
    # Get current user's department from session state
    current_user_dept_id = st.session_state.get('user_department_id')

    tab1, tab2, tab3 = st.tabs(
        ["Stock Levels", "Transaction History", "Export Data"])

    with tab1:
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
                    index=0,
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
                        index=0,
                        placeholder="Select Child Department",
                        format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                        key = "ListChildDept"
                    )
            df = st.session_state.data_manager.get_parts_by_department(selected_child)

        #df = st.session_state.data_manager.get_all_parts()
        if not df.empty:
            fig = create_stock_level_chart(df)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No inventory data available")

    with tab2:
        if st.session_state.user_role in ['Admin', 'Super User']:
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
                    index=0,
                    placeholder="Select Parent Department",
                    format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0],
                    key = "TranParentDept"
                )
            
            with cols[1]:
                child_depts = st.session_state.data_manager.get_child_departments(selected_parent)
                if not child_depts.empty:                                
                    selected_child = st.selectbox(
                        "Select Child Department*",
                        child_depts['id'].tolist(),
                        index=0,
                        placeholder="Select Child Department",
                        format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                        key = "TranChildDept"
                    )
        days = st.slider("Select time period (days)", 1, 90, 30)
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
            transactions = st.session_state.data_manager.get_transaction_history_by_department(current_user_dept_id, days)
        else:            
            transactions = st.session_state.data_manager.get_transaction_history_by_department(selected_child, days)

        if not transactions.empty:
            fig = create_transaction_trend(transactions)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader("Transaction Details")
            formatted_transactions = format_transaction_table(transactions)
            st.dataframe(formatted_transactions, hide_index=True)
        else:
            st.info("No transaction data available")

    with tab3:
        #st.subheader("Export Data")
        if st.session_state.user_role in ['Admin', 'Super User']:
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
                    index=0,
                    placeholder="Select Parent Department",
                    format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0],
                    key = "ExpParentDept"
                )
            
            with cols[1]:
                child_depts = st.session_state.data_manager.get_child_departments(selected_parent)
                if not child_depts.empty:                                
                    selected_child = st.selectbox(
                        "Select Child Department*",
                        child_depts['id'].tolist(),
                        index=0,
                        placeholder="Select Child Department",
                        format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                        key = "ExpChildDept"
                    )

        export_type = st.radio(
            "Select data to export",
            ["Inventory", "Transactions", "Low Stock Items"])

        if st.button("Generate Export"):
            if export_type == "Inventory":
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
                    data = st.session_state.data_manager.get_parts_by_department(current_user_dept_id)
                else:                    
                    data = st.session_state.data_manager.get_parts_by_department(selected_child)
                #data = st.session_state.data_manager.get_all_parts()
            elif export_type == "Transactions":
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
                    data = st.session_state.data_manager.get_transaction_history_by_department(current_user_dept_id)
                else:
                    data = st.session_state.data_manager.get_transaction_history_by_department(selected_child)
            else:
                if st.session_state.user_role == 'User':
                    data = st.session_state.data_manager.get_low_stock_items_by_dept(st.session_state.get('user_department_id'))
                else:
                    data = st.session_state.data_manager.get_low_stock_items_by_dept(selected_child)

            if not data.empty:
                csv = data.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"{export_type.lower()}_export.csv",
                    mime="text/csv")
            else:
                st.warning("No data available for export")


if __name__ == "__main__":
    render_reports_page()
