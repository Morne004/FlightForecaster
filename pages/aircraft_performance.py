# pages/aircraft_performance.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import get_flight_data

# Page configuration
st.set_page_config(
    page_title="Aircraft Performance | Flight Analysis",
    page_icon="✈️",
    layout="wide"
)

# Header
st.title("✈️ Aircraft Performance Analysis")
st.markdown("Track usage and compare fuel efficiency across different aircraft")

# Load the data
try:
    with st.spinner("Loading flight data..."):
        df = get_flight_data()
        
    if df.empty:
        st.error("No data available. Please check your connection to Supabase.")
    else:
        # Sidebar filters
        st.sidebar.header("Filters")
        
        # Filter by aircraft registration
        all_aircraft = sorted(df["registration"].unique())
        selected_aircraft = st.sidebar.multiselect(
            "Select Aircraft Registrations",
            options=all_aircraft,
            default=all_aircraft[:5] if len(all_aircraft) > 5 else all_aircraft
        )
        
        # Filter by date range if available
        if 'flight_date' in df.columns:
            if not pd.api.types.is_datetime64_any_dtype(df['flight_date']):
                df['flight_date'] = pd.to_datetime(df['flight_date'])
                
            min_date = df['flight_date'].min().date()
            max_date = df['flight_date'].max().date()
            
            date_range = st.sidebar.date_input(
                "Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                mask = (df['flight_date'].dt.date >= start_date) & (df['flight_date'].dt.date <= end_date)
                df_filtered = df[mask]
            else:
                df_filtered = df
        else:
            df_filtered = df
        
        # Apply aircraft registration filter
        if selected_aircraft:
            df_filtered = df_filtered[df_filtered["registration"].isin(selected_aircraft)]
        
        # Main content
        tab1, tab2, tab3 = st.tabs(["Usage Frequency", "Fuel Efficiency", "Aircraft Details"])
        
        with tab1:
            st.header("Aircraft Usage Frequency")
            
            # Aircraft usage by flight count
            aircraft_usage = df_filtered["registration"].value_counts().reset_index()
            aircraft_usage.columns = ["Aircraft Registration", "Number of Flights"]
            
            fig1 = px.bar(
                aircraft_usage,
                x="Aircraft Registration",
                y="Number of Flights",
                color="Number of Flights",
                color_continuous_scale=px.colors.sequential.Blues,
                title="Number of Flights by Aircraft Registration"
            )
            
            st.plotly_chart(fig1, use_container_width=True)
            
            # Route distribution by aircraft
            if not df_filtered.empty:
                st.subheader("Routes Flown by Each Aircraft")
                
                aircraft_routes = df_filtered.groupby(["registration", "origin_code", "destination_code"]).size().reset_index(name="count")
                aircraft_routes["route"] = aircraft_routes["origin_code"] + " → " + aircraft_routes["destination_code"]
                
                selected_aircraft_for_routes = st.selectbox(
                    "Select Aircraft Registration",
                    options=selected_aircraft
                )
                
                aircraft_route_data = aircraft_routes[aircraft_routes["registration"] == selected_aircraft_for_routes]
                
                if not aircraft_route_data.empty:
                    fig2 = px.pie(
                        aircraft_route_data,
                        values="count",
                        names="route",
                        title=f"Routes Flown by {selected_aircraft_for_routes}",
                        hole=0.4
                    )
                    fig2.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.info(f"No route data available for {selected_aircraft_for_routes}")
        
        with tab2:
            st.header("Fuel Efficiency Analysis")
            
            if all(col in df_filtered.columns for col in ["registration", "fuel_used", "fuel_volume"]):
                # Average fuel consumption by aircraft
                fuel_by_aircraft = df_filtered.groupby("registration")[["fuel_used", "fuel_volume"]].mean().reset_index()
                
                fig3 = px.bar(
                    fuel_by_aircraft,
                    x="registration",
                    y="fuel_used",
                    color="fuel_used",
                    color_continuous_scale=px.colors.sequential.Reds_r,  # Reversed so lower is better (green)
                    title="Average Fuel Consumption by Aircraft"
                )
                fig3.update_layout(xaxis_title="Aircraft Registration", yaxis_title="Average Fuel Used (L)")
                st.plotly_chart(fig3, use_container_width=True)
                
                # Compare planned vs actual fuel usage
                if "planned_fuel_usage" in df_filtered.columns:
                    st.subheader("Planned vs Actual Fuel Usage")
                    
                    fuel_comparison = df_filtered.groupby("registration").agg({
                        "fuel_used": "mean",
                        "planned_fuel_usage": "mean"
                    }).reset_index()
                    
                    fuel_comparison["difference"] = fuel_comparison["fuel_used"] - fuel_comparison["planned_fuel_usage"]
                    fuel_comparison["difference_percent"] = (fuel_comparison["difference"] / fuel_comparison["planned_fuel_usage"]) * 100
                    
                    fig4 = go.Figure()
                    
                    fig4.add_trace(go.Bar(
                        x=fuel_comparison["registration"],
                        y=fuel_comparison["planned_fuel_usage"],
                        name="Planned Fuel Usage",
                        marker_color="lightblue"
                    ))
                    
                    fig4.add_trace(go.Bar(
                        x=fuel_comparison["registration"],
                        y=fuel_comparison["fuel_used"],
                        name="Actual Fuel Used",
                        marker_color="darkblue"
                    ))
                    
                    fig4.update_layout(
                        title="Planned vs Actual Fuel Usage by Aircraft",
                        xaxis_title="Aircraft Registration",
                        yaxis_title="Fuel (L)",
                        barmode="group"
                    )
                    
                    st.plotly_chart(fig4, use_container_width=True)
                    
                    # Show efficiency as a percentage
                    st.subheader("Fuel Efficiency by Aircraft")
                    
                    fig5 = px.bar(
                        fuel_comparison,
                        x="registration",
                        y="difference_percent",
                        color="difference_percent",
                        color_continuous_scale=px.colors.diverging.RdBu_r,  # Red for over, blue for under
                        title="Fuel Usage Variance from Plan (%)"
                    )
                    
                    fig5.update_layout(
                        xaxis_title="Aircraft Registration",
                        yaxis_title="Variance from Planned Usage (%)",
                        hovermode="x unified"
                    )
                    
                    fig5.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray")
                    
                    st.plotly_chart(fig5, use_container_width=True)
            else:
                st.warning("Fuel data is not available in the dataset. Cannot perform fuel efficiency analysis.")
        
        with tab3:
            st.header("Aircraft Details")
            
            selected_aircraft_details = st.selectbox(
                "Select Aircraft for Detailed Information",
                options=selected_aircraft,
                key="aircraft_details"
            )
            
            if selected_aircraft_details:
                aircraft_data = df_filtered[df_filtered["registration"] == selected_aircraft_details]
                
                # Aircraft summary metrics
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total Flights", len(aircraft_data))
                
                with col2:
                    if "fuel_used" in aircraft_data.columns:
                        avg_fuel = aircraft_data["fuel_used"].mean()
                        st.metric("Avg Fuel Used", f"{avg_fuel:.0f} L")
                    else:
                        st.metric("Avg Fuel Used", "N/A")
                
                with col3:
                    unique_routes = aircraft_data[["origin_code", "destination_code"]].drop_duplicates().shape[0]
                    st.metric("Unique Routes", unique_routes)
                
                # Flight history
                st.subheader(f"Flight History for {selected_aircraft_details}")
                
                if 'flight_date' in aircraft_data.columns:
                    aircraft_data = aircraft_data.sort_values('flight_date', ascending=False)
                
                columns_to_show = [
                    "flight_number_full", "origin_code", "destination_code", 
                    "flight_date", "scheduled_departure", "actual_departure",
                    "scheduled_arrival", "actual_arrival"
                ]
                
                # Only include columns that exist in the dataframe
                valid_columns = [col for col in columns_to_show if col in aircraft_data.columns]
                
                st.dataframe(
                    aircraft_data[valid_columns],
                    use_container_width=True
                )

except Exception as e:
    st.error(f"Error: {e}")
    st.error("Please check your data connection and try again.")