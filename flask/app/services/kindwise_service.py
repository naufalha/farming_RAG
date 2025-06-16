# app/services/kindwise_service.py
# --- Layanan untuk Diagnosis Penyakit Tanaman via Kindwise API ---

import requests
import base64
import os
import json

# --- Konfigurasi ---
API_KEY = os.getenv("KINDWISE_API_KEY")
IDENTIFICATION_ENDPOINT = "https://crop.kindwise.com/api/v1/identification"
HEADERS = {
    "Api-Key": API_KEY,
    "Content-Type": "application/json"
}

def _get_structured_treatment(treatment_data: dict) -> str:
    """Mengubah data treatment dari Kindwise menjadi string yang rapi dan aman."""
    if not treatment_data:
        return "Tidak ada rekomendasi penanganan spesifik yang tersedia."
    
    parts = []
    
    def format_part(key_name, value):
        if isinstance(value, list):
            return f"{key_name}: {', '.join(value)}"
        elif value:
            return f"{key_name}: {value}"
        return None

    prevention = format_part("Pencegahan", treatment_data.get("prevention"))
    if prevention: parts.append(prevention)

    biological = format_part("Biologis", treatment_data.get("biological"))
    if biological: parts.append(biological)

    chemical = format_part("Kimiawi", treatment_data.get("chemical"))
    if chemical: parts.append(chemical)
        
    return "\n".join(parts) if parts else "Tidak ada rekomendasi penanganan."

def get_plant_diagnosis(image_path: str) -> dict | None:
    """
    Mengirim gambar ke Kindwise, mendapatkan diagnosis, dan mengembalikan
    hasilnya dalam format dictionary yang terstruktur.
    """
    print(f"KINDWISE_SERVICE: Memulai diagnosis untuk gambar: {image_path}")
    if not API_KEY:
        print("KINDWISE_SERVICE: ERROR - KINDWISE_API_KEY tidak ditemukan di .env")
        return None

    # 1. Kirim gambar untuk identifikasi awal & dapatkan access_token
    try:
        with open(image_path, "rb") as f:
            encoded_image = base64.b64encode(f.read()).decode('utf-8')
        
        payload = {"images": [encoded_image]}
        response = requests.post(IDENTIFICATION_ENDPOINT, headers=HEADERS, json=payload, timeout=45)
        response.raise_for_status()
        initial_result = response.json()
        access_token = initial_result.get('access_token')

        if not access_token:
            print("KINDWISE_SERVICE: Gagal mendapatkan access_token dari identifikasi awal.")
            return None

    except Exception as e:
        print(f"KINDWISE_SERVICE: Error pada identifikasi awal: {e}")
        return None

    # 2. Ambil detail diagnosis menggunakan access_token
    try:
        details_url = f"{IDENTIFICATION_ENDPOINT}/{access_token}"
        params = {"details": "common_names,wiki_description,treatment,symptoms"}
        response = requests.get(details_url, headers={"Api-Key": API_KEY}, params=params, timeout=45)
        response.raise_for_status()
        details_result = response.json()
        print(f"KINDWISE_SERVICE: Full details response received: {json.dumps(details_result, indent=2)}")

        # --- PERBAIKAN: Navigasi JSON yang lebih aman ---
        result_data = details_result.get("result")
        if not result_data:
            print("KINDWISE_SERVICE: 'result' key not found in API response.")
            return None

        disease_data = result_data.get("disease")
        if not disease_data:
            print("KINDWISE_SERVICE: 'disease' key not found in API response. Kemungkinan tanaman sehat atau tidak teridentifikasi.")
            # Anda bisa mengembalikan status 'sehat' jika ini yang diharapkan
            return None

        suggestions = disease_data.get("suggestions")
        if not suggestions or not isinstance(suggestions, list) or len(suggestions) == 0:
            print("KINDWISE_SERVICE: 'suggestions' list is empty or not found.")
            return None

        top_disease = suggestions[0]
        # Pastikan disease_details adalah dict, bahkan jika 'details' tidak ada
        disease_details = top_disease.get("details", {}) if top_disease else {}

        # --- Akhir Perbaikan Navigasi JSON ---

        # Logika pemrosesan yang lebih aman
        symptoms_data = disease_details.get("symptoms") if disease_details else None
        symptoms_str = "Tidak ada gejala spesifik yang tercantum."
        if isinstance(symptoms_data, dict):
            symptoms_str = ". ".join(symptoms_data.values())
        elif isinstance(symptoms_data, list):
            symptoms_str = ", ".join(symptoms_data)

        common_names_data = disease_details.get("common_names", []) if disease_details else []
        common_names_str = ", ".join(common_names_data) if isinstance(common_names_data, list) else "Tidak ada nama umum."

        # Format hasil menjadi dictionary yang bersih dan mudah digunakan
        diagnosis = {
            "name": top_disease.get("name", "Tidak diketahui"),
            "probability": top_disease.get("probability", 0),
            "common_names": common_names_str,
            "symptoms": symptoms_str,
            "description": disease_details.get("wiki_description", {}).get("value", "Tidak ada deskripsi.") if disease_details else "Tidak ada deskripsi.",
            "treatment": _get_structured_treatment(disease_details.get("treatment")) if disease_details else "Tidak ada rekomendasi."
        }
        
        print(f"KINDWISE_SERVICE: Diagnosis berhasil didapatkan -> {diagnosis['name']}")
        return diagnosis

    except Exception as e:
        print(f"KINDWISE_SERVICE: Error saat mengambil detail diagnosis: {e}")
        return None
