import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_telegram_message(bot_id, chat_id, message):
    """
    Send a message to a Telegram bot.

    Args:
        bot_id (str): The Telegram bot token
        chat_id (str): The chat ID to send the message to
        message (str): The message text to send

    Returns:
        dict: The JSON response from Telegram API, or None if failed
    """
    if not bot_id or not chat_id:
        logging.error("BOT_ID or CHAT_ID not provided. Cannot send Telegram message.")
        return None

    url = f'https://api.telegram.org/bot{bot_id}/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }

    try:
        logging.info("Sending message to Telegram...")
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status()  # Raise exception for HTTP errors

        result = response.json()
        if result.get('ok'):
            logging.info("Message sent successfully to Telegram.")
            return result
        else:
            logging.error(f"Telegram API returned error: {result.get('description')}")
            return None

    except requests.exceptions.Timeout:
        logging.error("Timeout while sending message to Telegram.")
        return None
    except requests.exceptions.RequestException as e:
        logging.exception(f"Failed to send message to Telegram: {e}")
        return None
    except Exception as e:
        logging.exception(f"Unexpected error while sending Telegram message: {e}")
        return None