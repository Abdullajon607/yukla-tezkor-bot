import os
import yt_dlp
import asyncio
import uuid
from config import DOWNLOAD_DIR

def _sync_download_yt(url: str) -> dict:
    """YouTube videosini yuklab olish (Sinxron qism)"""
    random_id = str(uuid.uuid4())[:8]
    # Fayl nomi shabloni
    file_template = os.path.join(DOWNLOAD_DIR, f"yt_{random_id}_%(id)s.%(ext)s")
    
    ydl_opts = {
        # 720p gacha bo'lgan eng yaxshi MP4 formatini tanlaydi
        'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': file_template,
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True, # Faqat bitta videoni yuklaydi
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Ma'lumotni olish va yuklash
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            
            # Agar kengaytma o'zgargan bo'lsa (masalan .mkv)
            base = path.rsplit('.', 1)[0]
            actual_path = None
            for ext in ['mp4', 'mkv', 'webm']:
                if os.path.exists(f"{base}.{ext}"):
                    actual_path = f"{base}.{ext}"
                    break
            
            if actual_path:
                return {"status": True, "path": actual_path}
                
    except Exception as e:
        return {"status": False, "error": str(e)}
        
    return {"status": False, "error": "YouTube fayli yuklanmadi."}

async def download_youtube(url: str) -> dict:
    """Asinxron o'ram (Bot qotib qolmasligi uchun)"""
    return await asyncio.to_thread(_sync_download_yt, url)