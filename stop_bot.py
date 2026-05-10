import asyncio
import logging
from aiogram import Bot
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

async def reset_bot_sessions():
    """
    Telegram serveridagi barcha faol ulanishlarni uzadi va 
    botni barcha qurilmalardan (seanslardan) chiqaradi.
    """
    bot = Bot(token=BOT_TOKEN)
    try:
        print("🔄 Telegram serveridan seanslar uzilmoqda...")
        # LogOut qilish barcha boshqa 'getUpdates' so'rovlarini to'xtatadi
        await bot.log_out()
        print("✅ Barcha faol ulanishlar muvaffaqiyatli to'xtatildi.")
    except Exception as e:
        print(f"❌ Xatolik yuz berdi: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(reset_bot_sessions())