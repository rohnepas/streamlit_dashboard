from config import setup_page_config, INDICATORS, TELEGRAM
from ui_components import loadUiComponents
import streamlit as st
from data_processing import process_fear_and_greed_data, process_historical_data, process_and_merge_data, calculate_sell_and_buy_history
from datetime import datetime, time
from streamlit_autorefresh import st_autorefresh
from telegrambot import send_telegram_message
import pandas as pd


def main():
    setup_page_config()  # Configure the Streamlit page

    # Auto-refresh every hour (3600000 ms - every hour)
    count = st_autorefresh(interval=3600000, limit=None, key="data_refresh")
    
    loadUiComponents()  # Load UI components
     # Check if the current time is 8:00 AM
    st.divider()
    sendTelegramMessage = st.checkbox("Send trading singnal to telegram bot")

    if sendTelegramMessage:
        current_time = datetime.now().time()
        if current_time >= time(8, 0) and current_time < time(9, 0):
            # Send the Telegram message only once at 8:00 AM
            if count % (3600000 // 15000) == 0:  # Ensuring the message sends once in the first hour
                now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                formatted_message = f"BTC Trading Signal on {now}: <b>your_signal</b>"
                send_telegram_message(st.secrets["BOT_ID"], st.secrets["CHAT_ID"],formatted_message)

def fetch_and_process_data_dashboard():
    return fetch_and_process_data(INDICATORS.get("LOWER_MM_QUANTIL"), INDICATORS.get("UPPER_MM_QUANTIL"), INDICATORS.get("LOWER_FEAR_AND_GREED"), INDICATORS.get("UPPER_FEAR_AND_GREED"), INDICATORS.get("BIGGER_SMA"), INDICATORS.get("SMALLER_SMA"))

def fetch_and_process_data(lower_mm_quantil, upper_mm_quantil, lower_fear_and_greed, upper_fear_and_greed, bigger_sma, smaller_sma):
    """
    This function is responsible for fetching and processing Bitcoin (BTC) market data. It performs two main tasks:

    1. Fetching Fear and Greed Index Data: It calls `process_fear_and_greed_data()` to retrieve data related to the Fear and Greed Index. This function returns a status flag (boolean), a message, and a DataFrame containing the Fear and Greed data.

    2. Fetching Historical BTC Data: Similarly, it invokes `process_historical_data()` to obtain historical BTC data. This function also returns a status flag, a message, and a DataFrame with the historical data.

    If both data types are successfully fetched, the method proceeds to merge and process these datasets by calling `process_and_merge_data()`. This processing includes integrating the Fear and Greed Index with the historical BTC data and applying specific parameters for data analysis.

    Returns:
    - On successful fetching and processing: A tuple (True, combined success message, merged DataFrame)
    - On failure to retrieve data: A tuple (False, combined error message, None)

    This method is crucial for ensuring that the necessary data for market analysis is accurately retrieved and prepared for further analysis or visualization.
    """
    fear_and_greed_fetched, fear_and_greed_message, df_fear_and_greed = process_fear_and_greed_data()
    historical_data_fetched, historical_data_message, df_historical_btc = process_historical_data()

    if fear_and_greed_fetched and historical_data_fetched:
        df_merged = process_and_merge_data(df_historical_btc, df_fear_and_greed, lower_mm_quantil, upper_mm_quantil, lower_fear_and_greed, upper_fear_and_greed, bigger_sma, smaller_sma)
        
        #df_merged = process_and_merge_data(df_historical_btc, df_fear_and_greed, INDICATORS.get("LOWER_MM_QUANTIL"), INDICATORS.get("UPPER_MM_QUANTIL"), INDICATORS.get("LOWER_FEAR_AND_GREED"), INDICATORS.get("UPPER_FEAR_AND_GREED"), INDICATORS.get("BIGGER_SMA"), INDICATORS.get("SMALLER_SMA"))
        combined_message = "Fear and Greed Data: " + fear_and_greed_message + " | Historical Data: " + historical_data_message
        return True, combined_message, df_merged
    else:
        combined_error_message = "Fear and Greed Data: " + fear_and_greed_message + " | Historical Data: " + historical_data_message
        return False, combined_error_message, None
    
def create_buy_and_sell_history(df_merged):
    df_sell_and_buy_history = calculate_sell_and_buy_history(df_merged)
    st.dataframe(df_sell_and_buy_history)
    return df_sell_and_buy_history
    

if __name__ == "__main__":
    main()  # Run the main function



