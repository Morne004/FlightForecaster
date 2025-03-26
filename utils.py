# utils.py
import pandas as pd
from supabase import create_client
import streamlit as st
from config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
@st.cache_resource
def get_supabase_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch flight data
@st.cache_data(ttl=600)
def get_flight_data():
    supabase = get_supabase_client()
    response = supabase.table("vw_historical_flights").select("*").execute()
    return pd.DataFrame(response.data)

# Calculate key metrics
def calculate_metrics(df):
    metrics = {
        "total_flights": len(df),
        "unique_routes": df[["origin_code", "destination_code"]].drop_duplicates().shape[0],
        "unique_aircraft": df["registration"].nunique(),
        "on_time_percentage": (df["is_delayed"] == False).mean() * 100 if "is_delayed" in df.columns else 0,
        "avg_delay_minutes": df["delay_minutes"].mean() if "delay_minutes" in df.columns else 0,
        "total_fuel_used": df["fuel_used"].sum() if "fuel_used" in df.columns else 0
    }
    return metrics

# Format route for display
def format_route(origin, destination):
    return f"{origin} → {destination}"

# Get most frequent routes
def get_top_routes(df, n=5):
    route_counts = df.groupby(["origin_code", "destination_code"]).size().reset_index(name="count")
    route_counts["route"] = route_counts.apply(lambda x: format_route(x["origin_code"], x["destination_code"]), axis=1)
    return route_counts.sort_values("count", ascending=False).head(n)

# Get aircraft usage stats
def get_aircraft_usage(df, n=5):
    return df["registration"].value_counts().head(n)