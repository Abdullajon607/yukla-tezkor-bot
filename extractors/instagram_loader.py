import os
import uuid
import logging
import json
import re
from config import DOWNLOAD_DIR, BASE_DIR
import aiohttp
import asyncio

async def get_insta_video(url):
    try:
        # 1. Cookie faylidan sessionid ni o'qiymiz (agar mavjud bo'lsa)
        cookies_path = os.path.join(BASE_DIR, "cookies.txt")
        session_id = None
        if os.path.exists(cookies_path):
            try:
                with open(cookies_path, 'r') as f:
                    for line in f:
                        if 'instagram.com' in line and 'sessionid' in line:
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                session_id = parts[6].strip()
                                break
            except Exception as e:
                logging.warning(f"Failed to read sessionid from cookies.txt: {e}")

        # Zamonaviy va ishonchli sarlavhalar (Eng asosiysi: X-IG-App-ID)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "X-IG-App-ID": "936619743392459",
            "Sec-Fetch-Mode": "navigate"
        }
        
        has_session = bool(session_id)
        is_story = "stories" in url.lower()
        
        if is_story and not has_session:
            return {"status": False, "error": "Instagram Stories yuklash uchun 'sessionid' cookie kerak. Iltimos, admin bilan bog'laning."}

        # Zamonaviy va ishonchli sarlavhalar (Eng asosiysi: X-IG-App-ID)
        headers = {
            **headers # Oldingi headersni saqlab qolamiz
        }
        if session_id:
            headers['Cookie'] = f'sessionid={session_id}'

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
                        if n.get('is_video'):
                            v_url = n.get('video_url')
                            # Eng yuqori sifatni qidirish (Full HD uchun)
                            if n.get('video_resources'):
                                best_res = max(n['video_resources'], key=lambda x: x.get('config_width', 0) * x.get('config_height', 0))
                                v_url = best_res.get('src', v_url)
                            media_urls.append({'type': 'video', 'url': v_url})
                        elif n.get('display_url'):
                            media_urls.append({'type': 'photo', 'url': n.get('display_url')})
                    return True

                # REST karusel
                if 'carousel_media' in obj and isinstance(obj['carousel_media'], list):
                    for c in obj['carousel_media']:
                        if 'video_versions' in c and c['video_versions']:
                            # Eng yuqori sifatli videoni tanlash
                            best_v = max(c['video_versions'], key=lambda x: x.get('width', 0) * x.get('height', 0))
                            media_urls.append({'type': 'video', 'url': best_v['url']})
                        elif 'image_versions2' in c and 'candidates' in c['image_versions2']:
                            # Eng yuqori sifatli rasmni tanlash
                            best_i = max(c['image_versions2']['candidates'], key=lambda x: x.get('width', 0) * x.get('height', 0))
                            media_urls.append({'type': 'photo', 'url': best_i['url']})
                    return True
                    
                # REST yagona video (Reels, Stories)
                if 'video_versions' in obj and isinstance(obj['video_versions'], list) and len(obj['video_versions']) > 0:
                    best_v = max(obj['video_versions'], key=lambda x: x.get('width', 0) * x.get('height', 0))
                    media_urls.append({'type': 'video', 'url': best_v['url']})
                    return True
                    
                # GraphQL yagona video (Reels, IGTV)
                if obj.get('is_video') and (obj.get('video_url') or obj.get('video_resources')):
                    v_url = obj.get('video_url')
                    if obj.get('video_resources'):
                        best_res = max(obj['video_resources'], key=lambda x: x.get('config_width', 0) * x.get('config_height', 0))
                        v_url = best_res.get('src', v_url)
                    media_urls.append({'type': 'video', 'url': v_url})
                    return True
                    
                # REST yagona rasm
                if 'image_versions2' in obj and 'candidates' in obj['image_versions2']:
                    cands = obj['image_versions2']['candidates']
                    if isinstance(cands, list) and len(cands) > 0:
                        best_i = max(cands, key=lambda x: x.get('width', 0) * x.get('height', 0))
                        url_str = best_i.get('url', '')
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
        json_url = url.split("?")[0] + "?__a=1&__d=dis" # Instagram API endpoint
        async with aiohttp.ClientSession() as aiohttp_session:
            async with aiohttp_session.get(json_url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                if response.status == 200:
                    try:
                        data = await response.json()
                        process_json(data)
                    except Exception as e:
                        logging.debug(f"__a=1 JSON parsing error: {e}")

            # 2-URINISH: Yopiq GraphQL API
            if not media_urls:
                gql_url = f"https://www.instagram.com/graphql/query/?query_hash=b3055c01b4b222b8a47dc12b090e4e64&variables={{\"shortcode\":\"{shortcode}\"}}"
                async with aiohttp_session.get(gql_url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            process_json(data)
                        except Exception as e:
                            logging.debug(f"GraphQL JSON parsing error: {e}")
                    
            # 3-URINISH: Eng og'ir holatlar uchun - HTML sahifa ichidan yashirin JSON larni portlatish
            if not media_urls:
                async with aiohttp_session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    html = await response.text()
                    
                    json_blocks = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
                    for block in json_blocks:
                        if 'xdt_shortcode_media' in block or 'carousel_media' in block or shortcode in block:
                            try:
                                data = json.loads(block)
                                process_json(data)
                                if media_urls: break
                            except Exception as e:
                                logging.debug(f"HTML script JSON parsing error: {e}")
                    
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
            # Check if the previous attempts failed and if the response indicated a login redirect or error
            # This part needs careful handling with aiohttp as response.url and status are from the last request
            # For simplicity, we'll re-attempt with cleared cookies if media_urls is still empty
            if not media_urls: # and ("login" in str(response.url) or response.status != 200): # This check is tricky with aiohttp's context
                logging.warning("Media topilmadi. Anonim tarzda HTML ni yuklashga urinilmoqda...")
                # Create a new session without cookies
                async with aiohttp.ClientSession() as anon_session:
                    anon_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                    async with anon_session.get(url, headers=anon_headers, timeout=aiohttp.ClientTimeout(total=7)) as anon_response:
                        html = await anon_response.text()
                        
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

    except aiohttp.ClientError as e:
        logging.error(f"Extractor tarmoq xatosi: {e}")
        return {"status": False, "error": f"Tarmoq xatosi: {str(e)}"}
    except asyncio.TimeoutError:
        logging.error(f"Extractor vaqt tugadi (timeout): {url}")
        return {"status": False, "error": "So'rovga javob kelmadi (vaqt tugadi)."}
    except Exception as e:
        logging.error(f"Extractor umumiy xatosi: {e}")
        return {"status": False, "error": f"Tizim xatosi: {str(e)}"}