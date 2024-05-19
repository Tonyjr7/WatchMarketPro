import os
from dotenv import load_dotenv
import telebot
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from threading import Timer

# Load environment variables from .env file
load_dotenv()

# Fetching the API keys from environment variables
TELEGRAM_API_TOKEN = os.getenv('TELEGRAM_API_TOKEN')
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

# API URLs
FOREX_API_URL = 'https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency={}&to_currency={}&apikey={}'
CRYPTO_API_URL = 'https://api.coingecko.com/api/v3/simple/price?ids={}&vs_currencies={}'

# In-memory store for alerts
price_alerts = {}

bot = telebot.TeleBot(TELEGRAM_API_TOKEN)

# Rest of the bot code remains the same...


def start(message):
    bot.reply_to(message, 'Welcome to the Forex and Crypto Market Monitor Bot!😉')

def get_forex_price(message):
    try:
        args = message.text.split()
        from_currency = args[1].upper()
        to_currency = args[2].upper()
        response = requests.get(FOREX_API_URL.format(from_currency, to_currency, ALPHA_VANTAGE_API_KEY))
        data = response.json()
        if 'Realtime Currency Exchange Rate' in data:
            price = data['Realtime Currency Exchange Rate']['5. Exchange Rate']
            bot.reply_to(message, f'The current exchange rate from {from_currency} to {to_currency} is {price}')
        else:
            bot.reply_to(message, 'Error retrieving Forex data.')
    except (IndexError, KeyError):
        bot.reply_to(message, 'Usage: /forex <from_currency> <to_currency>')

def get_crypto_price(message):
    try:
        args = message.text.split()
        crypto = args[1].lower()
        currency = args[2].lower()
        response = requests.get(CRYPTO_API_URL.format(crypto, currency))
        data = response.json()
        if crypto in data:
            price = data[crypto][currency]
            bot.reply_to(message, f'The current price of {crypto} in {currency} is {price}')
        else:
            bot.reply_to(message, 'Error retrieving Crypto data.')
    except (IndexError, KeyError):
        bot.reply_to(message, 'Usage: /crypto <crypto> <currency>')

def set_price_alert(message):
    try:
        args = message.text.split()
        asset_type = args[1].lower()
        asset = args[2].lower()
        target_price = float(args[3])
        
        chat_id = message.chat.id
        if chat_id not in price_alerts:
            price_alerts[chat_id] = []

        price_alerts[chat_id].append((asset_type, asset, target_price))
        bot.reply_to(message, f'Alert set for {asset} at {target_price}')
    except (IndexError, ValueError):
        bot.reply_to(message, 'Usage: /alert <forex|crypto> <asset> <target_price>')

def create_price_image(asset, price, target_price):
    # Create a blank image with white background
    img = Image.new('RGB', (400, 200), color='white')
    d = ImageDraw.Draw(img)

    # Add text to the image
    text = f'{asset.upper()}\nCurrent Price: {price}\nTarget Price: {target_price}'
    font = ImageFont.load_default()
    d.text((10, 10), text, fill='black', font=font)

    # Save the image to a BytesIO object
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def check_alerts():
    alerts_to_remove = []
    for chat_id, alerts in price_alerts.items():
        for alert in alerts:
            asset_type, asset, target_price = alert
            if asset_type == 'forex':
                from_currency, to_currency = asset.split('/')
                response = requests.get(FOREX_API_URL.format(from_currency, to_currency, ALPHA_VANTAGE_API_KEY))
                data = response.json()
                if 'Realtime Currency Exchange Rate' in data:
                    price = float(data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
                    if price >= target_price:
                        image = create_price_image(f'{from_currency}/{to_currency}', price, target_price)
                        bot.send_photo(chat_id, image, caption=f'Forex Alert: {from_currency}/{to_currency} has reached {price}')
                        alerts_to_remove.append((chat_id, alert))
            elif asset_type == 'crypto':
                response = requests.get(CRYPTO_API_URL.format(asset, 'usd'))
                data = response.json()
                if asset in data:
                    price = data[asset]['usd']
                    if price >= target_price:
                        image = create_price_image(asset, price, target_price)
                        bot.send_photo(chat_id, image, caption=f'Crypto Alert: {asset.upper()} has reached {price} USD')
                        alerts_to_remove.append((chat_id, alert))

    for chat_id, alert in alerts_to_remove:
        price_alerts[chat_id].remove(alert)
        if not price_alerts[chat_id]:
            del price_alerts[chat_id]

    Timer(10, check_alerts).start()

@bot.message_handler(commands=['start'])
def handle_start(message):
    start(message)

@bot.message_handler(commands=['forex'])
def handle_forex(message):
    get_forex_price(message)

@bot.message_handler(commands=['crypto'])
def handle_crypto(message):
    get_crypto_price(message)

@bot.message_handler(commands=['alert'])
def handle_alert(message):
    set_price_alert(message)

if __name__ == '__main__':
    Timer(10, check_alerts).start()
    bot.polling()
