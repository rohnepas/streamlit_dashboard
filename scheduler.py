from datetime import datetime
import pytz
import os
from telegrambot import send_telegram_message
from helpers import fetch_and_process_data
from config import TELEGRAM

def send_trading_signal(df_merged):
    sendTelegramMessage = TELEGRAM.get("SEND_MESSAGE", False)

    if sendTelegramMessage:
        signal_value = df_merged["signal"].iloc[-1].upper()  # Convert signal value to uppercase
        price = round(df_merged["close"].iloc[-1])  # Round price to the nearest whole number
        fear_and_greed_value = df_merged["value"].iloc[-1]
        
        # Use pytz to get the current time in Zurich
        tz = pytz.timezone('Europe/Zurich')
        now = datetime.now(tz).strftime("%d.%m.%Y %H:%M:%S")
        
        formatted_message = (
            f"BTC Trading Dashboard on {now}:\n"
            f"Signal: <b>{signal_value}</b>\n"
            f"Price: <b>{price}</b> USD\n"
            f"Fear and Greed Index: <b>{fear_and_greed_value}</b>"
        )
        
        send_telegram_message(os.getenv("BOT_ID"), os.getenv("CHAT_ID"), formatted_message)

if __name__ == "__main__":
    success, message, df_merged = fetch_and_process_data()
    if success:
        send_trading_signal(df_merged)
