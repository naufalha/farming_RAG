# app/services/mqtt_service.py
# --- Versi 4: Menambahkan validasi untuk memastikan data lengkap sebelum disimpan ---

import paho.mqtt.client as mqtt
import json
import time
import os
import threading
from datetime import datetime

from . import sql_database_service

# --- Konfigurasi MQTT (tetap sama) ---
MQTT_SERVER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_CLIENT_ID_BASE = os.getenv("MQTT_CLIENT_ID", "smart-farm-server")
TOPIC_DATA = "sensor/data"
TOPIC_COMMAND = "sensor/command"

# "Ember Penampung" Data untuk Siklus Saat Ini
current_log_data = {}

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
    """Callback ini hanya bertugas untuk mengisi "ember penampung"."""
    global current_log_data
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        sensor_type = data.get("type")
        
        # Menggunakan print yang lebih singkat untuk debugging
        # print(f"MQTT: Menerima data sementara -> {payload_str}")

        if sensor_type == 'ph':
            current_log_data['comp_ph'] = data.get('comp_ph') or data.get('ph')
            current_log_data['water_temp'] = data.get('temp') 
        elif sensor_type == 'tds':
            current_log_data['comp_tds'] = data.get('comp_tds') or data.get('tds')
            # Suhu air bisa diambil dari salah satu sensor, tidak masalah jika tertimpa
            current_log_data['water_temp'] = data.get('temp')
        else: # Asumsikan dari DHT22
            current_log_data['room_temp'] = data.get('temperature')
            current_log_data['humidity'] = data.get('humidity')

    except Exception as e:
        print(f"MQTT: Error saat memproses pesan: {e}")

def command_publisher_thread(client):
    """Orkestrator utama yang meminta data, menunggu, memvalidasi, lalu menyimpan."""
    global current_log_data
    while True:
        try:
            current_log_data = {}
            print("\n--- ORCHESTRATOR: Memulai siklus pengukuran ---")

            # Minta data dari semua sensor
            client.publish(TOPIC_COMMAND, "MEASURE_PH")
            time.sleep(30) # Beri waktu 30 detik untuk pH

            client.publish(TOPIC_COMMAND, "MEASURE_TDS")
            time.sleep(30) # Beri waktu 30 detik untuk TDS
            
            client.publish(TOPIC_COMMAND, "MEASURE_DHT22")
            time.sleep(10) # Beri waktu 10 detik untuk DHT22

            # --- PERBAIKAN UTAMA: Validasi data sebelum menyimpan ---
            # Tentukan kunci apa saja yang wajib ada
            required_keys = ['comp_ph', 'comp_tds', 'water_temp', 'room_temp', 'humidity']
            
            # Cek apakah semua kunci yang dibutuhkan ada di dalam 'ember' kita
            if all(key in current_log_data and current_log_data[key] is not None for key in required_keys):
                print(f"ORCHESTRATOR: Validasi berhasil. Menyimpan data gabungan: {current_log_data}")
                sql_database_service.insert_environment_log(current_log_data)
            else:
                # Jika ada data yang kurang, batalkan penyimpanan
                print(f"ORCHESTRATOR: Peringatan - Data tidak lengkap. Penyimpanan dibatalkan. Data yang terkumpul: {current_log_data}")

        except Exception as e:
            print(f"ORCHESTRATOR: Error di thread utama: {e}")
            time.sleep(10)

def start_mqtt_client():
    """Memulai koneksi MQTT client."""
    sql_database_service.initialize_database()
    
    if not all([MQTT_SERVER, MQTT_USERNAME, MQTT_PASSWORD]):
        print("MQTT: Konfigurasi tidak ditemukan. Layanan MQTT tidak akan dimulai.")
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
