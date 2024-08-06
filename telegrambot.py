import requests
from config import TELEGRAM

# Functuion to send message to the telegram bot
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{TELEGRAM.get("BOT_TOKEN")}/sendMessage'
    data = {
        'chat_id': TELEGRAM.get("CHAT_ID"),
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=data)
    return response.json()