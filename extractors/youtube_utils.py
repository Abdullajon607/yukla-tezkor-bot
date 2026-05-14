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
                # Musiqiy va himoyalangan videolarda 720p ni ochish uchun eng yaxshi mijozlar
                'player_client': ['android', 'ios', 'web'],
                # DASH manifestlarini majburan yuklash (bu 720p/1080p ni ochib beradi)
                'include_dash_manifest': True,
                'include_hls_manifest': True,
                'po_token': None # Ba'zi holatlarda kerak bo'lishi mumkin
            }
        },
        # Hamma formatlarni (DASH video va audio) ko'rish uchun eng keng qamrovli buyruq
        'format': 'bestvideo+bestaudio/best'
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
        
        # Avval barcha video formatlarni tahlil qilamiz
        all_formats = info.get('formats', [])
        
        # 720p ni qidirish (DASH yoki combined)
        for f in all_formats:
            h = f.get('height')
            vcodec = f.get('vcodec')
            if h and vcodec != 'none':
                # 720p yoki unga yaqin har qanday sifatni 720p tugmasiga bog'laymiz
                if 700 <= h <= 750:
                    unique_video_formats['720p'] = f['format_id']
                # Agar 720p bo'lmasa, 480p yoki 360p ni zaxira sifatida tugmaga chiqarmaymiz, 
                # lekin foydalanuvchi baribir 720p tugmasini ko'rishi kerak

        # Agar video o'zi juda past sifatli bo'lsa ham foydalanuvchiga tugma chiqarish kerak
        if not unique_video_formats:
            # Eng yaxshi mavjud video sifatini 720p tugmasiga beramiz (Fallback)
            best_v = max([f for f in all_formats if f.get('height') and f.get('vcodec') != 'none'], 
                         key=lambda x: x['height'], default=None)
            if best_v:
                unique_video_formats['720p'] = best_v['format_id']

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
        # Agar 50MB dan oshsa, avtomatik ravishda limitga sig'adigan eng yuqori sifatga tushadi
        format_str = (
            f'bestvideo[height<={q_num}][fps>=60][filesize<{limit}]+bestaudio[ext=m4a]/'
            f'bestvideo[height<={q_num}][filesize<{limit}]+bestaudio[ext=m4a]/'
            f'bestvideo[height<={q_num}][filesize<{limit}]+bestaudio/'
            f'best[height<={q_num}][filesize<{limit}]/'
            f'bestvideo[filesize<{limit}]+bestaudio/'
            f'best[filesize<{limit}]/'
            f'best'
        )

    ydl_opts = {
        'format': format_str,
        'outtmpl': file_path,
        'quiet': True,
        # Speed optimizations
        'concurrent_fragments': 10, # Parallel download for faster merge
        'buffersize': 1024*1024, # 1MB buffer
        'nocheckcertificate': True,
        'socket_timeout': 15,
        'no_warnings': True,
        'cookiefile': cookies_path if use_cookies else None,
        'extractor_args': {
            'youtube': {
                'player_client': ['web', 'android', 'ios'],
                'include_dash_manifest': True,
                'include_hls_manifest': True
            }
        },
        'ignoreerrors': True, # Ba'zi kichik xatolarda to'xtab qolmaslik uchun
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return {"status": True, "file_path": ydl.prepare_filename(info)}

async def download_yt_by_quality(url, quality):
    """Tanlangan sifatda videoni yuklab olish (Asinxron)"""
    try:
        return await asyncio.to_thread(_sync_download, url, quality)
    except Exception as e:
        logger.error(f"YouTube yuklashda xato: {e}")
        return {"status": False, "error": str(e)}