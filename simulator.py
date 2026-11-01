import json
import time
import random
import threading
import paho.mqtt.client as mqtt

# --- CONFIGURATION ---
BROKER = "localhost"
PORT = 1883
USER = "farm_admin"
PASSWORD = "iotproject@12345"

# Simulating 5 livestock collars around a base farm location
COLLARS = [f"cow_{i:02d}" for i in range(1, 6)]
BASE_LAT = 43.9454
BASE_LON = -78.8968

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[{userdata['collar_id']}] Connected to MQTT Broker successfully.")
        # Subscribe to receiving cue feedback commands
        cue_topic = f"livestock/collars/{userdata['collar_id']}/cue_command"
        client.subscribe(cue_topic, qos=1)
    else:
        print(f"[{userdata['collar_id']}] Connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        print(f"⚠️ [{userdata['collar_id']}] RECEIVED CUE COMMAND: {payload}")
    except Exception as e:
        print(f"Error parsing message: {e}")

def run_collar_simulator(collar_id):
    # Initialize initial state variables
    lat = BASE_LAT + random.uniform(-0.002, 0.002)
    lon = BASE_LON + random.uniform(-0.002, 0.002)
    battery = round(random.uniform(85.0, 100.0), 1)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=collar_id, userdata={"collar_id": collar_id})
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
        # Simulate slight random movement (1 Hz continuous stream)
        lat += random.uniform(-0.0001, 0.0001)
        lon += random.uniform(-0.0001, 0.0001)
        speed = round(random.uniform(0.1, 2.5), 2)  # m/s
        accel_x = round(random.uniform(-0.5, 0.5), 2)
        accel_y = round(random.uniform(-0.5, 0.5), 2)
        accel_z = round(random.uniform(9.5, 10.1), 2)
        battery = max(0.0, round(battery - 0.001, 3))

        payload = {
            "collar_id": collar_id,
            "timestamp": time.time(),
            "latitude": lat,
            "longitude": lon,
            "speed": speed,
            "accel_x": accel_x,
            "accel_y": accel_y,
            "accel_z": accel_z,
            "battery_level": battery
        }

        # Publish telemetry using QoS 1
        client.publish(topic, json.dumps(payload), qos=1)
        print(f"[{collar_id}] Published telemetry -> Lat: {lat:.5f}, Lon: {lon:.5f}, Speed: {speed} m/s")
        
        time.sleep(1)  # 1 Hz sampling rate

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