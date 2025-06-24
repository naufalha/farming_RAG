# app/services/robot_service.py
# --- Layanan untuk Berkomunikasi dengan Linear Robotic Platform ---

import requests
import os
import time
from datetime import datetime

# --- PERUBAHAN: Hapus 'from flask import current_app' ---

# (Konfigurasi tetap sama)
ROBOT_IP = os.getenv("ROBOT_IP", "127.0.0.1")
BASE_URL = f"http://{ROBOT_IP}:5001"
MOVE_URL = f"{BASE_URL}/api/move_to_plant/"
GET_IMAGE_URL = f"{BASE_URL}/api/get_latest_image"
SERVER_PUBLIC_URL = os.getenv("SERVER_PUBLIC_URL", "http://127.0.0.1:5000")

def get_latest_plant_image(plant_id: int, app_context) -> tuple[str, str] | None:
    """
    Meminta gambar dari robot, menyimpannya, dan mengembalikan
    (path_lokal, url_publik) menggunakan konteks aplikasi yang diberikan.
    """
    print(f"ROBOT_SERVICE: Meminta gambar untuk tanaman ID: {plant_id}...")
    
    try:
        # --- PERUBAHAN: Menggunakan 'with app_context.app_context()' ---
        # Ini memastikan kita memiliki akses ke konfigurasi Flask
        with app_context.app_context():
            move_response = requests.post(f"{MOVE_URL}{plant_id}", timeout=20)
            move_response.raise_for_status()
            print(f"ROBOT_SERVICE: Perintah gerak ke tanaman {plant_id} berhasil.")

            time.sleep(5) # Beri jeda setelah bergerak sebelum mengambil gambar

            image_response = requests.get(GET_IMAGE_URL, timeout=20)
            image_response.raise_for_status()
            image_content = image_response.content

            filename = f"inspeksi_tanaman_{plant_id}_{int(datetime.now().timestamp())}.jpg"
            
            # Menggunakan app_context untuk mendapatkan konfigurasi
            image_dir = app_context.config['UPLOAD_FOLDER_IMAGES']
            local_filepath = os.path.join(image_dir, filename)
            
            with open(local_filepath, 'wb') as f:
                f.write(image_content)
            
            public_url = f"{SERVER_PUBLIC_URL}/static/images/{filename}"
            print(f"ROBOT_SERVICE: Gambar disimpan. URL publik: {public_url}")
            
            return local_filepath, public_url

    except Exception as e:
        print(f"ROBOT_SERVICE: Terjadi error tak terduga: {e}")
        return None
