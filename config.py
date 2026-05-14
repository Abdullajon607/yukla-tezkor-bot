import os
from dotenv import load_dotenv

# .env faylidan muhit o'zgaruvchilarini yuklash
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN") # .env faylidan olinadi

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
ADMIN_IDS = [6907296588] # Bu yerga o'zingizning Telegram ID raqamingizni yozing