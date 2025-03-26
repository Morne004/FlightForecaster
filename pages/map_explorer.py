# pages/map_explorer.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import get_flight_data
from config import AIRPORT_COORDINATES

# Page configuration
st.set_page_config(
    page_title="Map Explorer | Flight Analysis",
    page_icon="✈️",
    layout="wide"
)

# Header
st.title("🗺️ Interactive Flight Map Explorer")
st.markdown("Visualize flight routes, frequencies, and metrics on an interactive map")

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
        
        # Sidebar filters
        st.sidebar.header("Map Filters")
        
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
        
        # Filter by airports
        all_airports = sorted(list(set(df_filtered['origin_code'].unique()) | set(df_filtered['destination_code'].unique())))
        
        selected_airports = st.sidebar.multiselect(
            "Filter by Airports",
            options=all_airports,
            default=[]
        )
        
        if selected_airports:
            df_filtered = df_filtered[
                (df_filtered['origin_code'].isin(selected_airports)) | 
                (df_filtered['destination_code'].isin(selected_airports))
            ]
        
        # Create a DataFrame of routes and their frequencies
        route_counts = df_filtered.groupby(['origin_code', 'destination_code']).size().reset_index(name='frequency')
        
        # Ensure we have the coordinates for all airports
        valid_airports = set(AIRPORT_COORDINATES.keys())
        route_counts = route_counts[
            (route_counts['origin_code'].isin(valid_airports)) & 
            (route_counts['destination_code'].isin(valid_airports))
        ]
        
        if route_counts.empty:
            st.error("No valid routes found with the current filters.")
        else:
            # Map visualization options
            st.sidebar.header("Map Options")
            
            map_metric = st.sidebar.selectbox(
                "Color Routes By",
                options=["Flight Frequency", "On-Time Performance", "Fuel Efficiency"],
                index=0
            )
            
            map_style = st.sidebar.selectbox(
                "Map Background",
                options=["Light", "Dark", "Satellite"],
                index=0
            )
            
            # Convert map style selection to appropriate colors
            if map_style == "Light":
                land_color = 'rgb(243, 243, 243)'
                ocean_color = 'rgb(230, 230, 250)'
                country_color = 'rgb(204, 204, 204)'
            elif map_style == "Dark":
                land_color = 'rgb(50, 50, 50)'
                ocean_color = 'rgb(20, 20, 30)'
                country_color = 'rgb(90, 90, 90)'
            else:  # Satellite
                land_color = 'rgb(68, 84, 106)'
                ocean_color = 'rgb(52, 62, 77)'
                country_color = 'rgb(150, 150, 150)'
            
            # Main content - Tabs
            tab1, tab2 = st.tabs(["Route Map", "Airport Statistics"])
            
            with tab1:
                st.header("Flight Route Visualization")
                
                # Prepare map data
                map_data = []
                max_frequency = route_counts['frequency'].max()
                
                for _, row in route_counts.iterrows():
                    origin = row['origin_code']
                    destination = row['destination_code']
                    frequency = row['frequency']
                    
                    if origin in AIRPORT_COORDINATES and destination in AIRPORT_COORDINATES:
                        origin_coords = AIRPORT_COORDINATES[origin]
                        dest_coords = AIRPORT_COORDINATES[destination]
                        
                        # Calculate width based on frequency
                        width = 1 + (frequency / max_frequency * 5)
                        
                        # Add path data
                        path_data = {
                            'origin': origin,
                            'destination': destination,
                            'origin_lat': origin_coords['lat'],
                            'origin_lon': origin_coords['lon'],
                            'dest_lat': dest_coords['lat'],
                            'dest_lon': dest_coords['lon'],
                            'frequency': frequency,
                            'width': width
                        }
                        
                        # Add metrics based on selection
                        if map_metric == "On-Time Performance":
                            if 'is_delayed' in df_filtered.columns:
                                route_df = df_filtered[
                                    (df_filtered['origin_code'] == origin) & 
                                    (df_filtered['destination_code'] == destination)
                                ]
                                on_time_pct = (route_df['is_delayed'] == False).mean() * 100
                                path_data['metric'] = on_time_pct
                                path_data['metric_name'] = "On-Time %"
                            else:
                                path_data['metric'] = frequency
                                path_data['metric_name'] = "Frequency"
                        elif map_metric == "Fuel Efficiency":
                            if 'fuel_used' in df_filtered.columns:
                                route_df = df_filtered[
                                    (df_filtered['origin_code'] == origin) & 
                                    (df_filtered['destination_code'] == destination)
                                ]
                                avg_fuel = route_df['fuel_used'].mean()
                                path_data['metric'] = avg_fuel
                                path_data['metric_name'] = "Avg Fuel (L)"
                            else:
                                path_data['metric'] = frequency
                                path_data['metric_name'] = "Frequency"
                        else:  # Flight Frequency
                            path_data['metric'] = frequency
                            path_data['metric_name'] = "Frequency"
                        
                        map_data.append(path_data)
                
                # Create the map
                if map_data:
                    map_df = pd.DataFrame(map_data)
                    
                    # Create airport points data
                    airports = []
                    for code in all_airports:
                        if code in AIRPORT_COORDINATES:
                            coords = AIRPORT_COORDINATES[code]
                            name = coords.get('name', code)
                            airports.append({
                                'code': code,
                                'name': name,
                                'lat': coords['lat'],
                                'lon': coords['lon'],
                                'flights': len(df_filtered[(df_filtered['origin_code'] == code) | 
                                                           (df_filtered['destination_code'] == code)])
                            })
                    
                    airports_df = pd.DataFrame(airports)
                    
                    # Create the map figure
                    fig = go.Figure()
                    
                    # Add flight paths
                    for _, row in map_df.iterrows():
                        fig.add_trace(
                            go.Scattergeo(
                                lon=[row['origin_lon'], row['dest_lon']],
                                lat=[row['origin_lat'], row['dest_lat']],
                                mode='lines',
                                line=dict(
                                    width=row['width'],
                                    color=px.colors.sequential.Blues[int(5 * row['metric'] / map_df['metric'].max())] 
                                          if map_metric != "On-Time Performance" 
                                          else px.colors.sequential.Greens[int(5 * row['metric'] / 100)]
                                ),
                                opacity=0.7,
                                name=f"{row['origin']} to {row['destination']}",
                                hoverinfo='text',
                                hovertext=(
                                    f"Route: {row['origin']} → {row['destination']}<br>"
                                    f"{row['metric_name']}: {row['metric']:.1f}<br>"
                                    f"Flights: {row['frequency']}"
                                )
                            )
                        )
                    
                    # Add airport markers
                    fig.add_trace(
                        go.Scattergeo(
                            lon=airports_df['lon'],
                            lat=airports_df['lat'],
                            text=airports_df['code'],
                            hovertext=airports_df.apply(
                                lambda x: f"{x['name']} ({x['code']})<br>Flights: {x['flights']}",
                                axis=1
                            ),
                            mode='markers+text',
                            marker=dict(
                                size=10,
                                color='red',
                                opacity=0.8,
                                symbol='circle'
                            ),
                            textposition='top center'
                        )
                    )
                    
                    # Update layout
                    fig.update_layout(
                        title=f"Flight Routes Colored by {map_metric}",
                        showlegend=False,
                        geo=dict(
                            scope='africa',
                            projection_type='natural earth',
                            showland=True,
                            landcolor=land_color,
                            countrycolor=country_color,
                            showocean=True,
                            oceancolor=ocean_color,
                            showlakes=True,
                            lakecolor=ocean_color,
                            showcountries=True,
                            showframe=False,
                            bgcolor='rgba(0,0,0,0)'
                        ),
                        height=700
                    )
                    
                    # Display the map
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Map legend explanation
                    if map_metric == "Flight Frequency":
                        st.info("Line thickness and color intensity indicate the number of flights on each route.")
                    elif map_metric == "On-Time Performance":
                        st.info("Line color indicates on-time performance percentage (greener = better).")
                    else:  # Fuel Efficiency
                        st.info("Line color indicates average fuel consumption (lighter blue = less fuel used).")
                else:
                    st.error("No route data available for mapping.")
            
            with tab2:
                st.header("Airport Statistics")
                
                # Calculate airport metrics
                airport_stats = []
                
                for code in all_airports:
                    if code in AIRPORT_COORDINATES:
                        # Count departures and arrivals
                        departures = len(df_filtered[df_filtered['origin_code'] == code])
                        arrivals = len(df_filtered[df_filtered['destination_code'] == code])
                        total = departures + arrivals
                        
                        # Get airport name
                        name = AIRPORT_COORDINATES[code].get('name', code)
                        
                        # Calculate on-time performance if available
                        on_time_departures = None
                        if 'is_delayed' in df_filtered.columns:
                            departure_df = df_filtered[df_filtered['origin_code'] == code]
                            if not departure_df.empty:
                                on_time_departures = (departure_df['is_delayed'] == False).mean() * 100
                        
                        # Calculate average fuel used if available
                        avg_fuel = None
                        if 'fuel_used' in df_filtered.columns:
                            fuel_df = df_filtered[
                                (df_filtered['origin_code'] == code) | 
                                (df_filtered['destination_code'] == code)
                            ]
                            if not fuel_df.empty:
                                avg_fuel = fuel_df['fuel_used'].mean()
                        
                        airport_stats.append({
                            'code': code,
                            'name': name,
                            'departures': departures,
                            'arrivals': arrivals,
                            'total_flights': total,
                            'on_time_departures': on_time_departures,
                            'avg_fuel': avg_fuel
                        })
                
                if airport_stats:
                    # Create DataFrame and sort by total flights
                    stats_df = pd.DataFrame(airport_stats)
                    stats_df = stats_df.sort_values('total_flights', ascending=False)
                    
                    # Display airport activity chart
                    st.subheader("Airport Activity")
                    
                    fig2 = px.bar(
                        stats_df,
                        x='code',
                        y=['departures', 'arrivals'],
                        title="Flights by Airport",
                        labels={'value': 'Number of Flights', 'code': 'Airport Code', 'variable': 'Flight Type'},
                        color_discrete_map={'departures': 'blue', 'arrivals': 'green'},
                        barmode='group'
                    )
                    
                    fig2.update_layout(legend_title_text='Flight Type')
                    
                    st.plotly_chart(fig2, use_container_width=True)
                    
                    # Display metrics table
                    st.subheader("Airport Metrics")
                    
                    # Format table data
                    display_cols = ['code', 'name', 'departures', 'arrivals', 'total_flights']
                    
                    if 'on_time_departures' in stats_df.columns and not stats_df['on_time_departures'].isna().all():
                        display_cols.append('on_time_departures')
                        stats_df['on_time_departures'] = stats_df['on_time_departures'].apply(
                            lambda x: f"{x:.1f}%" if not pd.isna(x) else "N/A"
                        )
                    
                    if 'avg_fuel' in stats_df.columns and not stats_df['avg_fuel'].isna().all():
                        display_cols.append('avg_fuel')
                        stats_df['avg_fuel'] = stats_df['avg_fuel'].apply(
                            lambda x: f"{x:.0f} L" if not pd.isna(x) else "N/A"
                        )
                    
                    # Rename columns for display
                    display_df = stats_df[display_cols].copy()
                    display_df.columns = [
                        'Code', 'Airport Name', 'Departures', 'Arrivals', 'Total Flights', 
                        'On-Time %' if 'on_time_departures' in display_cols else None,
                        'Avg Fuel Used' if 'avg_fuel' in display_cols else None
                    ]
                    display_df = display_df.dropna(axis=1)
                    
                    st.dataframe(display_df, use_container_width=True)
                else:
                    st.error("No airport statistics available.")

except Exception as e:
    st.error(f"Error: {e}")
    st.error("Please check your data connection and try again.")                    