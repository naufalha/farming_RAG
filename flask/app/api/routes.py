# app/api/routes.py
# --- Endpoint untuk Sistem Hibrida ---

from flask import Blueprint, jsonify, current_app, request
import os
import base64
import time
import json

# Import semua layanan yang kita butuhkan
from app.services import (
    sql_database_service,
    vector_store_service, 
    rag_service, 
    pdf_service,
    yolo_service,
    kindwise_service
)
from app.utils.helpers import allowed_file

# Membuat Blueprint untuk API
api_bp = Blueprint('api', __name__)

@api_bp.route('/')
def index():
    return jsonify({"status": "success", "message": "Mubarok Smart Farm Assistant API is online!"})

@api_bp.route('/ask', methods=['POST'])
def ask_question_endpoint():
    """Endpoint untuk RAG hibrida."""
    data = request.get_json()
    if not data or 'question' not in data or 'chat_id' not in data:
        return jsonify({"error": "Request body harus berisi 'question' dan 'chat_id'"}), 400
    
    question = data['question']
    chat_id = data['chat_id']
    
    # Memanggil layanan RAG yang sekarang menggunakan SQL dan Vector DB
    answer = rag_service.get_rag_response(
        question=question,
        db_collection=current_app.vector_db_collection, # Untuk mencari di PDF
        chat_id=chat_id
    )
    return jsonify({"question": question, "answer": answer})

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
    print(classification_result)
    # Alur kerja berdasarkan hasil klasifikasi
    if classification_result == "tidak sehat":
          # 2a. Jika tidak sehat, panggil Kindwise untuk diagnosis mendalam
        diagnosis = kindwise_service.get_plant_diagnosis(filepath)
        
        if diagnosis:
            # Buat prompt untuk AI agar merangkum hasil diagnosis Kindwise
            analysis_prompt = f"""
            Saya telah menganalisis gambar tanaman dan terdeteksi tidak sehat. Layanan diagnosis ahli memberikan data berikut dalam format teknis:
            {json.dumps(diagnosis, indent=2, ensure_ascii=False)}

            Tugas Anda adalah mengubah data teknis di atas menjadi penjelasan yang ramah dan mudah dimengerti untuk seorang petani dalam Bahasa Indonesia.
            Format jawaban Anda harus seperti ini:
            - **Nama Penyakit**: [Sebutkan nama penyakit dan nama umumnya].
            - **Gejala Utama**: [Jelaskan 2-3 gejala utama yang paling mudah dilihat].
            - **Rekomendasi Penanganan**: [Sebutkan langkah-langkah penanganan yang paling penting].
            """
        else:
            # Fallback jika Kindwise API gagal
            analysis_prompt = "Saya mendeteksi tanaman ini tidak sehat, namun gagal mendapatkan diagnosis detail dari layanan ahli. Sarankan pengguna untuk memeriksa secara manual atau mengirim gambar lain yang lebih jelas."
    
    else:
        # 2b. Jika sehat atau status lain, gunakan alur kerja lama
        analysis_prompt = f"""
        Saya telah menganalisis sebuah gambar tanaman dan statusnya adalah: '{classification_result}'.
        Berdasarkan status ini, berikan respons yang ramah dan informatif kepada pengguna dalam Bahasa Indonesia.
        """
    
    # Hapus file sementara
    os.remove(filepath)

    # 3. Dapatkan respons akhir dari RAG
    answer = rag_service.get_rag_response(
        analysis_prompt,
        current_app.vector_db_collection,
        chat_id
    )
    return jsonify({"answer": answer})



@api_bp.route('/upload-pdf-wa', methods=['POST'])
def upload_pdf_from_wa_endpoint():
    """Endpoint untuk upload PDF dari WhatsApp."""
    data = request.get_json()
    if not data or 'pdf_data' not in data:
        return jsonify({"error": "Request body harus berisi 'pdf_data' (base64)"}), 400
    
    pdf_b64_string = data['pdf_data']
    upload_folder = current_app.config['UPLOAD_FOLDER_PDFS']
    temp_filename = f"temp_{current_app.vector_db_collection.count()}.pdf"
    file_path = os.path.join(upload_folder, temp_filename)

    if not pdf_service.save_b64_as_pdf(pdf_b64_string, file_path):
        return jsonify({"error": "Gagal menyimpan file PDF."}), 500
        
    summary_response = pdf_service.process_and_summarize_pdf(file_path, current_app.vector_db_collection)
    return jsonify({"answer": summary_response})
