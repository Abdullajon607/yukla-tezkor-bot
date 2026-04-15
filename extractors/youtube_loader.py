import os
import uuid
import logging
import yt_dlp
from config import DOWNLOAD_DIR

def get_youtube_video(url):
    try:
        file_name = f"yt_{uuid.uuid4().hex[:6]}.mp4"
        file_path = os.path.join(DOWNLOAD_DIR, file_name)
        
        # Telegram uchun format va hajmni (maksimal 50MB) cheklash. 
        # 'b' - best (eng sifatli bitta fayl), qo'shimcha ffmpeg talab qilinmaydi.
        ydl_opts = {
            'format': 'b[ext=mp4][filesize<=50M]/b[filesize<=50M]',
            'outtmpl': file_path,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(file_path):
            return {"status": True, "file_path": file_path}
        else:
            return {"status": False, "error": "Video yuklanmadi yoki uning hajmi 50MB dan katta bo'lishi mumkin."}
            
    except yt_dlp.utils.DownloadError as e:
        logging.error(f"YouTube yuklash xatosi: {e}")
        return {"status": False, "error": "Kechirasiz, bu videoni yuklab bo'lmadi (Hajmi 50MB dan katta bo'lishi mumkin)."}
    except Exception as e:
        logging.error(f"YouTube tizim xatosi: {e}")
        return {"status": False, "error": f"Tizim xatosi: {str(e)}"}