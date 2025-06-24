# app/__init__.py
# --- Application Factory dengan Penanganan Thread yang Benar ---

import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

def create_app():
    """Membuat dan mengkonfigurasi instance aplikasi Flask."""
    app = Flask(__name__)

    # Konfigurasi aplikasi
    project_root = os.path.dirname(app.root_path)
    app.config['UPLOAD_FOLDER_IMAGES'] = os.path.join(project_root, 'static', 'images')
    app.config['UPLOAD_FOLDER_PDFS'] = os.path.join(project_root, 'uploads', 'knowledge_pdfs')
    
    # --- PERBAIKAN UTAMA: Mencegah Duplikasi Layanan di Mode Debug ---
    # `WERKZEUG_RUN_MAIN` adalah variabel yang disetel oleh Flask.
    # Kode di dalam blok if ini hanya akan berjalan di proses utama, 
    # bukan di proses reloader induk.
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        with app.app_context():
            print("MAIN_PROCESS: Memulai layanan latar belakang...")
            
            # Inisialisasi Database
            from .services import sql_database_service
            sql_database_service.initialize_database()

            # Inisialisasi Vector Store (jika masih digunakan untuk PDF)
            from .services import vector_store_service
            app.vector_db_collection = vector_store_service.setup_vector_store()

            # Mulai MQTT client
            from .services import mqtt_service
            mqtt_service.start_mqtt_client()

            # Mulai Scheduler
            from .services import scheduler_service
            scheduler_service.start_scheduler(app, app.vector_db_collection)
            
            print("MAIN_PROCESS: Semua layanan latar belakang berhasil dimulai.")

    # Daftarkan API routes (ini aman untuk dijalankan di kedua proses)
    with app.app_context():
        from .api.routes import api_bp
        app.register_blueprint(api_bp)

    return app
