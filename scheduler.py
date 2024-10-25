import logging
from datetime import datetime
import pytz
import os
from telegrambot import send_telegram_message
from helpers import fetch_and_process_data
from config import TELEGRAM

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_trading_signal(df_merged=None, error_message=None):
    try:
        if error_message:
            logging.info("Preparing to send error notification signal...")
            formatted_message = (
                f"BTC Trading Dashboard Alert:\n"
                f"Error: <b>{error_message}</b>"
            )
        else:
            logging.info("Preparing to send trading signal...")
            sendTelegramMessage = TELEGRAM.get("SEND_MESSAGE", False)

            if not sendTelegramMessage:
                logging.warning("Telegram message sending is disabled in the configuration.")
                return

            # Retrieve and format signal information
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

            logging.info("Trading signal message prepared: %s", formatted_message)

        # Send the message
        send_telegram_message(os.getenv("BOT_ID"), os.getenv("CHAT_ID"), formatted_message)
        logging.info("Trading signal sent successfully.")
    except Exception as e:
        logging.exception("An error occurred while sending the trading signal: %s", e)

if __name__ == "__main__":
    try:
        logging.info("Starting data fetch and processing.")
        success, message, df_merged = fetch_and_process_data()
        if success:
            logging.info("Data fetched and processed successfully: %s", message)
            send_trading_signal(df_merged)
        else:
            logging.error("Failed to fetch and process data: %s", message)
            send_trading_signal(error_message=f"Failed to fetch and process data: {message}")
    except Exception as e:
        logging.exception("An unexpected error occurred in the main function: %s", e)