# app/services/mqtt_service.py
# --- Versi 2: Menerima data secara otomatis dan meneruskannya ke InfluxDB ---

import paho.mqtt.client as mqtt
import json
import os
import time
import threading

from . import influxdb_service

# --- Konfigurasi MQTT (tetap sama) ---
MQTT_SERVER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_CLIENT_ID_BASE = os.getenv("MQTT_CLIENT_ID", "smart-farm-server")
TOPIC_DATA = "sensor/data"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client_id = client._client_id.decode()
        print(f"MQTT: Berhasil terhubung ke Broker dengan Client ID: {client_id}")
        client.subscribe(TOPIC_DATA)
        print(f"MQTT: Berlangganan topik '{TOPIC_DATA}'")
    else:
        print(f"MQTT: Gagal terhubung, kode error: {rc}")

def on_message(client, userdata, msg):
    """
    Callback yang menangani semua jenis data dari sensor dan memanggil
    layanan InfluxDB yang sesuai.
    """
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        sensor_type = data.get("type")
        
        print(f"MQTT: Pesan diterima [{sensor_type or 'dht'}] -> {payload_str}")

        # --- Logika Pemilihan Fungsi ---
        if sensor_type == 'ph':
            influxdb_service.insert_ph_log(data)
        elif sensor_type == 'tds':
            influxdb_service.insert_tds_log(data)
        else: # Jika tidak ada 'type', asumsikan itu dari DHT22
            influxdb_service.insert_dht_log(data)

    except Exception as e:
        print(f"MQTT: Error saat memproses pesan: {e}")

def start_mqtt_client():
    """Memulai koneksi MQTT client."""
    # Inisialisasi InfluxDB terlebih dahulu
    if not influxdb_service.initialize_influxdb():
        return # Hentikan jika InfluxDB gagal terhubung

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

    # Jalankan loop di background thread
    client.loop_start()
