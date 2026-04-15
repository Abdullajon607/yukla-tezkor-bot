import requests
import os
import uuid
import logging
import json
import re
import http.cookiejar
from config import DOWNLOAD_DIR, BASE_DIR

def get_insta_video(url):
    try:
        session = requests.Session()
        
        # 1. Cookie faylni o'qiymiz (yt-dlp ishlatadigan cookie lardan bevosita foydalanamiz)
        cookies_path = os.path.join(BASE_DIR, "cookies.txt")
        if os.path.exists(cookies_path):
            cj = http.cookiejar.MozillaCookieJar(cookies_path)
            cj.load(ignore_discard=True, ignore_expires=True)
            session.cookies.update(cj)
            
        # Zamonaviy va ishonchli sarlavhalar (Eng asosiysi: X-IG-App-ID)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "X-IG-App-ID": "936619743392459", # Instagramni to'liq sifatli JSON berishga majburlaydi
            "Sec-Fetch-Mode": "navigate"
        }
        
        # Aniqroq shortcode ajratish
        match = re.search(r'/(?:p|reel|reels|tv|stories/[^/]+)/([^/?#&]+)', url)
        if match:
            shortcode = match.group(1)
        else:
            shortcode = url.split("?")[0].strip("/").split("/")[-1]
        media_urls = []
        
        def extract_media(obj):
            if isinstance(obj, dict):
                # GraphQL karusel
                if 'edge_sidecar_to_children' in obj:
                    for edge in obj.get('edge_sidecar_to_children', {}).get('edges', []):
                        n = edge.get('node', {})
                        if n.get('is_video') and n.get('video_url'):
                            media_urls.append({'type': 'video', 'url': n.get('video_url')})
                        elif n.get('display_url'):
                            media_urls.append({'type': 'photo', 'url': n.get('display_url')})
                    return True
                # REST karusel
                if 'carousel_media' in obj and isinstance(obj['carousel_media'], list):
                    for c in obj['carousel_media']:
                        if 'video_versions' in c and c['video_versions']:
                            media_urls.append({'type': 'video', 'url': c['video_versions'][0]['url']})
                        elif 'image_versions2' in c and 'candidates' in c['image_versions2']:
                            media_urls.append({'type': 'photo', 'url': c['image_versions2']['candidates'][0]['url']})
                    return True
                    
                # REST yagona video (Reels, Stories)
                if 'video_versions' in obj and isinstance(obj['video_versions'], list) and len(obj['video_versions']) > 0:
                    media_urls.append({'type': 'video', 'url': obj['video_versions'][0]['url']})
                    return True
                    
                # GraphQL yagona video (Reels, IGTV)
                if obj.get('is_video') and obj.get('video_url'):
                    media_urls.append({'type': 'video', 'url': obj.get('video_url')})
                    return True
                    
                # REST yagona rasm
                if 'image_versions2' in obj and 'candidates' in obj['image_versions2']:
                    cands = obj['image_versions2']['candidates']
                    if isinstance(cands, list) and len(cands) > 0:
                        url_str = cands[0].get('url', '')
                        if 'profile_pic' not in url_str:
                            media_urls.append({'type': 'photo', 'url': url_str})
                            return True
                            
                # GraphQL yagona rasm
                if obj.get('display_url') and 'profile_pic' not in obj.get('display_url', ''):
                    media_urls.append({'type': 'photo', 'url': obj.get('display_url')})
                    return True

                for k, v in obj.items():
                    if extract_media(v): return True
            elif isinstance(obj, list):
                for item in obj:
                    if extract_media(item): return True
            return False

        def process_json(data):
            # Asosiy ildizlarni tekshirish (Related postlarga adashib o'tib ketmaslik uchun)
            items = data.get('items', [])
            if items and extract_media(items[0]):
                return
            
            gql = data.get('graphql', {}) or data.get('data', {})
            sm = gql.get('shortcode_media', {}) or gql.get('xdt_shortcode_media', {})
            if sm and extract_media(sm):
                return
                
            # Agar topilmasa, butun JSON bo'ylab chuqur qidiruv
            extract_media(data)
            
        # 1-URINISH: __a=1 REST API
        json_url = url.split("?")[0] + "?__a=1&__d=dis"
        response = session.get(json_url, headers=headers, timeout=20)
        if response.status_code == 200:
            try:
                data = response.json()
                process_json(data)
            except: pass

        # 2-URINISH: Yopiq GraphQL API
        if not media_urls:
            gql_url = f"https://www.instagram.com/graphql/query/?query_hash=b3055c01b4b222b8a47dc12b090e4e64&variables={{\"shortcode\":\"{shortcode}\"}}"
            response = session.get(gql_url, headers=headers, timeout=5)
            if response.status_code == 200:
                try:
                    data = response.json()
                    process_json(data)
                except: pass
                
        # 3-URINISH: Eng og'ir holatlar uchun - HTML sahifa ichidan yashirin JSON larni portlatish
        if not media_urls:
            response = session.get(url, headers=headers, timeout=5)
            html = response.text
            
            json_blocks = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
            for block in json_blocks:
                if 'xdt_shortcode_media' in block or 'carousel_media' in block or shortcode in block:
                    try:
                        data = json.loads(block)
                        process_json(data)
                        if media_urls: break
                    except: pass
            
            # Eng so'nggi chora (Regex Extractor)
            if not media_urls:
                v_matches = re.finditer(r'"video_url"\s*:\s*"([^"]+)"', html)
                for m in v_matches:
                    v_url = m.group(1).replace('\\/', '/').replace('\\u0026', '&')
                    if v_url.startswith('http') and not any(x['url'] == v_url for x in media_urls):
                        media_urls.append({'type': 'video', 'url': v_url})
                        
                i_matches = re.finditer(r'"display_url"\s*:\s*"([^"]+)"', html)
                for m in i_matches:
                    i_url = m.group(1).replace('\\/', '/').replace('\\u0026', '&')
                    if i_url.startswith('http') and '150x150' not in i_url and 'profile_pic' not in i_url and '320x320' not in i_url:
                        if not any(x['url'] == i_url for x in media_urls):
                            media_urls.append({'type': 'photo', 'url': i_url})
                            
        # 4-URINISH: Cookie larsiz anonim so'rov (Ochiq profillar uchun zaxira)
        if not media_urls and ("login" in response.url or response.status_code != 200):
            logging.warning("Cookie bloklandi. Anonim tarzda HTML ni yuklashga urinilmoqda...")
            session.cookies.clear()
            anon_response = session.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}, timeout=7)
            html = anon_response.text
            
            v_matches = re.finditer(r'"video_url"\s*:\s*"([^"]+)"', html)
            for m in v_matches:
                v_url = m.group(1).replace('\\/', '/').replace('\\u0026', '&')
                if v_url.startswith('http') and not any(x['url'] == v_url for x in media_urls):
                    media_urls.append({'type': 'video', 'url': v_url})
                    
            i_matches = re.finditer(r'"display_url"\s*:\s*"([^"]+)"', html)
            for m in i_matches:
                i_url = m.group(1).replace('\\/', '/').replace('\\u0026', '&')
                if i_url.startswith('http') and '150x150' not in i_url and 'profile_pic' not in i_url and '320x320' not in i_url:
                    if not any(x['url'] == i_url for x in media_urls):
                        media_urls.append({'type': 'photo', 'url': i_url})

        if not media_urls:
            return {"status": False, "error": "Media topilmadi. Profil yopiq yoki link xato."}

        # 3. URL ro'yxatini qaytaramiz (yuklash va yuborish main.py da ketma-ket qilinadi)
        if media_urls:
            return {"status": True, "media_urls": media_urls[:10]}
        else:
            return {"status": False, "error": "Media topilmadi."}

    except Exception as e:
        logging.error(f"Extractor xatosi: {e}")
        return {"status": False, "error": f"Tizim xatosi: {str(e)}"}