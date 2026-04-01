import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

# O'zimiz yaratgan fayllardan token va baza funksiyalarini chaqiramiz
from config import BOT_TOKEN
import database

# Terminalda xatolik va jarayonlarni ko'rib turish uchun
logging.basicConfig(level=logging.INFO)

# Bot va Dispatcher yaratamiz
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- /start BUYRUG'I UCHUN HANDLER ---
@dp.message(Command("start"))
async def cmd_start(message: Message):
    welcome_text = (
        "• Salom men Tezkor Yukla botman.!\n\n"
        "• Instagram - post, reels, stores;\n"
        "• TikTok - suv belgisiz videolar;\n"
        "• YouTube - video, shorts, audio;\n"
        "• Pinterest - rasm, video;\n"
        "• Snapchat - video;\n"
        "• Threads - rasm, video;\n\n"
        "• Bundan tashqari men ovozli habar, video va audiodagi musiqalarni ham topib beraman."
    )
    await message.answer(welcome_text)

# --- ASOSIY ISHGA TUSHIRISH FUNKSIYASI ---
async def main():
    # Bot ishga tushishidan oldin bazani tekshiradi yoki yaratadi
    database.init_db()
    
    print("Bot ishga tushdi...")
    
    # Bot oflayn payti kelgan eski xabarlarga javob bermasligi uchun
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Botni uzluksiz ishlash rejimida yoqish
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())