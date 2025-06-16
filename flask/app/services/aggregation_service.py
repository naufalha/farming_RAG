# app/services/aggregation_service.py
# --- Layanan untuk Agregasi Data Log Sensor ---

import sqlite3
import pandas as pd
from . import sql_database_service, vector_store_service
from datetime import datetime, timedelta

def create_and_store_log_summary(db_collection, hours: int = 4):
    """
    Menghitung agregasi data (min, max, avg, median) dari log sensor
    selama periode waktu tertentu dan menyimpannya ke Vector DB.
    """
    print(f"AGGREGATION_SERVICE: Memulai pembuatan ringkasan data untuk {hours} jam terakhir...")
    
    try:
        conn = sqlite3.connect(sql_database_service.DB_PATH)
        
        # Ambil data dari periode waktu yang ditentukan
        time_threshold = datetime.now() - timedelta(hours=hours)
        query = f"SELECT sensor_type, value FROM sensor_logs WHERE timestamp >= '{time_threshold}'"
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty:
            print("AGGREGATION_SERVICE: Tidak ada data sensor dalam periode waktu yang ditentukan. Melewatkan pembuatan ringkasan.")
            return

        summary_texts = []
        for sensor_type in ['ph', 'tds']:
            # Filter data untuk setiap tipe sensor
            sensor_df = df[df['sensor_type'] == sensor_type]
            if not sensor_df.empty:
                # Hitung statistik
                max_val = sensor_df['value'].max()
                min_val = sensor_df['value'].min()
                avg_val = sensor_df['value'].mean()
                median_val = sensor_df['value'].median()
                
                # Format menjadi kalimat deskriptif
                summary = (
                    f"Ringkasan data {sensor_type.upper()} selama {hours} jam terakhir: "
                    f"Nilai tertinggi adalah {max_val:.2f}, "
                    f"terendah {min_val:.2f}, "
                    f"rata-rata {avg_val:.2f}, "
                    f"dan nilai tengah (median) adalah {median_val:.2f}."
                )
                summary_texts.append(summary)
        
        # Simpan setiap kalimat ringkasan ke Vector DB
        for text in summary_texts:
            vector_store_service.add_text_to_db(text, db_collection)
            print(f"AGGREGATION_SERVICE: Ringkasan disimpan ke Vector DB -> '{text}'")

    except Exception as e:
        print(f"AGGREGATION_SERVICE: Gagal membuat ringkasan: {e}")

