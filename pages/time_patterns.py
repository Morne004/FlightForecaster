# pages/time_patterns.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import get_flight_data
import numpy as np
from datetime import time

# Page configuration
st.set_page_config(
    page_title="Time Patterns | Flight Analysis",
    page_icon="✈️",
    layout="wide"
)

# Header
st.title("⏰ Time-Based Flight Patterns")
st.markdown("Analyze flight patterns by time of day, day of week, and seasonal trends")

# Load the data
try:
    with st.spinner("Loading flight data..."):
        df = get_flight_data()
        
    if df.empty:
        st.error("No data available. Please check your connection to Supabase.")
    else:
        # Process date and time data
        if 'flight_date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['flight_date']):
            df['flight_date'] = pd.to_datetime(df['flight_date'])
        
        # Convert time columns to datetime if they're strings or timedeltas
        time_cols = ['scheduled_departure', 'actual_departure', 'scheduled_arrival', 'actual_arrival']
        
        for col in time_cols:
            if col in df.columns:
                if df[col].dtype == 'object':  # If it's a string
                    try:
                        df[col] = pd.to_datetime(df[col]).dt.time
                    except:
                        pass
                elif hasattr(df[col].iloc[0], 'seconds'):  # If it's a timedelta
                    try:
                        df[col] = df[col].apply(lambda x: (time(hour=int(x.seconds // 3600), 
                                                              minute=int((x.seconds % 3600) // 60))))
                    except:
                        pass
        
        # Extract time components if we have date columns
        if 'flight_date' in df.columns:
            df['day_of_week'] = df['flight_date'].dt.day_name()
            df['month'] = df['flight_date'].dt.month_name()
            df['week_of_year'] = df['flight_date'].dt.isocalendar().week
        
        # Extract hour from departure time if available
        if 'scheduled_departure' in df.columns:
            if hasattr(df['scheduled_departure'].iloc[0], 'hour'):
                df['departure_hour'] = df['scheduled_departure'].apply(lambda x: x.hour if pd.notna(x) else None)
            else:
                # Try to extract hour from string or other formats
                try:
                    df['departure_hour'] = pd.to_datetime(df['scheduled_departure']).dt.hour
                except:
                    df['departure_hour'] = None
        
        # Sidebar filters
        st.sidebar.header("Filters")
        
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
        
        # Filter by route
        all_routes = []
        for _, row in df_filtered[['origin_code', 'destination_code']].drop_duplicates().iterrows():
            all_routes.append(f"{row['origin_code']} → {row['destination_code']}")
        
        selected_routes = st.sidebar.multiselect(
            "Select Routes",
            options=sorted(all_routes),
            default=[]
        )
        
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
        
        # Main content - Tabs
        tab1, tab2, tab3 = st.tabs(["Time of Day", "Day of Week", "Monthly Patterns"])
        
        with tab1:
            st.header("Flight Patterns by Time of Day")
            
            if 'departure_hour' in df_filtered.columns and not df_filtered['departure_hour'].isna().all():
                # Group flights by hour
                hour_counts = df_filtered['departure_hour'].value_counts().sort_index().reset_index()
                hour_counts.columns = ['Hour', 'Number of Flights']
                
                # Create time of day categories
                def time_category(hour):
                    if 5 <= hour <= 8:
                        return "Early Morning (5-8)"
                    elif 9 <= hour <= 11:
                        return "Morning (9-11)"
                    elif 12 <= hour <= 15:
                        return "Afternoon (12-15)"
                    elif 16 <= hour <= 19:
                        return "Evening (16-19)"
                    elif 20 <= hour <= 23:
                        return "Night (20-23)"
                    else:
                        return "Late Night (0-4)"
                
                hour_counts['Time of Day'] = hour_counts['Hour'].apply(time_category)
                
                # Create hour chart
                fig1 = px.bar(
                    hour_counts,
                    x='Hour',
                    y='Number of Flights',
                    color='Time of Day',
                    title="Flight Distribution by Hour of Day",
                    labels={'Hour': 'Hour of Day (24h)', 'Number of Flights': 'Number of Flights'},
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                
                fig1.update_layout(
                    xaxis=dict(
                        tickmode='array',
                        tickvals=list(range(24)),
                        ticktext=[f"{h:02d}:00" for h in range(24)]
                    ),
                    bargap=0.1
                )
                
                st.plotly_chart(fig1, use_container_width=True)
                
                # Time of day distribution
                time_of_day = df_filtered['departure_hour'].apply(time_category).value_counts().reset_index()
                time_of_day.columns = ['Time of Day', 'Number of Flights']
                
                # Create custom sort order
                time_order = [
                    "Early Morning (5-8)",
                    "Morning (9-11)",
                    "Afternoon (12-15)",
                    "Evening (16-19)",
                    "Night (20-23)",
                    "Late Night (0-4)"
                ]
                
                time_of_day['sort_order'] = time_of_day['Time of Day'].apply(lambda x: time_order.index(x))
                time_of_day = time_of_day.sort_values('sort_order')
                
                # Create time category chart
                fig2 = px.pie(
                    time_of_day,
                    values='Number of Flights',
                    names='Time of Day',
                    title="Distribution of Flights by Time of Day",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                
                fig2.update_traces(textposition='inside', textinfo='percent+label')
                
                st.plotly_chart(fig2, use_container_width=True)
                
                # Peak hours analysis
                st.subheader("Peak Hours Analysis")
                
                peak_hour = hour_counts.iloc[hour_counts['Number of Flights'].idxmax()]
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric(
                        "Peak Hour",
                        f"{int(peak_hour['Hour']):02d}:00",
                        f"{peak_hour['Number of Flights']} flights"
                    )
                
                with col2:
                    busiest_period = time_of_day.iloc[time_of_day['Number of Flights'].idxmax()]
                    
                    st.metric(
                        "Busiest Time Period",
                        busiest_period['Time of Day'],
                        f"{busiest_period['Number of Flights']} flights"
                    )
                
                # On-time performance by hour if data is available
                if 'is_delayed' in df_filtered.columns:
                    st.subheader("On-Time Performance by Hour")
                    
                    hour_performance = df_filtered.groupby('departure_hour')['is_delayed'].agg(
                        on_time=lambda x: (x == False).mean() * 100,
                        total_flights=lambda x: len(x)
                    ).reset_index()
                    
                    # Sort by hour
                    hour_performance = hour_performance.sort_values('departure_hour')
                    
                    # Create chart
                    fig3 = px.line(
                        hour_performance,
                        x='departure_hour',
                        y='on_time',
                        markers=True,
                        title="On-Time Performance by Hour of Day",
                        labels={
                            'departure_hour': 'Hour of Day (24h)',
                            'on_time': 'On-Time Percentage (%)'
                        }
                    )
                    
                    fig3.update_layout(
                        xaxis=dict(
                            tickmode='array',
                            tickvals=list(range(24)),
                            ticktext=[f"{h:02d}:00" for h in range(24)]
                        ),
                        yaxis=dict(
                            range=[
                                max(0, hour_performance['on_time'].min() - 5),
                                min(100, hour_performance['on_time'].max() + 5)
                            ]
                        )
                    )
                    
                    # Add target line
                    fig3.add_hline(
                        y=90,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="Target (90%)",
                        annotation_position="bottom right"
                    )
                    
                    st.plotly_chart(fig3, use_container_width=True)
            else:
                st.warning("Departure time information is not available or could not be processed in the dataset.")
        
        with tab2:
            st.header("Flight Patterns by Day of Week")
            
            if 'day_of_week' in df_filtered.columns and not df_filtered['day_of_week'].isna().all():
                # Define day of week order
                dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                
                # Group flights by day of week
                day_counts = df_filtered['day_of_week'].value_counts().reset_index()
                day_counts.columns = ['Day of Week', 'Number of Flights']
                
                # Ensure proper sorting
                day_counts['sort_order'] = day_counts['Day of Week'].apply(lambda x: dow_order.index(x))
                day_counts = day_counts.sort_values('sort_order')
                
                # Create day of week chart
                fig4 = px.bar(
                    day_counts,
                    x='Day of Week',
                    y='Number of Flights',
                    color='Number of Flights',
                    color_continuous_scale=px.colors.sequential.Blues,
                    title="Flight Distribution by Day of Week",
                    category_orders={"Day of Week": dow_order}
                )
                
                fig4.update_layout(
                    xaxis_title="Day of Week",
                    yaxis_title="Number of Flights",
                    coloraxis_showscale=False
                )
                
                st.plotly_chart(fig4, use_container_width=True)
                
                # Weekday vs Weekend comparison
                st.subheader("Weekday vs Weekend Comparison")
                
                df_filtered['is_weekend'] = df_filtered['day_of_week'].apply(lambda x: x in ['Saturday', 'Sunday'])
                weekend_comparison = df_filtered.groupby('is_weekend').size().reset_index()
                weekend_comparison.columns = ['is_weekend', 'count']
                weekend_comparison['category'] = weekend_comparison['is_weekend'].apply(lambda x: 'Weekend' if x else 'Weekday')
                
                # Calculate percentages
                total = weekend_comparison['count'].sum()
                weekend_comparison['percentage'] = (weekend_comparison['count'] / total * 100).round(1)
                weekend_comparison['label'] = weekend_comparison.apply(lambda row: f"{row['category']} ({row['percentage']}%)", axis=1)
                
                # Create pie chart
                fig5 = px.pie(
                    weekend_comparison,
                    values='count',
                    names='label',
                    title="Weekday vs Weekend Flight Distribution",
                    color='category',
                    color_discrete_map={'Weekday': 'royalblue', 'Weekend': 'lightblue'},
                    hole=0.4
                )
                
                fig5.update_traces(textposition='inside', textinfo='percent+label')
                
                st.plotly_chart(fig5, use_container_width=True)
                
                # On-time performance by day of week if data is available
                if 'is_delayed' in df_filtered.columns:
                    st.subheader("On-Time Performance by Day of Week")
                    
                    day_performance = df_filtered.groupby('day_of_week')['is_delayed'].agg(
                        on_time=lambda x: (x == False).mean() * 100,
                        total_flights=lambda x: len(x)
                    ).reset_index()
                    
                    # Ensure proper sorting
                    day_performance['sort_order'] = day_performance['day_of_week'].apply(lambda x: dow_order.index(x))
                    day_performance = day_performance.sort_values('sort_order')
                    
                    # Create chart
                    fig6 = px.bar(
                        day_performance,
                        x='day_of_week',
                        y='on_time',
                        color='on_time',
                        color_continuous_scale=px.colors.sequential.Greens,
                        title="On-Time Performance by Day of Week",
                        labels={
                            'day_of_week': 'Day of Week',
                            'on_time': 'On-Time Percentage (%)'
                        },
                        category_orders={"day_of_week": dow_order}
                    )
                    
                    fig6.update_layout(
                        xaxis_title="Day of Week",
                        yaxis_title="On-Time Percentage (%)",
                        coloraxis_showscale=False
                    )
                    
                    # Add target line
                    fig6.add_hline(
                        y=90,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="Target (90%)",
                        annotation_position="bottom right"
                    )
                    
                    st.plotly_chart(fig6, use_container_width=True)
            else:
                st.warning("Day of week information is not available in the dataset.")
        
        with tab3:
            st.header("Monthly and Seasonal Flight Patterns")
            
            if 'month' in df_filtered.columns and not df_filtered['month'].isna().all():
                # Define month order
                month_order = [
                    'January', 'February', 'March', 'April', 'May', 'June',
                    'July', 'August', 'September', 'October', 'November', 'December'
                ]
                
                # Group flights by month
                month_counts = df_filtered['month'].value_counts().reset_index()
                month_counts.columns = ['Month', 'Number of Flights']
                
                # Ensure proper sorting
                month_counts['sort_order'] = month_counts['Month'].apply(lambda x: month_order.index(x))
                month_counts = month_counts.sort_values('sort_order')
                
                # Create month chart
                fig7 = px.bar(
                    month_counts,
                    x='Month',
                    y='Number of Flights',
                    color='Number of Flights',
                    color_continuous_scale=px.colors.sequential.Blues,
                    title="Flight Distribution by Month",
                    category_orders={"Month": month_order}
                )
                
                fig7.update_layout(
                    xaxis_title="Month",
                    yaxis_title="Number of Flights",
                    coloraxis_showscale=False
                )
                
                st.plotly_chart(fig7, use_container_width=True)
                
                # Seasonal analysis
                st.subheader("Seasonal Flight Patterns")
                
                # Define seasons (Southern Hemisphere)
                def get_season(month):
                    if month in ['December', 'January', 'February']:
                        return 'Summer'
                    elif month in ['March', 'April', 'May']:
                        return 'Autumn'
                    elif month in ['June', 'July', 'August']:
                        return 'Winter'
                    else:  # September, October, November
                        return 'Spring'
                
                df_filtered['season'] = df_filtered['month'].apply(get_season)
                
                season_order = ['Summer', 'Autumn', 'Winter', 'Spring']
                
                season_counts = df_filtered['season'].value_counts().reset_index()
                season_counts.columns = ['Season', 'Number of Flights']
                
                # Ensure proper sorting
                season_counts['sort_order'] = season_counts['Season'].apply(lambda x: season_order.index(x))
                season_counts = season_counts.sort_values('sort_order')
                
                # Create pie chart
                fig8 = px.pie(
                    season_counts,
                    values='Number of Flights',
                    names='Season',
                    title="Seasonal Distribution of Flights",
                    color='Season',
                    color_discrete_sequence=px.colors.qualitative.Set2,
                    hole=0.4
                )
                
                fig8.update_traces(textposition='inside', textinfo='percent+label')
                
                st.plotly_chart(fig8, use_container_width=True)
                
                # On-time performance by month if data is available
                if 'is_delayed' in df_filtered.columns:
                    st.subheader("Monthly On-Time Performance")
                    
                    month_performance = df_filtered.groupby('month')['is_delayed'].agg(
                        on_time=lambda x: (x == False).mean() * 100,
                        total_flights=lambda x: len(x)
                    ).reset_index()
                    
                    # Ensure proper sorting
                    month_performance['sort_order'] = month_performance['month'].apply(lambda x: month_order.index(x))
                    month_performance = month_performance.sort_values('sort_order')
                    
                    # Create chart
                    fig9 = px.line(
                        month_performance,
                        x='month',
                        y='on_time',
                        markers=True,
                        title="On-Time Performance by Month",
                        labels={
                            'month': 'Month',
                            'on_time': 'On-Time Percentage (%)'
                        },
                        category_orders={"month": month_order}
                    )
                    
                    fig9.update_layout(
                        xaxis_title="Month",
                        yaxis_title="On-Time Percentage (%)"
                    )
                    
                    # Add target line
                    fig9.add_hline(
                        y=90,
                        line_dash="dash",
                        line_color="red",
                        annotation_text="Target (90%)",
                        annotation_position="bottom right"
                    )
                    
                    st.plotly_chart(fig9, use_container_width=True)
                
                # Detailed table with monthly stats
                st.subheader("Monthly Flight Statistics")
                
                # Calculate additional stats by month
                monthly_stats = df_filtered.groupby('month').agg({
                    'flight_number_full': 'count',
                }).reset_index()
                
                monthly_stats.columns = ['Month', 'Total Flights']
                
                # Add on-time percentage if available
                if 'is_delayed' in df_filtered.columns:
                    on_time_by_month = df_filtered.groupby('month')['is_delayed'].apply(
                        lambda x: (x == False).mean() * 100
                    ).reset_index()
                    on_time_by_month.columns = ['Month', 'On-Time Percentage']
                    
                    monthly_stats = pd.merge(monthly_stats, on_time_by_month, on='Month', how='left')
                
                # Add fuel data if available
                if 'fuel_used' in df_filtered.columns:
                    fuel_by_month = df_filtered.groupby('month')['fuel_used'].mean().reset_index()
                    fuel_by_month.columns = ['Month', 'Avg Fuel Used']
                    
                    monthly_stats = pd.merge(monthly_stats, fuel_by_month, on='Month', how='left')
                
                # Sort by month order
                monthly_stats['sort_order'] = monthly_stats['Month'].apply(lambda x: month_order.index(x))
                monthly_stats = monthly_stats.sort_values('sort_order')
                
                # Format for display
                display_df = monthly_stats.drop(columns=['sort_order']).copy()
                
                if 'On-Time Percentage' in display_df.columns:
                    display_df['On-Time Percentage'] = display_df['On-Time Percentage'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                
                if 'Avg Fuel Used' in display_df.columns:
                    display_df['Avg Fuel Used'] = display_df['Avg Fuel Used'].apply(lambda x: f"{x:.0f} L" if pd.notna(x) else "N/A")
                
                st.dataframe(display_df, use_container_width=True)
            else:
                st.warning("Month information is not available in the dataset.")
            
            # Weekly trends if we have week data
            if 'week_of_year' in df_filtered.columns and 'flight_date' in df_filtered.columns:
                st.subheader("Weekly Flight Trends")
                
                # Group by week
                weekly_counts = df_filtered.groupby('week_of_year').size().reset_index()
                weekly_counts.columns = ['Week', 'Number of Flights']
                
                # Sort by week
                weekly_counts = weekly_counts.sort_values('Week')
                
                # Create chart
                fig10 = px.line(
                    weekly_counts,
                    x='Week',
                    y='Number of Flights',
                    markers=True,
                    title="Weekly Flight Trend"
                )
                
                fig10.update_layout(
                    xaxis_title="Week of Year",
                    yaxis_title="Number of Flights"
                )
                
                st.plotly_chart(fig10, use_container_width=True)
                
                # Calculate moving average
                if len(weekly_counts) > 4:
                    weekly_counts['4_Week_Avg'] = weekly_counts['Number of Flights'].rolling(window=4).mean()
                    
                    fig11 = go.Figure()
                    
                    fig11.add_trace(go.Scatter(
                        x=weekly_counts['Week'],
                        y=weekly_counts['Number of Flights'],
                        mode='lines+markers',
                        name='Weekly Flights'
                    ))
                    
                    fig11.add_trace(go.Scatter(
                        x=weekly_counts['Week'],
                        y=weekly_counts['4_Week_Avg'],
                        mode='lines',
                        name='4-Week Moving Average',
                        line=dict(color='red', dash='dash')
                    ))
                    
                    fig11.update_layout(
                        title="Weekly Flight Trend with Moving Average",
                        xaxis_title="Week of Year",
                        yaxis_title="Number of Flights",
                        legend_title="Metric"
                    )
                    
                    st.plotly_chart(fig11, use_container_width=True)

except Exception as e:
    st.error(f"Error: {e}")
    st.error("Please check your data connection and try again.")