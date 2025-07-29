import streamlit as st
import pandas as pd
from utils import (create_demand_forecast_chart, calculate_reorder_point,
                   calculate_stock_turnover)
from user_management import login_required, init_session_state, render_login_page
import navbar
from app_settings import set_page_configuration
from data_manager import DataManager

set_page_configuration()

current_page = "Analytics"
st.header(current_page)

navbar.nav(current_page)


@login_required
def render_analytics_page():
    #st.title("Advanced Analytics and Forecasting")
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

    if selected_child is not None:

        # Get data
        df = st.session_state.data_manager.get_parts_by_department(selected_child)
        transactions = st.session_state.data_manager.get_transaction_history_by_department(selected_parent, days=90)

        if df.empty:
            st.warning("No inventory data available for analysis")
            return

        # Part selection
        selected_part = st.selectbox("Select Part for Analysis",
                                    df['description'].tolist())

        if selected_part:
            part_data = df[df['description'] == selected_part].iloc[0]
            part_id = part_data['id']

            # Display current metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Current Stock",
                    int(part_data['quantity'])  # Convert to Python int
                )

            with col2:
                reorder_point = calculate_reorder_point(transactions, part_id)
                st.metric(
                    "Suggested Reorder Point",
                    reorder_point,
                    delta=int(part_data['quantity']) -
                    reorder_point  # Convert to Python int
                )

            with col3:
                turnover = calculate_stock_turnover(
                    transactions[transactions['part_id'] == part_id],
                    int(part_data['quantity'])  # Convert to Python int
                )
                st.metric("Stock Turnover Rate", f"{turnover}/year")

            # Demand Forecast Chart
            st.subheader("Demand Forecast Analysis")
            forecast_days = st.slider("Forecast Period (Days)",
                                    min_value=7,
                                    max_value=90,
                                    value=30)

            forecast_chart = create_demand_forecast_chart(
                transactions, part_id, days_to_forecast=forecast_days)

            if forecast_chart:
                st.plotly_chart(forecast_chart, use_container_width=True)

                # Analysis insights
                st.subheader("Inventory Insights")

                # Stock status
                if part_data['quantity'] <= reorder_point:
                    st.warning(f"""
                        🚨 Stock Alert: Current stock ({int(part_data['quantity'])}) is at or below
                        the recommended reorder point ({reorder_point}).
                        Consider restocking soon.
                    """)

                # Turnover analysis
                if turnover < 1:
                    st.info("💡 Low turnover rate indicates slow-moving inventory.")
                elif turnover > 12:
                    st.info(
                        "💡 High turnover rate indicates fast-moving inventory.")

                # Forecast interpretation
                st.info("""
                    📊 The forecast shown above uses:
                    - 7-day moving average (dashed line)
                    - Exponential smoothing (dotted line)
                    - Trend-based projection (dash-dot line)

                    The forecast considers historical demand patterns and recent trends.
                """)
            else:
                st.info("Insufficient transaction history for forecasting")


if __name__ == "__main__":
    if not st.session_state.authenticated:
        render_login_page()
    else:
        render_analytics_page()
