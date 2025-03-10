from supabase import create_client
import pandas as pd
import streamlit as st

def get_supabase_client():
    """Create and return a Supabase client"""
    supabase_url = st.secrets["supabase_url"]
    supabase_key = st.secrets["supabase_key"]
    
    return create_client(supabase_url, supabase_key)

def get_flight_data(start_date=None, end_date=None, origin=None, destination=None):
    """Fetch flight data from Supabase with optional filters"""
    try:
        supabase = get_supabase_client()
        
        # Start with the base query
        query = supabase.table('flights').select('*').eq('deleted', False)
        
        # Apply filters if provided
        if start_date and end_date:
            query = query.gte('flight_date', start_date).lte('flight_date', end_date)
        if origin:
            query = query.eq('origin_code', origin)
        if destination:
            query = query.eq('destination_code', destination)
            
        # Execute the query
        response = query.execute()
        
        # Convert to DataFrame
        if response.data:
            return pd.DataFrame(response.data)
        return pd.DataFrame()
    
    except Exception as e:
        st.error(f"Error fetching flight data: {str(e)}")
        return pd.DataFrame()  # Return empty DataFrame on error