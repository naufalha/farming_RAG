# app/services/inspection_service.py
# --- Versi dengan Kontrol Robot Jarak Jauh ---

import os
import time
from flask import current_app

# --- PERUBAHAN: Import layanan baru dan hapus yang tidak perlu ---
from . import (
    robot_service, 
    yolo_service, 
    kindwise_service, 
    sql_database_service, 
    notification_service,
    rag_service,
    remote_control_service # <-- Layanan baru untuk kontrol
)

def run_daily_check(app_context, plant_ids_to_check: list[int] = [1]):
    """Orkestrator utama yang sekarang mengontrol siklus hidup robot."""
   
    # --- LANGKAH AWAL: HIDUPKAN ROBOT ---

    print("INSPECTION_SERVICE: Menunggu 120 detik untuk Raspberry Pi boot up...")
    remote_control_service.reboot_raspi_via_mqtt()
    time.sleep(120)

    # --- PROSES INSPEKSI (Logika Inti) ---
    print(f"INSPECTION_SERVICE: Memulai inspeksi harian untuk tanaman ID: {plant_ids_to_check}...")
    unhealthy_plants = []
    healthy_plants_images = []

    for plant_id in plant_ids_to_check:
        print(f"\n--- Memeriksa Tanaman ID: {plant_id} ---")
        
        # Menggunakan konteks aplikasi untuk layanan robot
        image_result = robot_service.get_latest_plant_image(plant_id, app_context)
        
        if not image_result:
            print(f"INSPECTION_SERVICE: Gagal mengambil gambar untuk tanaman {plant_id}.")
            continue
        
        local_path, _ = image_result
        
        # (Sisa logika analisis gambar dan penyimpanan ke DB tidak berubah)
        condition = yolo_service.classify_image(local_path)
        # ...
        sql_database_service.insert_plant_condition(...)
        # ...
        time.sleep(15)

    # --- PEMBUATAN LAPORAN (Logika Inti) ---
    greenhouse_summary = rag_service.get_greenhouse_summary_for_report(app_context)
    weather_forecast = weather_service.get_daily_forecast_as_text() # Asumsi weather_service ada
    # (Sisa logika pembuatan laporan tidak berubah)
    # ...
    
    # Kirim notifikasi
    notification_service.send_report(final_report_message, image_to_send)
    print("INSPECTION_SERVICE: Inspeksi harian dan pengiriman laporan selesai.")
    sleep(10)
    remote_control_service.return_robot_to_home()
    #sleep(600)
    # --- LANGKAH AKHIR: MATIKAN ROBOT ---
    #remote_control_service.shutdown_raspi_via_ssh()

