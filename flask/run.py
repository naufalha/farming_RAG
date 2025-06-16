# run.py

import os
from app import create_app

# Membuat instance aplikasi Flask dari factory function di app/__init__.py
app = create_app()

if __name__ == '__main__':
    # Pastikan direktori yang dibutuhkan untuk upload sudah ada
    os.makedirs(app.config['UPLOAD_FOLDER_IMAGES'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER_PDFS'], exist_ok=True)
    
    # Menjalankan server development Flask
    # Catatan: Untuk produksi, gunakan server WSGI seperti Gunicorn atau Waitress
    app.run(host='0.0.0.0', port=5000, debug=True)