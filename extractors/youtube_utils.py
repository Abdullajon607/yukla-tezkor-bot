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

            # Tayyor (video+audio birlashtirilgan) formatlarni qidiramiz
            for f in info.get('formats', []):
                height = f.get('height')
                # acodec != 'none' bo'lsa merging shart emas, yuklash juda tez bo'ladi
                if height and f.get('acodec') != 'none' and f.get('vcodec') != 'none':
                    q_str = f"{height}p"
                    if q_str not in seen_qualities and height >= 360:
                        formats.append({'quality': q_str, 'format_id': f['format_id']})
                        seen_qualities.add(q_str)
            
            # Audio formatini ham qo'shamiz
            formats.append({'quality': 'audio', 'format_id': 'bestaudio'})

            # Sifat bo'yicha saralash
            formats.sort(key=lambda x: int(x['quality'].replace('p', '')) if 'p' in x['quality'] else 0)

            return {
                "status": True, 
                "formats": formats, 
                "vid": info['id'], 
                "title": info['title'], 
                "thumbnail": info.get('thumbnail'),
                "is_short": info.get('duration', 0) < 60
            }
    except Exception as e:
        logger.error(f"YouTube format olishda xato: {e}")
        return {"status": False, "error": str(e)}

def download_yt_by_quality(url, quality):
    """Tanlangan sifatda videoni yuklab olish"""
    random_id = str(uuid.uuid4())[:6]
    file_path = os.path.join(DOWNLOAD_DIR, f"yt_{random_id}.%(ext)s")
    
    if quality == 'audio':
        format_str = 'bestaudio[ext=m4a]/bestaudio/best'
    elif quality == 'best':
        format_str = 'best' # Hech qanday cheklovsiz eng yaxshi format
    else:
        # '+' belgisini olib tashlash merge jarayonini to'xtatadi va tezlikni oshiradi
        q_num = quality.replace('p', '')
        format_str = f'best[height<={q_num}][ext=mp4]/best[height<={q_num}]/best'

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
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return {"status": True, "file_path": ydl.prepare_filename(info)}
    except Exception as e:
        logger.error(f"YouTube yuklashda xato: {e}")
        return {"status": False, "error": str(e)}