from datetime import datetime, time
import json
import os
from telegrambot import send_telegram_message
from config import INDICATORS
from data_processing import process_fear_and_greed_data, process_historical_data, process_and_merge_data

def load_checkbox_state():
    print("Loading checkbox state")
    if os.path.exists('checkbox_state.json'):
        with open('checkbox_state.json', 'r') as f:
            config = json.load(f)
            state = config.get('sendTelegramMessage', False)
            print(f"Checkbox state loaded: {state}")
            return state
    print("Checkbox state file not found")
    return False

def send_trading_signal(df_merged):
    print("Sending trading signal")
    sendTelegramMessage = load_checkbox_state()

    if sendTelegramMessage:
        current_time = datetime.now().time()
        print(f"Current time: {current_time}")
        if current_time >= time(8, 0) and current_time < time(9, 0):
            signal_value = df_merged["signal"].iloc[-1]
            now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            formatted_message = f"BTC Trading Signal on {now}: <b>{signal_value}</b>"
            print(f"Formatted message: {formatted_message}")
            response = send_telegram_message(os.getenv("BOT_ID"), os.getenv("CHAT_ID"), formatted_message)
            print(f"Telegram response: {response}")
        else:
            print("Current time is outside the 8:00-9:00 AM window")
    else:
        print("Checkbox state is False, not sending message")

def fetch_and_process_data():
    print("Fetching and processing data")
    fear_and_greed_fetched, fear_and_greed_message, df_fear_and_greed = process_fear_and_greed_data()
    historical_data_fetched, historical_data_message, df_historical_btc = process_historical_data()

    if fear_and_greed_fetched and historical_data_fetched:
        df_merged = process_and_merge_data(df_historical_btc, df_fear_and_greed, INDICATORS.get("LOWER_MM_QUANTIL"), INDICATORS.get("UPPER_MM_QUANTIL"), INDICATORS.get("LOWER_FEAR_AND_GREED"), INDICATORS.get("UPPER_FEAR_AND_GREED"), INDICATORS.get("BIGGER_SMA"), INDICATORS.get("SMALLER_SMA"))
        print("Data processed successfully")
        return True, "Data processed successfully", df_merged
    else:
        print("Data processing failed")
        return False, "Data processing failed", None

if __name__ == "__main__":
    print("Starting scheduler script")
    success, message, df_merged = fetch_and_process_data()
    print(f"Fetch and process data success: {success}, message: {message}")
    if success:
        send_trading_signal(df_merged)
    else:
        print("Data processing was not successful, not sending signal")
