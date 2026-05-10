import requests
import re
import logging
from config import HEADERS

def get_pinterest_media(url):
    """
    Pinterestdan rasm yoki video ma'lumotlarini olish.
    Rasm bo'lsa: status=True va URL qaytaradi.
    Video bo'lsa: None qaytaradi (universal_loader yt-dlp ni ishlatishi uchun).
    """
    try:
        # Pin.it qisqa linklarini asliga aylantirish uchun allow_redirects=True
        session = requests.Session()
        response = session.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        
        if response.status_code != 200:
            return None
            
        html = response.text
        
        # Videolarni aniqlash (videolarni yt-dlp yaxshiroq yuklaydi)
        if 'property="og:type" content="video.other"' in html or '"video_v2"' in html:
            return None
            
        # Rasm havolasini meta tegidan olish
        image_match = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if image_match:
            img_url = image_match.group(1)
            
            # Rasm sifatini oshirish (thumbnails -> originals)
            if "/originals/" not in img_url:
                img_url = re.sub(r'/(?:\d+x|v2)/', '/originals/', img_url)
                
            return {"status": True, "media_urls": [{"type": "photo", "url": img_url}]}
            
    except Exception as e:
        logging.error(f"Pinterest yuklash xatosi: {e}")
    return None