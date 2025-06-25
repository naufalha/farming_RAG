# app/services/inspection_service.py
# --- Versi Final dengan Alur Kerja yang Benar dan Lengkap ---

import os
import time
import json
from flask import current_app

# --- PERBAIKAN: Menambahkan weather_service ke dalam import ---
from . import (
    robot_service, 
    yolo_service, 
    kindwise_service, 
    sql_database_service, 
    notification_service,
    rag_service,
    remote_control_service,
    weather_service 
)

def run_daily_check(app_context, plant_ids_to_check: list[int] = [1,2,3,4,5,6,7,8,9,10,11,12,13,14]):
    """
    Orkestrator utama yang menjalankan inspeksi, lalu memarkirkan dan mematikan robot.
    """
    print("INSPECTION_SERVICE: Menunggu 15 detik sebelum memulai inspeksi...")
    time.sleep(15)

    print(f"INSPECTION_SERVICE: Memulai inspeksi harian untuk tanaman ID: {plant_ids_to_check}...")
    unhealthy_plants, healthy_plants_images = [], []

    for plant_id in plant_ids_to_check:
        print(f"\n--- Memeriksa Tanaman ID: {plant_id} ---")
        
        image_result = robot_service.get_latest_plant_image(plant_id, app_context)
        
        if not image_result:
            print(f"INSPECTION_SERVICE: Gagal mengambil gambar untuk tanaman {plant_id}.")
            continue
        
        local_path, _ = image_result
        
        condition = yolo_service.classify_image(local_path)
        diagnosis_text = None

        if condition == "tidak sehat":
            diagnosis_data = kindwise_service.get_plant_diagnosis(local_path)
            if diagnosis_data:
                diagnosis_text = f"Diagnosis: {diagnosis_data.get('name')}"
                unhealthy_plants.append({
                    "id": plant_id, 
                    "diagnosis": diagnosis_text, 
                    "image_path": local_path
                })
        else:
            healthy_plants_images.append(local_path)
            
        sql_database_service.insert_plant_condition(
            plant_id=plant_id, 
            condition=condition,
            diagnosis=diagnosis_text, 
            image_url=local_path
        )
        
        print(f"INSPECTION_SERVICE: Proses untuk tanaman {plant_id} selesai. Jeda...")
        time.sleep(15)

    # --- PEMBUATAN & PENGIRIMAN LAPORAN ---
    greenhouse_summary = rag_service.get_greenhouse_summary_for_report(app_context)
    weather_forecast = weather_service.get_daily_forecast_as_text()
    
    if time.localtime().tm_hour < 12:
        report_header = "🌱 *Laporan Pagi Mubarok Farm* 🌱\n\n"
    else:
        report_header = "🌱 *Laporan Sore Mubarok Farm* 🌱\n\n"
        
    report_body, image_to_send = "", None

    if unhealthy_plants:
        report_body += f"🚨 Ditemukan *{len(unhealthy_plants)} tanaman* terindikasi tidak sehat:\n"
        for plant in unhealthy_plants:
            report_body += f"- *Tanaman #{plant['id']}*: {plant['diagnosis']}\n"
        image_to_send = unhealthy_plants[0]['image_path']
    elif healthy_plants_images:
        report_body += "✅ Inspeksi hari ini menunjukkan semua tanaman dalam kondisi baik.\n"
        image_to_send = healthy_plants_images[0]
    else:
        report_body = "Inspeksi hari ini selesai, namun tidak ada gambar yang berhasil diproses."

    report_footer = (
        f"\n*Analisis Lingkungan Greenhouse:*\n{greenhouse_summary}\n\n"
        f"*Prakiraan Cuaca Hari Ini:*\n{weather_forecast or 'Data tidak tersedia.'}"
    )
    final_report_message = report_header + report_body + report_footer
    
    notification_service.send_report(final_report_message, image_to_send)
    print("INSPECTION_SERVICE: Inspeksi dan pengiriman laporan selesai.")
    
    # --- SIKLUS AKHIR ROBOT ---
    print("INSPECTION_SERVICE: Memulai siklus akhir untuk robot...")
    time.sleep(10)
    remote_control_service.return_robot_to_home()
    
    #print("INSPECTION_SERVICE: Menunggu 1 menit sebelum mematikan Raspberry Pi...")
    #time.sleep(60)
    #remote_control_service.shutdown_raspi_via_ssh()
