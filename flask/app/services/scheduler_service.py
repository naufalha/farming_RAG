# app/services/scheduler_service.py
# --- Versi Final dengan Penanganan Konteks dan Argumen yang Benar ---

import schedule
import time
import threading

# Import semua layanan yang dibutuhkan oleh penjadwal
from . import (
    weather_service, 
    inspection_service, 
    vector_store_service,
    remote_control_service
)

def daily_weather_job(db_collection):
    """Tugas harian untuk mengambil data cuaca dan menyimpannya ke Vector DB."""
    print("SCHEDULER: Menjalankan tugas harian untuk data cuaca...")
    try:
        forecast_text = weather_service.get_daily_forecast_as_text()
        if forecast_text:
            vector_store_service.add_text_to_db(forecast_text, db_collection)
            print("SCHEDULER: Data cuaca berhasil diambil dan disimpan.")
    except Exception as e:
        print(f"SCHEDULER: Gagal menjalankan tugas cuaca harian: {e}")

def morning_inspection_job(app_context):
    """Tugas untuk menjalankan inspeksi pagi."""
    print("SCHEDULER: Memulai tugas inspeksi PAGI...")
    try:
        # Menggunakan 'with' untuk memastikan konteks aplikasi ditangani dengan benar
        with app_context.app_context():
            inspection_service.run_daily_check(app_context)
    except Exception as e:
        print(f"SCHEDULER: Gagal menjalankan tugas inspeksi pagi: {e}")

def afternoon_inspection_job(app_context):
    """Tugas untuk menjalankan inspeksi sore."""
    print("SCHEDULER: Memulai tugas inspeksi SORE...")
    try:
        with app_context.app_context():
            inspection_service.run_daily_check(app_context)
    except Exception as e:
        print(f"SCHEDULER: Gagal menjalankan tugas inspeksi sore: {e}")
        
def reboot_robot_job():
    """Tugas untuk me-reboot Raspberry Pi sebagai persiapan inspeksi."""
    print("SCHEDULER: Menjalankan tugas reboot untuk Raspberry Pi...")
    try:
        remote_control_service.reboot_raspi_via_mqtt()
    except Exception as e:
        print(f"SCHEDULER: Gagal menjalankan tugas reboot: {e}")

def run_scheduler(app_context, db_collection):
    """Loop utama untuk penjadwal."""
    print("SCHEDULER: Penjadwal aktif, menunggu waktu tugas...")
    
    # --- JADWAL TUGAS ---
    schedule.every().day.at("05:37", "Asia/Jakarta").do(daily_weather_job, db_collection=db_collection)
    
    # Jadwal untuk menyalakan robot sebelum inspeksi
    #schedule.every().day.at("05:40", "Asia/Jakarta").do(reboot_robot_job) # Persiapan inspeksi pagi
    #schedule.every().day.at("16:05", "Asia/Jakarta").do(reboot_robot_job) # Persiapan inspeksi sore
    
    # Jadwal untuk menjalankan inspeksi
    schedule.every().day.at("06:00", "Asia/Jakarta").do(morning_inspection_job, app_context=app_context)
    schedule.every().day.at("16:10", "Asia/Jakarta").do(afternoon_inspection_job, app_context=app_context)
    
    # --- PERBAIKAN: Memanggil tugas startup dengan argumen yang benar ---
    # Anda bisa menghapus komentar di bawah ini jika ingin tugas langsung berjalan
    # saat server pertama kali dinyalakan.
    print("SCHEDULER: Menjalankan tugas awal saat startup...")
    # daily_weather_job(db_collection)
    #afternoon_inspection_job(app_context)
    # morning_inspection_job(app_context) # Hanya perlu satu argumen

    while True:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler(app, db_collection):
    """Memulai thread penjadwal dengan membawa konteks aplikasi dan koleksi DB."""
    scheduler_thread = threading.Thread(target=run_scheduler, args=(app, db_collection,), daemon=True)
    scheduler_thread.start()
    print("SCHEDULER: Layanan penjadwal berhasil dimulai.")

