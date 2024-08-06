# Streamlit page configuration
PAGE_CONFIG = {
    "page_title": "Strategy Dashboard",
    "page_icon": "🧊",
    "layout": "centered",
    "initial_sidebar_state": "expanded",
    "menu_items": {
        "About": "# Investment Dashboard"
    }
}

# Time periods configuration
TIME_PERIODS = {
    "DAYS_PERIODE" : 2000,
}


# Indicators for the strategy (do usually not change)
INDICATORS = {
    "UPPER_MM_QUANTIL" : 0.90,
    "LOWER_MM_QUANTIL" : 0.10,
    "UPPER_FEAR_AND_GREED" : 76,
    "LOWER_FEAR_AND_GREED" : 25,  
    "BIGGER_SMA": 200,
    "SMALLER_SMA" : 100
}

# Ticker symbols
TICKER_SYMBOLS = {
    "BTC": "BTC-USD"
}

# Days for metrics
DAYS_FOR_METRICS = 1

# Function to set up Streamlit page configuration
def setup_page_config():
    import streamlit as st
    st.set_page_config(**PAGE_CONFIG)

# Function to create the URL to retrieve Fear and Greed data
def create_fear_and_greed_index_url(days):
    return f"https://api.alternative.me/fng/?limit={days}"
