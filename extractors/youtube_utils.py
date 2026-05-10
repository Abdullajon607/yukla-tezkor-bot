import yt_dlp
import os
import uuid
import logging
from config import DOWNLOAD_DIR, BASE_DIR

logger = logging.getLogger(__name__)
cookies_path = os.path.join(BASE_DIR, "cookies.txt")

def get_yt_formats(url):
    """YouTube videosi uchun mavjud sifatlarni olish"""
    ydl_opts = {
        'quiet': True, 
        'no_warnings': True,
        'nocheckcertificate': True,
        'skip_download': True,
        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web_creator']
            }
        }
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            seen_qualities = set()

            # Mavjud sifatlarni aniqlaymiz
            for f in info.get('formats', []):
                h = f.get('height')
                # Faqat video streamlarni (vcodec != none) olamiz
                # acodec ni tekshirmaymiz, chunki YouTube ko'pincha ularni alohida saqlaydi
                if h and h >= 360 and f.get('vcodec') and f.get('vcodec') != 'none':
                    q_str = f"{h}p"
                    # Faqat so'ralgan formatlarni (360, 480, 720, 1080) filtrlaymiz
                    if q_str not in seen_qualities and h in [360, 480, 720, 1080]:
                        formats.append({'quality': q_str, 'format_id': f['format_id']})
                        seen_qualities.add(q_str)
            
            # Sifat bo'yicha saralash
            formats.sort(key=lambda x: int(x['quality'].replace('p', '')) if 'p' in x['quality'] else 0)
            
            # Har doim audio variantini qo'shish
            formats.append({'quality': 'audio', 'format_id': 'bestaudio'})
            # Shorts ekanligini aniqlash (Davomiylik yoki URL orqali)
            is_short = info.get('duration', 0) < 60 or '/shorts/' in url or '/shorts/' in info.get('webpage_url', '')

            return {
                "status": True, 
                "formats": formats, 
                "vid": info['id'], 
                "title": info['title'], 
                "thumbnail": info.get('thumbnail'),
                "is_short": is_short
            }
    except Exception as e:
        logger.error(f"YouTube format olishda xato: {e}")
        return {"status": False, "error": str(e)}

def download_yt_by_quality(url, quality):
    """Tanlangan sifatda videoni yuklab olish"""
    random_id = str(uuid.uuid4())[:6]
    file_path = os.path.join(DOWNLOAD_DIR, f"yt_{random_id}.%(ext)s")
    
    if quality == 'audio':
        format_str = 'bestaudio[ext=m4a]/bestaudio/best' # Eng yaxshi audio
    elif quality == 'best':
        format_str = 'best' # Hech qanday cheklovsiz eng yaxshi format
    else:
        q_num = quality.replace('p', '')
        # 1. Video MP4 + Audio M4A (Eng yaxshi kombinatsiya)
        # 2. Tayyor MP4 (Tezkor)
        # 3. Har qanday video + Har qanday audio (FFmpeg orqali merge)
        # 4. Eng yaxshi mavjud format
        format_str = f'bestvideo[height<={q_num}][ext=mp4]+bestaudio[ext=m4a]/best[height<={q_num}][ext=mp4]/bestvideo[height<={q_num}]+bestaudio/best[height<={q_num}]/best'

    ydl_opts = {
        'format': format_str,
        'outtmpl': file_path,
        'quiet': True,
        'nocheckcertificate': True,
        'no_warnings': True,
        'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios', 'web_creator']
            }
        },
        'ignoreerrors': True, # Ba'zi kichik xatolarda to'xtab qolmaslik uchun
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return {"status": True, "file_path": ydl.prepare_filename(info)}
    except Exception as e:
        logger.error(f"YouTube yuklashda xato: {e}")
        return {"status": False, "error": str(e)}