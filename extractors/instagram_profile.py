import requests
import logging

def get_instagram_profile(username: str):
    url = "https://simple-instagram-api.p.rapidapi.com/account-info"
    querystring = {"username": username}
    
    headers = {
        "x-rapidapi-host": "simple-instagram-api.p.rapidapi.com",
        "x-rapidapi-key": "62b161efd8mshb89646ba94f2865p11bc06jsnab8d7d7a726e",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        
        if response.status_code == 200:
            return {"status": True, "data": response.json()}
        else:
            logging.error(f"Profile API Xatosi: {response.text}")
            return {"status": False, "error": "Profilni topib bo'lmadi yoki API limit tugagan."}
    except Exception as e:
        logging.error(f"Profile tizim xatosi: {e}")
        return {"status": False, "error": "Tizim xatosi yuz berdi."}