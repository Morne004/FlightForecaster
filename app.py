import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from database import get_flight_data
import traceback

# Set page configuration
st.set_page_config(
    page_title="Flight Forecaster",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add title and description
st.title("✈️ Flight Forecaster")
st.markdown("An advanced forecasting tool for flight volumes")

# Debug section
with st.sidebar.expander("Debug Options"):
    st.subheader("Debug Information")
    
    # Show available secret keys without exposing values
    if hasattr(st, "secrets"):
        st.write("Secrets available:", list(st.secrets.keys()))
        if "connections" in st.secrets:
            st.write("Connection types:", list(st.secrets.connections.keys()))
    
    # Test database connection button
    if st.button("Test Database Connection"):
        try:
            from database import get_supabase_client
            client = get_supabase_client()
            st.success("✅ Connection successful!")
            
            # Try to list tables
            try:
                response = client.from_("information_schema.tables").select("table_name").execute()
                if hasattr(response, 'data') and response.data:
                    tables = [t.get("table_name") for t in response.data if t.get("table_name")]
                    st.write("Available tables:", tables)
            except Exception as e:
                st.error(f"Could not list tables: {str(e)}")
                st.error(traceback.format_exc())
                
        except Exception as e:
            st.error(f"❌ Connection failed: {str(e)}")
            st.error(traceback.format_exc())

# Sidebar for filters
st.sidebar.header("Filters")

# Date range picker
default_start_date = datetime.now() - timedelta(days=30)
default_end_date = datetime.now()
start_date = st.sidebar.date_input("Start Date", default_start_date)
end_date = st.sidebar.date_input("End Date", default_end_date)

# Get unique airports for the dropdown (in a real app, you'd fetch this from the database)
# For now, let's use a placeholder list
airports = ["LAX", "JFK", "SFO", "LHR", "CDG"]  # Example airports
origin = st.sidebar.selectbox("Origin Airport", options=["All"] + airports)
destination = st.sidebar.selectbox("Destination Airport", options=["All"] + airports)

# Convert 'All' to None for the database query
origin_filter = None if origin == "All" else origin
destination_filter = None if destination == "All" else destination

# Initialize df as an empty DataFrame to avoid NameError
df = pd.DataFrame()

# Try with simpler test query option
use_simple_query = st.sidebar.checkbox("Use Simple Test Query", value=True, help="Try a simpler query without filters to test connection")

# Load data button
if st.sidebar.button("Load Data"):
    with st.spinner("Loading flight data..."):
        try:
            if use_simple_query:
                # Try a very simple query first to test connection
                st.info("Using simple test query first...")
                from database import get_supabase_client
                supabase = get_supabase_client()
                
                try:
                    # Just do a basic test query
                    test_response = supabase.table('flights').select('*').limit(5).execute()
                    st.success(f"Test query successful! Found {len(test_response.data)} records.")
                    
                    # If test successful, proceed with the actual query
                    df = get_flight_data(
                        start_date=start_date,
                        end_date=end_date,
                        origin=origin_filter,
                        destination=destination_filter
                    )
                except Exception as e:
                    st.error(f"Test query failed: {str(e)}")
                    st.error(traceback.format_exc())
                    
                    # Try to list available tables
                    try:
                        st.info("Attempting to list available tables...")
                        tables_query = supabase.from_("information_schema.tables").select("table_name").execute()
                        if hasattr(tables_query, 'data') and tables_query.data:
                            table_names = [t.get("table_name") for t in tables_query.data if t.get("table_name")]
                            st.info(f"Available tables: {', '.join(table_names)}")
                    except Exception as table_e:
                        st.error(f"Failed to list tables: {str(table_e)}")
            else:
                # Use the normal query method
                df = get_flight_data(
                    start_date=start_date,
                    end_date=end_date,
                    origin=origin_filter,
                    destination=destination_filter
                )
        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            st.error(traceback.format_exc())
            df = pd.DataFrame()  # Ensure df is defined even if there's an error
        
        if not df.empty:
            st.success(f"Loaded {len(df)} flights")
            
            # Display data overview
            st.header("Data Overview")
            st.dataframe(df.head())
            
            # Basic statistics
            st.header("Flight Statistics")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Flights", len(df))
            with col2:
                delayed_flights = df['is_delayed'].sum() if 'is_delayed' in df.columns else 0
                st.metric("Delayed Flights", delayed_flights)
            with col3:
                avg_delay = df['delay_minutes'].mean() if 'delay_minutes' in df.columns else 0
                st.metric("Average Delay (minutes)", f"{avg_delay:.1f}")
                
            # Data visualizations
            st.header("Flight Data Visualizations")
            
            # Prepare data for visualizations
            # Group flights by date
            if 'flight_date' in df.columns:
                df['flight_date'] = pd.to_datetime(df['flight_date'])
                flights_by_date = df.groupby('flight_date').size().reset_index(name='count')
                
                # Plot flights over time
                st.subheader("Flights Over Time")
                fig_time = px.line(
                    flights_by_date, 
                    x='flight_date', 
                    y='count',
                    title="Number of Flights Per Day",
                    labels={"flight_date": "Date", "count": "Number of Flights"}
                )
                st.plotly_chart(fig_time, use_container_width=True)
            
            # Plot flights by origin
            if 'origin_code' in df.columns:
                st.subheader("Flights by Origin Airport")
                flights_by_origin = df.groupby('origin_code').size().reset_index(name='count')
                flights_by_origin = flights_by_origin.sort_values('count', ascending=False)
                
                fig_origin = px.bar(
                    flights_by_origin, 
                    x='origin_code', 
                    y='count',
                    title="Number of Flights by Origin Airport",
                    labels={"origin_code": "Origin Airport", "count": "Number of Flights"}
                )
                st.plotly_chart(fig_origin, use_container_width=True)
            
            # Plot flights by destination
            if 'destination_code' in df.columns:
                st.subheader("Flights by Destination Airport")
                flights_by_dest = df.groupby('destination_code').size().reset_index(name='count')
                flights_by_dest = flights_by_dest.sort_values('count', ascending=False)
                
                fig_dest = px.bar(
                    flights_by_dest, 
                    x='destination_code', 
                    y='count',
                    title="Number of Flights by Destination Airport",
                    labels={"destination_code": "Destination Airport", "count": "Number of Flights"}
                )
                st.plotly_chart(fig_dest, use_container_width=True)
        else:
            st.warning("No data found for the selected filters")

# Forecasting section
st.header("Flight Volume Forecasting")
forecast_days = st.slider("Forecast Days", min_value=7, max_value=90, value=30, step=7)

# Check if we have data to work with
if not df.empty and 'flight_date' in df.columns:
    # Import forecasting functions
    from forecasting import prepare_time_series_data, simple_flight_forecast
    
    # Add a button to generate forecast
    if st.button("Generate Forecast"):
        with st.spinner("Generating forecast..."):
            try:
                # Prepare time series data
                if origin_filter and destination_filter:
                    # Forecast for specific route
                    st.subheader(f"Forecasting flights from {origin_filter} to {destination_filter}")
                    group_cols = ['origin_code', 'destination_code']
                    time_series_df = prepare_time_series_data(df, group_by_cols=group_cols)
                    filtered_df = time_series_df[
                        (time_series_df['origin_code'] == origin_filter) & 
                        (time_series_df['destination_code'] == destination_filter)
                    ]
                    if filtered_df.empty:
                        st.warning("Not enough data for the selected route to generate a forecast")
                    else:
                        forecast_df = simple_flight_forecast(filtered_df, days_to_forecast=forecast_days)
                elif origin_filter:
                    # Forecast for specific origin
                    st.subheader(f"Forecasting flights from {origin_filter}")
                    time_series_df = prepare_time_series_data(df, group_by_cols=['origin_code'])
                    filtered_df = time_series_df[time_series_df['origin_code'] == origin_filter]
                    forecast_df = simple_flight_forecast(filtered_df, days_to_forecast=forecast_days)
                elif destination_filter:
                    # Forecast for specific destination
                    st.subheader(f"Forecasting flights to {destination_filter}")
                    time_series_df = prepare_time_series_data(df, group_by_cols=['destination_code'])
                    filtered_df = time_series_df[time_series_df['destination_code'] == destination_filter]
                    forecast_df = simple_flight_forecast(filtered_df, days_to_forecast=forecast_days)
                else:
                    # Forecast all flights
                    st.subheader("Forecasting total flight volume")
                    time_series_df = prepare_time_series_data(df)
                    forecast_df = simple_flight_forecast(time_series_df, days_to_forecast=forecast_days)
                
                # Plot forecast
                st.subheader("Flight Volume Forecast")
                
                # Create Plotly figure for the forecast
                fig_forecast = px.line(
                    forecast_df, 
                    x='flight_date', 
                    y='count',
                    color='forecast',
                    title="Flight Volume Forecast",
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
                
                # Show the forecast plot
                st.plotly_chart(fig_forecast, use_container_width=True)
                
                # Display forecast metrics
                hist_avg = forecast_df[forecast_df['forecast'] == False]['count'].mean()
                forecast_avg = forecast_df[forecast_df['forecast'] == True]['count'].mean()
                percent_change = ((forecast_avg - hist_avg) / hist_avg) * 100 if hist_avg > 0 else 0
                
                st.metric(
                    "Forecasted Daily Average", 
                    f"{forecast_avg:.1f} flights",
                    f"{percent_change:.1f}%",
                    delta_color="normal" if percent_change >= 0 else "inverse"
                )
                
                # Show forecast data table
                st.subheader("Forecast Data")
                forecast_table = forecast_df[forecast_df['forecast'] == True][['flight_date', 'count']]
                forecast_table.columns = ['Date', 'Forecasted Flights']
                st.dataframe(forecast_table)
            except Exception as e:
                st.error(f"Error generating forecast: {str(e)}")
                st.error(traceback.format_exc())
else:
    st.info("Please load flight data using the 'Load Data' button in the sidebar to enable forecasting.")
            
# Sample data option (workaround for database issues)
st.sidebar.markdown("---")
if st.sidebar.checkbox("Use Sample Data", help="Use this to test the app without a database connection"):
    st.sidebar.info("Using sample data instead of database")
    # Generate sample flight data
    sample_flights = []
    base_date = datetime.now() - timedelta(days=60)
    
    for i in range(60):
        curr_date = base_date + timedelta(days=i)
        # Add random flights for this day
        for _ in range(10 + i % 5):  # 10-14 flights per day
            sample_flights.append({
                'flight_date': curr_date,
                'origin_code': airports[i % len(airports)],
                'destination_code': airports[(i + 2) % len(airports)],
                'is_delayed': i % 3 == 0,
                'delay_minutes': 15 if i % 3 == 0 else 0,
                'deleted': False
            })
    
    # Convert to DataFrame
    df = pd.DataFrame(sample_flights)
    st.success(f"Loaded {len(df)} sample flights")

# Footer
st.sidebar.markdown("---")
st.sidebar.info("FlightForecaster v1.0")