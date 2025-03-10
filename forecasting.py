import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

def prepare_time_series_data(df, date_column='flight_date', group_by_cols=None):
    """
    Prepare time series data for forecasting
    
    Args:
        df: DataFrame with flight data
        date_column: Name of the date column
        group_by_cols: List of columns to group by (e.g., ['origin_code', 'destination_code'])
        
    Returns:
        DataFrame with daily counts
    """
    # Convert date column to datetime if not already
    df[date_column] = pd.to_datetime(df[date_column])
    
    # Group by date and specified columns
    if group_by_cols:
        # Include the date column in the grouping
        group_cols = [date_column] + group_by_cols
        daily_counts = df.groupby(group_cols).size().reset_index(name='count')
    else:
        # Just group by date
        daily_counts = df.groupby(date_column).size().reset_index(name='count')
    
    return daily_counts

def simple_flight_forecast(df, days_to_forecast=30, date_column='flight_date'):
    """
    Create a simple linear regression forecast for flight volumes
    
    Args:
        df: DataFrame with daily flight counts
        days_to_forecast: Number of days to forecast into the future
        date_column: Name of the date column
        
    Returns:
        DataFrame with historical and forecasted values
    """
    # Make sure data is sorted by date
    df = df.sort_values(by=date_column)
    
    # Convert dates to numeric format (days since first date)
    first_date = df[date_column].min()
    df['day_number'] = (df[date_column] - first_date).dt.days
    
    # Prepare features and target
    X = df[['day_number']]
    y = df['count']
    
    # Train a linear regression model
    model = LinearRegression()
    model.fit(X, y)
    
    # Prepare forecast dates
    last_date = df[date_column].max()
    future_dates = [last_date + timedelta(days=i+1) for i in range(days_to_forecast)]
    future_day_numbers = [(last_date + timedelta(days=i+1) - first_date).days 
                           for i in range(days_to_forecast)]
    
    # Create future dataframe
    future_df = pd.DataFrame({
        date_column: future_dates,
        'day_number': future_day_numbers
    })
    
    # Make predictions
    future_df['count'] = model.predict(future_df[['day_number']])
    future_df['count'] = future_df['count'].apply(lambda x: max(0, round(x)))  # Ensure non-negative integers
    future_df['forecast'] = True
    
    # Add forecast flag to historical data
    df['forecast'] = False
    
    # Combine historical and forecasted data
    result = pd.concat([df, future_df], ignore_index=True)
    
    return result