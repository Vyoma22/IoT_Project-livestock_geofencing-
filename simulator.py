import os
import json
import time
import random
import threading
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

# Load variables from .env
load_dotenv()

# --- MQTT BROKER CONFIGURATION ---
BROKER = os.getenv("MQTT_BROKER", "localhost")
PORT = int(os.getenv("MQTT_PORT", 1883))
USER = os.getenv("MQTT_USER", "farm_admin")
PASSWORD = os.getenv("MQTT_PASS")

if not PASSWORD:
    raise ValueError("❌ Error: MQTT_PASS is missing from .env file!")

# Simulating 5 livestock collars around a base farm location
COLLARS = [f"cow_{i:02d}" for i in range(1, 6)]
BASE_LAT = 43.9454
BASE_LON = -78.8968


def on_connect(client, userdata, flags, rc, properties=None):
    collar_id = userdata["collar_id"]
    if rc == 0:
        print(f"[{collar_id}] Connected to MQTT Broker successfully.")
        cue_topic = f"livestock/collars/{collar_id}/cue_command"
        client.subscribe(cue_topic, qos=1)
    else:
        print(f"[{collar_id}] Connection failed with code {rc}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"⚠️ [{userdata['collar_id']}] RECEIVED CUE COMMAND: {payload}")
    except Exception as e:
        print(f"Error parsing message: {e}")


def run_collar_simulator(collar_id):
    lat = BASE_LAT + random.uniform(-0.002, 0.002)
    lon = BASE_LON + random.uniform(-0.002, 0.002)
    battery = round(random.uniform(85.0, 100.0), 1)

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=collar_id,
        userdata={"collar_id": collar_id}
    )
    client.username_pw_set(USER, PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_start()
    except Exception as e:
        print(f"[{collar_id}] Failed to connect to broker: {e}")
        return

    topic = f"livestock/collars/{collar_id}/telemetry"

    while True:
        now = time.time()
        lat += random.uniform(-0.0001, 0.0001)
        lon += random.uniform(-0.0001, 0.0001)
        speed = round(random.uniform(0.1, 2.5), 2)
        battery = max(0.0, round(battery - 0.001, 3))

        payload = {
            "collar_id": collar_id,
            "timestamp": now,
            "timestamp_str": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)),
            "latitude": lat,
            "longitude": lon,
            "speed": speed,
            "battery_level": int(battery)
        }

        client.publish(topic, json.dumps(payload), qos=1)
        print(f"[{collar_id}] Published telemetry -> Lat: {lat:.5f}, Lon: {lon:.5f}, Speed: {speed} m/s")

        time.sleep(1)


if __name__ == "__main__":
    print("Starting Multi-Threaded Livestock Telemetry Simulator...")
    threads = []
    for collar in COLLARS:
        t = threading.Thread(target=run_collar_simulator, args=(collar,))
        t.daemon = True
        t.start()
        threads.append(t)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping simulator.")