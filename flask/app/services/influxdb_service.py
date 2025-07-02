# app/services/influxdb_service.py
# --- Layanan untuk Mengelola InfluxDB v2 ---

import os
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

# --- Konfigurasi InfluxDB v2 (diambil dari .env) ---
INFLUX_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUX_ORG = os.getenv("INFLUXDB_ORG")
INFLUX_BUCKET = os.getenv("INFLUXDB_BUCKET", "smart_farm_data")

client = None
write_api = None

def initialize_influxdb():
    """Menginisialisasi koneksi ke klien InfluxDB v2."""
    global client, write_api
    if not all([INFLUX_TOKEN, INFLUX_ORG, INFLUX_URL]):
        print("INFLUX_SERVICE: Peringatan - Konfigurasi InfluxDB tidak lengkap di .env. Layanan tidak akan berjalan.")
        return False
    
    try:
        client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        write_api = client.write_api(write_options=SYNCHRONOUS)
        print("INFLUX_SERVICE: Koneksi ke InfluxDB v2 berhasil.")
        return True
    except Exception as e:
        print(f"INFLUX_SERVICE: Gagal terhubung ke InfluxDB: {e}")
        return False

def _write_point(point):
    """Fungsi internal untuk menulis satu data point ke InfluxDB."""
    if not write_api:
        print("INFLUX_SERVICE: Write API tidak diinisialisasi. Melewatkan penyimpanan.")
        return
    try:
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        # --- PERBAIKAN: Menggunakan atribut internal '_name' untuk mendapatkan nama measurement ---
        print(f"INFLUX_SERVICE: Data untuk '{point._name}' berhasil disimpan.")
    except Exception as e:
        print(f"INFLUX_SERVICE: Gagal menyimpan data ke InfluxDB: {e}")

def insert_ph_log(data: dict):
    """Menyimpan data log pH ke measurement 'ph_logs'."""
    ph_value = data.get("comp_ph") or data.get("ph")
    if ph_value is None: return

    point = Point("ph_logs") \
        .tag("location", "greenhouse_1") \
        .field("value", float(ph_value)) \
        .field("temperature", float(data.get("temp", 0.0)))
    _write_point(point)

def insert_tds_log(data: dict):
    """Menyimpan data log TDS ke measurement 'tds_logs'."""
    tds_value = data.get("comp_tds") or data.get("tds")
    if tds_value is None: return
        
    point = Point("tds_logs") \
        .tag("location", "greenhouse_1") \
        .field("value", float(tds_value)) \
        .field("temperature", float(data.get("temp", 0.0)))
    _write_point(point)

def insert_dht_log(data: dict):
    """Menyimpan data log DHT22 ke measurement 'dht_logs'."""
    temp_val = data.get("temperature")
    humidity_val = data.get("humidity")
    if temp_val is None or humidity_val is None: return

    point = Point("dht_logs") \
        .tag("location", "greenhouse_1") \
        .field("air_temperature", float(temp_val)) \
        .field("air_humidity", float(humidity_val))
    _write_point(point)

def insert_plant_condition_log(plant_id: int, condition: str, diagnosis: str = None, image_url: str = None):
    """Menyimpan data kondisi tanaman ke measurement 'plant_conditions'."""
    point = Point("plant_conditions") \
        .tag("plant_id", str(plant_id)) \
        .tag("condition", condition) \
        .field("diagnosis", diagnosis or "N/A") \
        .field("image_url", image_url or "N/A")
    _write_point(point)
