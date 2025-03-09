import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta

def create_stock_level_chart(df):
    fig = px.bar(
        df,
        x='name',
        y=['quantity', 'min_order_level'],
        title='Stock Levels vs Minimum Order Levels',
        barmode='group'
    )
    return fig

def create_transaction_trend(df):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    daily_transactions = df.groupby(['timestamp', 'transaction_type']).size().reset_index(name='count')

    fig = px.line(
        daily_transactions,
        x='timestamp',
        y='count',
        color='transaction_type',
        title='Transaction Trends'
    )
    return fig

def format_transaction_table(df):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp', ascending=False)
    return df[['timestamp', 'name', 'part_number', 'transaction_type', 'quantity']]

def calculate_moving_average(data, window=7):
    """Calculate moving average for demand forecasting"""
    return data.rolling(window=window).mean()

def calculate_exponential_smoothing(data, alpha=0.3):
    """Calculate exponential smoothing for trend analysis"""
    return data.ewm(alpha=alpha, adjust=False).mean()

def calculate_reorder_point(df, part_id, lead_time_days=7):
    """Calculate reorder point based on average daily demand and lead time"""
    part_transactions = df[df['part_id'] == part_id]
    if part_transactions.empty:
        return 0

    # Calculate daily demand
    daily_demand = part_transactions.groupby('timestamp')['quantity'].sum()
    avg_daily_demand = abs(daily_demand.mean())

    # Add safety stock (20% of lead time demand)
    safety_stock = avg_daily_demand * lead_time_days * 0.2
    reorder_point = (avg_daily_demand * lead_time_days) + safety_stock

    return round(reorder_point)

def calculate_stock_turnover(df, current_stock):
    """Calculate stock turnover rate"""
    if df.empty or current_stock == 0:
        return 0

    total_usage = abs(df[df['transaction_type'] == 'check_out']['quantity'].sum())
    avg_inventory = current_stock / 2  # Simple average inventory calculation

    if avg_inventory == 0:
        return 0

    turnover_rate = total_usage / avg_inventory
    return round(turnover_rate, 2)

def create_demand_forecast_chart(df, part_id, days_to_forecast=30):
    """Create demand forecast visualization"""
    part_transactions = df[df['part_id'] == part_id]
    if part_transactions.empty:
        return None

    # Prepare daily demand data
    daily_demand = part_transactions.groupby('timestamp')['quantity'].sum()

    # Calculate moving average and exponential smoothing
    ma = calculate_moving_average(daily_demand)
    ema = calculate_exponential_smoothing(daily_demand)

    # Create forecast dates
    last_date = daily_demand.index.max()
    forecast_dates = pd.date_range(
        start=last_date, 
        periods=days_to_forecast + 1, 
        freq='D'
    )[1:]

    # Create forecast values using the last 7 days trend
    last_week_trend = ema[-7:].mean()
    forecast_values = [last_week_trend] * days_to_forecast

    # Create visualization
    fig = go.Figure()

    # Historical data
    fig.add_trace(go.Scatter(
        x=daily_demand.index,
        y=daily_demand.values,
        name='Actual Demand',
        mode='lines+markers'
    ))

    # Moving average
    fig.add_trace(go.Scatter(
        x=ma.index,
        y=ma.values,
        name='7-Day Moving Average',
        line=dict(dash='dash')
    ))

    # Exponential moving average
    fig.add_trace(go.Scatter(
        x=ema.index,
        y=ema.values,
        name='Exponential Moving Average',
        line=dict(dash='dot')
    ))

    # Forecast
    fig.add_trace(go.Scatter(
        x=forecast_dates,
        y=forecast_values,
        name='Forecast',
        line=dict(dash='dashdot')
    ))

    fig.update_layout(
        title='Demand Forecast Analysis',
        xaxis_title='Date',
        yaxis_title='Quantity',
        showlegend=True
    )

    return fig