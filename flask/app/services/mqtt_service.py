# app/services/mqtt_service.py
# --- Versi 2: Mendukung berbagai jenis sensor dan menyimpan ke SQL ---

import paho.mqtt.client as mqtt
import json
import time
import os
import threading

from . import sql_database_service

# (Konfigurasi MQTT tetap sama)
MQTT_SERVER = os.getenv("MQTT_BROKER")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_CLIENT_ID_BASE = os.getenv("MQTT_CLIENT_ID", "smart-farm-server")
TOPIC_DATA = "sensor/data"
TOPIC_COMMAND = "sensor/command"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client_id = client._client_id.decode()
        print(f"MQTT: Berhasil terhubung ke Broker dengan Client ID: {client_id}")
        client.subscribe(TOPIC_DATA)
        print(f"MQTT: Berlangganan topik '{TOPIC_DATA}'")
    else:
        print(f"MQTT: Gagal terhubung, kode error: {rc}")

def on_message(client, userdata, msg):
    """Callback yang menangani semua jenis data dari sensor."""
    try:
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        sensor_type = data.get("type")
        
        print(f"MQTT: Pesan diterima [{sensor_type}] -> {payload_str}")

        # Menggunakan satu fungsi untuk menangani semua data lingkungan
        sql_database_service.insert_environment_log(data)

    except Exception as e:
        print(f"MQTT: Error saat memproses pesan: {e}")

def command_publisher_thread(client):
    """Thread untuk meminta data dari semua sensor secara bergantian."""
    while True:
        try:
            print("ORCHESTRATOR: Meminta pengukuran TDS...")
            client.publish(TOPIC_COMMAND, "MEASURE_TDS")
            time.sleep(60)

            print("ORCHESTRATOR: Meminta pengukuran pH...")
            client.publish(TOPIC_COMMAND, "MEASURE_PH")
            time.sleep(60)
            
            # Asumsikan ada perintah untuk sensor DHT22
            print("ORCHESTRATOR: Meminta pengukuran suhu/kelembapan udara...")
            client.publish(TOPIC_COMMAND, "MEASURE_DHT22") 
            time.sleep(60)

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
