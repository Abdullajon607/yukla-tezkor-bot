import os
import uuid
import logging
import yt_dlp
import asyncio # Added for asyncio.to_thread
from config import DOWNLOAD_DIR, BASE_DIR
from extractors.instagram_loader import get_insta_video
from extractors.pinterest_loader import get_pinterest_media

async def get_universal_media(url):
    try:
        # Instagram uchun yt-dlp ni kutmasdan to'g'ridan-to'g'ri tezkor tizimga yuboramiz
        if "instagram.com" in url.lower():
            logging.info("Instagram linki: yt-dlp chetlab o'tildi. Tezkor tizim ishga tushdi...")
            insta_result = await get_insta_video(url)
            if insta_result and insta_result.get("status"):
                return insta_result
            logging.warning(f"Tezkor tizim xatosi: {insta_result.get('error', '')}. Zaxira sifatida yt-dlp ga o'tilmoqda...")

        # Pinterest uchun maxsus modul
        if "pinterest.com" in url.lower() or "pin.it" in url.lower():
            pin_result = await asyncio.to_thread(get_pinterest_media, url) # Run synchronous pinterest_loader in a thread
            if pin_result and pin_result.get("status"):
                return pin_result
            
        # Dinamik format (video bo'lsa mp4, audio bo'lsa m4a/mp3, rasm bo'lsa jpg/png avtomatik tanlanadi)
        file_name = f"media_{uuid.uuid4().hex[:6]}.%(ext)s"
        file_path_template = os.path.join(DOWNLOAD_DIR, file_name)
        
        # Cookie fayl manzilini aniqlaymiz
        cookies_path = os.path.join(BASE_DIR, "cookies.txt")
        
        ydl_opts = {
            # Format tanlashni ancha yumshatamiz: har qanday holatda ham yuklash uchun
            'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/bestvideo[height<=720]+bestaudio/best[height<=720]/best',
            'outtmpl': file_path_template,
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True, # SSL tekshiruvini o'chirib tezlikni oshiradi
            'no_color': True,
            'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
            'noplaylist': True,
            'extract_flat': 'in_playlist',
            'socket_timeout': 10,
            'source_address': '0.0.0.0', # IPv6 dan keladigan kechikishlarni oldini olish
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios', 'web'], # Kengaytirilgan mijozlar
                    'include_dash_manifest': True,
                    'include_hls_manifest': True
                }
            },
            'ignoreerrors': True,
            'noprogress': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # yt_dlp orqali URL analiz qilinib, yuklab olinadi
            info = await asyncio.to_thread(ydl.extract_info, url, download=True) # Run synchronous yt_dlp in a thread
            
            # Agar yt-dlp baribir playlist (masalan istoriya/karusel) qaytarsa
            file_path = None
            if 'entries' in info:
                for idx, entry in enumerate(info['entries']):
                    if entry:
                        fpath = ydl.prepare_filename(entry)
                        if idx == 0 and fpath and os.path.exists(fpath):
                            file_path = fpath
                        elif fpath and os.path.exists(fpath):
                            # Ortiqcha fayllarni o'chiramiz (server to'lmasligi uchun)
                            try: os.remove(fpath)
                            except: pass
            else:
                fpath = ydl.prepare_filename(info)
                if fpath and os.path.exists(fpath):
                    file_path = fpath
                    
        if file_path:
            return {"status": True, "file_path": file_path}
        else:
            return {"status": False, "error": "Faylni topib bo'lmadi (Profil yopiq yoki link xato)."}
            
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"Universal yuklash xatosi (yt-dlp): {e}")
        return {"status": False, "error": "Kechirasiz, bu platforma yoki linkdan yuklab bo'lmadi."}
    except Exception as e: # Catch other potential errors
        logging.error(f"Universal tizim xatosi: {e}")
        return {"status": False, "error": f"Tizim xatosi yuz berdi."}