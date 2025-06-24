# app/api/routes.py
# --- Endpoint Lengkap untuk Sistem Hibrida ---

from flask import Blueprint, jsonify, current_app, request
import os
import base64
import time
import json
import re
import threading

# Import semua layanan yang kita butuhkan
from app.services import (
    sql_database_service,
    vector_store_service, 
    rag_service, 
    pdf_service,
    yolo_service,
    kindwise_service,
    inspection_service
    # Diimpor untuk kemungkinan pemicu manual di masa depan
)
from app.utils.helpers import allowed_file

# Membuat Blueprint untuk API
api_bp = Blueprint('api', __name__)

@api_bp.route('/')
def index():
    """Endpoint dasar untuk mengecek apakah API berjalan."""
    return jsonify({"status": "success", "message": "Mubarok Smart Farm Assistant API is online!"})


@api_bp.route('/ask', methods=['POST'])
def ask_question_endpoint():
    """Endpoint untuk RAG hibrida yang bisa mengembalikan teks atau gambar."""
    data = request.get_json()
    if not data or 'question' not in data or 'chat_id' not in data:
        return jsonify({"error": "Request body harus berisi 'question' dan 'chat_id'"}), 400
    
    question = data['question']
    chat_id = data['chat_id']
    
    # Dapatkan jawaban mentah dari RAG Agent
    raw_answer = rag_service.get_rag_response(
        question=question,
        db_collection=current_app.vector_db_collection,
        chat_id=chat_id
    )

    # --- PERBAIKAN UTAMA: Menggunakan Regex untuk mencari path gambar di dalam teks ---
    # Regex ini mencari string yang dimulai dengan /home/ dan diakhiri dengan ekstensi gambar.
    path_pattern = re.compile(r'(/home/[^\s`]+\.(?:png|jpg|jpeg))', re.IGNORECASE)
    match = path_pattern.search(raw_answer)

    if match:
        # Jika path ditemukan di dalam jawaban
        image_path = os.path.normpath(match.group(1)) # Ambil path yang cocok
        print(f"RESPONSE_HANDLER: Path gambar ditemukan dalam jawaban -> {image_path}")
        
        if os.path.exists(image_path):
            try:
                # Baca file gambar dan ubah ke base64
                with open(image_path, "rb") as f:
                    image_data_b64 = base64.b64encode(f.read()).decode('utf-8')
                
                # Buat caption dari teks jawaban asli, dengan path diganti
                caption = path_pattern.sub("[Gambar Terlampir]", raw_answer).strip()
                
                # Kirim respons dalam format khusus untuk gambar
                return jsonify({
                    "type": "image",
                    "imageData": image_data_b64,
                    "caption": caption
                })
            except Exception as e:
                print(f"RESPONSE_HANDLER: Gagal membaca file gambar: {e}")
                return jsonify({"type": "text", "answer": "Saya menemukan gambar yang Anda minta, tetapi gagal membukanya."})
        else:
            print(f"RESPONSE_HANDLER: Path gambar tidak ditemukan di server: {image_path}")
            return jsonify({"type": "text", "answer": "Saya menemukan referensi gambar untuk Anda, tetapi file-nya tidak dapat ditemukan di server."})

    else:
        # Jika tidak ada path gambar, kembalikan sebagai teks biasa
        return jsonify({"type": "text", "answer": raw_answer})

@api_bp.route('/summary', methods=['GET'])
def get_summary_endpoint():
    """Endpoint untuk mendapatkan ringkasan kondisi terkini."""
    summary = rag_service.get_latest_summary(current_app.vector_db_collection)
    return jsonify({"summary": summary})

@api_bp.route('/analyze-image', methods=['POST'])
def analyze_image_endpoint():
    """Endpoint untuk analisis gambar."""
    data = request.get_json()
    if not data or 'image_data' not in data or 'chat_id' not in data:
        return jsonify({"error": "Request body harus berisi 'image_data' dan 'chat_id'"}), 400

    image_b64_string, chat_id = data['image_data'], data['chat_id']

    # Simpan gambar sementara
    try:
        image_data = base64.b64decode(image_b64_string)
        temp_filename = f"analysis_{chat_id.split('@')[0]}_{int(time.time())}.jpg"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER_IMAGES'], temp_filename)
        with open(filepath, 'wb') as f:
            f.write(image_data)
    except Exception as e:
        return jsonify({"error": f"Format data gambar tidak valid: {e}"}), 400

    # Klasifikasi awal dengan YOLO
    classification_result = yolo_service.classify_image(filepath)
    
    # Alur kerja berdasarkan hasil klasifikasi
    if classification_result == "tidak sehat":
        diagnosis = kindwise_service.get_plant_diagnosis(filepath)
        if diagnosis:
            analysis_prompt = f"Saya telah menganalisis gambar tanaman dan terdeteksi tidak sehat. Layanan diagnosis ahli memberikan data berikut: {json.dumps(diagnosis, indent=2, ensure_ascii=False)}. Tolong ubah data ini menjadi penjelasan yang ramah untuk petani."
        else:
            analysis_prompt = "Saya mendeteksi tanaman ini tidak sehat, namun gagal mendapatkan diagnosis detail."
    else:
        analysis_prompt = f"Saya telah menganalisis sebuah gambar tanaman dan statusnya adalah: '{classification_result}'. Berikan respons yang ramah berdasarkan status ini."
    
    os.remove(filepath)
    answer = rag_service.get_rag_response(analysis_prompt, current_app.vector_db_collection, chat_id)
    return jsonify({"answer": answer})

@api_bp.route('/upload-pdf-wa', methods=['POST'])
def upload_pdf_from_wa_endpoint():
    """Endpoint untuk upload PDF dari WhatsApp."""
    data = request.get_json()
    if not data or 'pdf_data' not in data:
        return jsonify({"error": "Request body harus berisi 'pdf_data' (base64)"}), 400
    
    pdf_b64_string = data['pdf_data']
    upload_folder = current_app.config['UPLOAD_FOLDER_PDFS']
    temp_filename = f"temp_{int(time.time())}.pdf"
    file_path = os.path.join(upload_folder, temp_filename)

    if not pdf_service.save_b64_as_pdf(pdf_b64_string, file_path):
        return jsonify({"error": "Gagal menyimpan file PDF."}), 500
        
    summary_response = pdf_service.process_and_summarize_pdf(file_path, current_app.vector_db_collection)
    return jsonify({"answer": summary_response})

# --- ENDPOINT BARU UNTUK MEMICU INSPEKSI MANUAL ---
@api_bp.route('/trigger-inspection', methods=['POST'])
def trigger_inspection_endpoint():
    """
    Endpoint untuk memicu proses inspeksi harian secara manual.
    Dijalankan di thread terpisah agar tidak memblokir request.
    """
    print("API_ROUTE: Menerima perintah untuk memulai inspeksi manual...")
    
    # Ambil konteks aplikasi Flask saat ini
    app = current_app._get_current_object()

    # Buat fungsi target untuk thread yang memiliki konteks aplikasi
    def inspection_thread_target(app_context):
        with app_context.app_context():
            inspection_service.run_daily_check()

    # Jalankan proses inspeksi di thread background
    thread = threading.Thread(target=inspection_thread_target, args=(app,))
    thread.start()
    
    # Langsung berikan respons bahwa proses telah dimulai
    return jsonify({"status": "success", "message": "Proses inspeksi manual telah dimulai di latar belakang."})