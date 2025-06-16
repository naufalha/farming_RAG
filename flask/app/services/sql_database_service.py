# app/services/sql_database_service.py
# --- Layanan untuk Mengelola Database Log Sensor & Cuaca (SQLite) ---

import sqlite3
from datetime import datetime
import os

# --- Konfigurasi Database ---
# Menentukan path absolut untuk database agar konsisten
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'db', 'sensor_data.db'))

def initialize_database():
    """Membuat tabel 'sensor_logs' dan 'weather_logs' jika belum ada."""
    print("SQL_DB_SERVICE: Menginisialisasi database...")
    # Membuat direktori 'db' jika belum ada
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabel untuk log sensor (pH dan TDS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            sensor_type TEXT NOT NULL CHECK(sensor_type IN ('ph', 'tds')),
            value REAL NOT NULL,
            temperature REAL
        )
    ''')
    
    # Tabel untuk log prakiraan cuaca harian
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            temp_max REAL NOT NULL,
            temp_min REAL NOT NULL,
            uv_index REAL NOT NULL,
            precipitation_sum REAL NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()
    print("SQL_DB_SERVICE: Database dan tabel siap digunakan.")

def insert_sensor_log(data: dict):
    """Menyimpan satu data sensor ke dalam tabel SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        sensor_type = data.get("type")
        
        if sensor_type == 'ph':
            value = data.get("comp_ph")
        elif sensor_type == 'tds':
            value = data.get("comp_tds")
        else:
            # Abaikan jika tipe sensor tidak dikenal
            return

        temperature = data.get("temp")

        # Menggunakan parameterized query untuk keamanan
        cursor.execute('''
            INSERT INTO sensor_logs (timestamp, sensor_type, value, temperature)
            VALUES (?, ?, ?, ?)
        ''', (timestamp, sensor_type, value, temperature))
        
        conn.commit()
        conn.close()
        print(f"SQL_DB_SERVICE: Log sensor disimpan -> {sensor_type}={value}")

    except Exception as e:
        print(f"SQL_DB_SERVICE: Gagal menyimpan log sensor: {e}")


def insert_weather_log(data: dict):
    """Menyimpan satu data prakiraan cuaca ke dalam tabel SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Ambil data dari dictionary
        timestamp = data.get("date")
        temp_max = data.get("temperature_2m_max")
        temp_min = data.get("temperature_2m_min")
        uv_index = data.get("uv_index_max")
        precipitation_sum = data.get("precipitation_sum")

        cursor.execute('''
            INSERT INTO weather_logs (timestamp, temp_max, temp_min, uv_index, precipitation_sum)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, temp_max, temp_min, uv_index, precipitation_sum))
        
        conn.commit()
        conn.close()
        print(f"SQL_DB_SERVICE: Log cuaca untuk {timestamp.strftime('%Y-%m-%d')} berhasil disimpan.")
    except Exception as e:
        print(f"SQL_DB_SERVICE: Gagal menyimpan log cuaca: {e}")
