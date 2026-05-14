import yt_dlp
import os
import uuid
import logging
import asyncio
from config import DOWNLOAD_DIR, BASE_DIR

logger = logging.getLogger(__name__)
cookies_path = os.path.join(BASE_DIR, "cookies.txt")

def _sync_get_formats(url):
    """Sinxron yordamchi funksiya yt-dlp uchun"""
    use_cookies = os.path.exists(cookies_path)
    if use_cookies:
        logger.info(f"YouTube uchun cookies.txt fayli ishlatilmoqda: {cookies_path}")
    else:
        logger.warning(f"YouTube cookies.txt fayli topilmadi! Ba'zi videolar 'Please sign in' xatosini berishi mumkin.")

    ydl_opts = {
        'quiet': True, 
        'no_warnings': True,
        'nocheckcertificate': True,
        'skip_download': True,
        'socket_timeout': 10,
        'cookiefile': cookies_path if use_cookies else None,
        'extractor_args': {
            'youtube': {
                # DASH oqimlarni (720p, 1080p) ochish uchun eng yaxshi mijozlar
                'player_client': ['ios', 'android'],
                # Barcha sifatlarni (shu jumladan DASH) olish uchun eng yaxshi mijozlar kombinatsiyasi
                'player_client': ['web', 'android', 'ios'],
                # DASH manifestlarini majburan yuklash (bu 720p/1080p ni ochib beradi)
                'include_dash_manifest': True,
                'include_hls_manifest': True
            }
        }
        },
        'format': 'bestvideo*+bestaudio/best' # Barcha video va audio oqimlarini olishga urinish
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        
        # Debugging uchun qo'shimcha loglar
        logger.info(f"yt-dlp info for {url}: Duration={info.get('duration')}, Webpage URL={info.get('webpage_url')}")
        
        formats = []
        seen_qualities = set()

        # Barcha noyob video sifatlarini to'playmiz
        # { '720p': 'format_id' }
        unique_video_formats = {}
        for f in info.get('formats', []):
            h = f.get('height')            
            if not h or h < 144 or f.get('vcodec') == 'none':
                continue

            # Standart sifatlarga yaqinligini tekshirish
            standard_resolutions = [360, 480, 720, 1080, 1440, 2160]
            # Biz faqat 720p ni ko'rsatmoqchi bo'lganimiz uchun, bu yerda faqat 720p ni qidiramiz
            # Agar video 720p ga yaqin bo'lsa, uni 720p deb belgilaymiz
            target_res = 720
            matched_res = None
            for res in standard_resolutions:
                if abs(h - res) <= 10: # 10 piksel farq bilan sifatni aniqlash
                    matched_res = res
                    break
            if abs(h - target_res) <= 10: # 10 piksel farq bilan 720p ni aniqlash
                matched_res = target_res
            
            if matched_res:
                q_str = f"{matched_res}p"
                # DASH (video-only) oqimlar odatda yuqori sifatli bo'ladi
                is_dash = f.get('acodec') == 'none'
                if q_str not in unique_video_formats or is_dash:
                    unique_video_formats[q_str] = f['format_id']
        

        # Formats ro'yxatiga o'tkazish
        for q_str, f_id in unique_video_formats.items():
            formats.append({'quality': q_str, 'format_id': f_id})
        
        # Sifatlarni tartiblash (kichikdan kattaga)
        formats.sort(key=lambda x: int(x['quality'].replace('p', '')) if 'p' in x['quality'] else 0)
            
        formats.append({'quality': 'audio', 'format_id': 'bestaudio'})
        is_short = info.get('duration', 0) < 60 or '/shorts/' in url or '/shorts/' in info.get('webpage_url', '')
        logger.info(f"Topilgan formatlar: {[f['quality'] for f in formats]}")

        return {
            "status": True, 
            "formats": formats, 
            "vid": info['id'], 
            "title": info['title'], 
            "thumbnail": info.get('thumbnail'),
            "is_short": is_short
        }

async def get_yt_formats(url):
    """YouTube videosi uchun mavjud sifatlarni olish (Asinxron)"""
    try:
        return await asyncio.to_thread(_sync_get_formats, url)
    except Exception as e:
        logger.error(f"YouTube format olishda xato: {e}")
        return {"status": False, "error": str(e)}

def _sync_download(url, quality):
    """Sinxron yordamchi funksiya yuklash uchun"""
    use_cookies = os.path.exists(cookies_path)
    
    random_id = str(uuid.uuid4())[:6]
    file_path = os.path.join(DOWNLOAD_DIR, f"yt_{random_id}.%(ext)s")
    limit = "49M" # Xavfsiz limit

    if quality == 'audio':
        format_str = f'bestaudio[ext=m4a][filesize<{limit}]/bestaudio[filesize<{limit}]/bestaudio/best'
    elif quality == 'shorts':
        # Shorts uchun 720p60 va 50MB limit (Telegramga mos yuqori sifat)
        format_str = f'bestvideo[height<=720][fps>=60][filesize<{limit}]+bestaudio[ext=m4a]/bestvideo[height<=720][filesize<{limit}]+bestaudio/best[height<=720][filesize<{limit}]/best'
    elif quality == 'best':
        format_str = f'bestvideo[filesize<{limit}]+bestaudio/best[filesize<{limit}]/best'
    else:
        q_num = quality.replace('p', '')
        # SIZNING TALABINGIZ: Faqat 720p60 maqsad qilinadi.
        # Agar 50MB dan oshsa, avtomatik ravishda limitga sig'adigan eng yuqori sifatga tushadi.
        # Agar 50MB dan oshsa, avtomatik ravishda limitga sig'adigan eng yuqori sifatga tushadi
        format_str = (
            f'bestvideo[height<={q_num}][fps>=60][filesize<{limit}]+bestaudio[ext=m4a]/' # 720p60 preference
            f'bestvideo[height<={q_num}][filesize<{limit}]+bestaudio[ext=m4a]/'          # 720p standard
            f'bestvideo[height<={q_num}][filesize<{limit}]+bestaudio/'                 # DASH
            f'best[height<={q_num}][filesize<{limit}]/'                               # Tayyor
            f'bestvideo[filesize<{limit}]+bestaudio/'                                # Fallback (<50MB)
            f'best[filesize<{limit}]/'                                                # Fallback
            f'best[filesize<{limit}]/'                                                # Fallback (umumiy)
            f'best'
        )

    ydl_opts = {
        'format': format_str,
        'outtmpl': file_path,
        'quiet': True,
        'nocheckcertificate': True,
        'socket_timeout': 15,
        'no_warnings': True,
        'cookiefile': cookies_path if use_cookies else None,
      