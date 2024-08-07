from datetime import datetime, time
import json
import os
from telegrambot import send_telegram_message
from config import INDICATORS
from data_processing import process_fear_and_greed_data, process_historical_data, process_and_merge_data

def load_checkbox_state():
    if os.path.exists('checkbox_state.json'):
        with open('checkbox_state.json', 'r') as f:
            config = json.load(f)
            return config.get('sendTelegramMessage', False)
    return False

def send_trading_signal(df_merged):
    sendTelegramMessage = load_checkbox_state()

    if sendTelegramMessage:
        current_time = datetime.now().time()
        if current_time >= time(8, 0) and current_time < time(9, 0):
            signal_value = df_merged["signal"].iloc[-1]
            now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            formatted_message = f"BTC Trading Signal on {now}: <b>{signal_value}</b>"
            send_telegram_message(os.getenv("BOT_ID"), os.getenv("CHAT_ID"), formatted_message)

def fetch_and_process_data():
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
        df_merged = process_and_merge_data(df_historical_btc, df_fear_and_greed, INDICATORS.get("LOWER_MM_QUANTIL"), INDICATORS.get("UPPER_MM_QUANTIL"), INDICATORS.get("LOWER_FEAR_AND_GREED"), INDICATORS.get("UPPER_FEAR_AND_GREED"), INDICATORS.get("BIGGER_SMA"), INDICATORS.get("SMALLER_SMA"))
        return True, "Data processed successfully", df_merged
    else:
        return False, "Data processing failed", None

if __name__ == "__main__":
    success, message, df_merged = fetch_and_process_data()
    if success:
        send_trading_signal(df_merged)
    else:
        print(message)
