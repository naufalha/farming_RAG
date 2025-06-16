# generate_data.py
# --- Skrip untuk Menghasilkan Data Sintetis untuk Pengujian ---

import sqlite3
import random
from datetime import datetime, timedelta
import os

# Pastikan kita menggunakan path database yang sama dengan aplikasi utama
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'db', 'farm_data.db'))

def initialize_database():
    """Membuat tabel-tabel jika belum ada (duplikat dari sql_database_service)."""
    print("Memastikan database dan tabel ada...")
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS environment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME NOT NULL,
            ph REAL, tds REAL, water_temperature REAL,
            air_temperature REAL, air_humidity REAL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plant_conditions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp DATETIME NOT NULL,
            plant_id INTEGER NOT NULL, condition TEXT NOT NULL, diagnosis TEXT
        )
    ''')
    conn.commit()
    conn.close()

def generate_environment_logs(days=3, records_per_hour=4):
    """Menghasilkan data log lingkungan untuk beberapa hari terakhir."""
    print(f"Menghasilkan data log lingkungan untuk {days} hari terakhir...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for day in range(days, -1, -1): # Loop dari 3 hari yang lalu hingga hari ini
        for hour in range(24):
            for _ in range(records_per_hour):
                timestamp = datetime.now() - timedelta(days=day, hours=hour, minutes=random.randint(0, 59))
                
                # Menghasilkan nilai yang masuk akal
                ph = round(random.uniform(6.5, 7.5), 2)
                tds = round(random.uniform(900, 1100), 2)
                water_temp = round(random.uniform(24.0, 26.0), 2)
                air_temp = round(random.uniform(25.0, 30.0), 2)
                air_humidity = round(random.uniform(60.0, 85.0), 2)
                
                cursor.execute('''
                    INSERT INTO environment_logs (timestamp, ph, tds, water_temperature, air_temperature, air_humidity)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (timestamp, ph, tds, water_temp, air_temp, air_humidity))

    conn.commit()
    conn.close()
    print("Data log lingkungan berhasil dibuat.")

def generate_plant_conditions(days=3):
    """Menghasilkan data kondisi tanaman untuk 16 tanaman."""
    print("Menghasilkan data kondisi tanaman...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    conditions = ["sehat", "tidak sehat", "siap panen", "belum siap panen"]
    sample_diagnoses = [
        "Terdeteksi gejala awal jamur embun tepung. Rekomendasi: tingkatkan sirkulasi udara.",
        "Kekurangan nutrisi kalsium, terlihat dari ujung daun yang sedikit menguning.",
        "Serangan kutu daun ringan pada bagian bawah daun."
    ]

    for day in range(days, -1, -1):
        for plant_id in range(1, 17): # Tanaman 1 sampai 16
            timestamp = datetime.now() - timedelta(days=day, hours=random.randint(8, 17))
            
            # 80% kemungkinan sehat, sisanya acak
            if random.random() < 0.8:
                condition = "sehat"
                diagnosis = None
            else:
                condition = random.choice(conditions)
                diagnosis = random.choice(sample_diagnoses) if condition == "tidak sehat" else None
            
            cursor.execute('''
                INSERT INTO plant_conditions (timestamp, plant_id, condition, diagnosis)
                VALUES (?, ?, ?, ?)
            ''', (timestamp, plant_id, condition, diagnosis))

    conn.commit()
    conn.close()
    print("Data kondisi tanaman berhasil dibuat.")

def main():
    """Fungsi utama untuk menjalankan semua generator data."""
    print("--- Memulai Pembuatan Data Sintetis ---")
    
    # Hapus database lama untuk memastikan data bersih
    if os.path.exists(DB_PATH):
        print(f"Menghapus database lama: {DB_PATH}")
        os.remove(DB_PATH)
        
    initialize_database()
    generate_environment_logs()
    generate_plant_conditions()
    
    print("\n--- Pembuatan Data Selesai ---")
    print(f"Database baru telah dibuat di: {DB_PATH}")
    print("Anda sekarang bisa menjalankan 'python run.py' untuk menguji AI Agent.")

if __name__ == "__main__":
    main()
