import asyncio
import logging
import os
import signal
import psutil
from aiogram import Bot
from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

def kill_local_instances():
    """
    Kompyuterda 'main.py' ni ishlatayotgan barcha jarayonlarni qidirib topadi va o'chiradi.
    """
    current_pid = os.getpid()
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline')
            if cmdline and any('main.py' in arg for arg in cmdline):
                pid = proc.info['pid']
                if pid != current_pid:
                    os.kill(pid, signal.SIGTERM)
                    killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return killed_count

async def reset_bot_sessions():
    """
    Telegram serveridagi barcha faol ulanishlarni uzadi va 
    botni barcha qurilmalardan (seanslardan) chiqaradi.
    """
    # 1. Mahalliy (kompyuterdagi) jarayonlarni o'chirish
    killed = kill_local_instances()
    print(f"🛑 Mahalliy: {killed} ta ishlayotgan jarayon topildi va to'xtatildi.")

    bot = Bot(token=BOT_TOKEN)
    try:
        print("🔄 Telegram: Webhook va kutilayotgan xabarlar tozalanmoqda...")
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Telegram: Webhook muvaffaqiyatli tozalandi.")
    except Exception as e:
        print(f"❌ Telegram xatosi: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(reset_bot_sessions())