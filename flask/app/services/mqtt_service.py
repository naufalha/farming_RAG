# app/services/mqtt_service.py
# --- Versi dengan Logika Stabilisasi untuk Pencatatan Data ---

import paho.mqtt.client as mqtt
import json
import time
import os
import threading
from datetime import datetime

from . import sql_database_service

# (Konfigurasi MQTT tetap sama)
MQTT_SERVER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_CLIENT_ID_BASE = os.getenv("MQTT_CLIENT_ID", "smart-farm-server")
TOPIC_DATA = "sensor/data"
TOPIC_COMMAND = "sensor/command"

# --- PERUBAHAN: State untuk menyimpan pembacaan terakhir ---
# Dictionary ini akan menyimpan data terakhir yang diterima untuk setiap sensor
# sebelum disimpan ke database.
latest_readings = {
    "ph": None,
    "tds": None
}

def on_connect(client, userdata, flags, rc, properties=None):
    """Callback yang dipanggil saat berhasil terhubung ke broker."""
    if rc == 0:
        client_id = client._client_id.decode()
        print(f"MQTT: Berhasil terhubung ke Broker dengan Client ID: {client_id}")
        client.subscribe(TOPIC_DATA)
        print(f"MQTT: Berlangganan topik '{TOPIC_DATA}'")
    else:
        print(f"MQTT: Gagal terhubung, kode error: {rc}")

def on_message(client, userdata, msg):
    """
    Callback ini sekarang hanya bertugas untuk memperbarui pembacaan terakhir
    di memori, bukan langsung menyimpan ke database.
    """
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        sensor_type = data.get("type")

        if sensor_type in latest_readings:
            # Perbarui dictionary dengan data terbaru yang masuk
            latest_readings[sensor_type] = data
            print(f"MQTT: Data diterima dan disimpan sementara -> {payload_str}")

    except Exception as e:
        print(f"MQTT: Error saat memproses pesan: {e}")

def command_publisher_thread(client):
    """
    Thread ini sekarang mengorkestrasi seluruh alur:
    1. Kirim perintah.
    2. Tunggu 60 detik untuk stabilisasi.
    3. Ambil data terakhir yang disimpan oleh on_message.
    4. Simpan data tersebut ke SQL.
    """
    while True:
        try:
            # --- Siklus Pengukuran TDS ---
            print("ORCHESTRATOR: Meminta pengukuran TDS...")
            client.publish(TOPIC_COMMAND, "MEASURE_TDS")
            print("ORCHESTRATOR: Menunggu stabilisasi TDS selama 60 detik...")
            time.sleep(60)
            
            # Ambil data TDS terakhir setelah menunggu
            final_tds_reading = latest_readings.get("tds")
            if final_tds_reading:
                sql_database_service.insert_sensor_log(final_tds_reading)
                latest_readings["tds"] = None # Bersihkan setelah disimpan
            else:
                print("ORCHESTRATOR: Peringatan - Tidak ada data TDS yang diterima dalam 60 detik.")

            # --- Siklus Pengukuran pH ---
            print("ORCHESTRATOR: Meminta pengukuran pH...")
            client.publish(TOPIC_COMMAND, "MEASURE_PH")
            print("ORCHESTRATOR: Menunggu stabilisasi pH selama 60 detik...")
            time.sleep(60)

            # Ambil data pH terakhir setelah menunggu
            final_ph_reading = latest_readings.get("ph")
            if final_ph_reading:
                sql_database_service.insert_sensor_log(final_ph_reading)
                latest_readings["ph"] = None # Bersihkan setelah disimpan
            else:
                print("ORCHESTRATOR: Peringatan - Tidak ada data pH yang diterima dalam 60 detik.")

        except Exception as e:
            print(f"ORCHESTRATOR: Error di thread utama: {e}")
            time.sleep(10)

def start_mqtt_client():
    """Memulai koneksi MQTT client."""
    sql_database_service.initialize_database()
    
    if not all([MQTT_SERVER, MQTT_USERNAME, MQTT_PASSWORD]):
        print("MQTT: Konfigurasi tidak ditemukan di .env. Layanan MQTT tidak akan dimulai.")
        return

    is_debug_mode = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
    client_id = f"{MQTT_CLIENT_ID_BASE}-{int(time.time())}" if is_debug_mode else MQTT_CLIENT_ID_BASE
    
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message
    
    client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS)
    
    try:
        client.connect(MQTT_SERVER, int(MQTT_PORT), 60)
    except Exception as e:
        print(f"MQTT: Tidak dapat terhubung ke Broker: {e}")
        return

    client.loop_start()

    publisher = threading.Thread(target=command_publisher_thread, args=(client,), daemon=True)
    publisher.start()
