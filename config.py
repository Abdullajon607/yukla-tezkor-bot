import os

# Telegram Bot Token
BOT_TOKEN = "8743152447:AAFm8Mt2ZEax3BpQUcYgUFzh9vrHAvs4tdI" # Misol: "1234567890:ABCDEFGHIJKLMN_OPQRSTUVW_XYZ"

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
ADMIN_IDS = [55667788] # Bu yerga o'zingizning Telegram ID raqamingizni yozing