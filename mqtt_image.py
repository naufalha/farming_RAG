import paho.mqtt.client as mqtt
import base64
import time

broker = "d9718db4653a40878e1ba5ff1c0099eb.s1.eu.hivemq.cloud"
port = 8883
topic = "genz/image-transfer"
username = "naufal"
password = "Amda89600!"

# === MQTT Callbacks ===
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("[✅ CONNECTED] Sender connected successfully")
    else:
        print(f"[❌ ERROR] Sender failed to connect | Reason Code: {reason_code}")

def on_disconnect(client, userdata, reason_code, properties=None):
    print(f"[🔌 DISCONNECTED] Sender disconnected | Reason Code: {reason_code}")

def on_publish(client, userdata, mid):
    print(f"[📤 PUBLISHED] Message ID: {mid}")

# === Image Encode ===
try:
    with open("test.jpg", "rb") as f:
        img_bytes = f.read()
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    print("[📁 IMAGE LOADED] image.jpg loaded and encoded")
except Exception as e:
    print(f"[❌ ERROR] Failed to load image: {e}")
    exit(1)

# === MQTT Setup ===
client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(username, password)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish

try:
    print("[🔌 CONNECTING] Connecting to broker...")
    client.connect(broker, port)
except Exception as e:
    print(f"[❌ ERROR] Failed to connect to broker: {e}")
    exit(1)

client.loop_start()
time.sleep(1)  # Wait for connection
result = client.publish(topic, img_b64)

status = result[0]
if status == 0:
    print(f"[🚀 SENDING] Image published to topic `{topic}`")
else:
    print(f"[❌ ERROR] Failed to send image, status code: {status}")

time.sleep(1)  # Ensure callbacks are triggered
client.loop_stop()
client.disconnect()
