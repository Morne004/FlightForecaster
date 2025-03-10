import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from database import get_flight_data

# Set page configuration
st.set_page_config(
    page_title="Advanced Forecasting - Flight Forecaster",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Advanced Flight Forecasting")
st.markdown("Generate and compare sophisticated forecasting models")

# Sidebar filters
st.sidebar.header("Forecast Settings")

# Date range picker
default_start_date = datetime.now() - timedelta(days=90)  # Need more data for advanced forecasting
default_end_date = datetime.now()
start_date = st.sidebar.date_input("Historical Data Start Date", default_start_date)
end_date = st.sidebar.date_input("Historical Data End Date", default_end_date)

# Get unique airports (placeholder for now)
airports = ["LAX", "JFK", "SFO", "LHR", "CDG"]  # Example airports

# Airport selection
tab1, tab2 = st.sidebar.tabs(["Route Forecast", "Airport Forecast"])

with tab1:
    origin = st.selectbox("Origin Airport", options=airports, key="origin")
    destination = st.selectbox("Destination Airport", options=airports, key="destination")
    forecast_type = "route"

with tab2:
    airport = st.selectbox("Select Airport", options=airports, key="airport")
    direction = st.radio("Direction", options=["Departures", "Arrivals", "Both"])
    forecast_type = "airport"

# Forecast horizon
forecast_days = st.sidebar.slider(
    "Forecast Horizon (Days)", 
    min_value=7, 
    max_value=180, 
    value=30, 
    step=7
)

# Model selection
model_type = st.sidebar.selectbox(
    "Forecasting Model",
    options=["Linear Regression", "Random Forest", "Ensemble (Average)"],
    index=2
)

# Map model selection to model type parameter
model_param = {
    "Linear Regression": "linear",
    "Random Forest": "rf",
    "Ensemble (Average)": "ensemble"
}

# Generate forecast button
if st.sidebar.button("Generate Forecast"):
    # Import advanced forecasting module
    from advanced_forecasting import advanced_flight_forecast, create_features
    
    with st.spinner("Gathering data and generating forecast..."):
        try:
            if forecast_type == "route":
                # Get data for specific route
                df = get_flight_data(
                    start_date=start_date,
                    end_date=end_date,
                    origin=origin,
                    destination=destination
                )
                
                if df.empty:
                    st.error(f"No flight data found for the route {origin} to {destination} in the selected date range.")
                else:
                    # Prepare time series data
                    df['flight_date'] = pd.to_datetime(df['flight_date'])
                    daily_counts = df.groupby('flight_date').size().reset_index(name='count')
                    
                    # Generate forecast
                    st.header(f"Flight Volume Forecast: {origin} to {destination}")
                    forecast_df, metrics = advanced_flight_forecast(
                        daily_counts, 
                        days_to_forecast=forecast_days,
                        model_type=model_param[model_type]
                    )
                    
                    # Display forecast plot
                    fig_forecast = px.line(
                        forecast_df, 
                        x='flight_date', 
                        y='count',
                        color='forecast',
                        title=f"Flight Volume Forecast: {origin} to {destination} (Next {forecast_days} Days)",
                        labels={"flight_date": "Date", "count": "Number of Flights", "forecast": "Type"},
                        color_discrete_map={False: "blue", True: "red"}
                    )
                    
                    # Add a more descriptive legend
                    fig_forecast.update_traces(
                        name="Historical Data", 
                        selector=dict(name="False")
                    )
                    fig_forecast.update_traces(
                        name="Forecast", 
                        selector=dict(name="True")
                    )
                    
                    # Add confidence intervals (simplified)
                    historical_std = forecast_df[forecast_df['forecast'] == False]['count'].std()
                    forecast_values = forecast_df[forecast_df['forecast'] == True]
                    
                    upper_bound = forecast_values['count'] + 1.96 * historical_std
                    lower_bound = forecast_values['count'] - 1.96 * historical_std
                    lower_bound = lower_bound.apply(lambda x: max(0, x))  # Ensure non-negative
                    
                    fig_forecast.add_traces([
                        go.Scatter(
                            name='Upper Bound',
                            x=forecast_values['flight_date'],
                            y=upper_bound,
                            mode='lines',
                            marker=dict(color="#444"),
                            line=dict(width=0),
                            showlegend=True
                        ),
                        go.Scatter(
                            name='Lower Bound',
                            x=forecast_values['flight_date'],
                            y=lower_bound,
                            marker=dict(color="#444"),
                            line=dict(width=0),
                            mode='lines',
                            fillcolor='rgba(68, 68, 68, 0.3)',
                            fill='tonexty',
                            showlegend=True
                        )
                    ])
                    
                    st.plotly_chart(fig_forecast, use_container_width=True)
                    
                    # Display model metrics
                    st.subheader("Model Performance Metrics")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Historical Daily Average", 
                            f"{forecast_df[forecast_df['forecast'] == False]['count'].mean():.1f}"
                        )
                    with col2:
                        st.metric(
                            "Forecasted Daily Average", 
                            f"{forecast_df[forecast_df['forecast'] == True]['count'].mean():.1f}"
                        )
                    with col3:
                        forecast_total = forecast_df[forecast_df['forecast'] == True]['count'].sum()
                        st.metric(
                            f"Total Forecast ({forecast_days} days)", 
                            f"{forecast_total}"
                        )
                    
                    # Create a metrics table
                    metrics_df = pd.DataFrame({
                        'Model': ['Linear Regression', 'Random Forest'],
                        'MAE': [metrics['linear']['mae'], metrics['rf']['mae']],
                        'RMSE': [metrics['linear']['rmse'], metrics['rf']['rmse']],
                        'R²': [metrics['linear']['r2'], metrics['rf']['r2']]
                    })
                    
                    st.dataframe(metrics_df.style.highlight_min(axis=0, subset=['MAE', 'RMSE']).highlight_max(axis=0, subset=['R²']))
                    
                    # Show forecast data table
                    st.subheader("Detailed Forecast")
                    forecast_table = forecast_df[forecast_df['forecast'] == True][['flight_date', 'count']]
                    forecast_table.columns = ['Date', 'Forecasted Flights']
                    st.dataframe(forecast_table.style.highlight_max(axis=0, subset=['Forecasted Flights']))
                    
            else:  # airport forecast
                # Determine which data to fetch based on direction
                if direction == "Departures":
                    df = get_flight_data(
                        start_date=start_date,
                        end_date=end_date,
                        origin=airport
                    )
                    title_direction = "Departures from"
                elif direction == "Arrivals":
                    df = get_flight_data(
                        start_date=start_date,
                        end_date=end_date,
                        destination=airport
                    )
                    title_direction = "Arrivals to"
                else:  # Both
                    df_departures = get_flight_data(
                        start_date=start_date,
                        end_date=end_date,
                        origin=airport
                    )
                    df_arrivals = get_flight_data(
                        start_date=start_date,
                        end_date=end_date,
                        destination=airport
                    )
                    df = pd.concat([df_departures, df_arrivals])
                    title_direction = "Total Traffic for"
                
                if df.empty:
                    st.error(f"No flight data found for {airport} in the selected date range.")
                else:
                    # Prepare time series data
                    df['flight_date'] = pd.to_datetime(df['flight_date'])
                    daily_counts = df.groupby('flight_date').size().reset_index(name='count')
                    
                    # Generate forecast
                    st.header(f"Flight Volume Forecast: {title_direction} {airport}")
                    forecast_df, metrics = advanced_flight_forecast(
                        daily_counts, 
                        days_to_forecast=forecast_days,
                        model_type=model_param[model_type]
                    )
                    
                    # Display forecast plot
                    fig_forecast = px.line(
                        forecast_df, 
                        x='flight_date', 
                        y='count',
                        color='forecast',
                        title=f"Flight Volume Forecast: {title_direction} {airport} (Next {forecast_days} Days)",
                        labels={"flight_date": "Date", "count": "Number of Flights", "forecast": "Type"},
                        color_discrete_map={False: "blue", True: "red"}
                    )
                    
                    # Add a more descriptive legend
                    fig_forecast.update_traces(
                        name="Historical Data", 
                        selector=dict(name="False")
                    )
                    fig_forecast.update_traces(
                        name="Forecast", 
                        selector=dict(name="True")
                    )
                    
                    # Add confidence intervals (simplified)
                    historical_std = forecast_df[forecast_df['forecast'] == False]['count'].std()
                    forecast_values = forecast_df[forecast_df['forecast'] == True]
                    
                    upper_bound = forecast_values['count'] + 1.96 * historical_std
                    lower_bound = forecast_values['count'] - 1.96 * historical_std
                    lower_bound = lower_bound.apply(lambda x: max(0, x))  # Ensure non-negative
                    
                    fig_forecast.add_traces([
                        go.Scatter(
                            name='Upper Bound',
                            x=forecast_values['flight_date'],
                            y=upper_bound,
                            mode='lines',
                            marker=dict(color="#444"),
                            line=dict(width=0),
                            showlegend=True
                        ),
                        go.Scatter(
                            name='Lower Bound',
                            x=forecast_values['flight_date'],
                            y=lower_bound,
                            marker=dict(color="#444"),
                            line=dict(width=0),
                            mode='lines',
                            fillcolor='rgba(68, 68, 68, 0.3)',
                            fill='tonexty',
                            showlegend=True
                        )
                    ])
                    
                    st.plotly_chart(fig_forecast, use_container_width=True)
                    
                    # Rest of the code is the same as for route forecasting...
                    # Display model metrics
                    st.subheader("Model Performance Metrics")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(
                            "Historical Daily Average", 
                            f"{forecast_df[forecast_df['forecast'] == False]['count'].mean():.1f}"
                        )
                    with col2:
                        st.metric(
                            "Forecasted Daily Average", 
                            f"{forecast_df[forecast_df['forecast'] == True]['count'].mean():.1f}"
                        )
                    with col3:
                        forecast_total = forecast_df[forecast_df['forecast'] == True]['count'].sum()
                        st.metric(
                            f"Total Forecast ({forecast_days} days)", 
                            f"{forecast_total}"
                        )
                    
                    # Create a metrics table
                    metrics_df = pd.DataFrame({
                        'Model': ['Linear Regression', 'Random Forest'],
                        'MAE': [metrics['linear']['mae'], metrics['rf']['mae']],
                        'RMSE': [metrics['linear']['rmse'], metrics['rf']['rmse']],
                        'R²': [metrics['linear']['r2'], metrics['rf']['r2']]
                    })
                    
                    st.dataframe(metrics_df.style.highlight_min(axis=0, subset=['MAE', 'RMSE']).highlight_max(axis=0, subset=['R²']))
                    
                    # Show forecast data table
                    st.subheader("Detailed Forecast")
                    forecast_table = forecast_df[forecast_df['forecast'] == True][['flight_date', 'count']]
                    forecast_table.columns = ['Date', 'Forecasted Flights']
                    st.dataframe(forecast_table.style.highlight_max(axis=0, subset=['Forecasted Flights']))
        
        except Exception as e:
            st.error(f"An error occurred during forecasting: {str(e)}")
            st.info("This might be due to insufficient data. Try selecting a broader date range or different airports.")