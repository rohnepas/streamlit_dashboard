# config.py

# Streamlit page configuration
PAGE_CONFIG = {
    "page_title": "Strategy Dashboard",
    "page_icon": "🧊",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
    "menu_items": {
        "About": "# Investment Dashboard"
    }
}

# Time periods configuration
# Note: Fear and Greed API has data since Feb 2018 (~2900 days from Feb 2026)
TIME_PERIODS = {
    "DAYS_PERIODE": 3000,
}

# Indicators for the strategy (do usually not change)
INDICATORS = {
    "UPPER_MM_QUANTIL": 0.90,
    "LOWER_MM_QUANTIL": 0.10,
    "UPPER_FEAR_AND_GREED": 76,
    "LOWER_FEAR_AND_GREED": 25,
    "BIGGER_SMA": 200,
    "SMALLER_SMA": 100
}

# Strategie Konfiguration, 4+4 Signal-Strategie
# CVDD kommt von axeladlerjr.com (keine offizielle API, siehe Warnhinweis in
# data_processing.fetch_cvdd_from_axeladlerjr). bitcoin-data.com wurde dafuer
# verworfen, deren Wert wich um Faktor 3.3 von unabhaengigen Quellen ab.
STRATEGY_CONFIG = {
    "BUY_MM_QUANTILE": 0.10,       # Q10 Rolling Quantil (Kaufsignal)
    "SELL_MM_QUANTILE": 0.90,      # Q90 Rolling Quantil (Verkaufsignal)
    "Q_MIN_PERIODS": 200,          # Min. Perioden für expanding Quantile
    "BUY_FG_THRESHOLD": 25,        # F&G Kaufsignal (< 25)
    "SELL_FG_THRESHOLD": 75,       # F&G Verkaufsignal (> 75)
    "MVRV_SELL_THRESHOLD": 5,      # MVRV-Z Verkaufsignal (>= 5)
    "CVDD_TOLERANCE_PCT": 0.01,    # CVDD Naehe-Schwelle (1%)
    "BUY_BLOCK_MONTHS": 18,        # Kaufsignale erst nach 18 Mo. nach Halving
}

# Quick Reference URLs für Sidebar
QUICK_REFERENCE_URLS = {
    "Halving Progress": "https://charts.bitbo.io/halving-progress/",
    "Pi Cycle Top": "https://charts.bitbo.io/pi-cycle-top/",
    "Tether MarketCap": "https://charts.bitbo.io/tether-mkt-cap-mom/",
    "ETF Flows": "https://charts.bitbo.io/etf-flows-vs-new-btc/",
    "MVRV Z-Score": "https://charts.bitbo.io/mvrv-z-score/",
    "US M2": "https://charts.bitbo.io/us-m2/",
    "Funding Rates": "https://www.coinglass.com/FundingRate",
    "Open Interest": "https://www.coinglass.com/OI",
}

# Ticker symbols
TICKER_SYMBOLS = {
    "BTC": "BTC-USD"
}

# Bitcoin Halvings (all halvings until 02.02.2026)
BITCOIN_HALVINGS = {
    1: {"date": "2012-11-28", "block": 210000, "reward": "25 BTC"},
    2: {"date": "2016-07-09", "block": 420000, "reward": "12.5 BTC"},
    3: {"date": "2020-05-11", "block": 630000, "reward": "6.25 BTC"},
    4: {"date": "2024-04-20", "block": 840000, "reward": "3.125 BTC"},
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