import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from datetime import datetime, timedelta
import plotly.graph_objects as go

def create_features(df, date_column='flight_date'):
    """
    Create time-based features for forecasting
    """
    df = df.copy()
    df['dayofweek'] = df[date_column].dt.dayofweek
    df['month'] = df[date_column].dt.month
    df['year'] = df[date_column].dt.year
    df['dayofyear'] = df[date_column].dt.dayofyear
    df['dayofmonth'] = df[date_column].dt.day
    df['weekofyear'] = df[date_column].dt.isocalendar().week
    
    # Add lag features if enough data is available
    if len(df) > 7:
        df['lag_1'] = df['count'].shift(1)
        df['lag_7'] = df['count'].shift(7)
    
    return df

def train_test_split_time(df, test_size=0.2, date_column='flight_date'):
    """
    Split data into training and testing sets based on time
    """
    df = df.sort_values(by=date_column)
    n = len(df)
    test_indices = int(n * (1 - test_size))
    
    train = df.iloc[:test_indices].copy()
    test = df.iloc[test_indices:].copy()
    
    return train, test

def advanced_flight_forecast(df, days_to_forecast=30, date_column='flight_date', model_type='ensemble'):
    """
    Create an advanced forecast for flight volumes
    
    Args:
        df: DataFrame with daily flight counts
        days_to_forecast: Number of days to forecast into the future
        date_column: Name of the date column
        model_type: Type of model to use ('linear', 'rf', 'ensemble')
        
    Returns:
        DataFrame with historical and forecasted values, and model performance metrics
    """
    # Make sure data is sorted by date
    df = df.sort_values(by=date_column)
    df = df[[date_column, 'count']].copy()  # Keep only necessary columns
    
    # Create features
    df_features = create_features(df, date_column)
    
    # Handle missing values from lag features
    df_features = df_features.dropna()
    
    if len(df_features) < 10:
        raise ValueError("Not enough data for forecasting. Need at least 10 data points.")
    
    # Split data
    train_df, test_df = train_test_split_time(df_features, test_size=0.2)
    
    # Feature columns
    feature_cols = ['dayofweek', 'month', 'year', 'dayofyear', 'dayofmonth', 'weekofyear']
    
    # Add lag features if available
    if 'lag_1' in df_features.columns and 'lag_7' in df_features.columns:
        feature_cols.extend(['lag_1', 'lag_7'])
    
    # Prepare training data
    X_train = train_df[feature_cols]
    y_train = train_df['count']
    
    # Initialize models
    linear_model = LinearRegression()
    rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
    
    # Train models
    linear_model.fit(X_train, y_train)
    rf_model.fit(X_train, y_train)
    
    # Model evaluation
    metrics = {}
    
    # Test data
    X_test = test_df[feature_cols]
    y_test = test_df['count']
    
    # Linear regression evaluation
    y_pred_linear = linear_model.predict(X_test)
    metrics['linear'] = {
        'mae': mean_absolute_error(y_test, y_pred_linear),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred_linear)),
        'r2': r2_score(y_test, y_pred_linear)
    }
    
    # Random forest evaluation
    y_pred_rf = rf_model.predict(X_test)
    metrics['rf'] = {
        'mae': mean_absolute_error(y_test, y_pred_rf),
        'rmse': np.sqrt(mean_squared_error(y_test, y_pred_rf)),
        'r2': r2_score(y_test, y_pred_rf)
    }
    
    # Generate future dates for forecasting
    last_date = df[date_column].max()
    future_dates = [last_date + timedelta(days=i+1) for i in range(days_to_forecast)]
    
    # Create future dataframe
    future_df = pd.DataFrame({date_column: future_dates})
    
    # Create features for future data
    future_df = create_features(future_df, date_column)
    
    # Handle lag features for future prediction
    if 'lag_1' in future_df.columns and 'lag_7' in future_df.columns:
        # Initialize with last known values
        last_count = df['count'].iloc[-1]
        lag7_seed = None
        if len(df) >= 7:
            lag7_seed = df['count'].iloc[-7]
        
        # Fill initial lags
        future_df.loc[0, 'lag_1'] = last_count
        if lag7_seed is not None:
            future_df.loc[0, 'lag_7'] = lag7_seed
        
        # Iteratively predict and update lags
        for i in range(1, len(future_df)):
            if i < 7:
                if lag7_seed is not None:
                    # Still using historical data for lag_7
                    future_idx = -7 + i
                    if future_idx < 0:
                        future_df.loc[i, 'lag_7'] = df['count'].iloc[future_idx]
                    else:
                        future_df.loc[i, 'lag_7'] = future_df.loc[future_idx, 'prediction']
                else:
                    # No historical data, use the prediction
                    future_df.loc[i, 'lag_7'] = future_df.loc[i-1, 'prediction'] if i > 0 else last_count
            else:
                # Use the prediction from 7 days ago
                future_df.loc[i, 'lag_7'] = future_df.loc[i-7, 'prediction']
            
            # Always use yesterday's prediction for lag_1
            future_df.loc[i, 'lag_1'] = future_df.loc[i-1, 'prediction'] if i > 0 else last_count
            
    # Prepare features for prediction
    X_future = future_df[feature_cols]
    
    # Make predictions with both models
    future_df['linear_prediction'] = linear_model.predict(X_future)
    future_df['rf_prediction'] = rf_model.predict(X_future)
    
    # Choose or ensemble the predictions based on model_type
    if model_type == 'linear':
        future_df['prediction'] = future_df['linear_prediction']
    elif model_type == 'rf':
        future_df['prediction'] = future_df['rf_prediction']
    else:  # ensemble
        # Simple average ensemble
        future_df['prediction'] = (future_df['linear_prediction'] + future_df['rf_prediction']) / 2
    
    # Round predictions to integers and ensure non-negative
    future_df['prediction'] = future_df['prediction'].apply(lambda x: max(0, round(x)))
    
    # Combine with historical data
    df['forecast'] = False
    future_df['forecast'] = True
    future_df['count'] = future_df['prediction']
    
    result = pd.concat([df, future_df[[date_column, 'count', 'forecast']]], ignore_index=True)
    
    return result, metrics