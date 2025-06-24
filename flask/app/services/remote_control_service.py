# app/services/remote_control_service.py
# --- Layanan untuk Mengontrol Perangkat Raspberry Pi ---

import os
import paho.mqtt.client as mqtt
import paramiko
import time
import requests 
import certifi 
import threading # <-- Import library threading

def reboot_raspi_via_mqtt():
    """Mengirim perintah reboot ke Raspberry Pi melalui MQTT dengan koneksi yang andal."""
    print("REMOTE_CONTROL: Mengirim perintah reboot via MQTT...")
    
    publish_event = threading.Event()

    def on_connect(client, userdata, flags, rc, properties=None):
        if rc == 0:
            print("REMOTE_CONTROL (MQTT): Koneksi ke broker berhasil.")
            # Menggunakan QoS 1 untuk pengiriman yang lebih andal
            client.publish(TOPIC_COMMAND, "reboot", qos=1)
        else:
            print(f"REMOTE_CONTROL (MQTT): Gagal terhubung, kode: {rc}")
            publish_event.set() 

    # --- PERBAIKAN: Menyesuaikan definisi fungsi dengan argumen yang benar ---
    def on_publish(client, userdata, mid, reason_code, properties):
        print("REMOTE_CONTROL (MQTT): Perintah 'reboot' berhasil dikirim.")
        publish_event.set() 
        client.disconnect()

    try:
        MQTT_SERVER = os.getenv("MQTT_BROKER")
        MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
        MQTT_USERNAME = os.getenv("MQTT_USERNAME")
        MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
        TOPIC_COMMAND = "raspi/command"

        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"flask-reboot-client-{int(time.time())}")
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        client.tls_set(tls_version=mqtt.ssl.PROTOCOL_TLS, ca_certs=certifi.where())
        
        client.on_connect = on_connect
        client.on_publish = on_publish

        client.connect(MQTT_SERVER, MQTT_PORT, 60)
        client.loop_start()

        # Tunggu hingga 10 detik untuk event on_publish dipicu
        published = publish_event.wait(timeout=10)
        
        client.loop_stop()

        if not published:
            print("REMOTE_CONTROL (MQTT): Peringatan - Proses publish timeout.")
            return False
        
        return True
        
    except Exception as e:
        print(f"REMOTE_CONTROL (MQTT): Gagal mengirim perintah reboot: {e}")
        return False
def shutdown_raspi_via_ssh():
    """Masuk ke Raspberry Pi via SSH dan mengirim perintah shutdown."""
    print("REMOTE_CONTROL: Memulai proses shutdown via SSH...")
    try:
        RASPI_IP = os.getenv("ROBOT_IP")
        RASPI_USER = os.getenv("RASPI_USER")
        RASPI_PASSWORD = os.getenv("RASPI_PASSWORD")

        if not all([RASPI_IP, RASPI_USER, RASPI_PASSWORD]):
            print("REMOTE_CONTROL: Peringatan - Konfigurasi SSH untuk Pi tidak lengkap di .env.")
            return

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print(f"REMOTE_CONTROL: Menghubungkan ke {RASPI_IP}...")
        ssh_client.connect(hostname=RASPI_IP, username=RASPI_USER, password=RASPI_PASSWORD, port=22)
        
        # Menjalankan perintah shutdown.
        shutdown_command = f"echo '{RASPI_PASSWORD}' | sudo -S shutdown now"
        print(f"REMOTE_CONTROL: Menjalankan perintah: {shutdown_command}")
        stdin, stdout, stderr = ssh_client.exec_command(shutdown_command)

        # Tunggu sebentar untuk memastikan perintah terkirim sebelum koneksi terputus
        time.sleep(5)
        
        ssh_client.close()
        print("REMOTE_CONTROL: Perintah shutdown berhasil dikirim. Pi akan mati.")
        
    except Exception as e:
        print(f"REMOTE_CONTROL: Gagal mematikan Pi via SSH: {e}")

# --- FUNGSI BARU UNTUK HOMING ---
def return_robot_to_home():
    """Mengirim perintah homing ke robot platform."""
    print("REMOTE_CONTROL: Mengirim perintah homing ke robot...")
    try:
        ROBOT_IP = os.getenv("ROBOT_IP")
        if not ROBOT_IP:
            print("REMOTE_CONTROL: Peringatan - ROBOT_IP tidak ditemukan di .env.")
            return

        homing_url = f"http://{ROBOT_IP}:5001/api/homing"
        response = requests.post(homing_url, timeout=20)
        response.raise_for_status()
        print("REMOTE_CONTROL: Perintah homing berhasil dikirim.")

    except requests.exceptions.RequestException as e:
        print(f"REMOTE_CONTROL: Gagal mengirim perintah homing: {e}")
