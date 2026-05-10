import sqlite3
import logging
import os
from config import BASE_DIR

DB_NAME = os.path.join(BASE_DIR, "database.db")

def init_db():
    """Bazani va jadvallarni yaratish (agar yo'q bo'lsa)"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # url - video manzili, file_id - Telegram bergan kod, media_type - bu video, rasm yoki audio ekanligi
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS media_cache (
            url TEXT PRIMARY KEY,
            file_id TEXT,
            media_type TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("Ma'lumotlar bazasi ishga tushdi.")

def save_file_id(url: str, file_id: str, media_type: str = "video"):
    """Yangi yuklangan videoning file_id sini bazaga saqlash"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # INSERT OR REPLACE - agar bu link oldin saqlangan bo'lsa, yangilaydi
        cursor.execute("INSERT OR REPLACE INTO media_cache (url, file_id, media_type) VALUES (?, ?, ?)", 
                       (url, file_id, media_type))
        conn.commit()
    except Exception as e:
        logging.error(f"Bazaga saqlashda xatolik: {e}")
    finally:
        conn.close()

def get_file_id(url: str):
    """Link bazada bor-yo'qligini tekshirish"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, media_type FROM media_cache WHERE url = ?", (url,))
    result = cursor.fetchone()
    conn.close()
    
    # Agar topsa (file_id, media_type) qaytaradi, topmasa None
    return result

def add_user(user_id: int):
    """Yangi foydalanuvchini bazaga qo'shish"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
    finally:
        conn.close()

def get_all_users():
    """Barcha foydalanuvchilar ID larini olish"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_users_count():
    """Foydalanuvchilar sonini aniqlash"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count