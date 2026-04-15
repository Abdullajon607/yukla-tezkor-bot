import os
import uuid
import logging
import yt_dlp
from config import DOWNLOAD_DIR, BASE_DIR
from extractors.instagram_loader import get_insta_video

def get_universal_media(url):
    try:
        # Instagram uchun yt-dlp ni kutmasdan to'g'ridan-to'g'ri tezkor tizimga yuboramiz
        if "instagram.com" in url.lower():
            logging.info("Instagram linki: yt-dlp chetlab o'tildi. Tezkor tizim ishga tushdi...")
            insta_result = get_insta_video(url)
            if insta_result and insta_result.get("status"):
                return insta_result
            logging.warning(f"Tezkor tizim xatosi: {insta_result.get('error', '')}. Zaxira sifatida yt-dlp ga o'tilmoqda...")
            
        # Dinamik format (video bo'lsa mp4, audio bo'lsa m4a/mp3, rasm bo'lsa jpg/png avtomatik tanlanadi)
        file_name = f"media_{uuid.uuid4().hex[:6]}.%(ext)s"
        file_path_template = os.path.join(DOWNLOAD_DIR, file_name)
        
        # Cookie fayl manzilini aniqlaymiz
        cookies_path = os.path.join(BASE_DIR, "cookies.txt")
        
        ydl_opts = {
            # Telegram uchun MP4 formatni majburlash va 50MB limitni nazorat qilish
            'format': 'b[ext=mp4][filesize<=50M]/best[ext=mp4][filesize<=50M]/b[filesize<=50M]/best',
            'outtmpl': file_path_template,
            'quiet': True,
            'no_warnings': True,
            'cookiefile': cookies_path if os.path.exists(cookies_path) else None,
            'noplaylist': True, # Instagram istoriya yoki karuselda ortiqcha narsalarni yuklamaslik uchun
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # yt_dlp orqali URL analiz qilinib, yuklab olinadi
            info = ydl.extract_info(url, download=True)
            
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
    except Exception as e:
        logging.error(f"Universal tizim xatosi: {e}")
        return {"status": False, "error": f"Tizim xatosi yuz berdi."}