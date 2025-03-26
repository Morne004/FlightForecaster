# pages/route_analysis.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import get_flight_data, format_route
from datetime import timedelta

# Page configuration
st.set_page_config(
    page_title="Route Analysis | Flight Analysis",
    page_icon="✈️",
    layout="wide"
)

# Header
st.title("🛫 Route Analysis")
st.markdown("Analyze on-time performance and flight times between destinations")

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
        
        # Add route column
        df['route'] = df.apply(lambda row: format_route(row['origin_code'], row['destination_code']), axis=1)
        
        # Sidebar filters
        st.sidebar.header("Filters")
        
        # Get unique routes
        all_routes = sorted(df['route'].unique())
        
        selected_routes = st.sidebar.multiselect(
            "Select Routes",
            options=all_routes,
            default=all_routes[:5] if len(all_routes) > 5 else all_routes
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
            df_filtered = df_filtered[df_filtered['route'].isin(selected_routes)]
        
        # Main content - Tabs
        tab1, tab2, tab3 = st.tabs(["On-Time Performance", "Flight Times", "Route Frequency"])
        
        with tab1:
            st.header("On-Time Performance by Route")
            
            if 'is_delayed' in df_filtered.columns:
                # Calculate on-time performance by route
                route_performance = df_filtered.groupby('route')['is_delayed'].agg(
                    on_time=lambda x: (x == False).mean() * 100,
                    total_flights=lambda x: len(x)
                ).reset_index()
                
                # Add count of on-time flights
                route_performance['on_time_count'] = route_performance.apply(
                    lambda row: int(row['total_flights'] * (row['on_time'] / 100)),
                    axis=1
                )
                
                # Sort by on-time percentage
                route_performance = route_performance.sort_values('on_time', ascending=False)
                
                # Create the chart
                fig1 = px.bar(
                    route_performance,
                    x='route',
                    y='on_time',
                    color='on_time',
                    color_continuous_scale=px.colors.sequential.Greens,
                    hover_data=['total_flights', 'on_time_count'],
                    labels={
                        'route': 'Route',
                        'on_time': 'On-Time Percentage (%)',
                        'total_flights': 'Total Flights',
                        'on_time_count': 'On-Time Flights'
                    },
                    title="On-Time Performance by Route"
                )
                
                fig1.update_layout(
                    xaxis_title="Route",
                    yaxis_title="On-Time Percentage (%)",
                    coloraxis_showscale=False
                )
                
                # Add target line at 90%
                fig1.add_hline(
                    y=90, 
                    line_dash="dash", 
                    line_color="red",
                    annotation_text="Target (90%)",
                    annotation_position="bottom right"
                )
                
                st.plotly_chart(fig1, use_container_width=True)
                
                # Add insights
                best_route = route_performance.iloc[0]
                worst_route = route_performance.iloc[-1]
                
                st.subheader("Insights")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric(
                        "Best Performing Route",
                        best_route['route'],
                        f"{best_route['on_time']:.1f}% On-Time"
                    )
                
                with col2:
                    st.metric(
                        "Route Needing Improvement",
                        worst_route['route'],
                        f"{worst_route['on_time']:.1f}% On-Time"
                    )
                
                # Detailed table
                st.subheader("On-Time Performance Details")
                
                # Add delay minutes if available
                if 'delay_minutes' in df_filtered.columns:
                    delay_by_route = df_filtered.groupby('route')['delay_minutes'].mean().reset_index()
                    delay_by_route.columns = ['route', 'avg_delay_minutes']
                    
                    route_performance = pd.merge(route_performance, delay_by_route, on='route', how='left')
                    route_performance['avg_delay_minutes'] = route_performance['avg_delay_minutes'].fillna(0)
                
                # Format for display
                display_df = route_performance.copy()
                display_df['on_time'] = display_df['on_time'].apply(lambda x: f"{x:.1f}%")
                
                if 'avg_delay_minutes' in display_df.columns:
                    display_df['avg_delay_minutes'] = display_df['avg_delay_minutes'].apply(lambda x: f"{x:.1f} min")
                    display_df.columns = ['Route', 'On-Time %', 'Total Flights', 'On-Time Flights', 'Avg Delay']
                else:
                    display_df.columns = ['Route', 'On-Time %', 'Total Flights', 'On-Time Flights']
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.warning("Delay information is not available in the dataset.")
        
        with tab2:
            st.header("Average Flight Times by Route")
            
            if all(col in df_filtered.columns for col in ['scheduled_departure', 'scheduled_arrival', 'actual_departure', 'actual_arrival']):
                # Process time columns
                time_cols = ['scheduled_departure', 'scheduled_arrival', 'actual_departure', 'actual_arrival']
                
                # Calculate flight duration
                def calculate_duration_minutes(row, start_col, end_col):
                    try:
                        if pd.isna(row[start_col]) or pd.isna(row[end_col]):
                            return None
                        
                        start = pd.to_datetime(row[start_col]) if isinstance(row[start_col], str) else row[start_col]
                        end = pd.to_datetime(row[end_col]) if isinstance(row[end_col], str) else row[end_col]
                        
                        if isinstance(start, timedelta) and isinstance(end, timedelta):
                            # Handle time deltas
                            if end < start:  # Flight crosses midnight
                                return (end + timedelta(days=1) - start).total_seconds() / 60
                            else:
                                return (end - start).total_seconds() / 60
                        else:
                            # Handle timestamps
                            return (end - start).total_seconds() / 60
                    except:
                        return None
                
                # Calculate scheduled and actual duration
                df_filtered['scheduled_duration'] = df_filtered.apply(
                    lambda row: calculate_duration_minutes(row, 'scheduled_departure', 'scheduled_arrival'),
                    axis=1
                )
                
                df_filtered['actual_duration'] = df_filtered.apply(
                    lambda row: calculate_duration_minutes(row, 'actual_departure', 'actual_arrival'),
                    axis=1
                )
                
                # Group by route
                route_times = df_filtered.groupby('route').agg({
                    'scheduled_duration': 'mean',
                    'actual_duration': 'mean',
                    'flight_number_full': 'count'
                }).reset_index()
                
                route_times.columns = ['route', 'avg_scheduled_duration', 'avg_actual_duration', 'total_flights']
                
                # Filter out routes with missing data
                route_times = route_times.dropna(subset=['avg_scheduled_duration', 'avg_actual_duration'])
                
                if not route_times.empty:
                    # Calculate difference
                    route_times['duration_difference'] = route_times['avg_actual_duration'] - route_times['avg_scheduled_duration']
                    
                    # Sort by route
                    route_times = route_times.sort_values('route')
                    
                    # Create bar chart
                    fig2 = go.Figure()
                    
                    fig2.add_trace(go.Bar(
                        x=route_times['route'],
                        y=route_times['avg_scheduled_duration'],
                        name='Scheduled Duration',
                        marker_color='lightblue'
                    ))
                    
                    fig2.add_trace(go.Bar(
                        x=route_times['route'],
                        y=route_times['avg_actual_duration'],
                        name='Actual Duration',
                        marker_color='darkblue'
                    ))
                    
                    fig2.update_layout(
                        title="Average Flight Duration by Route",
                        xaxis_title="Route",
                        yaxis_title="Duration (minutes)",
                        barmode='group',
                        legend_title="Duration Type"
                    )
                    
                    st.plotly_chart(fig2, use_container_width=True)
                    
                    # Display average time difference
                    st.subheader("Flight Time Analysis")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Find fastest and slowest routes
                        fastest_route = route_times.iloc[route_times['avg_actual_duration'].idxmin()]
                        
                        st.metric(
                            "Fastest Route",
                            fastest_route['route'],
                            f"{fastest_route['avg_actual_duration']:.0f} min"
                        )
                    
                    with col2:
                        # Find most accurate schedule
                        most_accurate = route_times.iloc[abs(route_times['duration_difference']).idxmin()]
                        
                        st.metric(
                            "Most Accurate Schedule",
                            most_accurate['route'],
                            f"Diff: {abs(most_accurate['duration_difference']):.1f} min"
                        )
                    
                    # Detailed table
                    st.subheader("Flight Time Details")
                    
                    # Format for display
                    display_df = route_times.copy()
                    display_df['avg_scheduled_duration'] = display_df['avg_scheduled_duration'].apply(lambda x: f"{x:.0f} min")
                    display_df['avg_actual_duration'] = display_df['avg_actual_duration'].apply(lambda x: f"{x:.0f} min")
                    display_df['duration_difference'] = display_df['duration_difference'].apply(
                        lambda x: f"+{x:.1f} min" if x > 0 else f"{x:.1f} min"
                    )
                    
                    display_df.columns = ['Route', 'Avg Scheduled Duration', 'Avg Actual Duration', 'Total Flights', 'Duration Difference']
                    
                    st.dataframe(display_df, use_container_width=True)
                else:
                    st.warning("No valid flight duration data available for the selected routes.")
            else:
                st.warning("Flight time information is not available in the dataset.")
        
        with tab3:
            st.header("Most Frequent Routes")
            
            # Calculate route frequencies
            route_freq = df_filtered['route'].value_counts().reset_index()
            route_freq.columns = ['route', 'frequency']
            
            # Sort by frequency
            route_freq = route_freq.sort_values('frequency', ascending=False)
            
            # Create the chart
            fig3 = px.bar(
                route_freq,
                x='route',
                y='frequency',
                color='frequency',
                color_continuous_scale=px.colors.sequential.Blues,
                title="Route Frequency"
            )
            
            fig3.update_layout(
                xaxis_title="Route",
                yaxis_title="Number of Flights",
                coloraxis_showscale=False
            )
            
            st.plotly_chart(fig3, use_container_width=True)
            
            # Show route distribution pie chart
            st.subheader("Route Distribution")
            
            # Calculate percentages
            total_flights = route_freq['frequency'].sum()
            route_freq['percentage'] = (route_freq['frequency'] / total_flights * 100).round(1)
            
            # Take top 5 routes and group the rest as "Other"
            top_routes = route_freq.head(5).copy()
            other_routes = route_freq.iloc[5:].copy() if len(route_freq) > 5 else None
            
            if other_routes is not None and not other_routes.empty:
                other_sum = pd.DataFrame({
                    'route': ['Other Routes'],
                    'frequency': [other_routes['frequency'].sum()],
                    'percentage': [other_routes['percentage'].sum()]
                })
                
                pie_data = pd.concat([top_routes, other_sum])
            else:
                pie_data = top_routes
            
            # Add percentage to labels
            pie_data['route_label'] = pie_data.apply(lambda row: f"{row['route']} ({row['percentage']}%)", axis=1)
            
            # Create pie chart
            fig4 = px.pie(
                pie_data,
                values='frequency',
                names='route_label',
                title="Distribution of Flights by Route",
                hole=0.4,
                color_discrete_sequence=px.colors.sequential.Blues
            )
            
            fig4.update_traces(textposition='inside', textinfo='percent+label')
            
            st.plotly_chart(fig4, use_container_width=True)
            
            # Detailed table
            st.subheader("Route Frequency Details")
            
            # Format for display
            display_df = route_freq.copy()
            display_df['percentage'] = display_df['percentage'].apply(lambda x: f"{x:.1f}%")
            
            display_df.columns = ['Route', 'Number of Flights', 'Percentage']
            
            st.dataframe(display_df, use_container_width=True)
            
            # Route growth over time (if date data is available)
            if 'flight_date' in df_filtered.columns:
                st.subheader("Route Growth Over Time")
                
                # Select time period
                time_period = st.selectbox(
                    "Group By",
                    options=["Day", "Week", "Month"],
                    index=1
                )
                
                # Get top 3 routes for trend analysis
                top_3_routes = route_freq.head(3)['route'].tolist()
                
                # Filter to top 3 routes
                top_routes_df = df_filtered[df_filtered['route'].isin(top_3_routes)]
                
                if not top_routes_df.empty:
                    # Group by time period and route
                    if time_period == "Day":
                        top_routes_df['time_group'] = top_routes_df['flight_date'].dt.date
                    elif time_period == "Week":
                        top_routes_df['time_group'] = top_routes_df['flight_date'].dt.to_period('W').apply(lambda x: x.start_time.date())
                    else:  # Month
                        top_routes_df['time_group'] = top_routes_df['flight_date'].dt.to_period('M').apply(lambda x: x.start_time.date())
                    
                    # Count flights by time period and route
                    route_trends = top_routes_df.groupby(['time_group', 'route']).size().reset_index(name='count')
                    
                    # Create line chart
                    fig5 = px.line(
                        route_trends,
                        x='time_group',
                        y='count',
                        color='route',
                        markers=True,
                        title=f"Trend of Top Routes by {time_period}"
                    )
                    
                    fig5.update_layout(
                        xaxis_title=time_period,
                        yaxis_title="Number of Flights",
                        legend_title="Route"
                    )
                    
                    st.plotly_chart(fig5, use_container_width=True)
                else:
                    st.warning("No trend data available for the top routes.")
            else:
                st.info("Date information is required to analyze route growth over time.")

except Exception as e:
    st.error(f"Error: {e}")
    st.error("Please check your data connection and try again.")
