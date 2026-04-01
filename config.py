import os

# 1. Telegram bot tokeningiz (@BotFather'dan olingan)
BOT_TOKEN = "SIZNING_BOT_TOKENINGIZNI_SHU_YERGA_YOZING"

# 2. Loyihaning asosiy papkasi yo'lini avtomatik aniqlash
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 3. Cookies fayli yo'li (Instagram/YouTube kabi tarmoqlardan xatosiz yuklash uchun)
COOKIES_FILE = os.path.join(BASE_DIR, "cookies.txt")

# 4. Qo'shimcha sozlamalar (ixtiyoriy)
# Bot xatolik bersa yoki statistika ko'rish uchun o'zingizning Telegram ID raqamingiz
ADMIN_IDS = [123456789]