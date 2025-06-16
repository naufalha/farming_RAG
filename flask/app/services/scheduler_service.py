# app/services/scheduler_service.py (Diperbarui)

import schedule
import time
import threading
from . import weather_service, sql_database_service, aggregation_service # <-- Import layanan baru

def daily_weather_job():
    """Tugas yang dijalankan sekali sehari untuk menyimpan data cuaca ke SQL."""
    print("SCHEDULER: Menjalankan tugas harian untuk data cuaca...")
    try:
        forecast_dict = weather_service.get_daily_forecast_as_dict()
        if forecast_dict:
            sql_database_service.insert_weather_log(forecast_dict)
    except Exception as e:
        print(f"SCHEDULER: Gagal menjalankan tugas cuaca harian: {e}")

def periodic_log_summary_job(db_collection):
    """Tugas baru untuk membuat ringkasan log secara periodik."""
    print("SCHEDULER: Menjalankan tugas ringkasan log sensor...")
    try:
        aggregation_service.create_and_store_log_summary(db_collection, hours=4)
    except Exception as e:
        print(f"SCHEDULER: Gagal menjalankan tugas ringkasan log: {e}")

def run_scheduler(db_collection):
    """Loop utama untuk penjadwal."""
    # Jalankan tugas sekali saat aplikasi pertama kali dimulai
    daily_weather_job()
    periodic_log_summary_job(db_collection)
    
    # Jadwalkan tugas-tugas
    schedule.every().day.at("02:00", "Asia/Jakarta").do(daily_weather_job)
    schedule.every(4).hours.do(periodic_log_summary_job, db_collection=db_collection)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler(db_collection):
    """Memulai thread penjadwal di background."""
    scheduler_thread = threading.Thread(target=run_scheduler, args=(db_collection,), daemon=True)
    scheduler_thread.start()
    print("SCHEDULER: Layanan penjadwal berhasil dimulai dengan tugas cuaca dan agregasi.")
