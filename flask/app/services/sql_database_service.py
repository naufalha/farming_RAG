# app/services/sql_database_service.py
# --- Versi 2: Mengelola tabel environment dan kondisi tanaman ---

import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'db', 'farm_data.db'))

def initialize_database():
    """Membuat tabel-tabel baru jika belum ada."""
    print("SQL_DB_SERVICE: Menginisialisasi database v2...")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabel untuk log sensor lingkungan
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS environment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            ph REAL,
            tds REAL,
            water_temperature REAL,
            air_temperature REAL,
            air_humidity REAL
        )
    ''')
    
    # Tabel untuk log kondisi tanaman dari robot
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plant_conditions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            plant_id INTEGER NOT NULL,
            condition TEXT NOT NULL,
            diagnosis TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("SQL_DB_SERVICE: Database dan tabel v2 siap digunakan.")

def insert_environment_log(data: dict):
    """Menyimpan data sensor lingkungan ke dalam tabel SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        
        # Menggunakan .get() dengan nilai default None agar aman
        cursor.execute('''
            INSERT INTO environment_logs (
                timestamp, ph, tds, water_temperature, air_temperature, air_humidity
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now(),
            data.get("comp_ph"),
            data.get("comp_tds"),
            data.get("water_temp"),
            data.get("room_temp"),
            data.get("humidity")
        ))
        
        conn.commit()
        conn.close()
        print(f"SQL_DB_SERVICE: Log lingkungan disimpan -> {data}")
    except Exception as e:
        print(f"SQL_DB_SERVICE: Gagal menyimpan log lingkungan: {e}")

def insert_plant_condition(plant_id: int, condition: str, diagnosis: str = None):
    """Menyimpan data kondisi tanaman (untuk digunakan nanti oleh robot)."""
    try:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO plant_conditions (timestamp, plant_id, condition, diagnosis)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now(), plant_id, condition, diagnosis))
        conn.commit()
        conn.close()
        print(f"SQL_DB_SERVICE: Kondisi untuk tanaman ID {plant_id} disimpan.")
    except Exception as e:
        print(f"SQL_DB_SERVICE: Gagal menyimpan kondisi tanaman: {e}")
