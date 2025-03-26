# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
from utils import get_flight_data, calculate_metrics, get_top_routes, get_aircraft_usage

# Page configuration
st.set_page_config(
    page_title="Flight Analysis Dashboard",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
    }
    .metric-label {
        font-size: 1rem;
        color: #555;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">✈️ Flight Analysis Dashboard</div>', unsafe_allow_html=True)

# Load data
try:
    with st.spinner("Loading flight data..."):
        df = get_flight_data()
    
    # Add date column if not present
    if 'flight_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['flight_date']):
        df['flight_date'] = pd.to_datetime(df['flight_date'])
    
    # Calculate metrics
    metrics = calculate_metrics(df)
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics["total_flights"]}</div>
            <div class="metric-label">Total Flights</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics["unique_routes"]}</div>
            <div class="metric-label">Unique Routes</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics["unique_aircraft"]}</div>
            <div class="metric-label">Aircraft Used</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{metrics["on_time_percentage"]:.1f}%</div>
            <div class="metric-label">On-Time Performance</div>
        </div>
        """, unsafe_allow_html=True)
    
    # Charts section
    st.markdown("### Flight Analytics")
    
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("Top Routes by Flight Count")
        top_routes = get_top_routes(df)
        fig = px.bar(
            top_routes, 
            x="route", 
            y="count",
            labels={"route": "Route", "count": "Number of Flights"},
            color="count",
            color_continuous_scale=px.colors.sequential.Blues,
        )
        fig.update_layout(
            xaxis_title="Route",
            yaxis_title="Number of Flights"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with chart_col2:
        st.subheader("Most Used Aircraft")
        aircraft_usage = get_aircraft_usage(df)
        fig = px.pie(
            values=aircraft_usage.values,
            names=aircraft_usage.index,
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.Blues
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent flights section
    st.markdown("### Recent Flights")
    if 'flight_date' in df.columns:
        recent_flights = df.sort_values('flight_date', ascending=False).head(5)
        st.dataframe(
            recent_flights[['flight_number_full', 'origin_code', 'destination_code', 
                          'flight_date', 'scheduled_departure', 'actual_departure', 
                          'scheduled_arrival', 'actual_arrival', 'is_delayed', 'registration']],
            use_container_width=True
        )
    else:
        st.warning("Flight date information not available")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.error("Please check your Supabase connection and try again.")

# Footer
st.markdown("---")
st.markdown("Flight Analysis Dashboard | Developed with Streamlit")