import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
from database import get_flight_data

# Set page configuration
st.set_page_config(
    page_title="Advanced Analysis - Flight Forecaster",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Advanced Flight Analysis")
st.markdown("Detailed analysis of flight patterns and trends")

# Sidebar filters
st.sidebar.header("Filters")

# Date range picker
default_start_date = datetime.now() - timedelta(days=90)  # Longer timeframe for advanced analysis
default_end_date = datetime.now()
start_date = st.sidebar.date_input("Start Date", default_start_date)
end_date = st.sidebar.date_input("End Date", default_end_date)

# Get unique airports (placeholder for now)
airports = ["LAX", "JFK", "SFO", "LHR", "CDG"]  # Example airports
selected_airports = st.sidebar.multiselect("Select Airports", options=airports)

# Analysis type selection
analysis_type = st.sidebar.selectbox(
    "Analysis Type",
    options=["Route Performance", "Delay Analysis", "Seasonal Patterns"]
)

# Load data button
if st.sidebar.button("Run Analysis"):
    with st.spinner("Loading and analyzing flight data..."):
        # For each selected airport, get both origin and destination flights
        dfs = []
        for airport in selected_airports:
            # Get flights where this airport is origin
            origin_df = get_flight_data(
                start_date=start_date,
                end_date=end_date,
                origin=airport
            )
            if not origin_df.empty:
                origin_df['airport_role'] = 'Origin'
                origin_df['airport'] = airport
                dfs.append(origin_df)
            
            # Get flights where this airport is destination
            dest_df = get_flight_data(
                start_date=start_date,
                end_date=end_date,
                destination=airport
            )
            if not dest_df.empty:
                dest_df['airport_role'] = 'Destination'
                dest_df['airport'] = airport
                dfs.append(dest_df)
        
        if dfs:
            # Combine all data
            df = pd.concat(dfs)
            df['flight_date'] = pd.to_datetime(df['flight_date'])
            
            # Show different analysis based on selection
            if analysis_type == "Route Performance":
                st.header("Route Performance Analysis")
                
                # Create a unique route identifier
                df['route'] = df['origin_code'] + ' → ' + df['destination_code']
                
                # Analyze top routes
                route_counts = df.groupby('route').size().reset_index(name='flights')
                top_routes = route_counts.sort_values('flights', ascending=False).head(10)
                
                # Plot top routes
                fig_routes = px.bar(
                    top_routes,
                    x='route',
                    y='flights',
                    title="Top 10 Routes by Flight Volume",
                    labels={"route": "Route", "flights": "Number of Flights"}
                )
                st.plotly_chart(fig_routes, use_container_width=True)
                
                # Route trends over time
                if len(top_routes) > 0:
                    st.subheader("Route Trends Over Time")
                    top_5_routes = top_routes.head(5)['route'].tolist()
                    route_df = df[df['route'].isin(top_5_routes)]
                    
                    # Group by route and date
                    route_trend = route_df.groupby(['route', 'flight_date']).size().reset_index(name='flights')
                    
                    # Plot trends
                    fig_trends = px.line(
                        route_trend,
                        x='flight_date',
                        y='flights',
                        color='route',
                        title="Flight Volume Trends for Top 5 Routes",
                        labels={"flight_date": "Date", "flights": "Number of Flights", "route": "Route"}
                    )
                    st.plotly_chart(fig_trends, use_container_width=True)
            
            elif analysis_type == "Delay Analysis":
                st.header("Flight Delay Analysis")
                
                # Check if delay data is available
                if 'is_delayed' in df.columns and 'delay_minutes' in df.columns:
                    # Calculate delay metrics
                    total_flights = len(df)
                    delayed_flights = df['is_delayed'].sum()
                    delay_rate = (delayed_flights / total_flights) * 100 if total_flights > 0 else 0
                    
                    # Display metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Flights Analyzed", total_flights)
                    with col2:
                        st.metric("Delayed Flights", delayed_flights)
                    with col3:
                        st.metric("Delay Rate", f"{delay_rate:.1f}%")
                    
                    # Delay distribution
                    st.subheader("Delay Duration Distribution")
                    delay_df = df[df['is_delayed'] == True]
                    
                    if not delay_df.empty:
                        fig_delay_hist = px.histogram(
                            delay_df,
                            x='delay_minutes',
                            nbins=20,
                            title="Distribution of Delay Durations",
                            labels={"delay_minutes": "Delay (minutes)"}
                        )
                        st.plotly_chart(fig_delay_hist, use_container_width=True)
                        
                        # Delay by airport
                        st.subheader("Delay Rate by Airport")
                        airport_delays = df.groupby('airport').agg(
                            total_flights=('flight_id', 'count'),
                            delayed_flights=('is_delayed', 'sum')
                        ).reset_index()
                        
                        airport_delays['delay_rate'] = (airport_delays['delayed_flights'] / airport_delays['total_flights']) * 100
                        
                        fig_airport_delays = px.bar(
                            airport_delays,
                            x='airport',
                            y='delay_rate',
                            title="Delay Rate by Airport",
                            labels={"airport": "Airport", "delay_rate": "Delay Rate (%)"}
                        )
                        st.plotly_chart(fig_airport_delays, use_container_width=True)
                    else:
                        st.info("No delayed flights found in the selected data")
                else:
                    st.warning("Delay information is not available in the dataset")
            
            elif analysis_type == "Seasonal Patterns":
                st.header("Seasonal Flight Patterns")
                
                # Add month and day of week
                df['month'] = df['flight_date'].dt.month_name()
                df['day_of_week'] = df['flight_date'].dt.day_name()
                
                # Flights by month
                monthly_flights = df.groupby('month').size().reset_index(name='flights')
                # Ensure correct month order
                month_order = ['January', 'February', 'March', 'April', 'May', 'June', 
                              'July', 'August', 'September', 'October', 'November', 'December']
                monthly_flights['month'] = pd.Categorical(monthly_flights['month'], categories=month_order, ordered=True)
                monthly_flights = monthly_flights.sort_values('month')
                
                st.subheader("Flights by Month")
                fig_monthly = px.bar(
                    monthly_flights,
                    x='month',
                    y='flights',
                    title="Flight Volume by Month",
                    labels={"month": "Month", "flights": "Number of Flights"}
                )
                st.plotly_chart(fig_monthly, use_container_width=True)
                
                # Flights by day of week
                daily_flights = df.groupby('day_of_week').size().reset_index(name='flights')
                # Ensure correct day order
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                daily_flights['day_of_week'] = pd.Categorical(daily_flights['day_of_week'], categories=day_order, ordered=True)
                daily_flights = daily_flights.sort_values('day_of_week')
                
                st.subheader("Flights by Day of Week")
                fig_daily = px.bar(
                    daily_flights,
                    x='day_of_week',
                    y='flights',
                    title="Flight Volume by Day of Week",
                    labels={"day_of_week": "Day of Week", "flights": "Number of Flights"}
                )
                st.plotly_chart(fig_daily, use_container_width=True)
        else:
            st.warning("No data found for the selected airports and date range")