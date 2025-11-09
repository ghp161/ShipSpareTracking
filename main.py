import streamlit as st
from app_settings import set_page_configuration

set_page_configuration()

from data_manager import DataManager
from barcode_handler import BarcodeHandler
from user_management import init_session_state, render_login_page, check_and_restore_session
from navbar import make_sidebar
from datetime import datetime, timedelta
import pandas as pd


# Initialize alerts in session state
if 'alerts' not in st.session_state:
    st.session_state.alerts = []

def main():
    """Main application entry point"""
    # Initialize session state
    init_session_state()
    
    # Check for existing session
    if not st.session_state.authenticated:
        check_and_restore_session()
    
    # Show appropriate content based on authentication
    if st.session_state.authenticated:
        show_application()
    else:
        render_login_page()

def show_application():
    
    st.title("Ship Inventory Management System")

    # Show user info in sidebar
    with st.sidebar:
        make_sidebar()

    # Dashboard layout
    col1, col2, col3 = st.columns(3)

    with col1:
        lpl_stock = st.session_state.data_manager.get_last_piece_stock_items()
        low_stock = st.session_state.data_manager.get_low_stock_items()
        df = st.session_state.data_manager.get_all_parts()
        total_parts = len(df)
        low_stock_count = len(low_stock)
        lpl_stock_count = len(lpl_stock)

        st.metric("Total Parts",
                  total_parts,
                  help="Total number of unique parts in inventory")
 
    with col2:
        st.metric("LPL Stock Items",
                  lpl_stock_count,
                  delta=lpl_stock_count,
                  delta_color="inverse",
                  help="Number of items below last piece level")
        
    with col3:
        active_alerts = len(low_stock) + len(lpl_stock)
        monthly_turnover = calculate_monthly_turnover()
        st.metric("Active Alerts", active_alerts, delta=active_alerts, delta_color="inverse")

    # Quick Insights Section
    st.subheader("📊 Quick Insights")
    
    insight_col1, insight_col2 = st.columns(2)
    
    with insight_col1:
        # Top moving items
        st.write("**🚀 Fast Moving Items**")
        fast_moving = get_fast_moving_items()
        if not fast_moving.empty:
            for _, item in fast_moving.head(3).iterrows():
                st.write(f"• {item['name']} - {item['transaction_count']} moves")
        else:
            st.write("• No fast moving items data")
        
        # Maintenance schedule
        st.write("**🔧 Upcoming Maintenance**")
        maintenance_due = get_maintenance_due()
        if not maintenance_due.empty:
            for _, item in maintenance_due.head(3).iterrows():
                days_until = (item['next_maintenance_date'] - datetime.now().date()).days
                st.write(f"• {item['name']} - {days_until} days")
        else:
            st.write("• No maintenance scheduled")
    
    with insight_col2:
        # Department overview
        st.write("**🏗️ Department Overview**")
        dept_summary = get_department_summary()
        
        # Fix: Handle dictionary properly - dictionaries don't have .empty attribute
        if dept_summary and isinstance(dept_summary, dict):
            # Convert to list of items and take first 4
            dept_items = list(dept_summary.items())[:4]
            for dept, count in dept_items:
                st.write(f"• {dept}: {count} items")
        elif isinstance(dept_summary, pd.DataFrame) and not dept_summary.empty:
            # Handle DataFrame case
            for dept, count in dept_summary.head(4).items():
                st.write(f"• {dept}: {count} items")
        else:
            st.write("• No department data available")
        
        # Recent critical events
        st.write("**⚠️ Recent Critical Events**")
        critical_events = get_critical_events()
        if critical_events:
            for event in critical_events[:3]:  # Show only first 3 events
                st.write(f"• {event}")
        else:
            st.write("• No critical events")

    # Quick Actions
    st.subheader("🚀 Quick Actions")
    action_col1, action_col2 = st.columns(2)
    
    with action_col1:
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

    with action_col2:
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
    
    # Enhanced Recent Transactions with filters
    trans_col1, trans_col2 = st.columns(2)
    with trans_col1:
        trans_days = st.selectbox("Time Period", [7, 30, 90], index=0, key="trans_days")
    with trans_col2:
        trans_type = st.selectbox("Transaction Type", ["All", "Check-Out", "Check-In"], key="trans_type")
    
    recent_transactions = st.session_state.data_manager.get_transaction_history(days=30)
    filtered_transactions = filter_transactions(recent_transactions, trans_days, trans_type)
    
    if not filtered_transactions.empty:
        st.dataframe(filtered_transactions[[
            'timestamp', 'name', 'transaction_type', 'quantity'
        ]],
                     hide_index=True)
        
        # Transaction summary
        summary_col1, summary_col2, summary_col3 = st.columns(3)
        with summary_col1:
            check_outs = len(filtered_transactions[filtered_transactions['transaction_type'] == 'check_out'])
            st.metric("Check-Outs", check_outs)
        with summary_col2:
            check_ins = len(filtered_transactions[filtered_transactions['transaction_type'] == 'check_in'])
            st.metric("Check-Ins", check_ins)
        with summary_col3:
            total_movement = abs(filtered_transactions['quantity'].sum())
            st.metric("Total Movement", total_movement)
    else:
        st.info("No recent transactions found")

# Helper functions
def calculate_inventory_value(spare_parts):
    """Calculate total inventory value (simplified)"""
    if spare_parts.empty:
        return 0
    
    spare_parts = spare_parts.copy()
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    
    return (spare_parts['quantity'] * spare_parts['min_order_level'] * 10).sum()

def calculate_monthly_turnover():
    """Calculate monthly inventory turnover rate"""
    try:
        # This would need to be implemented based on your business logic
        return 15  # Placeholder
    except:
        return 0

def get_fast_moving_items():
    """Get items with highest transaction frequency"""
    try:
        data_manager = st.session_state.data_manager
        transactions = data_manager.get_transaction_history(days=30)
        
        if transactions.empty:
            return pd.DataFrame()
        
        # Group by item name and count transactions
        fast_moving = transactions.groupby('name').agg({
            'quantity': 'sum',
            'timestamp': 'count'
        }).rename(columns={'timestamp': 'transaction_count'})
        
        # Sort by transaction count
        fast_moving = fast_moving.sort_values('transaction_count', ascending=False)
        return fast_moving.reset_index()
        
    except Exception as e:
        print(f"Error in get_fast_moving_items: {e}")
        return pd.DataFrame()

def get_maintenance_due():
    """Get items due for maintenance soon"""
    try:
        data_manager = st.session_state.data_manager
        spare_parts = data_manager.get_all_parts()
        
        if spare_parts.empty:
            return pd.DataFrame()
        
        # Check for next_maintenance_date column
        if 'next_maintenance_date' not in spare_parts.columns:
            return pd.DataFrame()
        
        # Filter items with upcoming maintenance
        spare_parts = spare_parts.copy()
        spare_parts['next_maintenance_date'] = pd.to_datetime(spare_parts['next_maintenance_date'], errors='coerce')
        
        # Get items with maintenance due in next 30 days
        today = datetime.now().date()
        future_date = today + timedelta(days=30)
        
        maintenance_due = spare_parts[
            (spare_parts['next_maintenance_date'].notna()) &
            (spare_parts['next_maintenance_date'].dt.date >= today) &
            (spare_parts['next_maintenance_date'].dt.date <= future_date)
        ]
        
        return maintenance_due[['name', 'next_maintenance_date']].sort_values('next_maintenance_date')
        
    except Exception as e:
        print(f"Error in get_maintenance_due: {e}")
        return pd.DataFrame()

def get_department_summary():
    """Get item count by department"""
    try:
        data_manager = st.session_state.data_manager
        spare_parts = data_manager.get_all_parts()
        
        if spare_parts.empty:
            return {}
        
        # Ensure we have department information
        if 'child_department' in spare_parts.columns:
            dept_counts = spare_parts['child_department'].value_counts().to_dict()
        elif 'department_id' in spare_parts.columns:
            # Create department mapping
            dept_mapping = {}
            for dept_id in spare_parts['department_id'].unique():
                dept_info = data_manager.get_department_info(dept_id)
                if dept_info is not None and not dept_info.empty:
                    dept_name = dept_info.get('child_department', f'Dept_{dept_id}')
                else:
                    dept_name = f'Dept_{dept_id}'
                dept_mapping[dept_id] = dept_name
            
            # Count items per department
            dept_counts = {}
            for dept_id in spare_parts['department_id'].unique():
                dept_name = dept_mapping.get(dept_id, f'Dept_{dept_id}')
                count = len(spare_parts[spare_parts['department_id'] == dept_id])
                dept_counts[dept_name] = count
        else:
            dept_counts = {'General': len(spare_parts)}
        
        return dept_counts
        
    except Exception as e:
        print(f"Error in get_department_summary: {e}")
        return {}

def get_critical_events():
    """Get recent critical stock events"""
    try:
        data_manager = st.session_state.data_manager
        
        # Get low stock and last piece items
        low_stock = data_manager.get_low_stock_items()
        last_piece = data_manager.get_last_piece_stock_items()
        
        critical_events = []
        
        # Add last piece alerts
        if not last_piece.empty:
            for _, item in last_piece.head(2).iterrows():  # Limit to 2 items
                critical_events.append(f"Last piece: {item['name']} (Only {item['quantity']} left)")
        
        # Add low stock alerts
        if not low_stock.empty:
            for _, item in low_stock.head(2).iterrows():  # Limit to 2 items
                critical_events.append(f"Low stock: {item['name']} ({item['quantity']} left, min: {item['min_order_level']})")
        
        # If no critical events, add a message
        if not critical_events:
            critical_events.append("No critical events - all systems normal")
        
        return critical_events
        
    except Exception as e:
        print(f"Error in get_critical_events: {e}")
        return ["Error loading critical events"]

def filter_transactions(transactions, days, trans_type):
    """Filter transactions based on criteria"""
    try:
        filtered = transactions.copy()
        
        # Filter by date
        if days > 0:
            cutoff_date = datetime.now() - timedelta(days=days)
            filtered['timestamp'] = pd.to_datetime(filtered['timestamp'])
            filtered = filtered[filtered['timestamp'] >= cutoff_date]
        
        # Filter by transaction type
        if trans_type != "All":
            trans_type_map = {"Check-Out": "check_out", "Check-In": "check_in"}
            if trans_type in trans_type_map:
                filtered = filtered[filtered['transaction_type'] == trans_type_map[trans_type]]
        
        return filtered
        
    except Exception as e:
        print(f"Error in filter_transactions: {e}")
        return pd.DataFrame()

# Only run the main function if this is the main script
if __name__ == "__main__":
    main()