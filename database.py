from supabase import create_client
import pandas as pd
import streamlit as st
import traceback
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flight_forecaster")

def get_supabase_client():
    """Create and return a Supabase client with detailed error handling"""
    try:
        # Print available keys in secrets for debugging
        logger.info(f"Available secret keys: {list(st.secrets.keys())}")
        
        # Get connection details from Streamlit secrets
        try:
            # Get credentials
            supabase_url = st.secrets["supabase_url"]
            supabase_key = st.secrets["supabase_key"]
            
            # Check if URL contains "be." instead of "db." and fix it
            if "be.b4i-systems" in supabase_url:
                corrected_url = supabase_url.replace("be.b4i-systems", "db.b4i-systems")
                logger.info(f"Corrected URL from {supabase_url[:15]}... to {corrected_url[:15]}...")
                supabase_url = corrected_url
            
            logger.info(f"Connecting to Supabase URL: {supabase_url[:15]}...")
            client = create_client(supabase_url, supabase_key)
            logger.info("Supabase client created successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to get or use credentials: {str(e)}")
            st.error(f"Error with database credentials: {str(e)}")
            raise
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Failed to create Supabase client: {str(e)}\n{error_details}")
        st.error(f"Database connection error: {str(e)}")
        raise

def get_flight_data(start_date=None, end_date=None, origin=None, destination=None, use_mock_data=False):
    """Fetch flight data from Supabase with detailed error handling"""
    if use_mock_data:
        return _generate_mock_flight_data(start_date, end_date, origin, destination)
    
    try:
        logger.info(f"Fetching flight data with filters: start_date={start_date}, end_date={end_date}, origin={origin}, destination={destination}")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # First try a simple test query to check if the table exists
        try:
            logger.info("Attempting test query to verify table exists")
            test_query = supabase.table('flights').select('*').limit(5)
            test_response = test_query.execute()
            logger.info(f"Test query successful: {len(test_response.data)} records found")
            
            # Start with the base query
            logger.info("Building main query")
            query = supabase.table('flights').select('*')
            
            # Apply filters if provided
            if start_date and end_date:
                logger.info(f"Adding date filter: {start_date} to {end_date}")
                query = query.gte('flight_date', start_date).lte('flight_date', end_date)
            if origin:
                logger.info(f"Adding origin filter: {origin}")
                query = query.eq('origin_code', origin)
            if destination:
                logger.info(f"Adding destination filter: {destination}")
                query = query.eq('destination_code', destination)
            
            # Check if 'deleted' column exists
            has_deleted = False
            if test_response.data and len(test_response.data) > 0:
                columns = list(test_response.data[0].keys())
                has_deleted = 'deleted' in columns
            
            # Add deleted filter if column exists
            if has_deleted:
                logger.info("Adding deleted=False filter")
                query = query.eq('deleted', False)
            
            # Execute the final query
            logger.info("Executing final query")
            response = query.execute()
            
            if response.data:
                logger.info(f"Query successful, returned {len(response.data)} records")
                return pd.DataFrame(response.data)
            
            logger.info("Query returned no data")
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Test query failed: {str(e)}")
            st.error(f"Database query failed: {str(e)}")
            
            # Fallback to mock data
            st.warning("Using mock data as fallback")
            return _generate_mock_flight_data(start_date, end_date, origin, destination)
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error fetching flight data: {str(e)}\n{error_details}")
        st.error(f"Error fetching flight data: {str(e)}")
        
        # Fallback to mock data
        st.warning("Using mock data as fallback due to error")
        return _generate_mock_flight_data(start_date, end_date, origin, destination)

def _generate_mock_flight_data(start_date=None, end_date=None, origin=None, destination=None):
    """Generate mock flight data for testing when database is unavailable"""
    from datetime import datetime, timedelta
    import random
    
    st.info("Generating mock flight data for testing")
    
    # If no dates provided, use last 30 days
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
    
    # Sample airports
    airports = ["LAX", "JFK", "SFO", "ORD", "ATL", "DFW", "LHR", "CDG", "DXB", "HND"]
    
    # Generate sample data
    mock_data = []
    current_date = start_date
    while current_date <= end_date:
        # Generate 5-15 flights per day
        num_flights = random.randint(5, 15)
        
        for _ in range(num_flights):
            # Select random airports if not specified
            flight_origin = origin if origin else random.choice(airports)
            flight_dest = destination if destination else random.choice(airports)
            
            # Ensure origin and destination are different
            while flight_origin == flight_dest:
                flight_dest = random.choice(airports)
            
            # Generate flight data
            is_delayed = random.random() < 0.2  # 20% chance of delay
            delay_minutes = random.randint(15, 120) if is_delayed else 0
            
            flight = {
                'flight_date': current_date,
                'origin_code': flight_origin,
                'destination_code': flight_dest,
                'flight_number': f"{random.choice(['AA', 'DL', 'UA', 'BA', 'LH'])}{random.randint(100, 999)}",
                'is_delayed': is_delayed,
                'delay_minutes': delay_minutes,
                'deleted': False
            }
            
            mock_data.append(flight)
        
        current_date += timedelta(days=1)
    
    # Filter mock data if origin/destination specified
    filtered_data = mock_data
    if origin:
        filtered_data = [f for f in filtered_data if f['origin_code'] == origin]
    if destination:
        filtered_data = [f for f in filtered_data if f['destination_code'] == destination]
    
    st.success(f"Generated {len(filtered_data)} mock flight records")
    return pd.DataFrame(filtered_data)