import os

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Kataloglar
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "downloads")

if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Umumiy HTTP so'rovlar uchun sarlavhalar (Common Headers)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
}

# Admin foydalanuvchilarining ID'lari ro'yxati
# O'zingizning Telegram ID'ingizni bu yerga qo'shing.
ADMIN_IDS = [123456789, 987654321] # Misol uchun ID'lar, o'zingiznikiga o'zgartiring