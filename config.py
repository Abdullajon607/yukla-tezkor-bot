import os

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "7944352953:AAGy3vEqM7gqwLJly0xs5upRX7CbGDaHJWA")

# Kataloglar
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)