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
        # Try different possible structures
        try:
            # Try top-level keys first
            supabase_url = st.secrets["supabase_url"]
            supabase_key = st.secrets["supabase_key"]
            logger.info("Using top-level supabase_url and supabase_key from secrets")
        except KeyError:
            try:
                # Try nested structure
                supabase_url = st.secrets["connections"]["supabase"]["url"]
                supabase_key = st.secrets["connections"]["supabase"]["key"]
                logger.info("Using nested connections.supabase.url and connections.supabase.key from secrets")
            except KeyError:
                # Output available keys for debugging
                if "connections" in st.secrets:
                    logger.info(f"Keys in connections: {list(st.secrets.connections.keys())}")
                    if "supabase" in st.secrets.connections:
                        logger.info(f"Keys in connections.supabase: {list(st.secrets.connections.supabase.keys())}")
                
                # Fall back to environment variables or config
                from config import SUPABASE_URL, SUPABASE_KEY
                supabase_url = SUPABASE_URL
                supabase_key = SUPABASE_KEY
                logger.info("Using SUPABASE_URL and SUPABASE_KEY from config.py")
        
        logger.info(f"Connecting to Supabase URL: {supabase_url[:10]}...")
        client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client created successfully")
        return client
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Failed to create Supabase client: {str(e)}\n{error_details}")
        st.error(f"Database connection error: {str(e)}")
        raise

def get_flight_data(start_date=None, end_date=None, origin=None, destination=None):
    """Fetch flight data from Supabase with detailed error handling"""
    try:
        logger.info(f"Fetching flight data with filters: start_date={start_date}, end_date={end_date}, origin={origin}, destination={destination}")
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # First try a simple test query to check if the table exists
        try:
            logger.info("Attempting test query to verify table exists")
            test_query = supabase.table('flights').select('count').limit(1)
            test_response = test_query.execute()
            logger.info(f"Test query successful: {json.dumps(test_response.data)}")
        except Exception as e:
            logger.error(f"Test query failed: {str(e)}")
            st.error(f"Test query failed: {str(e)}")
            
            # Try to list available tables
            try:
                logger.info("Attempting to list available tables")
                tables_query = supabase.from_("information_schema.tables").select("table_name").execute()
                if hasattr(tables_query, 'data') and tables_query.data:
                    table_names = [t.get("table_name") for t in tables_query.data]
                    logger.info(f"Available tables: {table_names}")
                    st.warning(f"Available tables: {', '.join(table_names)}")
            except Exception as table_e:
                logger.error(f"Failed to list tables: {str(table_e)}")
            
            raise Exception(f"Could not access 'flights' table: {str(e)}")
        
        # Start with the base query
        logger.info("Building main query")
        query = supabase.table('flights').select('*')
        
        # Try a simpler query first without the deleted condition
        try:
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
            
            # Add deleted=False filter only after checking if others work
            logger.info("Executing query without deleted filter first")
            initial_response = query.limit(1).execute()
            
            # If that worked, add the deleted filter
            if initial_response.data:
                logger.info("Basic query succeeded, adding deleted filter")
                query = query.eq('deleted', False)
                
            # Execute the final query
            logger.info("Executing final query")
            response = query.execute()
            
            if response.data:
                logger.info(f"Query successful, returned {len(response.data)} records")
                return pd.DataFrame(response.data)
            
            logger.info("Query returned no data")
            return pd.DataFrame()
            
        except Exception as query_e:
            logger.error(f"Error in query execution: {str(query_e)}")
            raise
        
    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"Error fetching flight data: {str(e)}\n{error_details}")
        st.error(f"Error fetching flight data: {str(e)}")
        return pd.DataFrame()