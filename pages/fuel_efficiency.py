# pages/fuel_efficiency.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import get_flight_data, format_route

# Page configuration
st.set_page_config(
    page_title="Fuel Efficiency | Flight Analysis",
    page_icon="✈️",
    layout="wide"
)

# Header
st.title("⛽ Fuel Efficiency Analysis")
st.markdown("Analyze fuel consumption patterns per route and compare efficiency across aircraft")

# Load the data
try:
    with st.spinner("Loading flight data..."):
        df = get_flight_data()
        
    if df.empty:
        st.error("No data available. Please check your connection to Supabase.")
    else:
        # Process data
        if 'flight_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['flight_date']):
            df['flight_date'] = pd.to_datetime(df['flight_date'])
        
        # Check if fuel data columns exist
        fuel_cols = ['fuel_used', 'fuel_volume', 'uplift_volume', 'planned_fuel_usage', 'arrival_fuel']
        has_fuel_data = any(col in df.columns for col in fuel_cols)
        
        if not has_fuel_data:
            st.error("Fuel data columns not found in the dataset. Cannot perform fuel efficiency analysis.")
        else:
            # Sidebar filters
            st.sidebar.header("Filters")
            
            # Filter by route
            routes = []
            for _, row in df[['origin_code', 'destination_code']].drop_duplicates().iterrows():
                routes.append(format_route(row['origin_code'], row['destination_code']))
            
            selected_routes = st.sidebar.multiselect(
                "Select Routes",
                options=routes,
                default=routes[:3] if len(routes) > 3 else routes
            )
            
            # Filter by aircraft
            all_aircraft = sorted(df["registration"].unique())
            selected_aircraft = st.sidebar.multiselect(
                "Select Aircraft",
                options=all_aircraft,
                default=[]
            )
            
            # Filter by date range if available
            if 'flight_date' in df.columns:
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
            
            # Apply route filter
            if selected_routes:
                filtered_routes = []
                for route in selected_routes:
                    origin, destination = route.split(" → ")
                    filtered_routes.append((origin, destination))
                
                mask = df_filtered.apply(
                    lambda row: (row['origin_code'], row['destination_code']) in filtered_routes,
                    axis=1
                )
                df_filtered = df_filtered[mask]
            
            # Apply aircraft filter
            if selected_aircraft:
                df_filtered = df_filtered[df_filtered["registration"].isin(selected_aircraft)]
            
            # Main content - Tabs
            tab1, tab2, tab3 = st.tabs(["Route Fuel Analysis", "Aircraft Comparison", "Fuel Trends"])
            
            with tab1:
                st.header("Fuel Consumption by Route")
                
                if 'fuel_used' in df_filtered.columns:
                    # Create a route column
                    df_filtered['route'] = df_filtered.apply(
                        lambda row: format_route(row['origin_code'], row['destination_code']), 
                        axis=1
                    )
                    
                    # Calculate average fuel used by route
                    route_fuel = df_filtered.groupby('route')['fuel_used'].agg(['mean', 'min', 'max', 'count']).reset_index()
                    route_fuel.columns = ['Route', 'Average Fuel Used', 'Min Fuel Used', 'Max Fuel Used', 'Flight Count']
                    
                    # Sort by average fuel used
                    route_fuel = route_fuel.sort_values('Average Fuel Used', ascending=False)
                    
                    # Plot the data
                    fig1 = px.bar(
                        route_fuel,
                        x='Route',
                        y='Average Fuel Used',
                        error_y=route_fuel['Max Fuel Used'] - route_fuel['Average Fuel Used'],
                        error_y_minus=route_fuel['Average Fuel Used'] - route_fuel['Min Fuel Used'],
                        color='Average Fuel Used',
                        color_continuous_scale=px.colors.sequential.Blues,
                        hover_data=['Min Fuel Used', 'Max Fuel Used', 'Flight Count'],
                        title="Average Fuel Consumption by Route"
                    )
                    
                    fig1.update_layout(
                        xaxis_title="Route",
                        yaxis_title="Fuel Used (L)",
                        xaxis={'categoryorder':'total descending'}
                    )
                    
                    st.plotly_chart(fig1, use_container_width=True)
                    
                    # Show the data table
                    st.subheader("Fuel Consumption Data by Route")
                    st.dataframe(route_fuel, use_container_width=True)
                    
                    # Calculate fuel per distance
                    if all(col in df_filtered.columns for col in ['origin_icao', 'destination_icao']):
                        st.subheader("Fuel Efficiency Analysis")
                        st.info("To calculate precise fuel efficiency per distance, we would need distance data between airports which is not currently available in the dataset. This would allow us to show fuel used per kilometer for each route.")
                else:
                    st.warning("Fuel usage data is not available in the selected dataset.")
            
            with tab2:
                st.header("Aircraft Fuel Efficiency Comparison")
                
                if 'fuel_used' in df_filtered.columns and 'registration' in df_filtered.columns:
                    # Group by route and aircraft
                    df_filtered['route'] = df_filtered.apply(
                        lambda row: format_route(row['origin_code'], row['destination_code']), 
                        axis=1
                    )
                    
                    aircraft_route_fuel = df_filtered.groupby(['route', 'registration'])['fuel_used'].mean().reset_index()
                    aircraft_route_fuel.columns = ['Route', 'Aircraft', 'Average Fuel Used']
                    
                    # Filter to routes with multiple aircraft for comparison
                    route_aircraft_counts = df_filtered.groupby('route')['registration'].nunique()
                    routes_with_multiple_aircraft = route_aircraft_counts[route_aircraft_counts > 1].index.tolist()
                    
                    if routes_with_multiple_aircraft:
                        selected_route_for_comparison = st.selectbox(
                            "Select Route for Aircraft Comparison",
                            options=routes_with_multiple_aircraft
                        )
                        
                        route_data = aircraft_route_fuel[aircraft_route_fuel['Route'] == selected_route_for_comparison]
                        
                        if not route_data.empty:
                            # Sort by fuel used
                            route_data = route_data.sort_values('Average Fuel Used')
                            
                            # Calculate the average for the route
                            route_avg = route_data['Average Fuel Used'].mean()
                            
                            # Plot the comparison
                            fig2 = px.bar(
                                route_data,
                                x='Aircraft',
                                y='Average Fuel Used',
                                color='Average Fuel Used',
                                color_continuous_scale=px.colors.sequential.Blues_r,  # Reversed so lower is better
                                title=f"Aircraft Fuel Efficiency Comparison for {selected_route_for_comparison}"
                            )
                            
                            fig2.add_hline(
                                y=route_avg,
                                line_dash="dash",
                                line_color="red",
                                annotation_text=f"Route Average: {route_avg:.0f}L"
                            )
                            
                            fig2.update_layout(
                                xaxis_title="Aircraft Registration",
                                yaxis_title="Average Fuel Used (L)"
                            )
                            
                            st.plotly_chart(fig2, use_container_width=True)
                            
                            # Add context
                            most_efficient = route_data.iloc[0]
                            least_efficient = route_data.iloc[-1]
                            
                            efficiency_diff = (least_efficient['Average Fuel Used'] - most_efficient['Average Fuel Used'])
                            efficiency_percent = (efficiency_diff / least_efficient['Average Fuel Used']) * 100
                            
                            st.info(f"For the route {selected_route_for_comparison}, aircraft {most_efficient['Aircraft']} is the most fuel-efficient, using {efficiency_diff:.0f}L ({efficiency_percent:.1f}%) less fuel than {least_efficient['Aircraft']}.")
                        else:
                            st.warning(f"No comparison data available for {selected_route_for_comparison}")
                    else:
                        st.warning("No routes with multiple aircraft available for comparison.")
                        
                    # Planned vs Actual fuel usage by aircraft
                    if 'planned_fuel_usage' in df_filtered.columns:
                        st.subheader("Planned vs Actual Fuel Usage by Aircraft")
                        
                        fuel_comparison = df_filtered.groupby('registration').agg({
                            'fuel_used': 'mean',
                            'planned_fuel_usage': 'mean'
                        }).reset_index()
                        
                        fuel_comparison['difference'] = ((fuel_comparison['fuel_used'] - fuel_comparison['planned_fuel_usage']) / 
                                                        fuel_comparison['planned_fuel_usage'] * 100)
                        fuel_comparison.columns = ['Aircraft', 'Actual Fuel Used', 'Planned Fuel Usage', 'Difference (%)']
                        
                        # Sort by efficiency (smallest difference first)
                        fuel_comparison = fuel_comparison.sort_values('Difference (%)')
                        
                        # Create a plot
                        fig3 = go.Figure()
                        
                        for i, row in fuel_comparison.iterrows():
                            color = 'green' if row['Difference (%)'] <= 0 else 'red'
                            
                            fig3.add_trace(go.Bar(
                                x=[row['Aircraft']],
                                y=[row['Difference (%)']],
                                name=row['Aircraft'],
                                marker_color=color
                            ))
                        
                        fig3.update_layout(
                            title="Fuel Usage Variance from Plan by Aircraft (%)",
                            xaxis_title="Aircraft Registration",
                            yaxis_title="Variance from Planned Usage (%)",
                            showlegend=False
                        )
                        
                        fig3.add_hline(y=0, line_width=1, line_dash="dash", line_color="black")
                        
                        st.plotly_chart(fig3, use_container_width=True)
                        
                        # Show data table
                        st.dataframe(fuel_comparison, use_container_width=True)
                else:
                    st.warning("Required fuel usage or aircraft data is not available in the selected dataset.")
            
            with tab3:
                st.header("Fuel Consumption Trends Over Time")
                
                if all(col in df_filtered.columns for col in ['fuel_used', 'flight_date']):
                    # Create time series analysis
                    time_grouping = st.selectbox(
                        "Group By",
                        options=["Day", "Week", "Month"],
                        index=0
                    )
                    
                    # Group data by time
                    if time_grouping == "Day":
                        df_filtered['time_group'] = df_filtered['flight_date'].dt.date
                    elif time_grouping == "Week":
                        df_filtered['time_group'] = df_filtered['flight_date'].dt.to_period('W').apply(lambda x: x.start_time.date())
                    else:  # Month
                        df_filtered['time_group'] = df_filtered['flight_date'].dt.to_period('M').apply(lambda x: x.start_time.date())
                    
                    # Calculate average fuel used per time group
                    time_fuel = df_filtered.groupby('time_group')['fuel_used'].mean().reset_index()
                    time_fuel.columns = ['Date', 'Average Fuel Used']
                    
                    # Plot the trend
                    fig4 = px.line(
                        time_fuel,
                        x='Date',
                        y='Average Fuel Used',
                        markers=True,
                        title=f"Average Fuel Consumption Trend by {time_grouping}"
                    )
                    
                    fig4.update_layout(
                        xaxis_title=time_grouping,
                        yaxis_title="Average Fuel Used (L)"
                    )
                    
                    st.plotly_chart(fig4, use_container_width=True)
                    
                    # Add trend analysis
                    if len(time_fuel) > 1:
                        first_value = time_fuel['Average Fuel Used'].iloc[0]
                        last_value = time_fuel['Average Fuel Used'].iloc[-1]
                        percent_change = ((last_value - first_value) / first_value) * 100
                        
                        trend_direction = "increased" if percent_change > 0 else "decreased"
                        
                        st.info(f"Fuel consumption has {trend_direction} by {abs(percent_change):.1f}% from the first to the last period.")
                    
                    # Show the raw data
                    st.subheader(f"Fuel Consumption Data by {time_grouping}")
                    st.dataframe(time_fuel.sort_values('Date', ascending=False), use_container_width=True)
                else:
                    st.warning("Required fuel usage or date data is not available in the selected dataset.")

except Exception as e:
    st.error(f"Error: {e}")
    st.error("Please check your data connection and try again.")