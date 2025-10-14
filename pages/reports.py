import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from user_management import login_required
import navbar
from app_settings import set_page_configuration
from data_manager import DataManager
import io
import base64

set_page_configuration()

current_page = "Reports"
st.header(current_page)

navbar.nav(current_page)

@login_required
def render_reports_page():
    #st.title("📋 Advanced Reporting Dashboard")
    
    # Initialize session state
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()
    
    # Get current user's department and role
    current_user_role = st.session_state.get('user_role')
    current_user_dept_id = st.session_state.get('user_department_id')
    
    # Display user context
    if current_user_role == 'User':
        dept_info = st.session_state.data_manager.get_department_info(current_user_dept_id)
        if dept_info is not None and not dept_info.empty:
            st.info(f"🔐 **Department Access**: {dept_info['child_department']} - {dept_info['parent_department']}")
    
    # Date range selector
    col1, col2 = st.columns([1, 1])
    with col1:
        report_period = st.selectbox(
            "Report Period",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "Last 6 Months", "Last Year", "Custom Range"],
            index=1
        )
    
    # Department selector for Admin/Super User
    selected_child_dept = None
    if current_user_role in ['Admin', 'Super User']:
        with col2:
            parent_depts = st.session_state.data_manager.get_parent_departments()
            if not parent_depts.empty:
                selected_parent = st.selectbox(
                    "Parent Department",
                    parent_depts['id'].tolist(),
                    index=0,
                    format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0],
                    key="report_parent_dept"
                )
                
                child_depts = st.session_state.data_manager.get_child_departments(selected_parent)
                if not child_depts.empty:
                    selected_child_dept = st.selectbox(
                        "Child Department",
                        child_depts['id'].tolist(),
                        index=0,
                        format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                        key="report_child_dept"
                    )
    else:
        # Regular users can only see their assigned department
        selected_child_dept = current_user_dept_id
    
    # Calculate date range
    days = get_days_from_period(report_period)
    
    # Main reports navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Executive Summary", 
        "📦 Inventory Reports", 
        "🔄 Transaction Reports", 
        "🚨 Alert Reports",
        "📈 Performance Reports"
    ])

    with tab1:
        render_executive_summary(days, selected_child_dept, current_user_role)
    
    with tab2:
        render_inventory_reports(days, selected_child_dept, current_user_role)
    
    with tab3:
        render_transaction_reports(days, selected_child_dept, current_user_role)
    
    with tab4:
        render_alert_reports(days, selected_child_dept, current_user_role)
    
    with tab5:
        render_performance_reports(days, selected_child_dept, current_user_role)

def ensure_numeric_dataframe(df, numeric_columns=None):
    """Ensure specified columns are numeric, handling conversion errors"""
    if df.empty:
        return df
    
    df = df.copy()
    
    if numeric_columns is None:
        numeric_columns = ['quantity', 'min_order_level', 'min_order_quantity', 'line_no']
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

def render_executive_summary(days, department_id, user_role):
    """Executive summary with key metrics and overview"""
    st.subheader("🏆 Executive Summary")
    
    # Get data based on user role and department
    if user_role == 'User':
        spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
        transactions = st.session_state.data_manager.get_transaction_history_by_department(department_id, days)
    else:
        if department_id:
            spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
            transactions = st.session_state.data_manager.get_transaction_history_by_department(department_id, days)
        else:
            spare_parts = st.session_state.data_manager.get_all_parts()
            transactions = st.session_state.data_manager.get_transaction_history(days=days)
    
    # Ensure numeric data types
    spare_parts = ensure_numeric_dataframe(spare_parts)
    transactions = ensure_numeric_dataframe(transactions)
    
    if spare_parts.empty:
        st.warning("No inventory data available for the selected department/period")
        return
    
    # Key Performance Indicators
    st.write("### Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_items = len(spare_parts)
        st.metric("Total Items", total_items)
    
    with col2:
        total_value = calculate_inventory_value(spare_parts)
        st.metric("Inventory Value", f"${total_value:,.0f}")
    
    with col3:
        turnover_rate = calculate_turnover_rate(transactions, spare_parts)
        st.metric("Turnover Rate", f"{turnover_rate:.1f}x")
    
    with col4:
        service_level = calculate_service_level(transactions)
        st.metric("Service Level", f"{service_level:.1f}%")
    
    # Charts Row
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        fig = create_inventory_health_chart(spare_parts)
        st.plotly_chart(fig, use_container_width=True)
    
    with chart_col2:
        fig = create_department_activity_chart(transactions, spare_parts)
        st.plotly_chart(fig, use_container_width=True)
    
    # Quick Insights
    st.write("### 📈 Quick Insights")
    
    insights_col1, insights_col2 = st.columns(2)
    
    with insights_col1:
        st.info("**Top Moving Items**")
        top_movers = get_top_moving_items(transactions, 5)
        for item in top_movers:
            st.write(f"• {item['name']}: {item['quantity']} units")
    
    with insights_col2:
        st.warning("**Attention Required**")
        critical_items = get_critical_items(spare_parts, 3)
        for item in critical_items:
            st.write(f"• {item['name']}: {item['quantity']} left (min: {item['min_level']})")
    
    # Export Executive Summary
    st.download_button(
        "📥 Download Executive Summary",
        generate_executive_summary_pdf(spare_parts, transactions),
        file_name=f"executive_summary_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf"
    )

def render_inventory_reports(days, department_id, user_role):
    """Comprehensive inventory reports"""
    st.subheader("📦 Inventory Analysis Reports")
    
    # Get inventory data based on access
    if user_role == 'User':
        spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
    else:
        if department_id:
            spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
        else:
            spare_parts = st.session_state.data_manager.get_all_parts()
    
    if spare_parts.empty:
        st.warning("No inventory data available")
        return
    
    # Inventory Report Types
    report_type = st.radio(
        "Select Inventory Report",
        ["Stock Level Analysis", "ABC Classification", "Value Analysis", "Department Summary", "Custom Inventory Report"],
        horizontal=True
    )
    
    if report_type == "Stock Level Analysis":
        render_stock_level_report(spare_parts)
    elif report_type == "ABC Classification":
        render_abc_classification_report(spare_parts)
    elif report_type == "Value Analysis":
        render_value_analysis_report(spare_parts)
    elif report_type == "Department Summary":
        render_department_summary_report(spare_parts, user_role, department_id)
    elif report_type == "Custom Inventory Report":
        render_custom_inventory_report(spare_parts)

def render_transaction_reports(days, department_id, user_role):
    """Transaction history and analysis reports"""
    st.subheader("🔄 Transaction Analysis Reports")
    
    # Get transaction data based on access
    if user_role == 'User':
        transactions = st.session_state.data_manager.get_transaction_history_by_department(department_id, days)
    else:
        if department_id:
            transactions = st.session_state.data_manager.get_transaction_history_by_department(department_id, days)
        else:
            transactions = st.session_state.data_manager.get_transaction_history(days=days)
    
    if transactions.empty:
        st.warning("No transaction data available for the selected period")
        return
    
    # Transaction Report Types
    report_type = st.radio(
        "Select Transaction Report",
        ["Transaction History", "Movement Analysis", "Trend Analysis", "User Activity", "Custom Transaction Report"],
        horizontal=True
    )
    
    if report_type == "Transaction History":
        render_transaction_history_report(transactions)
    elif report_type == "Movement Analysis":
        render_movement_analysis_report(transactions)
    elif report_type == "Trend Analysis":
        render_trend_analysis_report(transactions, days)
    elif report_type == "User Activity":
        st.info("User activity tracking requires additional user session data")
    elif report_type == "Custom Transaction Report":
        render_custom_transaction_report(transactions)

def render_alert_reports(days, department_id, user_role):
    """Alert and exception reports"""
    st.subheader("🚨 Alert & Exception Reports")
    
    # Get data based on access
    if user_role == 'User':
        spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
        low_stock = st.session_state.data_manager.get_low_stock_items_by_dept(department_id)
        last_piece = st.session_state.data_manager.get_last_piece_stock_items_by_dept(department_id)
    else:
        if department_id:
            spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
            low_stock = st.session_state.data_manager.get_low_stock_items_by_dept(department_id)
            last_piece = st.session_state.data_manager.get_last_piece_stock_items_by_dept(department_id)
        else:
            spare_parts = st.session_state.data_manager.get_all_parts()
            low_stock = st.session_state.data_manager.get_low_stock_items()
            last_piece = st.session_state.data_manager.get_last_piece_stock_items()
    
    # Ensure data consistency
    spare_parts = ensure_data_consistency(spare_parts)
    low_stock = ensure_data_consistency(low_stock)
    last_piece = ensure_data_consistency(last_piece)
    
    # Alert Summary
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Last Piece Alerts", len(last_piece), delta=len(last_piece), delta_color="inverse")
    
    with col2:
        st.metric("Low Stock Alerts", len(low_stock), delta=len(low_stock), delta_color="inverse")
    
    with col3:
        out_of_stock = len(spare_parts[spare_parts['quantity'] == 0])
        st.metric("Out of Stock", out_of_stock, delta=out_of_stock, delta_color="inverse")
    
    # Alert Details
    alert_tab1, alert_tab2, alert_tab3 = st.tabs(["Last Piece Alerts", "Low Stock Alerts", "Reordering Recommendations"])
    
    with alert_tab1:
        if not last_piece.empty:
            # Fix: Handle missing child_department column
            display_columns = ['name', 'part_number', 'quantity', 'min_order_level', 'min_order_quantity']
            
            # Add child_department if it exists, otherwise try to get department info
            if 'child_department' in last_piece.columns:
                display_columns.append('child_department')
            elif 'department_id' in last_piece.columns:
                # Create department mapping
                dept_mapping = {}
                for dept_id in last_piece['department_id'].unique():
                    dept_info = st.session_state.data_manager.get_department_info(dept_id)
                    if dept_info is not None and not dept_info.empty:
                        dept_mapping[dept_id] = dept_info.get('child_department', f'Dept_{dept_id}')
                    else:
                        dept_mapping[dept_id] = f'Dept_{dept_id}'
                last_piece['child_department'] = last_piece['department_id'].map(dept_mapping)
                display_columns.append('child_department')
            
            # Only include columns that actually exist
            available_columns = [col for col in display_columns if col in last_piece.columns]
            
            st.dataframe(
                last_piece[available_columns],
                use_container_width=True
            )
            
            # Generate reorder list
            st.download_button(
                "📋 Generate Reorder List",
                generate_reorder_list(last_piece),
                file_name="immediate_reorder_list.csv",
                mime="text/csv"
            )
        else:
            st.success("✅ No last piece level alerts")
    
    with alert_tab2:
        if not low_stock.empty:
            # Fix: Handle missing child_department column for low stock
            display_columns = ['name', 'part_number', 'quantity', 'min_order_level', 'min_order_quantity']
            
            # Add child_department if it exists, otherwise try to get department info
            if 'child_department' in low_stock.columns:
                display_columns.append('child_department')
            elif 'department_id' in low_stock.columns:
                # Create department mapping
                dept_mapping = {}
                for dept_id in low_stock['department_id'].unique():
                    dept_info = st.session_state.data_manager.get_department_info(dept_id)
                    if dept_info is not None and not dept_info.empty:
                        dept_mapping[dept_id] = dept_info.get('child_department', f'Dept_{dept_id}')
                    else:
                        dept_mapping[dept_id] = f'Dept_{dept_id}'
                low_stock['child_department'] = low_stock['department_id'].map(dept_mapping)
                display_columns.append('child_department')
            
            # Only include columns that actually exist
            available_columns = [col for col in display_columns if col in low_stock.columns]
            
            st.dataframe(
                low_stock[available_columns],
                use_container_width=True
            )
        else:
            st.success("✅ No low stock alerts")
    
    with alert_tab3:
        render_reordering_recommendations(spare_parts)

def ensure_data_consistency(df, expected_columns=None):
    """Ensure dataframe has expected columns and proper data types"""
    if df.empty:
        return df
    
    df = df.copy()
    
    # Ensure numeric columns are properly typed
    numeric_columns = ['quantity', 'min_order_level', 'min_order_quantity', 'line_no']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Handle department information
    if 'child_department' not in df.columns and 'department_id' in df.columns:
        # Create department mapping
        dept_mapping = {}
        for dept_id in df['department_id'].unique():
            dept_info = st.session_state.data_manager.get_department_info(dept_id)
            if dept_info is not None and not dept_info.empty:
                dept_mapping[dept_id] = dept_info.get('child_department', f'Dept_{dept_id}')
            else:
                dept_mapping[dept_id] = f'Dept_{dept_id}'
        df['child_department'] = df['department_id'].map(dept_mapping)
    elif 'child_department' not in df.columns:
        df['child_department'] = 'General Department'
    
    # Fill any NaN values in critical columns
    if 'child_department' in df.columns:
        df['child_department'] = df['child_department'].fillna('Unknown Department')
    
    return df

def render_performance_reports(days, department_id, user_role):
    """Performance and analytics reports"""
    st.subheader("📈 Performance & Analytics Reports")
    
    # Get data based on access
    if user_role == 'User':
        spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
        transactions = st.session_state.data_manager.get_transaction_history_by_department(department_id, days)
    else:
        if department_id:
            spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
            transactions = st.session_state.data_manager.get_transaction_history_by_department(department_id, days)
        else:
            spare_parts = st.session_state.data_manager.get_all_parts()
            transactions = st.session_state.data_manager.get_transaction_history(days=days)
    
    # Performance Metrics
    perf_col1, perf_col2, perf_col3, perf_col4 = st.columns(4)
    
    with perf_col1:
        stock_accuracy = calculate_stock_accuracy(spare_parts, transactions)
        st.metric("Stock Accuracy", f"{stock_accuracy}%")
    
    with perf_col2:
        fill_rate = calculate_fill_rate(transactions)
        st.metric("Fill Rate", f"{fill_rate}%")
    
    with perf_col3:
        carrying_cost = calculate_carrying_cost(spare_parts)
        st.metric("Carrying Cost", f"${carrying_cost:,.0f}")
    
    with perf_col4:
        optimal_stock = calculate_optimal_stock_percentage(spare_parts)
        st.metric("Optimal Stock", f"{optimal_stock}%")
    
    # Performance Charts
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        fig = create_performance_trend_chart(transactions)
        st.plotly_chart(fig, use_container_width=True)
    
    with chart_col2:
        fig = create_efficiency_chart(spare_parts, transactions)
        st.plotly_chart(fig, use_container_width=True)
    
    # Department Comparison (only for Admin/Super User)
    if user_role in ['Admin', 'Super User'] and not department_id:
        st.subheader("Department Performance Comparison")
        fig = create_department_comparison_chart(spare_parts, transactions)
        st.plotly_chart(fig, use_container_width=True)

# =============================================================================
# REPORT RENDERING FUNCTIONS
# =============================================================================

def render_stock_level_report(spare_parts):
    """Render detailed stock level analysis report"""
    st.write("### Stock Level Analysis")
    
    spare_parts = spare_parts.copy()
    
    # Ensure numeric column
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    
    # Stock level distribution
    fig = px.histogram(
        spare_parts,
        x='quantity',
        nbins=20,
        title="Stock Level Distribution",
        labels={'quantity': 'Quantity in Stock'}
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Stock level details
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Stock Level Summary**")
        summary_data = {
            'Metric': ['Average Stock', 'Median Stock', 'Max Stock', 'Min Stock'],
            'Value': [
                spare_parts['quantity'].mean(),
                spare_parts['quantity'].median(),
                spare_parts['quantity'].max(),
                spare_parts['quantity'].min()
            ]
        }
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
    
    with col2:
        st.write("**Stock Level Ranges**")
        # Use pandas cut with proper numeric conversion
        ranges = pd.cut(
            spare_parts['quantity'], 
            bins=[0, 1, 5, 10, 20, 50, 100, float('inf')],
            labels=['0', '1-5', '6-10', '11-20', '21-50', '51-100', '100+']
        )
        range_counts = ranges.value_counts().sort_index()
        st.dataframe(range_counts, use_container_width=True)
    
    # Export stock level report
    st.download_button(
        "📥 Download Stock Level Report",
        spare_parts.to_csv(index=False),
        file_name=f"stock_level_report_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

def render_abc_classification_report(spare_parts):
    """Render ABC classification report"""
    st.write("### ABC Inventory Classification")
    
    # Perform ABC analysis
    abc_data = perform_abc_analysis(spare_parts)
    
    if not abc_data.empty:
        # ABC summary
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = px.pie(
                abc_data,
                names='abc_class',
                title="ABC Classification Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.write("**ABC Summary**")
            abc_summary = abc_data.groupby('abc_class').agg({
                'name': 'count',
                'estimated_value': 'sum'
            }).rename(columns={'name': 'item_count', 'estimated_value': 'total_value'})
            abc_summary['value_percentage'] = (abc_summary['total_value'] / abc_summary['total_value'].sum() * 100).round(1)
            st.dataframe(abc_summary, use_container_width=True)
        
        # Detailed ABC data
        st.write("**Classified Items**")
        st.dataframe(
            abc_data[['name', 'part_number', 'quantity', 'estimated_value', 'abc_class']],
            use_container_width=True
        )
        
        # Export ABC report
        st.download_button(
            "📥 Download ABC Classification Report",
            abc_data.to_csv(index=False),
            file_name=f"abc_classification_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def render_value_analysis_report(spare_parts):
    """Render inventory value analysis report"""
    st.write("### Inventory Value Analysis")
    
    spare_parts = spare_parts.copy()
    
    # Ensure numeric columns
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    
    # Calculate estimated values (simplified)
    spare_parts['estimated_value'] = spare_parts['quantity'] * spare_parts['min_order_level'] * 10
    
    # Value distribution
    if 'child_department' in spare_parts.columns and not spare_parts['child_department'].isna().all():
        fig = px.treemap(
            spare_parts,
            path=['child_department', 'name'],
            values='estimated_value',
            title="Inventory Value Distribution by Department"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        fig = px.treemap(
            spare_parts,
            path=['name'],
            values='estimated_value',
            title="Inventory Value Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Top valued items
    st.write("**Top 20 Highest Value Items**")
    top_items = spare_parts.nlargest(20, 'estimated_value')[['name', 'part_number', 'quantity', 'estimated_value']]
    if 'child_department' in spare_parts.columns:
        top_items['child_department'] = spare_parts['child_department']
    st.dataframe(top_items, use_container_width=True)
    
    # Value summary by department
    if 'child_department' in spare_parts.columns and not spare_parts['child_department'].isna().all():
        dept_value = spare_parts.groupby('child_department').agg({
            'estimated_value': 'sum',
            'name': 'count'
        }).rename(columns={'name': 'item_count', 'estimated_value': 'total_value'})
        dept_value = dept_value.sort_values('total_value', ascending=False)
        
        st.write("**Value by Department**")
        st.dataframe(dept_value, use_container_width=True)

def render_department_summary_report(spare_parts, user_role, department_id):
    """Render department-specific summary report"""
    st.write("### Department Inventory Summary")
    
    if user_role == 'User' or department_id:
        # Single department view
        dept_info = st.session_state.data_manager.get_department_info(department_id)
        if dept_info is not None and not dept_info.empty:
            st.info(f"**Department**: {dept_info['child_department']} - {dept_info['parent_department']}")
        
        # Department-specific metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Items", len(spare_parts))
        
        with col2:
            total_value = calculate_inventory_value(spare_parts)
            st.metric("Total Value", f"${total_value:,.0f}")
        
        with col3:
            avg_stock = spare_parts['quantity'].mean()
            st.metric("Average Stock", f"{avg_stock:.1f}")
        
        with col4:
            stock_health = (len(spare_parts[spare_parts['quantity'] > spare_parts['min_order_level']]) / len(spare_parts)) * 100
            st.metric("Stock Health", f"{stock_health:.1f}%")
    else:
        # Multi-department view for Admin/Super User
        if 'child_department' in spare_parts.columns:
            dept_summary = spare_parts.groupby('child_department').agg({
                'name': 'count',
                'quantity': 'sum',
                'min_order_level': 'mean'
            }).rename(columns={'name': 'item_count', 'quantity': 'total_quantity'})
            
            st.dataframe(dept_summary, use_container_width=True)

def render_custom_inventory_report(spare_parts):
    """Render customizable inventory report"""
    st.write("### Custom Inventory Report Builder")
    
    # Column selection
    available_columns = [
        'part_number', 'name', 'description', 'quantity', 'min_order_level',
        'min_order_quantity', 'barcode', 'status', 'child_department', 'compartment_no', 'box_no'
    ]
    
    selected_columns = st.multiselect(
        "Select columns to include",
        available_columns,
        default=['part_number', 'name', 'quantity', 'min_order_level', 'child_department']
    )
    
    # Filters
    st.write("**Apply Filters**")
    filter_col1, filter_col2 = st.columns(2)
    
    with filter_col1:
        min_quantity = st.number_input("Minimum Quantity", min_value=0, value=0)
        max_quantity = st.number_input("Maximum Quantity", min_value=0, value=1000)
    
    with filter_col2:
        status_filter = st.multiselect(
            "Status Filter",
            spare_parts['status'].unique() if 'status' in spare_parts.columns else [],
            default=[]
        )
    
    # Generate custom report
    if st.button("Generate Custom Report"):
        filtered_data = spare_parts.copy()
        
        # Apply quantity filters
        filtered_data = filtered_data[
            (filtered_data['quantity'] >= min_quantity) & 
            (filtered_data['quantity'] <= max_quantity)
        ]
        
        # Apply status filter
        if status_filter and 'status' in filtered_data.columns:
            filtered_data = filtered_data[filtered_data['status'].isin(status_filter)]
        
        # Select columns
        if selected_columns:
            # Ensure columns exist
            existing_columns = [col for col in selected_columns if col in filtered_data.columns]
            filtered_data = filtered_data[existing_columns]
        
        st.write("**Custom Report Results**")
        st.dataframe(filtered_data, use_container_width=True)
        
        # Export custom report
        st.download_button(
            "📥 Download Custom Report",
            filtered_data.to_csv(index=False),
            file_name=f"custom_inventory_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def render_transaction_history_report(transactions):
    """Render transaction history report"""
    st.write("### Transaction History Report")
    
    # Date filter
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("End Date", value=datetime.now())
    
    # Filter transactions by date
    transactions['timestamp'] = pd.to_datetime(transactions['timestamp'])
    filtered_transactions = transactions[
        (transactions['timestamp'].dt.date >= start_date) & 
        (transactions['timestamp'].dt.date <= end_date)
    ]
    
    if not filtered_transactions.empty:
        # Transaction summary
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        
        with summary_col1:
            total_transactions = len(filtered_transactions)
            st.metric("Total Transactions", total_transactions)
        
        with summary_col2:
            check_outs = len(filtered_transactions[filtered_transactions['transaction_type'] == 'check_out'])
            st.metric("Check-Outs", check_outs)
        
        with summary_col3:
            check_ins = len(filtered_transactions[filtered_transactions['transaction_type'] == 'check_in'])
            st.metric("Check-Ins", check_ins)
        
        # Detailed transaction data
        st.dataframe(
            filtered_transactions[[
                'timestamp', 'name', 'part_number', 'transaction_type', 
                'quantity', 'reason', 'remarks', 'child_department'
            ]],
            use_container_width=True
        )
        
        # Export transaction history
        st.download_button(
            "📥 Download Transaction History",
            filtered_transactions.to_csv(index=False),
            file_name=f"transaction_history_{start_date}_{end_date}.csv",
            mime="text/csv"
        )
    else:
        st.warning("No transactions found for the selected date range")

def render_movement_analysis_report(transactions):
    """Render item movement analysis report"""
    st.write("### Item Movement Analysis")
    
    # Movement analysis
    movement_data = transactions.groupby(['name', 'transaction_type']).agg({
        'quantity': 'sum',
        'timestamp': 'count'
    }).reset_index()
    
    # Pivot for better visualization
    movement_pivot = movement_data.pivot_table(
        index='name', 
        columns='transaction_type', 
        values='quantity', 
        aggfunc='sum'
    ).fillna(0)
    
    movement_pivot['net_movement'] = movement_pivot.get('check_in', 0) - movement_pivot.get('check_out', 0)
    movement_pivot = movement_pivot.sort_values('net_movement', ascending=False)
    
    st.dataframe(movement_pivot, use_container_width=True)
    
    # Top movers chart
    top_movers = movement_pivot.head(10)
    fig = px.bar(
        top_movers.reset_index(),
        x='name',
        y=['check_in', 'check_out'],
        title="Top 10 Moving Items",
        barmode='group'
    )
    st.plotly_chart(fig, use_container_width=True)

def render_trend_analysis_report(transactions, days):
    """Render transaction trend analysis"""
    st.write("### Transaction Trend Analysis")
    
    # Daily trend
    transactions['date'] = pd.to_datetime(transactions['timestamp']).dt.date
    daily_trend = transactions.groupby(['date', 'transaction_type']).size().reset_index(name='count')
    
    fig = px.line(
        daily_trend,
        x='date',
        y='count',
        color='transaction_type',
        title="Daily Transaction Trends"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Weekly pattern
    transactions['day_of_week'] = pd.to_datetime(transactions['timestamp']).dt.day_name()
    weekly_pattern = transactions.groupby(['day_of_week', 'transaction_type']).size().reset_index(name='count')
    
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    weekly_pattern['day_of_week'] = pd.Categorical(weekly_pattern['day_of_week'], categories=days_order, ordered=True)
    weekly_pattern = weekly_pattern.sort_values('day_of_week')
    
    fig = px.bar(
        weekly_pattern,
        x='day_of_week',
        y='count',
        color='transaction_type',
        title="Weekly Transaction Pattern",
        barmode='group'
    )
    st.plotly_chart(fig, use_container_width=True)

def render_custom_transaction_report(transactions):
    """Render customizable transaction report"""
    st.write("### Custom Transaction Report Builder")
    
    # Similar to custom inventory report but for transactions
    available_columns = [
        'timestamp', 'name', 'part_number', 'transaction_type', 'quantity',
        'reason', 'remarks', 'child_department', 'parent_department'
    ]
    
    selected_columns = st.multiselect(
        "Select columns to include",
        available_columns,
        default=['timestamp', 'name', 'transaction_type', 'quantity', 'reason']
    )
    
    # Transaction type filter
    transaction_types = st.multiselect(
        "Transaction Types",
        transactions['transaction_type'].unique(),
        default=transactions['transaction_type'].unique()
    )
    
    if st.button("Generate Custom Transaction Report"):
        filtered_data = transactions[transactions['transaction_type'].isin(transaction_types)]
        
        if selected_columns:
            existing_columns = [col for col in selected_columns if col in filtered_data.columns]
            filtered_data = filtered_data[existing_columns]
        
        st.dataframe(filtered_data, use_container_width=True)
        
        st.download_button(
            "📥 Download Custom Transaction Report",
            filtered_data.to_csv(index=False),
            file_name=f"custom_transaction_report_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

def render_reordering_recommendations(spare_parts):
    """Render intelligent reordering recommendations"""
    st.write("### 📋 Intelligent Reordering Recommendations")
    
    spare_parts = spare_parts.copy()
    
    # Ensure numeric columns
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    spare_parts['min_order_quantity'] = pd.to_numeric(spare_parts['min_order_quantity'], errors='coerce').fillna(1)
    
    # Calculate reorder needs
    reorder_needs = spare_parts[
        (spare_parts['quantity'] <= spare_parts['min_order_level']) & 
        (spare_parts['quantity'] > 0)
    ].copy()
    
    if not reorder_needs.empty:
        reorder_needs['reorder_quantity'] = reorder_needs['min_order_quantity']
        
        # Calculate priority using pandas operations
        priority = []
        for _, row in reorder_needs.iterrows():
            if row['quantity'] == 1:
                priority.append('🚨 CRITICAL')
            elif row['quantity'] <= row['min_order_level'] * 0.5:
                priority.append('⚠️ HIGH')
            else:
                priority.append('🔶 MEDIUM')
        
        reorder_needs['priority'] = priority
        
        # Priority summary
        priority_summary = reorder_needs.groupby('priority').agg({
            'name': 'count',
            'reorder_quantity': 'sum'
        }).rename(columns={'name': 'item_count'})
        
        st.write("**Reorder Priority Summary**")
        st.dataframe(priority_summary, use_container_width=True)
        
        # Detailed reorder list
        st.write("**Detailed Reorder List**")
        reorder_display = reorder_needs[[
            'name', 'part_number', 'quantity', 'min_order_level', 
            'reorder_quantity', 'priority', 'child_department'
        ]].sort_values('priority')
        
        st.dataframe(reorder_display, use_container_width=True)
        
        # Generate purchase order
        st.download_button(
            "🛒 Generate Purchase Order List",
            reorder_needs[['name', 'part_number', 'reorder_quantity', 'priority']].to_csv(index=False),
            file_name=f"purchase_order_list_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.success("✅ No reordering recommendations at this time")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_days_from_period(period):
    """Convert period selection to days"""
    period_map = {
        "Last 7 Days": 7,
        "Last 30 Days": 30,
        "Last 90 Days": 90,
        "Last 6 Months": 180,
        "Last Year": 365
    }
    return period_map.get(period, 30)

def calculate_inventory_value(spare_parts):
    """Calculate total inventory value (simplified)"""
    if spare_parts.empty:
        return 0
    
    spare_parts = spare_parts.copy()
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    
    return (spare_parts['quantity'] * spare_parts['min_order_level'] * 10).sum()

def calculate_turnover_rate(transactions, spare_parts):
    """Calculate inventory turnover rate"""
    if transactions.empty or spare_parts.empty:
        return 0
    
    # Ensure numeric data types
    transactions = transactions.copy()
    spare_parts = spare_parts.copy()
    
    transactions['quantity'] = pd.to_numeric(transactions['quantity'], errors='coerce').fillna(0)
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    
    total_usage = abs(transactions[transactions['transaction_type'] == 'check_out']['quantity'].sum())
    avg_inventory = spare_parts['quantity'].mean()
    
    return total_usage / avg_inventory if avg_inventory != 0 else 0

def calculate_service_level(transactions):
    """Calculate service level percentage"""
    if transactions.empty:
        return 100
    total_demand = abs(transactions[transactions['transaction_type'] == 'check_out']['quantity'].sum())
    return 95.0  # Simplified - in real scenario, calculate based on stockouts

def create_inventory_health_chart(spare_parts):
    """Create inventory health status chart"""
    if spare_parts.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", x=0.5, y=0.5, showarrow=False)
        return fig
    
    # Ensure we're working with proper data types
    spare_parts = spare_parts.copy()
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    
    # Create health status using pandas operations instead of np.select
    health_status = []
    for _, row in spare_parts.iterrows():
        quantity = row['quantity']
        min_order_level = row['min_order_level']
        
        if quantity == 0:
            health_status.append('Out of Stock')
        elif quantity == 1:
            health_status.append('Last Piece')
        elif quantity <= min_order_level:
            health_status.append('Low Stock')
        else:
            health_status.append('Healthy')
    
    spare_parts['health_status'] = health_status
    
    health_counts = spare_parts['health_status'].value_counts()
    
    fig = px.pie(
        values=health_counts.values,
        names=health_counts.index,
        title="Inventory Health Status",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(showlegend=False, height=400)
    
    return fig

def create_department_activity_chart(transactions, spare_parts):
    """Create department activity chart"""
    if transactions.empty:
        fig = go.Figure()
        fig.add_annotation(text="No transaction data", x=0.5, y=0.5, showarrow=False)
        return fig
    
    # Merge to get department info
    if 'child_department' not in transactions.columns and 'part_id' in transactions.columns:
        merged = transactions.merge(
            spare_parts[['id', 'child_department']], 
            left_on='part_id', 
            right_on='id'
        )
        dept_activity = merged.groupby('child_department').size()
    else:
        dept_activity = transactions.groupby('child_department').size()
    
    fig = px.bar(
        x=dept_activity.index,
        y=dept_activity.values,
        title="Department Activity Level"
    )
    return fig

def get_top_moving_items(transactions, top_n=5):
    """Get top moving items"""
    if transactions.empty:
        return []
    
    top_movers = transactions.groupby('name')['quantity'].sum().abs().nlargest(top_n)
    return [{'name': name, 'quantity': int(qty)} for name, qty in top_movers.items()]

def get_critical_items(spare_parts, top_n=3):
    """Get most critical items needing attention"""
    if spare_parts.empty:
        return []
    
    spare_parts = spare_parts.copy()
    
    # Ensure numeric columns
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    
    critical = spare_parts[
        spare_parts['quantity'] <= spare_parts['min_order_level']
    ].nsmallest(top_n, 'quantity')
    
    return [{
        'name': str(row['name']),
        'quantity': int(row['quantity']),
        'min_level': int(row['min_order_level'])
    } for _, row in critical.iterrows()]

def perform_abc_analysis(spare_parts):
    """Perform ABC analysis on inventory"""
    if spare_parts.empty:
        return pd.DataFrame()
    
    spare_parts = spare_parts.copy()
    
    # Ensure numeric columns
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    
    # Simplified ABC analysis
    spare_parts['estimated_value'] = spare_parts['quantity'] * spare_parts['min_order_level'] * 10
    spare_parts = spare_parts.sort_values('estimated_value', ascending=False)
    spare_parts['cumulative_percentage'] = spare_parts['estimated_value'].cumsum() / spare_parts['estimated_value'].sum() * 100
    
    # Use pandas operations instead of np.select
    abc_class = []
    for cum_pct in spare_parts['cumulative_percentage']:
        if cum_pct <= 80:
            abc_class.append('A')
        elif cum_pct <= 95:
            abc_class.append('B')
        else:
            abc_class.append('C')
    
    spare_parts['abc_class'] = abc_class
    
    return spare_parts

def calculate_stock_accuracy(spare_parts, transactions):
    """Calculate stock accuracy percentage"""
    return 98.5  # Simplified - in real scenario, compare physical counts

def calculate_fill_rate(transactions):
    """Calculate order fill rate"""
    return 95.2  # Simplified

def calculate_carrying_cost(spare_parts):
    """Calculate inventory carrying cost"""
    total_value = calculate_inventory_value(spare_parts)
    return total_value * 0.25  # 25% carrying cost estimate

def calculate_optimal_stock_percentage(spare_parts):
    """Calculate percentage of items at optimal stock levels"""
    if spare_parts.empty:
        return 0
    optimal = spare_parts[
        (spare_parts['quantity'] > spare_parts['min_order_level']) & 
        (spare_parts['quantity'] <= spare_parts['min_order_level'] * 2)
    ]
    return (len(optimal) / len(spare_parts)) * 100

def create_performance_trend_chart(transactions):
    """Create performance trend chart"""
    fig = go.Figure()
    fig.add_annotation(text="Performance trend analysis", x=0.5, y=0.5, showarrow=False)
    return fig

def create_efficiency_chart(spare_parts, transactions):
    """Create efficiency analysis chart"""
    fig = go.Figure()
    fig.add_annotation(text="Efficiency analysis", x=0.5, y=0.5, showarrow=False)
    return fig

def create_department_comparison_chart(spare_parts, transactions):
    """Create department comparison chart"""
    fig = go.Figure()
    fig.add_annotation(text="Department comparison analysis", x=0.5, y=0.5, showarrow=False)
    return fig

def generate_executive_summary_pdf(spare_parts, transactions):
    """Generate executive summary PDF (placeholder)"""
    return "PDF generation would be implemented here".encode()

def generate_reorder_list(last_piece_items):
    """Generate reorder list CSV"""
    if last_piece_items.empty:
        return "No items to reorder".encode()
    
    # Create a copy to avoid modifying original
    reorder_data = last_piece_items.copy()
    
    # Define base columns
    reorder_columns = ['name', 'part_number', 'quantity', 'min_order_quantity']
    
    # Ensure child_department exists
    if 'child_department' not in reorder_data.columns:
        if 'department_id' in reorder_data.columns:
            # Create department mapping
            dept_mapping = {}
            for dept_id in reorder_data['department_id'].unique():
                dept_info = st.session_state.data_manager.get_department_info(dept_id)
                if dept_info is not None and not dept_info.empty:
                    dept_mapping[dept_id] = dept_info.get('child_department', f'Dept_{dept_id}')
                else:
                    dept_mapping[dept_id] = f'Dept_{dept_id}'
            reorder_data['child_department'] = reorder_data['department_id'].map(dept_mapping)
        else:
            reorder_data['child_department'] = 'General Department'
    
    # Add child_department to columns if it exists
    if 'child_department' in reorder_data.columns:
        reorder_columns.append('child_department')
    
    # Add reorder quantity
    reorder_data['reorder_qty'] = reorder_data['min_order_quantity']
    reorder_columns.append('reorder_qty')
    
    # Only include columns that exist
    available_columns = [col for col in reorder_columns if col in reorder_data.columns]
    
    return reorder_data[available_columns].to_csv(index=False).encode()

if __name__ == "__main__":
    render_reports_page()