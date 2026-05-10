import os
import uuid
import logging
import yt_dlp
from config import DOWNLOAD_DIR

def get_youtube_video(url):
    try:
        file_name = f"yt_{uuid.uuid4().hex[:6]}.mp4"
        file_path = os.path.join(DOWNLOAD_DIR, file_name)
        
        # 50MB limitni qaytaramiz
        ydl_opts = {
            'format': 'best[ext=mp4][filesize<=50M]/best[filesize<=50M]/best',
            'outtmpl': file_path,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(file_path):
            return {"status": True, "file_path": file_path}
        else:
            return {"status": False, "error": "Video yuklanmadi. Fayl topilmadi."}
            
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"YouTube yuklash xatosi: {e}")
        return {"status": False, "error": "Kechirasiz, bu videoni yuklab bo'lmadi (Hajmi 50MB dan katta yoki yopiq video)."}
    except Exception as e:
        logging.error(f"YouTube tizim xatosi: {e}")
        return {"status": False, "error": f"Tizim xatosi: {str(e)}"}