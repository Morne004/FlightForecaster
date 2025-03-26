# config.py
import os

# Supabase credentials
SUPABASE_URL = "https://jfms.db.b4i-systems.co.za"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.ewogICJyb2xlIjogImFub24iLAogICJpc3MiOiAic3VwYWJhc2UiLAogICJpYXQiOiAxNzM3OTI4ODAwLAogICJleHAiOiAxODk1Njk1MjAwCn0.E6_8ZmMClOqMPQA5IbEGGV1HRewCIP68ZqkL7Hl-BtQ"

# Airport coordinates
AIRPORT_COORDINATES = {
    "CPT": {"lat": -33.9648, "lon": 18.5965, "name": "Cape Town International Airport"},
    "HLA": {"lat": -25.9359, "lon": 27.9262, "name": "Lanseria International Airport"},
    "JNB": {"lat": -26.1348, "lon": 28.2405, "name": "O. R. Tambo International Airport"},
    "DUR": {"lat": -29.6144, "lon": 31.1197, "name": "King Shaka International Airport"},
    "GRJ": {"lat": -34.0015, "lon": 22.3789, "name": "George Airport"},
    "PLZ": {"lat": -33.9847, "lon": 25.6172, "name": "Chief Dawid Stuurman International Airport"},
    "BFN": {"lat": -29.0959, "lon": 26.2975, "name": "Bram Fischer International Airport"},
    "ELS": {"lat": -33.0356, "lon": 27.8259, "name": "King Phalo Airport"},
    "HRE": {"lat": -17.9318, "lon": 31.0929, "name": "Robert Gabriel Mugabe International Airport"},
    "VFA": {"lat": -18.0959, "lon": 25.8390, "name": "Victoria Falls Airport"},
    "MRU": {"lat": -20.4300, "lon": 57.6830, "name": "Sir Seewoosagur Ramgoolam International Airport"},
    "EBB": {"lat": 0.0400, "lon": 32.4388, "name": "Entebbe International Airport"},
    "MGQ": {"lat": 2.0132, "lon": 45.3047, "name": "Aden Adde International Airport"},
    "MQP": {"lat": -25.3836, "lon": 31.1050, "name": "Kruger Mpumalanga International Airport"},
    "ZNZ": {"lat": -6.2220, "lon": 39.2248, "name": "Abeid Amani Karume International Airport"},
    "WDH": {"lat": -22.4799, "lon": 17.4625, "name": "Hosea Kutako International Airport"}
}