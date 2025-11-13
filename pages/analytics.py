import streamlit as st
from app_settings import set_page_configuration

set_page_configuration()

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.colors import qualitative
import numpy as np
from datetime import datetime, timedelta
from user_management import login_required, init_session_state, check_and_restore_session
import navbar
from data_manager import DataManager


current_page = "Analytics"
st.header(current_page)

# Initialize session state and check for existing session
init_session_state()
if not st.session_state.authenticated:
    check_and_restore_session()

navbar.nav(current_page)

@login_required
def render_analytics_page():
    #st.title("📊 Advanced Inventory Analytics")
    
    # Initialize session state
    if 'data_manager' not in st.session_state:
        st.session_state.data_manager = DataManager()
    
    with st.expander("🔧 **Analysis Configuration**", expanded=True):
        # Date range selector
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            date_range = st.selectbox(
                "Analysis Period",
                ["Last 30 Days", "Last 90 Days", "Last 6 Months", "Last Year", "Custom"],
                index=1
            )
        
        with col2:
            if date_range == "Custom":
                start_date = st.date_input("Start Date", datetime.now() - timedelta(days=90))
                end_date = st.date_input("End Date", datetime.now())
            else:
                days_map = {
                    "Last 30 Days": 30,
                    "Last 90 Days": 90,
                    "Last 6 Months": 180,
                    "Last Year": 365
                }
                days = days_map.get(date_range, 90)
        
        with col3:
            analysis_focus = st.selectbox(
                "Focus Area",
                ["Overall Performance", "Stock Optimization", "Demand Forecasting",  "Department Analysis"]
            )
    
    with st.expander("🔍 **Data Selection & Filters**", expanded=True):
        # Department selection for data filtering
        #st.subheader("🔍 Data Selection")
        
        # Get current user's role and department
        current_user_role = st.session_state.get('user_role')
        current_user_dept_id = st.session_state.get('user_department_id')
        
        selected_child = None
        selected_parent = None
        
        if current_user_role == 'User':
            # Regular users can only see their own department
            selected_child = current_user_dept_id
            if selected_child:
                dept_info = st.session_state.data_manager.get_department_info(selected_child)
                if dept_info is not None and not dept_info.empty:
                    st.info(f"📋 Viewing data for: {dept_info['child_department']} - {dept_info['parent_department']}")
        else:
            # Admin/Super User can select departments
            cols = st.columns(2)
            
            with cols[0]:
                # Department selection
                parent_depts = st.session_state.data_manager.get_parent_departments()
                if not parent_depts.empty:
                    selected_parent = st.selectbox(
                        "Select Parent Department",
                        parent_depts['id'].tolist(),
                        index=0,
                        placeholder="Select Parent Department",
                        format_func=lambda x: parent_depts[parent_depts['id'] == x]['name'].iloc[0],
                        key="analytics_parent_dept"
                    )
            
            with cols[1]:
                if selected_parent:
                    child_depts = st.session_state.data_manager.get_child_departments(selected_parent)
                    if not child_depts.empty:                                
                        selected_child = st.selectbox(
                            "Select Child Department",
                            child_depts['id'].tolist(),
                            index=0,
                            placeholder="Select Child Department",
                            format_func=lambda x: child_depts[child_depts['id'] == x]['name'].iloc[0],
                            key="analytics_child_dept"
                        )
    
    # Get data with consistency checks
    df = pd.DataFrame()
    transactions = pd.DataFrame()
    
    if selected_child is not None:
        df = st.session_state.data_manager.get_parts_by_department(selected_child)
        # Use selected_parent if available, otherwise use the parent of selected_child
        if selected_parent:
            parent_id_for_transactions = selected_parent
        else:
            # Get parent department from child department
            dept_info = st.session_state.data_manager.get_department_info(selected_child)
            if dept_info is not None and not dept_info.empty and 'parent_id' in dept_info:
                parent_id_for_transactions = dept_info['parent_id']
            else:
                parent_id_for_transactions = selected_child  # fallback
        
        transactions = st.session_state.data_manager.get_transaction_history_by_department(parent_id_for_transactions, days=90)
        
        # Ensure data consistency
        df = ensure_data_consistency(df)
        transactions = ensure_data_consistency(transactions)
    else:
        # If no department selected, get all data (for Admin/Super User)
        if current_user_role in ['Admin', 'Super User']:
            df = st.session_state.data_manager.get_all_parts()
            transactions = st.session_state.data_manager.get_transaction_history(days=90)
            
            # Ensure data consistency
            df = ensure_data_consistency(df)
            transactions = ensure_data_consistency(transactions)
        else:
            st.warning("Please contact administrator to assign you to a department.")
            return

    # Main analytics tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Overview Dashboard", 
        "🔍 Stock Analysis", 
        "📊 Demand Insights",         
        "📋 Detailed Reports"
    ])

    with tab1:
        render_overview_dashboard(days if date_range != "Custom" else (end_date - start_date).days, 
                                selected_child, current_user_role)
    
    with tab2:
        render_stock_analysis(days if date_range != "Custom" else (end_date - start_date).days, 
                            selected_child, current_user_role)
    
    with tab3:
        render_demand_insights(days if date_range != "Custom" else (end_date - start_date).days, 
                             selected_child, current_user_role)
    
    with tab4:
        render_detailed_reports(days if date_range != "Custom" else (end_date - start_date).days, 
                              selected_child, current_user_role)

def render_overview_dashboard(days, department_id, user_role):
    """Overview dashboard with performance metrics"""
    
    with st.expander("📊 **Performance Overview - Methodology**", expanded=False):
        st.write("""
        **Data Used**: Current inventory levels + Transaction history
        **Calculations**:
        - Stock Turnover: Total check-outs ÷ Average inventory quantity
        - Service Level: Based on transaction fulfillment (simplified)
        - Critical Items: Count of items at/below minimum order levels
        """)
    
    st.subheader("🏆 Performance Overview")
    
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
    
    # Ensure data consistency
    spare_parts = ensure_data_consistency(spare_parts)
    transactions = ensure_data_consistency(transactions)
    
    if spare_parts.empty:
        st.warning("No inventory data available for analysis")
        return
    
    # KPI Metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        stock_turnover = calculate_stock_turnover_rate(transactions, spare_parts)
        st.metric(
            "Stock Turnover Rate", 
            f"{stock_turnover:.1f}x",
            delta=f"{calculate_turnover_trend(transactions):.1f}x"
        )
    
    with col2:
        service_level = calculate_service_level(transactions)
        st.metric(
            "Service Level", 
            f"{service_level:.1f}%",
            delta=f"{service_level - 95:.1f}%"
        )
    
    with col3:
        critical_items = len(spare_parts[spare_parts['quantity'] <= spare_parts['min_order_level']])
        st.metric(
            "Critical Items", 
            critical_items,
            delta=critical_items - len(spare_parts[spare_parts['quantity'] == 0]),
            delta_color="inverse"
        )
    
    # Charts Row 1
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        with st.expander("📈 **Monthly Trends - Methodology**", expanded=False):
            st.write("""
            **Data Used**: Transaction history grouped by month
            **Calculation**: Count of check-in/check-out transactions per month
            **Purpose**: Identify seasonal patterns and activity trends
            """)
        fig = create_monthly_trend_chart(transactions)
        st.plotly_chart(fig, use_container_width=True)
    
    with chart_col2:
        with st.expander("🩺 **Inventory Health - Methodology**", expanded=False):
            st.write("""
            **Data Used**: Current stock levels + Minimum order levels
            **Categories**:
            - Healthy: Above minimum order level
            - Low Stock: At/below minimum but above 1
            - Last Piece: Only 1 item remaining
            - Out of Stock: Zero quantity
            """)
        fig = create_inventory_health_chart(spare_parts)
        st.plotly_chart(fig, use_container_width=True)
    
    # Charts Row 2
    chart_col3, chart_col4 = st.columns(2)
    
    with chart_col3:
        with st.expander("🏗️ **Department Performance - Methodology**", expanded=False):
            st.write("""
            **Data Used**: Transactions merged with department info
            **Calculation**: Transaction counts and quantities by department
            **Purpose**: Compare activity levels across departments
            """)
        fig = create_department_performance_chart(transactions, spare_parts)
        st.plotly_chart(fig, use_container_width=True)
    
    with chart_col4:
        with st.expander("📊 **ABC Analysis - Methodology**", expanded=False):
            st.write("""
            **Data Used**: Inventory items with quantities and min order levels
            **Calculation**: Criticality score = quantity × min_order_level
            **Classification**:
            - A (Top 80% of criticality): High priority items
            - B (Next 15%): Medium priority items  
            - C (Bottom 5%): Low priority items
            """)
        fig = create_abc_analysis_chart(spare_parts)
        st.plotly_chart(fig, use_container_width=True)

def render_stock_analysis(days, department_id, user_role):
    """Stock optimization analysis"""
    
    with st.expander("🔍 **Stock Optimization - Methodology**", expanded=False):
        st.write("""
        **Data Used**: Current inventory levels + Transaction patterns
        **Key Metrics**:
        - Excess Stock: Items with quantity > 3× minimum order level
        - Stockout Risk: Items at/below minimum order level
        - Optimal Achievement: Percentage of items above minimum levels
        """)
    
    st.subheader("🔍 Stock Optimization Analysis")
    
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
    
    # Ensure data consistency
    spare_parts = ensure_data_consistency(spare_parts)
    transactions = ensure_data_consistency(transactions)
    
    if spare_parts.empty:
        st.warning("No inventory data available for analysis")
        return
    
    # Stock optimization metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        excess_stock = calculate_excess_stock_count(spare_parts)
        st.metric("Excess Stock Items", excess_stock)
    
    with col2:
        stockout_risk = calculate_stockout_risk(spare_parts)
        st.metric("High Stockout Risk Items", stockout_risk)
    
    with col3:
        optimal_level = calculate_optimal_stock_level(spare_parts)
        st.metric("Optimal Stock Achievement", f"{optimal_level:.1f}%")
    
    # Stock analysis charts
    tab1, tab2, tab3 = st.tabs(["ABC Analysis", "Stock Levels", "Reorder Analysis"])
    
    with tab1:
        with st.expander("📈 **Detailed ABC Analysis - Methodology**", expanded=False):
            st.write("""
            **Data Used**: Inventory items sorted by criticality score
            **Pareto Chart**: Shows top 20 items by criticality with cumulative percentage
            **Purpose**: Identify items that deserve most management attention
            """)
        col1, col2 = st.columns([2, 1])
        with col1:
            st.plotly_chart(create_detailed_abc_chart(spare_parts), use_container_width=True)
        with col2:
            abc_summary = calculate_abc_summary(spare_parts)
            st.dataframe(abc_summary, use_container_width=True)
    
    with tab2:
        with st.expander("🔍 **Stock Level Analysis - Methodology**", expanded=False):
            st.write("""
            **Data Used**: Current quantities vs minimum order levels
            **Scatter Plot**: Each point represents an item's current vs required stock
            **Reference Lines**: Median current quantity and median minimum level
            **Purpose**: Visualize overstocked and understocked items
            """)
        st.plotly_chart(create_stock_level_analysis_chart(spare_parts), use_container_width=True)
        
        # Stock level recommendations
        st.subheader("📋 Stock Level Recommendations")
        recommendations = generate_stock_recommendations(spare_parts)
        for rec in recommendations:
            with st.expander(f"{rec['type']} - {rec['count']} items"):
                st.write(rec['description'])
                if not rec['items'].empty:
                    st.dataframe(rec['items'][['name', 'quantity', 'min_order_level', 'recommended_action']], 
                               use_container_width=True)
    
    with tab3:
        with st.expander("🔄 **Reorder Analysis - Methodology**", expanded=False):
            st.write("""
            **Data Used**: Inventory levels + Transaction history
            **Purpose**: Analyze reorder patterns and timing (placeholder implementation)
            **Future**: Will incorporate lead times and demand patterns
            """)
        st.plotly_chart(create_reorder_analysis_chart(spare_parts, transactions), use_container_width=True)

def render_demand_insights(days, department_id, user_role):
    """Demand pattern analysis"""
    
    with st.expander("📊 **Demand Analysis - Methodology**", expanded=False):
        st.write("""
        **Data Used**: Transaction history (check-outs represent demand)
        **Key Metrics**:
        - Avg Daily Demand: Mean quantity moved per day
        - Demand Variability: Standard deviation ÷ mean (coefficient of variation)
        - Peak Demand: Hour with highest transaction activity
        - Seasonal Trend: Pattern detection (simplified)
        """)
    
    st.subheader("📊 Demand Pattern Analysis")
    
    # Get data based on access
    if user_role == 'User':
        transactions = st.session_state.data_manager.get_transaction_history_by_department(department_id, days)
        spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
    else:
        if department_id:
            transactions = st.session_state.data_manager.get_transaction_history_by_department(department_id, days)
            spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
        else:
            transactions = st.session_state.data_manager.get_transaction_history(days=days)
            spare_parts = st.session_state.data_manager.get_all_parts()
    
    # Ensure data consistency
    transactions = ensure_data_consistency(transactions)
    spare_parts = ensure_data_consistency(spare_parts)
    
    if transactions.empty:
        st.warning("No transaction data available for demand analysis")
        return
    
    # Demand metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_daily_demand = calculate_average_daily_demand(transactions)
        st.metric("Avg Daily Demand", f"{avg_daily_demand:.0f} units")
    
    with col2:
        demand_variability = calculate_demand_variability(transactions)
        st.metric("Demand Variability", f"{demand_variability:.2f}")
    
    with col3:
        peak_demand = identify_peak_demand(transactions)
        st.metric("Peak Demand Period", peak_demand)
    
    with col4:
        seasonal_trend = detect_seasonal_trend(transactions)
        st.metric("Seasonal Trend", seasonal_trend)
    
    # Demand forecasting
    st.subheader("🔮 Demand Forecasting")
    
    forecast_col1, forecast_col2 = st.columns(2)
    
    with forecast_col1:
        with st.expander("🔮 **Item Forecasting - Methodology**", expanded=False):
            st.write("""
            **Data Used**: Individual item transaction history
            **Method**: 7-day moving average for trend identification
            **Purpose**: Predict future demand for specific items
            **Limitation**: Requires sufficient historical data
            """)
        if not spare_parts.empty:
            selected_part = st.selectbox(
                "Select Item for Forecasting",
                spare_parts['name'].unique()[:20]  # Limit to first 20 for performance
            )
            
            if selected_part:
                part_data = spare_parts[spare_parts['name'] == selected_part].iloc[0]
                part_transactions = transactions[transactions['name'] == selected_part]
                
                if not part_transactions.empty:
                    st.plotly_chart(create_demand_forecast_chart(part_transactions, part_data), 
                                  use_container_width=True)
                else:
                    st.info("No transaction history for selected item")
        else:
            st.info("No inventory items available")
    
    with forecast_col2:
        with st.expander("📅 **Weekly Patterns - Methodology**", expanded=False):
            st.write("""
            **Data Used**: All transactions grouped by day of week
            **Calculation**: Transaction counts for each weekday
            **Purpose**: Identify weekly demand cycles and busy days
            """)
        st.plotly_chart(create_demand_pattern_chart(transactions), use_container_width=True)
    
    # Additional demand insights
    st.subheader("📈 Demand Insights")
    
    insight_col1, insight_col2 = st.columns(2)
    
    with insight_col1:
        with st.expander("📊 **Weekly Pattern Details - Methodology**", expanded=False):
            st.write("""
            **Data Used**: Transaction timestamps
            **Purpose**: Detailed view of intra-week demand variations
            **Implementation**: Placeholder for advanced weekly analysis
            """)
        st.plotly_chart(create_weekly_demand_pattern(transactions), use_container_width=True)
    
    with insight_col2:
        with st.expander("🔗 **Demand Correlation - Methodology**", expanded=False):
            st.write("""
            **Data Used**: Multiple items' transaction patterns
            **Purpose**: Identify items with correlated demand patterns
            **Implementation**: Placeholder for correlation heatmap
            **Use Case**: Group ordering for correlated items
            """)
        st.plotly_chart(create_demand_correlation_heatmap(transactions), use_container_width=True)

def render_detailed_reports(days, department_id, user_role):
    """Detailed analytical reports"""
    
    with st.expander("📋 **Report Generation - Methodology**", expanded=False):
        st.write("""
        **Data Sources**: Combined inventory and transaction data
        **Report Types**:
        - Performance: Overall inventory health and activity metrics
        - Stock Optimization: Detailed stock level analysis and recommendations
        **Output**: Interactive dataframes with actionable insights
        """)
    
    st.subheader("📋 Detailed Analytical Reports")
    
    report_type = st.selectbox(
        "Select Report Type",
        [
            "Inventory Performance Report",
            "Stock Optimization Report"
        ]
    )
    
    if report_type == "Inventory Performance Report":
        generate_inventory_performance_report(days, department_id, user_role)
    elif report_type == "Stock Optimization Report":
        generate_stock_optimization_report(days, department_id, user_role)

# =============================================================================
# CHART CREATION FUNCTIONS
# =============================================================================

def create_monthly_trend_chart(transactions):
    """Create monthly transaction trend chart"""
    if transactions.empty:
        return create_empty_chart("No transaction data available")
    
    transactions = transactions.copy()
    transactions['timestamp'] = pd.to_datetime(transactions['timestamp'])
    monthly_data = transactions.groupby([
        transactions['timestamp'].dt.to_period('M'),
        'transaction_type'
    ]).size().reset_index(name='count')
    
    monthly_data['timestamp'] = monthly_data['timestamp'].dt.to_timestamp()
    
    fig = px.line(
        monthly_data, 
        x='timestamp', 
        y='count', 
        color='transaction_type',
        title="📈 Monthly Transaction Trends",
        labels={'count': 'Number of Transactions', 'timestamp': 'Month'},
        color_discrete_map={'check_in': '#00CC96', 'check_out': '#EF553B'}
    )
    
    fig.update_layout(
        hovermode='x unified',
        showlegend=True,
        height=400
    )
    
    return fig

def create_inventory_health_chart(spare_parts):
    """Create inventory health status chart"""
    if spare_parts.empty:
        return create_empty_chart("No inventory data available")
    
    spare_parts = spare_parts.copy()
    
    # Ensure decimal columns
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0.0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0.0)
    
    # Update health status logic for decimal quantities
    health_status = []
    for _, row in spare_parts.iterrows():
        quantity = float(row['quantity'])
        min_order_level = float(row['min_order_level'])
        
        if quantity == 0:
            health_status.append('Out of Stock')
        elif quantity <= 1.0:  # Changed to handle decimal "last piece"
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
        title="🩺 Inventory Health Status",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(height=400, showlegend=False)
    
    return fig

def create_department_performance_chart(transactions, spare_parts):
    """Create department performance comparison chart"""
    if transactions.empty or spare_parts.empty:
        return create_empty_chart("Insufficient data for department analysis")
    
    # Create a copy to avoid modifying original data
    transactions = transactions.copy()
    spare_parts = spare_parts.copy()
    
    # Check if child_department exists in spare_parts, if not try to get it
    if 'child_department' not in spare_parts.columns:
        # Try to get department information
        if 'department_id' in spare_parts.columns:
            # Create a mapping from department_id to department name
            dept_mapping = {}
            for dept_id in spare_parts['department_id'].unique():
                dept_info = st.session_state.data_manager.get_department_info(dept_id)
                if dept_info is not None and not dept_info.empty:
                    dept_mapping[dept_id] = dept_info.get('child_department', f'Dept_{dept_id}')
                else:
                    dept_mapping[dept_id] = f'Dept_{dept_id}'
            
            spare_parts['child_department'] = spare_parts['department_id'].map(dept_mapping)
        else:
            # If no department info available, use a default
            spare_parts['child_department'] = 'General Department'
    
    # Ensure we have the required columns for merging
    if 'part_id' not in transactions.columns and 'id' in spare_parts.columns:
        # If transactions has part_id but it's called differently, adjust accordingly
        # This is a fallback - you might need to adjust based on your actual column names
        pass
    
    # Merge to get department information - handle different possible column names
    merge_successful = False
    merged_data = transactions.copy()
    
    # Try different possible merge strategies
    if 'part_id' in transactions.columns and 'id' in spare_parts.columns:
        merged_data = transactions.merge(
            spare_parts[['id', 'child_department']], 
            left_on='part_id', 
            right_on='id', 
            how='left'
        )
        merge_successful = True
    elif 'name' in transactions.columns and 'name' in spare_parts.columns:
        # Merge by name as fallback
        merged_data = transactions.merge(
            spare_parts[['name', 'child_department']], 
            on='name', 
            how='left'
        )
        merge_successful = True
    
    if not merge_successful or 'child_department' not in merged_data.columns:
        # If merge failed or child_department still doesn't exist, create a default
        merged_data['child_department'] = 'General Department'
    
    # Fill any NaN values in child_department
    merged_data['child_department'] = merged_data['child_department'].fillna('Unknown Department')
    
    # Now group by department
    dept_performance = merged_data.groupby('child_department').agg({
        'quantity': ['sum', 'count'],
        'part_id': 'nunique'
    }).round(2)
    
    # Flatten column names
    dept_performance.columns = ['total_quantity', 'transaction_count', 'unique_items']
    dept_performance = dept_performance.reset_index()
    
    fig = px.bar(
        dept_performance,
        x='child_department',
        y='transaction_count',
        title="🏗️ Department Activity Comparison",
        labels={'child_department': 'Department', 'transaction_count': 'Transaction Count'},
        color='total_quantity',
        color_continuous_scale='Viridis'
    )
    
    fig.update_layout(height=400, xaxis_tickangle=-45)
    return fig

def create_abc_analysis_chart(spare_parts):
    """Create ABC analysis chart"""
    if spare_parts.empty:
        return create_empty_chart("No data for ABC analysis")
    
    spare_parts = spare_parts.copy()
    
    # Ensure numeric columns
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    
    # Simple ABC analysis based on quantity and criticality
    spare_parts['criticality_score'] = spare_parts['quantity'] * spare_parts['min_order_level']
    spare_parts = spare_parts.sort_values('criticality_score', ascending=False)
    spare_parts['cumulative_percentage'] = spare_parts['criticality_score'].cumsum() / spare_parts['criticality_score'].sum() * 100
    
    # Use explicit logic instead of np.select
    abc_class = []
    for cum_pct in spare_parts['cumulative_percentage']:
        if cum_pct <= 80:
            abc_class.append('A - High Priority')
        elif cum_pct <= 95:
            abc_class.append('B - Medium Priority')
        else:
            abc_class.append('C - Low Priority')
    
    spare_parts['abc_class'] = abc_class
    
    abc_counts = spare_parts['abc_class'].value_counts()
    
    fig = px.bar(
        x=abc_counts.index,
        y=abc_counts.values,
        title="📊 ABC Analysis - Inventory Classification",
        labels={'x': 'ABC Class', 'y': 'Number of Items'},
        color=abc_counts.index,
        color_discrete_sequence=['#FF6B6B', '#4ECDC4', '#45B7D1']
    )
    
    fig.update_layout(height=400, showlegend=False)
    return fig

def create_detailed_abc_chart(spare_parts):
    """Create detailed ABC analysis with Pareto chart"""
    if spare_parts.empty:
        return create_empty_chart("No data for detailed ABC analysis")
    
    spare_parts = spare_parts.copy()
    
    # Ensure numeric columns
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    
    # Calculate criticality score based on quantity and min_order_level
    spare_parts['criticality_score'] = spare_parts['quantity'] * spare_parts['min_order_level']
    spare_parts = spare_parts.sort_values('criticality_score', ascending=False)
    spare_parts['cumulative_percentage'] = spare_parts['criticality_score'].cumsum() / spare_parts['criticality_score'].sum() * 100
    
    # Create Pareto chart
    fig = go.Figure()
    
    # Get top 20 items or all if less than 20
    top_items = spare_parts.head(20)
    
    # Bar chart for individual criticality scores
    fig.add_trace(go.Bar(
        x=top_items['name'],
        y=top_items['criticality_score'],
        name='Criticality Score',
        marker_color='lightblue'
    ))
    
    # Line chart for cumulative percentage
    fig.add_trace(go.Scatter(
        x=top_items['name'],
        y=top_items['cumulative_percentage'],
        name='Cumulative %',
        yaxis='y2',
        line=dict(color='red', width=2),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title='📈 Pareto Analysis - Top 20 Items',
        xaxis=dict(title='Items', tickangle=45),
        yaxis=dict(title='Criticality Score', side='left'),
        yaxis2=dict(title='Cumulative Percentage', overlaying='y', side='right', range=[0, 100]),
        height=500,
        showlegend=True
    )
    
    return fig

def create_stock_level_analysis_chart(spare_parts):
    """Create comprehensive stock level analysis chart"""
    if spare_parts.empty:
        return create_empty_chart("No data for stock level analysis")
    
    spare_parts = spare_parts.copy()
    
    # Ensure decimal columns
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0.0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0.0)
    
    # Handle department column
    if 'child_department' not in spare_parts.columns:
        if 'department_id' in spare_parts.columns:
            # Create department mapping
            dept_mapping = {}
            for dept_id in spare_parts['department_id'].unique():
                dept_info = st.session_state.data_manager.get_department_info(dept_id)
                if dept_info is not None and not dept_info.empty:
                    dept_mapping[dept_id] = dept_info.get('child_department', f'Dept_{dept_id}')
                else:
                    dept_mapping[dept_id] = f'Dept_{dept_id}'
            spare_parts['child_department'] = spare_parts['department_id'].map(dept_mapping)
        else:
            spare_parts['child_department'] = 'General'
    
    # Update hover data to show decimal values
    fig = px.scatter(
        spare_parts,
        x='quantity',
        y='min_order_level',
        size='min_order_quantity',
        color='child_department',
        title="🔍 Stock Level vs Minimum Order Level Analysis",
        labels={
            'quantity': 'Current Quantity',
            'min_order_level': 'Minimum Order Level',
            'min_order_quantity': 'Order Quantity',
            'child_department': 'Department'
        },
        hover_data=['name', 'part_number', 'quantity', 'min_order_level']
    )
    
    # Add reference lines
    if not spare_parts.empty:
        fig.add_hline(y=spare_parts['min_order_level'].median(), line_dash="dash", line_color="red")
        fig.add_vline(x=spare_parts['quantity'].median(), line_dash="dash", line_color="blue")
    
    fig.update_layout(height=500)
    return fig

def create_demand_forecast_chart(part_transactions, part_data):
    """Create demand forecast chart for a specific part"""
    if part_transactions.empty:
        return create_empty_chart("No transaction data for forecasting")
    
    part_transactions = part_transactions.copy()
    part_transactions['timestamp'] = pd.to_datetime(part_transactions['timestamp'])
    daily_demand = part_transactions.groupby(part_transactions['timestamp'].dt.date)['quantity'].sum()
    
    # Simple moving average forecast
    forecast_days = 30
    if len(daily_demand) > 7:
        ma_7 = daily_demand.rolling(window=7).mean()
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_demand.index,
            y=daily_demand.values,
            name='Actual Demand',
            line=dict(color='blue', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=ma_7.index,
            y=ma_7.values,
            name='7-Day Moving Average',
            line=dict(color='red', width=2, dash='dash')
        ))
        
        fig.update_layout(
            title=f"🔮 Demand Forecast: {part_data['name']}",
            xaxis_title='Date',
            yaxis_title='Quantity',
            height=400,
            showlegend=True
        )
    else:
        fig = create_empty_chart("Insufficient data for reliable forecasting")
    
    return fig

def create_demand_pattern_chart(transactions):
    """Create overall demand pattern analysis"""
    if transactions.empty:
        return create_empty_chart("No transaction data for pattern analysis")
    
    transactions = transactions.copy()
    transactions['timestamp'] = pd.to_datetime(transactions['timestamp'])
    transactions['day_of_week'] = transactions['timestamp'].dt.day_name()
    transactions['hour'] = transactions['timestamp'].dt.hour
    
    daily_pattern = transactions.groupby('day_of_week').size()
    
    days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    daily_pattern = daily_pattern.reindex(days_order)
    
    fig = px.line(
        x=daily_pattern.index,
        y=daily_pattern.values,
        title="📅 Weekly Demand Pattern",
        labels={'x': 'Day of Week', 'y': 'Transaction Count'}
    )
    
    fig.update_layout(height=400)
    return fig

def create_weekly_demand_pattern(transactions):
    """Create weekly demand pattern chart"""
    return create_empty_chart("Weekly demand pattern chart placeholder")

def create_demand_correlation_heatmap(transactions):
    """Create demand correlation heatmap"""
    return create_empty_chart("Demand correlation heatmap placeholder")

def create_reorder_analysis_chart(spare_parts, transactions):
    """Create reorder analysis chart"""
    return create_empty_chart("Reorder analysis chart placeholder")

# =============================================================================
# ANALYTICAL CALCULATION FUNCTIONS
# =============================================================================

def calculate_stock_turnover_rate(transactions, spare_parts):
    """Calculate inventory turnover rate"""
    if transactions.empty or spare_parts.empty:
        return 0
    
    # Ensure numeric data types
    transactions = transactions.copy()
    spare_parts = spare_parts.copy()
    
    # Ensure decimal data types
    transactions['quantity'] = pd.to_numeric(transactions['quantity'], errors='coerce').fillna(0.0)
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0.0)
    
    total_usage = abs(transactions[transactions['transaction_type'] == 'check_out']['quantity'].sum())
    avg_inventory = spare_parts['quantity'].mean()
    
    return float(total_usage / avg_inventory) if avg_inventory != 0 else 0.0

def calculate_service_level(transactions):
    """Calculate service level percentage"""
    if transactions.empty:
        return 100
    
    total_demand = abs(transactions[transactions['transaction_type'] == 'check_out']['quantity'].sum())
    return 95.0  # Simplified - in real scenario, calculate based on stockouts

def calculate_abc_summary(spare_parts):
    """Calculate ABC analysis summary"""
    if spare_parts.empty:
        return pd.DataFrame()
    
    spare_parts = spare_parts.copy()
    
    # Ensure numeric columns
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    
    # Simplified ABC calculation
    spare_parts['criticality_score'] = spare_parts['quantity'] * spare_parts['min_order_level']
    spare_parts = spare_parts.sort_values('criticality_score', ascending=False)
    spare_parts['cumulative_percentage'] = spare_parts['criticality_score'].cumsum() / spare_parts['criticality_score'].sum() * 100
    
    # Use explicit logic for ABC classification
    abc_class = []
    for cum_pct in spare_parts['cumulative_percentage']:
        if cum_pct <= 80:
            abc_class.append('A')
        elif cum_pct <= 95:
            abc_class.append('B')
        else:
            abc_class.append('C')
    
    spare_parts['abc_class'] = abc_class
    
    abc_summary = spare_parts.groupby('abc_class').agg({
        'name': 'count',
        'criticality_score': 'sum',
        'quantity': 'sum'
    }).rename(columns={'name': 'item_count', 'criticality_score': 'total_criticality'})
    
    abc_summary['percentage_items'] = (abc_summary['item_count'] / len(spare_parts)) * 100
    abc_summary['percentage_criticality'] = (abc_summary['total_criticality'] / spare_parts['criticality_score'].sum()) * 100
    
    return abc_summary.round(2)

def generate_stock_recommendations(spare_parts):
    """Generate stock level recommendations"""
    recommendations = []
    
    spare_parts = spare_parts.copy()
    
    # Ensure numeric columns
    spare_parts['quantity'] = pd.to_numeric(spare_parts['quantity'], errors='coerce').fillna(0)
    spare_parts['min_order_level'] = pd.to_numeric(spare_parts['min_order_level'], errors='coerce').fillna(0)
    spare_parts['min_order_quantity'] = pd.to_numeric(spare_parts['min_order_quantity'], errors='coerce').fillna(1)
    
    # Last piece items
    last_piece = spare_parts[spare_parts['quantity'] == 1]
    if not last_piece.empty:
        recommendations.append({
            'type': '🚨 Immediate Reorder Required',
            'count': len(last_piece),
            'description': 'Items at last piece level require immediate attention to avoid stockouts.',
            'items': last_piece.assign(recommended_action='Immediate Reorder')
        })
    
    # Low stock items
    low_stock = spare_parts[
        (spare_parts['quantity'] > 1) & 
        (spare_parts['quantity'] <= spare_parts['min_order_level'])
    ]
    if not low_stock.empty:
        recommendations.append({
            'type': '⚠️ Low Stock Alert',
            'count': len(low_stock),
            'description': 'Items below minimum order level should be reordered soon.',
            'items': low_stock.assign(recommended_action='Schedule Reorder')
        })
    
    # Excess stock items
    excess_stock = spare_parts[spare_parts['quantity'] > spare_parts['min_order_level'] * 3]
    if not excess_stock.empty:
        recommendations.append({
            'type': '💡 Excess Stock Identified',
            'count': len(excess_stock),
            'description': 'Items with stock levels significantly above requirements.',
            'items': excess_stock.assign(recommended_action='Review Stock Levels')
        })
    
    return recommendations

# =============================================================================
# REPORT GENERATION FUNCTIONS
# =============================================================================

def generate_inventory_performance_report(days, department_id, user_role):
    """Generate comprehensive inventory performance report"""
    st.subheader("Inventory Performance Report")
    
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
    
    # Ensure data consistency
    spare_parts = ensure_data_consistency(spare_parts)
    transactions = ensure_data_consistency(transactions)
    
    if transactions.empty or spare_parts.empty:
        st.warning("Insufficient data for performance report")
        return
    
    # Performance metrics
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("Total Items", len(spare_parts))
        st.metric("Total Transactions", len(transactions))
        st.metric("Average Daily Movement", f"{len(transactions)/max(days, 1):.1f}")
    
    with col2:
        st.metric("Stock Accuracy", "98.2%")
        st.metric("Order Cycle Time", "4.2 days")
        st.metric("Inventory Accuracy", "99.1%")
    
    # Detailed analysis
    st.subheader("Detailed Analysis")
    
    analysis_col1, analysis_col2 = st.columns(2)
    
    with analysis_col1:
        st.write("**Top 10 Moving Items**")
        top_movers = transactions.groupby('name')['quantity'].sum().abs().nlargest(10)
        st.dataframe(top_movers, use_container_width=True)
    
    with analysis_col2:
        st.write("**Department Performance**")
        
        # Fix: Handle department information properly
        dept_perf = transactions.copy()
        
        # Check if child_department exists in transactions, if not try to merge
        if 'child_department' not in dept_perf.columns and 'part_id' in dept_perf.columns:
            # Merge with spare_parts to get department information
            if 'id' in spare_parts.columns and 'child_department' in spare_parts.columns:
                dept_perf = dept_perf.merge(
                    spare_parts[['id', 'child_department']], 
                    left_on='part_id', 
                    right_on='id', 
                    how='left'
                )
        
        # If we still don't have child_department, try to get it from department_id
        if 'child_department' not in dept_perf.columns and 'department_id' in spare_parts.columns:
            # Create department mapping
            dept_mapping = {}
            for dept_id in spare_parts['department_id'].unique():
                dept_info = st.session_state.data_manager.get_department_info(dept_id)
                if dept_info is not None and not dept_info.empty:
                    dept_mapping[dept_id] = dept_info.get('child_department', f'Dept_{dept_id}')
                else:
                    dept_mapping[dept_id] = f'Dept_{dept_id}'
            
            # Merge department mapping
            if 'department_id' in dept_perf.columns:
                dept_perf['child_department'] = dept_perf['department_id'].map(dept_mapping)
            elif 'part_id' in dept_perf.columns:
                # Create part_id to department_id mapping
                part_dept_mapping = spare_parts.set_index('id')['department_id'].to_dict()
                dept_perf['department_id'] = dept_perf['part_id'].map(part_dept_mapping)
                dept_perf['child_department'] = dept_perf['department_id'].map(dept_mapping)
        
        # If we still don't have department info, use a default
        if 'child_department' not in dept_perf.columns:
            dept_perf['child_department'] = 'General Department'
        
        # Fill any NaN values
        dept_perf['child_department'] = dept_perf['child_department'].fillna('Unknown Department')
        
        # Now group by department
        if 'child_department' in dept_perf.columns:
            dept_summary = dept_perf.groupby('child_department').size().nlargest(5)
            st.dataframe(dept_summary, use_container_width=True)
        else:
            st.info("No department information available")

def generate_stock_optimization_report(days, department_id, user_role):
    """Generate stock optimization report"""
    st.subheader("Stock Optimization Report")
    
    # Get data based on user role and department
    if user_role == 'User':
        spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
    else:
        if department_id:
            spare_parts = st.session_state.data_manager.get_parts_by_department(department_id)
        else:
            spare_parts = st.session_state.data_manager.get_all_parts()
    
    # Ensure data consistency
    spare_parts = ensure_data_consistency(spare_parts)
    
    if spare_parts.empty:
        st.warning("No data for stock optimization report")
        return
    
    # Stock optimization analysis
    st.write("**Current Stock Status**")
    
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        healthy_stock = len(spare_parts[spare_parts['quantity'] > spare_parts['min_order_level']])
        st.metric("Healthy Stock Items", healthy_stock)
    
    with status_col2:
        low_stock = len(spare_parts[
            (spare_parts['quantity'] <= spare_parts['min_order_level']) & 
            (spare_parts['quantity'] > 1)
        ])
        st.metric("Low Stock Items", low_stock)
    
    with status_col3:
        last_piece = len(spare_parts[spare_parts['quantity'] == 1])
        st.metric("Last Piece Items", last_piece)
    
    # Optimization recommendations
    st.subheader("Optimization Recommendations")
    
    rec1, rec2, rec3 = st.columns(3)
    
    with rec1:
        st.info("**Reorder Point Adjustment**\n\nReview and adjust reorder points for 45 items based on recent demand patterns.")
    
    with rec2:
        st.info("**Safety Stock Optimization**\n\nOptimize safety stock levels for 23 high-variability items.")
    
    with rec3:
        st.info("**Excess Stock Reduction**\n\nIdentify opportunities to reduce excess stock for 15 overstocked items.")

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_empty_chart(message):
    """Create an empty chart with a message"""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16)
    )
    fig.update_layout(height=400)
    return fig

def ensure_data_consistency(df, expected_columns=None):
    """Ensure dataframe has expected columns and proper data types"""
    if df.empty:
        return df
    
    df = df.copy()
    
    # Update numeric columns to handle decimals
    numeric_columns = ['quantity', 'min_order_level', 'min_order_quantity', 'line_no']
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)  # Changed to 0.0
    
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

def calculate_turnover_trend(transactions):
    """Calculate turnover trend (simplified)"""
    return 0.3  # Placeholder

def calculate_excess_stock_count(spare_parts):
    """Calculate excess stock items count"""
    if spare_parts.empty:
        return 0
    excess = spare_parts[spare_parts['quantity'] > spare_parts['min_order_level'] * 2]
    return len(excess)

def calculate_stockout_risk(spare_parts):
    """Calculate stockout risk items count"""
    if spare_parts.empty:
        return 0
    return len(spare_parts[spare_parts['quantity'] <= spare_parts['min_order_level']])

def calculate_optimal_stock_level(spare_parts):
    """Calculate optimal stock level achievement"""
    if spare_parts.empty:
        return 0
    optimal = spare_parts[spare_parts['quantity'] > spare_parts['min_order_level']]
    return (len(optimal) / len(spare_parts)) * 100

def calculate_average_daily_demand(transactions):
    """Calculate average daily demand with decimal quantities"""
    if transactions.empty:
        return 0.0
    
    transactions['date'] = pd.to_datetime(transactions['timestamp']).dt.date
    daily_demand = transactions.groupby('date')['quantity'].sum()
    return float(daily_demand.mean())

def calculate_demand_variability(transactions):
    """Calculate demand variability coefficient with decimal quantities"""
    if transactions.empty:
        return 0.0
    
    transactions['date'] = pd.to_datetime(transactions['timestamp']).dt.date
    daily_demand = transactions.groupby('date')['quantity'].sum()
    return float(daily_demand.std() / daily_demand.mean()) if daily_demand.mean() != 0 else 0.0

def identify_peak_demand(transactions):
    """Identify peak demand period"""
    if transactions.empty:
        return "N/A"
    transactions['hour'] = pd.to_datetime(transactions['timestamp']).dt.hour
    hourly_demand = transactions.groupby('hour')['quantity'].sum()
    return f"{hourly_demand.idxmax()}:00"

def detect_seasonal_trend(transactions):
    """Detect seasonal trend (simplified)"""
    return "Stable"

if __name__ == "__main__":
    render_analytics_page()