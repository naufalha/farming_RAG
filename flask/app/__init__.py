# app/__init__.py

import os
from flask import Flask
from dotenv import load_dotenv

# Memuat semua variabel dari file .env agar bisa diakses oleh aplikasi
load_dotenv()

def create_app():
    """
    Factory function untuk membuat dan mengkonfigurasi 
    instance aplikasi Flask.
    """
    app = Flask(__name__)

    # --- Konfigurasi Aplikasi ---
    # Menentukan path absolut untuk folder upload agar tidak ambigu
    app.config['UPLOAD_FOLDER_IMAGES'] = os.path.join(app.root_path, '..', 'static', 'images')
    app.config['UPLOAD_FOLDER_PDFS'] = os.path.join(app.root_path, '..', 'uploads', 'knowledge_pdfs')
    
    # Menambahkan konfigurasi dari file .env untuk API
    app.config['DEEPSEEK_API_KEY'] = os.getenv("DEEPSEEK_API_KEY")
    app.config['DEEPSEEK_API_BASE'] = os.getenv("DEEPSEEK_API_BASE")

    # Konteks aplikasi diperlukan untuk mengakses 'current_app' saat inisialisasi
    with app.app_context():
        # --- Inisialisasi Layanan (Services) ---
        # Kita akan mengisi file-file ini di langkah berikutnya
        
        # 1. Inisialisasi Database SQL (untuk log sensor & cuaca)
        from .services import sql_database_service
        sql_database_service.initialize_database()
        print("Database SQL initialized.")

        # 2. Inisialisasi Vector Store (untuk pengetahuan dari PDF)
        from .services import vector_store_service
        app.vector_db_collection = vector_store_service.setup_vector_store()
        print("Vector store initialized.")

        # 3. Mulai MQTT client (sekarang terhubung ke database SQL)
        from .services import mqtt_service
        mqtt_service.start_mqtt_client()
        print("MQTT client started.")

        # 4. Mulai Scheduler (untuk mengambil data cuaca harian)
        from .services import scheduler_service
        scheduler_service.start_scheduler(app.vector_db_collection)
        print("Scheduler started.")

        # 5. Daftarkan API routes
        from .api.routes import api_bp
        app.register_blueprint(api_bp)
        
        

        
    return app