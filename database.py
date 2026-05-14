import sqlite3
import logging
import os
from config import BASE_DIR

DB_NAME = os.path.join(BASE_DIR, "database.db")

def init_db():
    """Bazani va jadvallarni yaratish (agar yo'q bo'lsa)"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
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
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mandatory_channels (
                channel_id TEXT PRIMARY KEY
            )
        ''')
        conn.commit()
    logging.info("Ma'lumotlar bazasi ishga tushdi.")

def save_file_id(url: str, file_id: str, media_type: str = "video"):
    """Yangi yuklangan videoning file_id sini bazaga saqlash"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # INSERT OR REPLACE - agar bu link oldin saqlangan bo'lsa, yangilaydi
        cursor.execute("INSERT OR REPLACE INTO media_cache (url, file_id, media_type) VALUES (?, ?, ?)", 
                       (url, file_id, media_type))
        conn.commit()

def get_file_id(url: str):
    """Link bazada bor-yo'qligini tekshirish"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT file_id, media_type FROM media_cache WHERE url = ?", (url,))
        result = cursor.fetchone()
        return result

def add_user(user_id: int):
    """Yangi foydalanuvchini bazaga qo'shish"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()

def get_all_users():
    """Barcha foydalanuvchilar ID larini olish"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = [row[0] for row in cursor.fetchall()]
        return users

def get_users_count():
    """Foydalanuvchilar sonini aniqlash"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        return count

def add_mandatory_channel(channel_id: str):
    """Majburiy obuna uchun kanal qo'shish"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO mandatory_channels (channel_id) VALUES (?)", (channel_id,))
        conn.commit()

def remove_mandatory_channel(channel_id: str):
    """Majburiy obunadan kanalni o'chirish"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM mandatory_channels WHERE channel_id = ?", (channel_id,))
        conn.commit()

def get_mandatory_channels():
    """Barcha majburiy kanallarni olish"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT channel_id FROM mandatory_channels")
        return [row[0] for row in cursor.fetchall()]