import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from database import get_flight_data

# Set page configuration
st.set_page_config(
    page_title="Dashboard - Flight Forecaster",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Flight Operations Dashboard")
st.markdown("Overview of flight operations and key performance indicators")

# Date filter in the sidebar
st.sidebar.header("Date Range")
end_date = datetime.now().date()
start_date = end_date - timedelta(days=30)

start_date = st.sidebar.date_input("Start Date", start_date)
end_date = st.sidebar.date_input("End Date", end_date)

# Load data
with st.spinner("Loading dashboard data..."):
    # Get all flights for the date range
    df = get_flight_data(start_date=start_date, end_date=end_date)
    
    if not df.empty:
        # Convert date column
        df['flight_date'] = pd.to_datetime(df['flight_date'])
        
        # Create metrics
        total_flights = len(df)
        unique_origins = df['origin_code'].nunique()
        unique_destinations = df['destination_code'].nunique()
        delay_rate = (df['is_delayed'].sum() / total_flights * 100) if 'is_delayed' in df.columns else 0
        
        # Display KPIs
        st.header("Key Performance Indicators")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Flights", total_flights)
        with col2:
            st.metric("Origin Airports", unique_origins)
        with col3:
            st.metric("Destination Airports", unique_destinations)
        with col4:
            st.metric("Delay Rate", f"{delay_rate:.1f}%")
            
        # Create two columns for the charts
        col_left, col_right = st.columns(2)
        
        with col_left:
            # Flights by day
            st.subheader("Daily Flight Volume")
            daily_flights = df.groupby('flight_date').size().reset_index(name='count')
            
            # Calculate 7-day moving average
            daily_flights['7d_avg'] = daily_flights['count'].rolling(7, min_periods=1).mean()
            
            # Create figure with dual y-axis
            fig_daily = go.Figure()
            
            # Add bar chart for daily counts
            fig_daily.add_trace(
                go.Bar(
                    x=daily_flights['flight_date'],
                    y=daily_flights['count'],
                    name="Daily Flights",
                    marker_color='lightblue'
                )
            )
            
            # Add line chart for moving average
            fig_daily.add_trace(
                go.Scatter(
                    x=daily_flights['flight_date'],
                    y=daily_flights['7d_avg'],
                    name="7-Day Average",
                    line=dict(color='darkblue', width=2)
                )
            )
            
            fig_daily.update_layout(
                title="Daily Flight Volume",
                xaxis_title="Date",
                yaxis_title="Number of Flights",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )
            
            st.plotly_chart(fig_daily, use_container_width=True)
            
            # Top origin airports
            st.subheader("Top Origin Airports")
            top_origins = df.groupby('origin_code').size().reset_index(name='count')
            top_origins = top_origins.sort_values('count', ascending=False).head(10)
            
            fig_origins = px.bar(
                top_origins,
                x='origin_code',
                y='count',
                title="Top 10 Origin Airports by Flight Volume",
                labels={"origin_code": "Airport Code", "count": "Number of Flights"}
            )
            
            st.plotly_chart(fig_origins, use_container_width=True)
            
        with col_right:
            # Delay metrics (if available)
            if 'is_delayed' in df.columns and 'delay_minutes' in df.columns:
                st.subheader("Delay Analysis")
                
                # Delay distribution
                delayed_df = df[df['is_delayed'] == True]
                
                if not delayed_df.empty:
                    # Create a delay category
                    bins = [0, 15, 30, 60, 120, float('inf')]
                    labels = ['< 15 min', '15-30 min', '30-60 min', '1-2 hours', '> 2 hours']
                    
                    delayed_df['delay_category'] = pd.cut(
                        delayed_df['delay_minutes'], 
                        bins=bins, 
                        labels=labels
                    )
                    
                    delay_counts = delayed_df['delay_category'].value_counts().reset_index()
                    delay_counts.columns = ['category', 'count']
                    delay_counts = delay_counts.sort_values('count', ascending=False)
                    
                    fig_delays = px.pie(
                        delay_counts,
                        values='count',
                        names='category',
                        title="Delay Duration Distribution",
                        hole=0.4,
                        color_discrete_sequence=px.colors.sequential.RdBu
                    )
                    
                    st.plotly_chart(fig_delays, use_container_width=True)
                    
                    # Delay trend over time
                    daily_delay_rate = df.groupby('flight_date').agg(
                        total=('flight_id', 'count'),
                        delayed=('is_delayed', 'sum')
                    ).reset_index()
                    
                    daily_delay_rate['delay_rate'] = (daily_delay_rate['delayed'] / daily_delay_rate['total'] * 100)
                    
                    fig_delay_trend = px.line(
                        daily_delay_rate,
                        x='flight_date',
                        y='delay_rate',
                        title="Daily Delay Rate Trend",
                        labels={"flight_date": "Date", "delay_rate": "Delay Rate (%)"}
                    )
                    
                    # Add a reference line for average delay rate
                    avg_delay_rate = delay_rate
                    fig_delay_trend.add_hline(
                        y=avg_delay_rate,
                        line_dash="dash",
                        line_color="red",
                        annotation_text=f"Avg: {avg_delay_rate:.1f}%",
                        annotation_position="bottom right"
                    )
                    
                    st.plotly_chart(fig_delay_trend, use_container_width=True)
                    
                    # Identify problem airports
                    st.subheader("Airports with Highest Delay Rates")
                    
                    # Calculate delay rate by airport
                    airport_delays = df.groupby('origin_code').agg(
                        total=('flight_id', 'count'),
                        delayed=('is_delayed', 'sum')
                    ).reset_index()
                    
                    airport_delays['delay_rate'] = (airport_delays['delayed'] / airport_delays['total'] * 100)
                    airport_delays = airport_delays.sort_values('delay_rate', ascending=False).head(5)
                    
                    fig_problem_airports = px.bar(
                        airport_delays,
                        x='origin_code',
                        y='delay_rate',
                        title="Top 5 Airports by Delay Rate",
                        labels={"origin_code": "Airport Code", "delay_rate": "Delay Rate (%)"}
                    )
                    
                    st.plotly_chart(fig_problem_airports, use_container_width=True)
            
            # Top destination airports
            st.subheader("Top Destination Airports")
            top_destinations = df.groupby('destination_code').size().reset_index(name='count')
            top_destinations = top_destinations.sort_values('count', ascending=False).head(10)
            
            fig_destinations = px.bar(
                top_destinations,
                x='destination_code',
                y='count',
                title="Top 10 Destination Airports by Flight Volume",
                labels={"destination_code": "Airport Code", "count": "Number of Flights"}
            )
            
            st.plotly_chart(fig_destinations, use_container_width=True)
        
        # Add a section for top routes
        st.header("Top Flight Routes")
        
        # Create route identifier
        df['route'] = df['origin_code'] + ' → ' + df['destination_code']
        
        # Get top routes
        top_routes = df.groupby('route').size().reset_index(name='count')
        top_routes = top_routes.sort_values('count', ascending=False).head(10)
        
        fig_routes = px.bar(
            top_routes,
            x='route',
            y='count',
            title="Top 10 Routes by Flight Volume",
            labels={"route": "Route", "count": "Number of Flights"}
        )
        
        st.plotly_chart(fig_routes, use_container_width=True)
        
    else:
        st.warning("No flight data available for the selected date range")