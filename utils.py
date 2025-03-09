import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
