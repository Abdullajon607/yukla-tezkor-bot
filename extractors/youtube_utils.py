import yt_dlp
import os
import uuid
import logging
from config import DOWNLOAD_DIR

logger = logging.getLogger(__name__)

def get_yt_formats(url):
    """YouTube videosi uchun mavjud sifatlarni olish"""
    ydl_opts = {'quiet': True, 'no_warnings': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            seen_qualities = set()

            # Faqat video+audio bo'lgan yoki eng yaxshi mp4 formatlarni tanlaymiz
            for f in info.get('formats', []):
                quality = f.get('format_note') or f.get('height')
                if quality and f.get('ext') == 'mp4' and f.get('vcodec') != 'none':
                    q_str = f"{quality}p" if isinstance(quality, int) else str(quality)
                    if q_str not in seen_qualities and q_str in ['360p', '720p', '1080p']:
                        formats.append({'quality': q_str, 'format_id': f['format_id']})
                        seen_qualities.add(q_str)
            
            # Audio formatini ham qo'shamiz
            formats.append({'quality': 'audio', 'format_id': 'bestaudio'})

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
        format_str = 'bestaudio[ext=m4a]/bestaudio'
    else:
        q_num = quality.replace('p', '')
        format_str = f'bestvideo[height<={q_num}][ext=mp4]+bestaudio[ext=m4a]/best[height<={q_num}][ext=mp4]/best'

    ydl_opts = {
        'format': format_str,
        'outtmpl': file_path,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return {"status": True, "file_path": ydl.prepare_filename(info)}
    except Exception as e:
        logger.error(f"YouTube yuklashda xato: {e}")
        return {"status": False, "error": str(e)}