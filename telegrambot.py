import requests
from config import TELEGRAM

# Functuion to send message to the telegram bot
def send_telegram_message(bot_id, chat_id, message):
    url = f'https://api.telegram.org/bot{bot_id}/sendMessage'
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    response = requests.post(url, data=data)
    return response.json()