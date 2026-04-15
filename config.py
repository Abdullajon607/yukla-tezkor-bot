import os

# Telegram Bot Token
BOT_TOKEN = "7944352953:AAGy3vEqM7gqwLJly0xs5upRX7CbGDaHJWA"

# RapidAPI - Bu eng ishonchli yo'l. Sessionid kabi tez o'lib qolmaydi.
# SIZNING OXIRGI SKRINSHOTDAGI AKTIV KALITINGIZ:
RAPIDAPI_KEY = "62b161efd8mshb89646ba94f2865p11bc06jsnab8d7da726e"
RAPIDAPI_HOST = "instagram120.p.rapidapi.com"

# Kataloglar
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)