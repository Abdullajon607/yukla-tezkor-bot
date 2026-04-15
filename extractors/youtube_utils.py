import os
import uuid
import logging
import yt_dlp
from config import DOWNLOAD_DIR, BASE_DIR

def get_yt_formats(url: str) -> dict:
    """YouTube URL uchun mavjud video va audio formatlarini oladi."""
    cookies_path = os.path.join(BASE_DIR, "cookies.txt")
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Noma`lum video')
            duration = info.get('duration', 0)
            vid = info.get('id')
            thumbnail = info.get('thumbnail')
            # Shorts videoni faqat havolasida "shorts" so'zi borligiga qarab aniqlaymiz
            is_short = "/shorts/" in url.lower()
            
            # Agar Shorts bo'lsa, faqat 720p taklif qilamiz
            if is_short:
                return {"status": True, "title": title, "is_short": True}

            # Oddiy videolar uchun barcha sifatlarni doimiy ko'rsatamiz (yt-dlp o'zi eng yaqinini tanlab oladi)
            formats_to_show = [
                {'quality': '360p'},
                {'quality': '480p'},
                {'quality': '720p'},
                {'quality': '1080p'}
            ]
            
            # Audio varianti
            formats_to_show.append({'quality': 'audio'})

            return {"status": True, "title": title, "formats": formats_to_show, "is_short": False, "vid": vid, "thumbnail": thumbnail}

    except Exception as e:
        logging.error(f"YouTube formatlarini olishda xato: {e}")
        return {"status": False, "error": "Video ma'lumotlarini olib bo'lmadi."}

def download_yt_by_quality(url: str, quality: str) -> dict:
    """YouTube videosini belgilangan sifatda yuklaydi."""
    file_name = f"yt_{uuid.uuid4().hex[:6]}.%(ext)s"
    file_path_template = os.path.join(DOWNLOAD_DIR, file_name)

    format_selector = ""
    if quality == 'audio':
        format_selector = 'bestaudio[ext=m4a]/bestaudio/best'
    else:
        height = quality[:-1] # '720p' -> '720'
        # FFmpeg talab qilmasligi uchun bitta fayl (video+audio birga) formatini tanlaymiz
        format_selector = f'b[height<={height}][ext=mp4]/b[height<={height}]/best'

    cookies_path = os.path.join(BASE_DIR, "cookies.txt")
    ydl_opts = {
        'format': format_selector,
        'outtmpl': file_path_template,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        'socket_timeout': 15,
        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            
            if os.path.exists(downloaded_file):
                if os.path.getsize(downloaded_file) > 50 * 1024 * 1024:
                    os.remove(downloaded_file)
                    return {"status": False, "error": f"Tanlangan sifatdagi video hajmi 50MB dan katta."}
                return {"status": True, "file_path": downloaded_file}
            else:
                base, _ = os.path.splitext(downloaded_file)
                for ext in ['.mp4', '.mkv', '.webm', '.m4a']:
                    if os.path.exists(base + ext):
                        if os.path.getsize(base + ext) > 50 * 1024 * 1024:
                            os.remove(base + ext)
                            return {"status": False, "error": f"Tanlangan sifatdagi video hajmi 50MB dan katta."}
                        return {"status": True, "file_path": base + ext}
                return {"status": False, "error": "Faylni yuklab bo'lmadi."}
    except Exception as e:
        logging.error(f"YouTube yuklash xatosi: {e}")
        return {"status": False, "error": "Videoni yuklashda xatolik yuz berdi."}